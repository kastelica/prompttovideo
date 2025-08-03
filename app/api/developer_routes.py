from flask import Blueprint, request, jsonify, current_app
from app.models import User, Video, db
from app.auth.rate_limit import rate_limit
from app.auth.utils import verify_token
from app.tasks import generate_video_task
import time
from datetime import datetime
from sqlalchemy import or_, and_

bp = Blueprint('developer', __name__)

@bp.route('/api/v1/generate', methods=['POST'])
@rate_limit()
def generate_video_api():
    """Developer API endpoint for video generation"""
    # Verify API token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = token[7:]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Parse request data
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    prompt = data.get('prompt')
    quality = data.get('quality', 'free')
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    # Validate quality
    valid_qualities = ['free', 'premium', '360p', '1080p']
    if quality not in valid_qualities:
        return jsonify({'error': f'Invalid quality. Must be one of: {", ".join(valid_qualities)}'}), 400
    
    # Calculate credit cost
    credit_cost = 1 if quality == 'free' else 3
    if user.credits < credit_cost:
        return jsonify({
            'error': 'Insufficient credits',
            'required': credit_cost,
            'available': user.credits
        }), 402
    
    # Create video record
    video = Video(
        user_id=user.id,
        prompt=prompt,
        quality=quality
    )
    
    db.session.add(video)
    db.session.commit()
    
    # Generate slug and set priority
    video.slug = video.generate_slug()
    video.update_priority()
    
    db.session.commit()
    
    # Deduct credits
    user.credits -= credit_cost
    user.api_calls_today += 1
    user.last_api_call = datetime.utcnow()
    db.session.commit()
    
    # Queue the video generation task using background thread
    try:
        import threading
        from app import create_app
        import os
        
        # DUPLICATE PREVENTION: Check if video is already being processed
        if video.status == 'processing':
            return jsonify({
                'success': True,
                'video_id': video.id,
                'status': 'processing',
                'message': 'Video is already being processed',
                'credits_remaining': user.credits
            }), 200
        
        if video.veo_job_id:
            return jsonify({
                'success': True,
                'video_id': video.id,
                'status': 'processing',
                'message': 'Video generation already started',
                'credits_remaining': user.credits
            }), 200
        
        def run_video_generation():
            try:
                # Always create a new app context for background thread
                config_name = 'testing' if os.environ.get('FLASK_ENV') == 'testing' else None
                app = create_app(config_name)
                with app.app_context():
                    generate_video_task(video.id)
            except Exception as e:
                print(f"❌ API Background thread error: {e}")
        
        thread = threading.Thread(target=run_video_generation)
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        # If task execution fails, mark as failed and refund credits
        video.status = 'failed'
        user.credits += credit_cost
        db.session.commit()
        return jsonify({'error': 'Failed to start video generation'}), 500
    
    return jsonify({
        'success': True,
        'video_id': video.id,
        'status': 'pending',
        'credits_remaining': user.credits,
        'queue_position': get_queue_position(video.id),
        'estimated_wait_time': estimate_wait_time(video.priority)
    })

@bp.route('/api/v1/video/<int:video_id>/status', methods=['GET'])
@rate_limit()
def video_status_api(video_id):
    """Get video generation status"""
    # Verify API token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = token[7:]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    # Get video
    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    response_data = {
        'video_id': video.id,
        'status': video.status,
        'prompt': video.prompt,
        'quality': video.quality,
        'created_at': video.created_at.isoformat(),
        'updated_at': video.updated_at.isoformat()
    }
    
    if video.status == 'completed':
        response_data.update({
            'video_url': video.gcs_signed_url,
            'duration': video.duration,
            'thumbnail_url': video.thumbnail_url,
            'completed_at': video.completed_at.isoformat() if video.completed_at else None
        })
    elif video.status == 'failed':
        response_data['error'] = 'Video generation failed'
    
    return jsonify(response_data)

