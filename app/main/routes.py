from flask import render_template, request, jsonify, current_app, g, redirect, url_for
from app.main import bp
from app.models import db, User, Video, PromptPack
from app.auth.utils import login_required, verify_token
from app.auth.rate_limit import rate_limit
import json
import requests
import os
from datetime import datetime

@bp.route('/')
def index():
    """Home page with video generation form"""
    # Get videos that are public, completed, and have GCS URLs (preferred)
    featured_videos = Video.query.join(User).filter(
        Video.public == True,
        Video.status == 'completed',
        Video.gcs_signed_url.isnot(None),
        Video.gcs_signed_url != ''
    ).order_by(Video.views.desc()).limit(9).all()
    
    # If we don't have enough videos with GCS URLs, add some without
    if len(featured_videos) < 6:
        additional_videos = Video.query.join(User).filter(
            Video.public == True,
            Video.status == 'completed',
            Video.gcs_signed_url.is_(None)
        ).order_by(Video.views.desc()).limit(6 - len(featured_videos)).all()
        featured_videos.extend(additional_videos)
    
    # Limit to 9 total videos
    featured_videos = featured_videos[:9]
    
    # Generate signed URLs for thumbnails that don't have them
    from app.gcs_utils import generate_signed_url
    for video in featured_videos:
        if not video.thumbnail_url:
            try:
                # Generate signed URL for thumbnail based on video ID
                thumbnail_gcs_url = f"gs://{current_app.config['GCS_BUCKET_NAME']}/thumbnails/{video.id}.jpg"
                signed_thumbnail_url = generate_signed_url(thumbnail_gcs_url)
                if signed_thumbnail_url:
                    video.thumbnail_url = signed_thumbnail_url
            except Exception as e:
                current_app.logger.warning(f"Failed to generate signed URL for thumbnail {video.id}: {e}")
    
    prompt_packs = PromptPack.query.filter_by(featured=True).limit(3).all()
    
    return render_template('main/index.html', 
                         featured_videos=featured_videos,
                         prompt_packs=prompt_packs)

@bp.route('/prompt-packs')
def prompt_packs():
    """Show all prompt packs"""
    all_packs = PromptPack.query.order_by(PromptPack.featured.desc(), PromptPack.name).all()
    return render_template('main/prompt_packs.html', prompt_packs=all_packs)

@bp.route('/prompt-pack/<int:pack_id>')
def view_prompt_pack(pack_id):
    """View a specific prompt pack"""
    pack = PromptPack.query.get_or_404(pack_id)
    return render_template('main/prompt_pack_detail.html', pack=pack)

