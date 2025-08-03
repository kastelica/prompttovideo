from flask import Blueprint, request, jsonify, current_app
from app.models import User, Video, db
from app.auth.rate_limit import rate_limit
from app.auth.utils import verify_token
from app.tasks import generate_video_task
import time

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
    
    if quality not in ['free', 'premium']:
        return jsonify({'error': 'Quality must be free or premium'}), 400
    
    # Check credits
    cost = 1 if quality == '360p' else 3
    if not user.can_generate_video(quality):
        return jsonify({
            'error': 'Insufficient credits',
            'required': cost,
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
    
    # Queue the video generation task
    generate_video_task(video.id)
    
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

# Helper functions
def get_queue_position(video_id):
    """Get position of video in queue"""
    video = Video.query.get(video_id)
    if not video or video.status != 'pending':
        return None
    
    # Count videos with higher priority or same priority but queued earlier
    position = Video.query.filter(
        Video.status == 'pending',
        db.or_(
            Video.priority > video.priority,
            db.and_(Video.priority == video.priority, Video.queued_at < video.queued_at)
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