@bp.route('/api/v1/videos', methods=['GET'])
@rate_limit()
def list_videos_api():
    """List user's videos"""
    # Verify API token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = token[7:]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Parse query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status')
    
    # Build query
    query = Video.query.filter_by(user_id=user.id)
    if status:
        query = query.filter_by(status=status)
    
    # Paginate results
    videos = query.order_by(Video.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    video_list = []
    for video in videos.items:
        video_data = {
            'id': video.id,
            'prompt': video.prompt,
            'quality': video.quality,
            'status': video.status,
            'created_at': video.created_at.isoformat(),
            'updated_at': video.updated_at.isoformat()
        }
        
        if video.status == 'completed':
            video_data.update({
                'video_url': video.gcs_signed_url,
                'duration': video.duration,
                'thumbnail_url': video.thumbnail_url
            })
        
        video_list.append(video_data)
    
    return jsonify({
        'videos': video_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': videos.total,
            'pages': videos.pages,
            'has_next': videos.has_next,
            'has_prev': videos.has_prev
        }
    })

@bp.route('/api/v1/account', methods=['GET'])
@rate_limit()
def account_info_api():
    """Get user account information"""
    # Verify API token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = token[7:]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.id,
        'email': user.email,
        'credits': user.credits,
        'subscription_tier': user.subscription_tier,
        'rate_limit_info': user.get_rate_limit_info(),
        'created_at': user.created_at.isoformat()
    })

@bp.route('/api/v1/queue/status', methods=['GET'])
@rate_limit()
def queue_status_api():
    """Get queue status for API users"""
    # Verify API token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'error': 'Authorization header required'}), 401
    
    token = token[7:]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get user's pending videos
    pending_videos = Video.query.filter_by(
        user_id=user.id, 
        status='pending'
    ).order_by(Video.priority.desc(), Video.queued_at.asc()).all()
    
    queue_info = []
    for video in pending_videos:
        position = get_queue_position(video.id)
        wait_time = estimate_wait_time(video.priority)
        queue_info.append({
            'video_id': video.id,
            'prompt': video.prompt[:50] + '...' if len(video.prompt) > 50 else video.prompt,
            'quality': video.quality,
            'position': position,
            'estimated_wait_minutes': wait_time,
            'queued_at': video.queued_at.isoformat()
        })
    
    # Get overall queue stats
    total_pending = Video.query.filter_by(status='pending').count()
    processing_count = Video.query.filter_by(status='processing').count()
    
    return jsonify({
        'user_videos': queue_info,
        'queue_stats': {
            'total_pending': total_pending,
            'currently_processing': processing_count,
            'user_pending_count': len(pending_videos)
        }
    })

@bp.route('/api/v1/test-veo-auth', methods=['GET'])
def test_veo_auth():
    """Test endpoint to trigger VEO authentication debugging"""
    try:
        from app.veo_client import VeoClient
        
        # Create VEO client instance
        veo_client = VeoClient()
        
        # Try to get auth token (this will trigger all the debugging)
        token = veo_client._get_auth_token()
        
        if token:
            return jsonify({
                'success': True,
                'message': 'VEO authentication successful',
                'token_preview': f"{token[:20]}..."
            })
        else:
            return jsonify({
                'success': False,
                'message': 'VEO authentication failed',
                'error': 'No token obtained'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'VEO authentication test failed',
            'error': str(e)
        }), 500

# Helper functions
def get_queue_position(video_id):
    """Get position of video in queue"""
    video = Video.query.get(video_id)
    if not video or video.status != 'pending':
        return None
    
    # Count videos with higher priority or same priority but queued earlier
    position = Video.query.filter(
        Video.status == 'pending',
        or_(
            Video.priority > video.priority,
            and_(Video.priority == video.priority, Video.queued_at < video.queued_at)
        )
    ).count()
    
    return position + 1

def estimate_wait_time(priority):
    """Estimate wait time in minutes based on priority"""
    # Simple estimation: higher priority = shorter wait
    base_wait = 30  # Base wait time in minutes
    priority_bonus = priority * 2  # Each priority point reduces wait by 2 minutes
    estimated = max(5, base_wait - priority_bonus)  # Minimum 5 minutes
    return estimated 