@bp.route('/generate', methods=['POST'])
@login_required
def generate_video():
    """Generate a video using Veo API"""
    current_app.logger.info("🎬 ===== BACKEND: VIDEO GENERATION REQUEST STARTED =====")
    current_app.logger.info(f"📋 BACKEND: Request method: {request.method}")
    current_app.logger.info(f"📋 BACKEND: Request headers: {dict(request.headers)}")
    current_app.logger.info(f"📋 BACKEND: Request cookies: {dict(request.cookies)}")
    current_app.logger.info(f"📋 BACKEND: Request data: {request.get_json()}")
    
    try:
        # Get user from token (set by login_required decorator)
        user_id = request.user_id
        current_app.logger.info(f"👤 BACKEND: User ID from token: {user_id}")
        
        # Get request data
        data = request.get_json()
        if not data:
            current_app.logger.error("❌ BACKEND: No JSON data in request")
            return jsonify({'error': 'No data provided'}), 400
        
        prompt = data.get('prompt', '').strip()
        quality = data.get('quality', 'free')
        
        current_app.logger.info(f"📝 BACKEND: Prompt extracted: '{prompt}'")
        current_app.logger.info(f"📝 BACKEND: Quality extracted: {quality}")
        current_app.logger.info(f"📝 BACKEND: Prompt type: {type(prompt)}")
        current_app.logger.info(f"📝 BACKEND: Quality type: {type(quality)}")
        
        if not prompt:
            current_app.logger.error("❌ BACKEND: No prompt provided")
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Validate quality
        valid_qualities = ['free', 'premium', '360p', '1080p']
        if quality not in valid_qualities:
            current_app.logger.error(f"❌ BACKEND: Invalid quality: {quality}")
            return jsonify({'error': f'Invalid quality. Must be one of: {", ".join(valid_qualities)}'}), 400
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            current_app.logger.error(f"❌ BACKEND: User {user_id} not found")
            return jsonify({'error': 'User not found'}), 404
        
        current_app.logger.info(f"👤 BACKEND: User found: {user.email}, Credits: {user.credits}")
        
        # Check rate limits
        if not user.can_make_api_call():
            current_app.logger.error(f"❌ BACKEND: Rate limit exceeded for user {user.email}")
            rate_info = user.get_rate_limit_info()
            return jsonify({
                'error': 'Rate limit exceeded',
                'rate_limit_info': rate_info
            }), 429
        
        current_app.logger.info(f"✅ BACKEND: Rate limit check passed")
        
        # Calculate credit cost
        credit_cost = 1 if quality == 'free' else 3
        current_app.logger.info(f"💰 BACKEND: Credit cost calculated: {credit_cost}")
        
        # Check if user has enough credits
        if user.credits < credit_cost:
            current_app.logger.error(f"❌ BACKEND: Insufficient credits: {user.credits} < {credit_cost}")
            return jsonify({'error': 'Insufficient credits'}), 402
        
        current_app.logger.info(f"✅ BACKEND: Sufficient credits available")
        
        # Deduct credits
        user.credits -= credit_cost
        user.api_calls_today += 1
        user.last_api_call = datetime.utcnow()
        current_app.logger.info(f"💳 BACKEND: Credits deducted: {credit_cost}, New balance: {user.credits}")
        
        # Create video record
        video = Video(
            user_id=user.id,
            prompt=prompt,
            quality=quality
        )
        
        current_app.logger.info(f"🎬 BACKEND: Creating video record: ID={video.id}, Status={video.status}, Slug={video.slug}")
        
        db.session.add(video)
        db.session.commit()
        
        current_app.logger.info(f"✅ BACKEND: Video record committed to database: ID={video.id}")
        
        # Generate slug after commit when ID is available
        video.ensure_slug()
        current_app.logger.info(f"🔗 BACKEND: Video slug: {video.slug}")
        
        # Calculate and set priority
        video.update_priority()
        
        db.session.commit()
        current_app.logger.info(f"✅ BACKEND: Video priority updated and committed")
        
        # Queue the video generation task using background threads
        try:
            import threading
            from app.tasks import generate_video_task
            
            current_app.logger.info("🚀 BACKEND: Starting video generation with background thread")
            
            # Start video generation in background thread
            def run_video_generation():
                try:
                    # Always create a new app context for background thread
                    from app import create_app
                    config_name = 'testing' if os.environ.get('FLASK_ENV') == 'testing' else None
                    app = create_app(config_name)
                    with app.app_context():
                        generate_video_task(video.id)
                except Exception as e:
                    # Use print instead of current_app.logger in background thread
                    print(f"❌ BACKEND: Background thread error: {e}")
            
            thread = threading.Thread(target=run_video_generation)
            thread.daemon = True
            thread.start()
            
            current_app.logger.info(f"✅ BACKEND: Video generation started in background thread")
            
            return jsonify({
                'success': True,
                'video_id': video.id,
                'message': 'Video generation started successfully'
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"❌ BACKEND: Failed to start video generation: {e}")
            # If task execution fails, mark as failed and refund credits
            video.status = 'failed'
            user.add_credits(credit_cost, 'refund')
            db.session.commit()
            current_app.logger.info(f"💳 BACKEND: Credits refunded due to task failure")
            return jsonify({'error': 'Failed to start video generation'}), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Exception in generate_video route: {e}")
        import traceback
        current_app.logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/search')
def search():
    """Search results page"""
    return render_template('main/search.html')

@bp.route('/challenges')
def challenges():
    """Community challenges page"""
    return render_template('main/challenges.html')

@bp.route('/community')
def community():
    """Community page (redirect to challenges for now)"""
    return render_template('main/challenges.html')

@bp.route('/dashboard')
def dashboard():
    """User dashboard showing their videos"""
    # Try to get user from JWT token if available
    user = None
    videos = []
    
    # Check Authorization header first (for API calls)
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token[7:]
        user_id = verify_token(token)
        if user_id:
            user = User.query.get(user_id)
    
    # If no user found from header, check for token in cookies (for web interface)
    if not user:
        token = request.cookies.get('auth_token')
        if token:
            user_id = verify_token(token)
            if user_id:
                user = User.query.get(user_id)
    
    # If user found, get their videos (excluding deleted/failed ones)
    if user:
        videos = Video.query.filter(
            Video.user_id == user.id,
            Video.status.in_(['completed', 'processing', 'pending'])
        ).order_by(Video.created_at.desc()).all()
    
    return render_template('main/dashboard.html', 
                         user=user,
                         videos=videos)

@bp.route('/watch/<int:video_id>-<slug>')
def watch_video(video_id, slug):
    """Public video watch page"""
    video = Video.query.filter_by(id=video_id, slug=slug, public=True, status='completed').first()
    
    if not video:
        return render_template('errors/404.html'), 404
    
    # Increment view count
    video.increment_views()
    db.session.commit()
    
    # Get related videos - try to find videos with similar prompts first, then fall back to most viewed
    related_videos = Video.query.filter(
        Video.public == True,
        Video.status == 'completed',
        Video.id != video.id
    ).order_by(Video.views.desc()).limit(12).all()
    
    # If no related videos found, get any public videos
    if not related_videos:
        related_videos = Video.query.filter(
            Video.public == True,
            Video.status == 'completed'
        ).order_by(Video.created_at.desc()).limit(6).all()
    
    return render_template('main/watch.html', video=video, related_videos=related_videos)

@bp.route('/watch/private/<token>')
def watch_video_private(token):
    """Private video watch page using share token"""
    video = Video.query.filter_by(share_token=token, status='completed').first()
    
    if not video:
        return render_template('errors/404.html'), 404
    
    # Increment view count
    video.increment_views()
    db.session.commit()
    
    # Get related videos - try to find videos with similar prompts first, then fall back to most viewed
    related_videos = Video.query.filter(
        Video.public == True,
        Video.status == 'completed',
        Video.id != video.id
    ).order_by(Video.views.desc()).limit(12).all()
    
    # If no related videos found, get any public videos
    if not related_videos:
        related_videos = Video.query.filter(
            Video.public == True,
            Video.status == 'completed'
        ).order_by(Video.created_at.desc()).limit(6).all()
    
    return render_template('main/watch.html', video=video, related_videos=related_videos)

@bp.route('/watch/<int:video_id>-<slug>/embed')
def watch_video_embed(video_id, slug):
    """Embedded video player"""
    video = Video.query.filter_by(id=video_id, slug=slug, public=True, status='completed').first()
    
    if not video or not video.embed_enabled:
        return render_template('errors/404.html'), 404
    
    return render_template('main/watch_embed.html', video=video)

@bp.route('/watch/private/<token>/embed')
def watch_video_private_embed(token):
    """Embedded video player for private videos"""
    video = Video.query.filter_by(share_token=token, status='completed').first()
    
    if not video or not video.embed_enabled:
        return render_template('errors/404.html'), 404
    
    return render_template('main/watch_embed.html', video=video)

@bp.route('/api/videos/<int:video_id>/status')
def video_status(video_id):
    """Get video generation status"""
    video = Video.query.get_or_404(video_id)
    
    response_data = {
        'id': video.id,
        'status': video.status,
        'prompt': video.prompt,
        'quality': video.quality,
        'created_at': video.created_at.isoformat(),
        'completed_at': video.completed_at.isoformat() if video.completed_at else None
    }
    
    if video.status == 'completed':
        response_data['gcs_url'] = video.gcs_signed_url
        response_data['duration'] = video.duration
        response_data['views'] = video.views
    
    return jsonify(response_data)

@bp.route('/api/videos/<int:video_id>/share', methods=['POST'])
@login_required
def share_video(video_id):
    """Share a video (make public or get share token)"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    if video.status != 'completed':
        return jsonify({'error': 'Video not ready for sharing'}), 400
    
    data = request.get_json() or {}
    share_type = data.get('type', 'public')  # 'public' or 'private'
    
    if share_type == 'public':
        video.public = True
        db.session.commit()
        return jsonify({
            'success': True,
            'share_url': video.get_share_url(),
            'message': 'Video is now public'
        })
    elif share_type == 'private':
        if not video.share_token:
            video.generate_share_token()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'share_url': video.get_share_url(),
            'share_token': video.share_token,
            'message': 'Private share link created'
        })
    else:
        return jsonify({'error': 'Invalid share type'}), 400

@bp.route('/api/videos/<int:video_id>/unshare', methods=['POST'])
@login_required
def unshare_video(video_id):
    """Make a video private"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    video.public = False
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Video is now private'
    })

@bp.route('/api/videos/<int:video_id>/seo', methods=['POST'])
@login_required
def update_video_seo(video_id):
    """Update video SEO data"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    video.set_seo_data(
        title=data.get('title'),
        description=data.get('description'),
        tags=data.get('tags')
    )
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'SEO data updated'
    })

@bp.route('/api/videos/<int:video_id>/edit', methods=['POST'])
@login_required
def edit_video(video_id):
    """Comprehensive video editing endpoint"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update title and description
    if 'title' in data:
        video.title = data['title']
    if 'description' in data:
        video.description = data['description']
    if 'tags' in data:
        video.tags = data['tags'] if isinstance(data['tags'], list) else [data['tags']]
    
    # Update visibility settings
    if 'public' in data:
        video.public = bool(data['public'])
    if 'embed_enabled' in data:
        video.embed_enabled = bool(data['embed_enabled'])
    
    # Generate new slug if title changed significantly
    if 'title' in data and data['title']:
        video.ensure_slug()
    
    video.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Video updated successfully',
        'video': {
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'tags': video.tags,
            'public': video.public,
            'embed_enabled': video.embed_enabled,
            'slug': video.slug,
            'updated_at': video.updated_at.isoformat()
        }
    })

@bp.route('/api/videos/<int:video_id>/analytics')
@login_required
def video_analytics(video_id):
    """Get video analytics for the owner"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # Calculate engagement metrics
    engagement_rate = 0
    if video.views > 0:
        # This would be calculated based on likes, comments, shares, etc.
        # For now, using a simple metric
        engagement_rate = min(100, (video.views / 100) * 10)  # Placeholder calculation
    
    # Get view trends (last 7 days)
    # This would require a separate analytics table, but for now we'll use the total views
    view_trend = {
        'total_views': video.views,
        'daily_views': video.views // 7,  # Placeholder
        'growth_rate': 0  # Placeholder
    }
    
    return jsonify({
        'video_id': video.id,
        'title': video.title,
        'analytics': {
            'views': video.views,
            'engagement_rate': round(engagement_rate, 2),
            'created_at': video.created_at.isoformat(),
            'updated_at': video.updated_at.isoformat(),
            'view_trend': view_trend,
            'quality': video.quality,
            'duration': video.duration,
            'public': video.public,
            'embed_enabled': video.embed_enabled
        }
    })

@bp.route('/api/videos/<int:video_id>', methods=['DELETE'])
@login_required
def delete_video(video_id):
    """Delete a video"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    try:
        # Delete from database
        db.session.delete(video)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Video deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete video'}), 500

@bp.route('/api/videos/<int:video_id>/embed', methods=['POST'])
@login_required
def toggle_embed(video_id):
    """Toggle video embedding"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    video.embed_enabled = not video.embed_enabled
    db.session.commit()
    
    return jsonify({
        'success': True,
        'embed_enabled': video.embed_enabled,
        'message': f"Embedding {'enabled' if video.embed_enabled else 'disabled'}"
    })

def get_queue_position(video_id):
    """Get the position of a video in the queue"""
    video = Video.query.get(video_id)
    if not video or video.status != 'pending':
        return None
    
    # Count videos with higher priority or same priority but queued earlier
    position = Video.query.filter(
        Video.status == 'pending',
        (
            (Video.priority > video.priority) |
            ((Video.priority == video.priority) & (Video.queued_at < video.queued_at))
        )
    ).count()
    
    return position + 1

def estimate_wait_time(priority):
    """Estimate wait time based on priority and current queue"""
    # Get average processing time (in minutes)
    avg_processing_time = 5  # 5 minutes average
    
    # Count pending videos with similar or higher priority
    pending_count = Video.query.filter_by(status='pending').count()
    
    # Estimate based on priority and queue length
    if priority >= 50:  # Enterprise users
        estimated_minutes = max(1, pending_count // 3)  # High priority
    elif priority >= 30:  # Pro users
        estimated_minutes = max(2, pending_count // 2)  # Medium priority
    else:  # Free/Basic users
        estimated_minutes = max(3, pending_count)  # Standard priority
    
    return estimated_minutes

@bp.route('/api/queue/status')
@login_required
@rate_limit()
def queue_status():
    """Get current queue status and user's position"""
    user = User.query.get(request.user_id)
    
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
            'priority': video.priority,
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
        },
        'rate_limit_info': user.get_rate_limit_info()
    })

@bp.route('/api/rate-limits/status')
@login_required
def rate_limit_status():
    """Get user's current rate limit status"""
    user = User.query.get(request.user_id)
    
    return jsonify({
        'rate_limit_info': user.get_rate_limit_info(),
        'subscription_tier': user.subscription_tier
    })

@bp.route('/api/docs')
def api_docs():
    """API documentation page"""
    return render_template('main/api_docs.html')

@bp.route('/videos/<filename>')
def serve_video(filename):
    """Serve video files from the videos directory"""
    import os
    from flask import send_from_directory
    
    # Get the videos directory path
    videos_dir = os.path.join(os.getcwd(), 'videos')
    
    # Check if file exists
    video_path = os.path.join(videos_dir, filename)
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video not found'}), 404
    
    # Serve the video file
    return send_from_directory(videos_dir, filename, mimetype='video/mp4')

@bp.route('/api/ai-suggest', methods=['POST'])
@login_required
def ai_suggest():
    """Get AI-powered prompt suggestions using Gemini"""
    try:
        data = request.get_json()
        if not data or not data.get('prompt'):
            return jsonify({'error': 'Prompt is required'}), 400
        
        user_prompt = data.get('prompt', '').strip()
        
        # Gemini API configuration
        gemini_api_key = current_app.config.get('GEMINI_API_KEY') or "AIzaSyD3g5TYJ1bqmKsfbWuUg9lGLlkSn9BzXag"
        gemini_url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        
        # Create the prompt for Gemini
        system_prompt = f"""
        You are an expert video prompt writer for AI video generation. 
        The user has provided this basic description: "{user_prompt}"
        
        Please provide 3 improved, detailed video prompts that would work well for AI video generation.
        Each prompt should be:
        - More descriptive and specific
        - Include visual details, camera movements, lighting, and atmosphere
        - Optimized for AI video generation
        - 1-2 sentences long
        - Creative and engaging
        
        Return only the 3 prompts, one per line, without numbering or additional text.
        """
        
        # Prepare the request to Gemini
        gemini_data = {
            "contents": [{
                "parts": [{
                    "text": system_prompt
                }]
            }]
        }
        
        # Make request to Gemini API
        response = requests.post(
            f"{gemini_url}?key={gemini_api_key}",
            json=gemini_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code != 200:
            current_app.logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to get AI suggestions'}), 500
        
        # Parse Gemini response
        gemini_response = response.json()
        
        if 'candidates' not in gemini_response or not gemini_response['candidates']:
            return jsonify({'error': 'No suggestions generated'}), 500
        
        # Extract the generated text
        generated_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
        
        # Split into individual suggestions
        suggestions = [s.strip() for s in generated_text.split('\n') if s.strip()]
        
        # Limit to 3 suggestions and clean them up
        suggestions = suggestions[:3]
        
        current_app.logger.info(f"AI suggestions generated for prompt: '{user_prompt}'")
        current_app.logger.info(f"Suggestions: {suggestions}")
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'original_prompt': user_prompt
        })
        
    except requests.exceptions.Timeout:
        current_app.logger.error("Gemini API timeout")
        return jsonify({'error': 'AI suggestion service timed out'}), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Gemini API request error: {e}")
        return jsonify({'error': 'Failed to connect to AI service'}), 503
    except Exception as e:
        current_app.logger.error(f"AI suggestion error: {e}")
        return jsonify({'error': 'Internal server error'}), 500 

@bp.route('/api/ai-suggest-random', methods=['POST'])
@login_required
def ai_suggest_random():
    """Get AI-powered random prompt suggestions using Gemini"""
    try:
        # Gemini API configuration
        gemini_api_key = current_app.config.get('GEMINI_API_KEY') or "AIzaSyD3g5TYJ1bqmKsfbWuUg9lGLlkSn9BzXag"
        gemini_url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        
        # Create a dynamic prompt with randomization
        import random
        import time
        
        # Set a random seed based on current time to ensure different results each time
        random.seed(int(time.time() * 1000) % 1000000)
        
        # Define various themes and styles for randomization
        themes = [
            "nature and wildlife", "urban cityscapes", "sci-fi and space", "fantasy and magic", 
            "underwater worlds", "desert landscapes", "mountain adventures", "ocean scenes",
            "forest environments", "industrial settings", "futuristic technology", "medieval times",
            "modern architecture", "abstract art", "cosmic events", "weather phenomena",
            "cultural celebrations", "sports and action", "peaceful meditation", "chaotic energy"
        ]
        
        styles = [
            "cinematic", "documentary", "artistic", "commercial", "experimental", "vintage",
            "modern", "surreal", "realistic", "cartoon", "anime", "photorealistic"
        ]
        
        camera_movements = [
            "slow panning", "dramatic zoom", "orbiting camera", "dolly shot", "handheld",
            "aerial view", "ground level", "bird's eye view", "dutch angle", "steady cam"
        ]
        
        lighting_styles = [
            "golden hour", "blue hour", "dramatic shadows", "soft diffused", "neon lights",
            "candlelight", "moonlight", "sunset", "sunrise", "stormy", "foggy", "crystal clear"
        ]
        
        time_periods = [
            "ancient times", "medieval era", "1920s", "1950s", "1980s", "present day", 
            "near future", "distant future", "timeless", "alternate reality"
        ]
        
        moods = [
            "peaceful and serene", "dramatic and intense", "mysterious and eerie", 
            "joyful and energetic", "melancholic and reflective", "adventurous and exciting",
            "romantic and dreamy", "chaotic and wild", "elegant and sophisticated", 
            "raw and gritty", "whimsical and playful", "epic and grand"
        ]
        
        # Additional random elements for more variety
        adjectives = [
            "magnificent", "enchanting", "breathtaking", "surreal", "majestic", "ethereal",
            "dramatic", "whimsical", "mysterious", "vibrant", "serene", "dynamic",
            "futuristic", "vintage", "cosmic", "organic", "industrial", "pristine"
        ]
        
        objects = [
            "crystal formations", "floating islands", "neon cityscapes", "ancient ruins",
            "bioluminescent creatures", "steam-powered machines", "cosmic storms",
            "underwater palaces", "floating lanterns", "digital rain", "aurora borealis",
            "desert mirages", "forest spirits", "mechanical dragons", "time portals"
        ]
        
        # Randomly select elements
        selected_themes = random.sample(themes, 3)
        selected_styles = random.sample(styles, 3)
        selected_movements = random.sample(camera_movements, 3)
        selected_lighting = random.sample(lighting_styles, 3)
        selected_periods = random.sample(time_periods, 3)
        selected_moods = random.sample(moods, 3)
        selected_adjectives = random.sample(adjectives, 3)
        selected_objects = random.sample(objects, 3)
        
        # Create the dynamic prompt
        system_prompt = f"""
        You are an expert video prompt writer for AI video generation. 
        
        Generate 3 completely unique and creative video prompts based on these specific parameters:
        
        Prompt 1: Theme: {selected_themes[0]} | Style: {selected_styles[0]} | Camera: {selected_movements[0]} | Lighting: {selected_lighting[0]} | Time: {selected_periods[0]} | Mood: {selected_moods[0]} | Adjective: {selected_adjectives[0]} | Object: {selected_objects[0]}
        
        Prompt 2: Theme: {selected_themes[1]} | Style: {selected_styles[1]} | Camera: {selected_movements[1]} | Lighting: {selected_lighting[1]} | Time: {selected_periods[1]} | Mood: {selected_moods[1]} | Adjective: {selected_adjectives[1]} | Object: {selected_objects[1]}
        
        Prompt 3: Theme: {selected_themes[2]} | Style: {selected_styles[2]} | Camera: {selected_movements[2]} | Lighting: {selected_lighting[2]} | Time: {selected_periods[2]} | Mood: {selected_moods[2]} | Adjective: {selected_adjectives[2]} | Object: {selected_objects[2]}
        
        Each prompt should:
        - Incorporate ALL the specified elements (theme, style, camera, lighting, time period, mood, adjective, object)
        - Be highly descriptive and specific with visual details
        - Be optimized for AI video generation
        - Be 1-2 sentences long
        - Be creative, engaging, and visually appealing
        - Be completely different from each other
        
        Make each prompt unique and interesting - think of prompts that would create amazing, shareable videos.
        
        Return only the 3 prompts, one per line, without numbering or additional text.
        """
        
        # Prepare the request to Gemini
        gemini_data = {
            "contents": [{
                "parts": [{
                    "text": system_prompt
                }]
            }]
        }
        
        # Make request to Gemini API
        response = requests.post(
            f"{gemini_url}?key={gemini_api_key}",
            json=gemini_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code != 200:
            current_app.logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to get AI suggestions'}), 500
        
        # Parse Gemini response
        gemini_response = response.json()
        
        if 'candidates' not in gemini_response or not gemini_response['candidates']:
            return jsonify({'error': 'No suggestions generated'}), 500
        
        # Extract the generated text
        generated_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
        
        # Split into individual suggestions
        suggestions = [s.strip() for s in generated_text.split('\n') if s.strip()]
        
        # Limit to 3 suggestions and clean them up
        suggestions = suggestions[:3]
        
        current_app.logger.info(f"Random AI suggestions generated with parameters:")
        current_app.logger.info(f"Themes: {selected_themes}")
        current_app.logger.info(f"Styles: {selected_styles}")
        current_app.logger.info(f"Camera: {selected_movements}")
        current_app.logger.info(f"Lighting: {selected_lighting}")
        current_app.logger.info(f"Time periods: {selected_periods}")
        current_app.logger.info(f"Moods: {selected_moods}")
        current_app.logger.info(f"Adjectives: {selected_adjectives}")
        current_app.logger.info(f"Objects: {selected_objects}")
        current_app.logger.info(f"Final suggestions: {suggestions}")
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except requests.exceptions.Timeout:
        current_app.logger.error("Gemini API timeout")
        return jsonify({'error': 'AI suggestion service timed out'}), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Gemini API request error: {e}")
        return jsonify({'error': 'Failed to connect to AI service'}), 503
    except Exception as e:
        current_app.logger.error(f"AI suggestion error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/reset-rate-limits')
def reset_rate_limits():
    """Reset rate limits for development"""
    # Allow in both development and production for now
    # if current_app.config.get('FLASK_ENV') != 'development':
    #     return jsonify({'error': 'Rate limit reset only available in development mode'}), 403
    
    try:
        users = User.query.all()
        for user in users:
            user.api_calls_today = 0
            user.last_api_call = None
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Reset rate limits for {len(users)} users'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/update-thumbnail-urls')
def update_thumbnail_urls():
    """Temporary endpoint to update thumbnail URLs to signed URLs"""
    from app.gcs_utils import generate_thumbnail_signed_url
    
    try:
        # Get all videos with thumbnails
        videos = Video.query.filter_by(status='completed', public=True).filter(
            Video.thumbnail_url.isnot(None)
        ).all()
        
        updated_count = 0
        error_count = 0
        
        for video in videos:
            try:
                # Extract thumbnail path from current URL
                if video.thumbnail_url and 'thumbnails/' in video.thumbnail_url:
                    # Extract the thumbnail path (e.g., "thumbnails/51.jpg")
                    thumbnail_path = video.thumbnail_url.split('prompt-veo-videos/')[-1]
                    
                    # Generate new signed URL
                    new_signed_url = generate_thumbnail_signed_url(thumbnail_path)
                    
                    if new_signed_url:
                        # Update the video record
                        video.thumbnail_url = new_signed_url
                        db.session.commit()
                        updated_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                db.session.rollback()
        
        # Get final counts
        videos_with_signed_urls = Video.query.filter_by(status='completed', public=True).filter(
            Video.thumbnail_url.isnot(None),
            Video.thumbnail_url.like('%signature=%')  # Check for signed URLs
        ).count()
        
        return {
            'success': True,
            'message': f'Updated {updated_count} thumbnails to signed URLs',
            'total_videos': len(videos),
            'updated_count': updated_count,
            'error_count': error_count,
            'videos_with_signed_urls': videos_with_signed_urls
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@bp.route('/profile')
@bp.route('/profile/<int:user_id>')
def profile(user_id=None):
    """User profile page"""
    # If no user_id provided, redirect to current user's profile
    if user_id is None:
        # For now, just show a basic profile page
        # In a real implementation, you'd get the current user's ID from session/JWT
        return render_template('main/profile.html', user_id=None)
    
    # Show specific user's profile
    return render_template('main/profile.html', user_id=user_id)


@bp.route('/settings')
def settings():
    """User settings page"""
    return render_template('main/settings.html')

@bp.route('/my-videos')
def my_videos():
    """User's video management page - redirects to profile with videos tab"""
    # Check for auth token in cookie (web interface)
    auth_token = request.cookies.get('auth_token')
    if not auth_token:
        # No token found, redirect to login
        return redirect(url_for('auth.login_page'))
    
    # Verify the token
    user_id = verify_token(auth_token)
    if not user_id:
        # Invalid token, redirect to login
        return redirect(url_for('auth.login_page'))
    
    # Token is valid, redirect to profile with videos tab
    return redirect(url_for('main.profile') + '?tab=videos')

 