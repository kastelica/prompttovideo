from flask import request, jsonify, current_app
from app.api import bp
from app.auth.utils import login_required
from app.models import (db, User, Video, CreditTransaction, ChatMessage, ChatReaction, ChatReply,
                      Tag, VideoTag, CommunityChallenge, ChallengeSubmission, ChallengeVote,
                      UserProfile, UserFollow, Notification)
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
import stripe
import json

def get_user_profile(user):
    """Safely get user profile, handling potential list returns"""
    try:
        current_app.logger.info(f"Getting profile for user {user.id}")
        
        if not hasattr(user, 'profile'):
            current_app.logger.warning(f"User {user.id} has no profile attribute")
            return None
            
        if not user.profile:
            current_app.logger.warning(f"User {user.id} profile is None/empty")
            return None
        
        # Check if profile is returned as a list (relationship issue)
        if isinstance(user.profile, list):
            current_app.logger.warning(f"User {user.id} profile returned as list with {len(user.profile)} items")
            return user.profile[0] if user.profile else None
        
        # Check if it's a single profile object
        current_app.logger.info(f"User {user.id} profile type: {type(user.profile)}")
        return user.profile
        
    except Exception as e:
        current_app.logger.error(f"Error getting profile for user {user.id}: {str(e)}")
        return None

# Initialize Stripe - will be set in app context
stripe.api_key = None

@bp.route('/v1/generate', methods=['POST'])
@login_required
def api_generate_video():
    """API endpoint for video generation"""
    data = request.get_json()
    
    if not data or 'prompt' not in data:
        return jsonify({'error': 'Prompt is required'}), 400
    
    prompt = data['prompt'].strip()
    quality = data.get('quality', 'free')
    
    if not prompt:
        return jsonify({'error': 'Prompt cannot be empty'}), 400
    
    # Validate quality
    valid_qualities = ['free', 'premium', '360p', '1080p']
    if quality not in valid_qualities:
        return jsonify({'error': f'Invalid quality. Must be one of: {", ".join(valid_qualities)}'}), 400
    
    # Check if user has enough credits
    user = User.query.get(request.user_id)
    if not user.can_generate_video(quality):
        return jsonify({'error': 'Insufficient credits'}), 402
    
    # Create video record
    video = Video(
        user_id=user.id,
        prompt=prompt,
        quality=quality
    )
    
    db.session.add(video)
    db.session.commit()
    
    # Queue the video generation task
    # In a real implementation, this would use Celery
    # generate_video_task.delay(video.id)
    # For now, just update status
    video.status = 'pending'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'video_id': video.id,
        'status': 'pending',
        'estimated_time': '2-5 minutes'
    })

@bp.route('/v1/videos/<int:video_id>', methods=['GET'])
@login_required
def api_get_video(video_id):
    """Get video details"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    return jsonify({
        'id': video.id,
        'prompt': video.prompt,
        'quality': video.quality,
        'status': video.status,
        'gcs_url': video.gcs_signed_url if video.status == 'completed' else None,
        'created_at': video.created_at.isoformat(),
        'completed_at': video.completed_at.isoformat() if video.completed_at else None
    })

@bp.route('/videos/<int:video_id>/share', methods=['POST'])
@login_required
def api_share_video(video_id):
    """Share a video (make public or create share link)"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    if video.status != 'completed':
        return jsonify({'error': 'Only completed videos can be shared'}), 400
    
    data = request.get_json()
    share_type = data.get('type', 'public')
    
    try:
        if share_type == 'public':
            video.public = True
            message = 'Video made public successfully'
        elif share_type == 'private':
            # Generate share token for private sharing
            import secrets
            video.share_token = secrets.token_urlsafe(16)
            message = 'Private share link created successfully'
        else:
            return jsonify({'error': 'Invalid share type'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'share_url': video.get_share_url() if video.share_token else None
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error sharing video: {str(e)}")
        return jsonify({'error': 'Failed to share video'}), 500

@bp.route('/videos/<int:video_id>/unshare', methods=['POST'])
@login_required
def api_unshare_video(video_id):
    """Unshare a video (make private)"""
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    try:
        video.public = False
        video.share_token = None  # Remove share token
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Video made private successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unsharing video: {str(e)}")
        return jsonify({'error': 'Failed to unshare video'}), 500

@bp.route('/v1/videos', methods=['GET'])
@login_required
def api_list_videos():
    """List user's videos"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    videos = Video.query.filter_by(user_id=request.user_id)\
        .order_by(Video.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'videos': [{
            'id': video.id,
            'title': video.title,
            'display_title': video.get_display_title(60),
            'prompt': video.prompt,
            'quality': video.quality,
            'status': video.status,
            'created_at': video.created_at.isoformat()
        } for video in videos.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': videos.total,
            'pages': videos.pages
        }
    })

@bp.route('/v1/user/credits', methods=['GET'])
@login_required
def api_get_credits():
    """Get user's credit balance"""
    user = User.query.get(request.user_id)
    
    return jsonify({
        'credits': user.credits,
        'daily_credits_used': user.daily_credits_used
    })

@bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        handle_subscription_created(subscription)
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    return jsonify({'success': True})

def handle_checkout_completed(session):
    """Handle completed checkout session"""
    customer_id = session['customer']
    metadata = session.get('metadata', {})
    
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return
    
    # Add credits based on product
    if 'credit_pack' in metadata:
        credit_amount = int(metadata['credit_pack'])
        user.add_credits(credit_amount, 'purchase')
        db.session.commit()

def handle_subscription_created(subscription):
    """Handle new subscription"""
    customer_id = subscription['customer']
    
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return
    
    # Add monthly credits for subscription
    # This would depend on your subscription tiers
    pass

def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    pass

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    pass


# ===== CHAT API ENDPOINTS =====

@bp.route('/v1/videos/<int:video_id>/chat/messages', methods=['GET'])
@login_required
def api_get_chat_messages(video_id):
    """Get chat messages for a video"""
    # Check if video exists and is accessible
    video = Video.query.filter(
        Video.id == video_id,
        or_(Video.public == True, Video.user_id == request.user_id)
    ).first()
    
    if not video:
        return jsonify({'error': 'Video not found or not accessible'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    
    messages = ChatMessage.query.filter_by(video_id=video_id)\
        .order_by(ChatMessage.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'messages': [message.to_dict() for message in reversed(messages.items)],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': messages.total,
            'pages': messages.pages
        }
    })


@bp.route('/v1/videos/<int:video_id>/chat/messages', methods=['POST'])
@login_required
def api_post_chat_message(video_id):
    """Post a new chat message"""
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Message content is required'}), 400
    
    content = data['content'].strip()
    if not content:
        return jsonify({'error': 'Message content cannot be empty'}), 400
    
    # Check if video exists and is accessible
    video = Video.query.filter(
        Video.id == video_id,
        or_(Video.public == True, Video.user_id == request.user_id)
    ).first()
    
    if not video:
        return jsonify({'error': 'Video not found or not accessible'}), 404
    
    # Create the message
    message = ChatMessage(
        video_id=video_id,
        user_id=request.user_id,
        content=content
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': message.to_dict()
    }), 201


@bp.route('/v1/chat/messages/<int:message_id>', methods=['PUT'])
@login_required
def api_edit_chat_message(message_id):
    """Edit a chat message"""
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Message content is required'}), 400
    
    content = data['content'].strip()
    if not content:
        return jsonify({'error': 'Message content cannot be empty'}), 400
    
    # Check if message exists and user owns it
    message = ChatMessage.query.filter_by(
        id=message_id,
        user_id=request.user_id
    ).first()
    
    if not message:
        return jsonify({'error': 'Message not found or not authorized'}), 404
    
    # Update the message
    message.content = content
    message.edited = True
    message.edited_at = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': message.to_dict()
    })


@bp.route('/v1/chat/messages/<int:message_id>', methods=['DELETE'])
@login_required
def api_delete_chat_message(message_id):
    """Delete a chat message"""
    # Check if message exists and user owns it
    message = ChatMessage.query.filter_by(
        id=message_id,
        user_id=request.user_id
    ).first()
    
    if not message:
        return jsonify({'error': 'Message not found or not authorized'}), 404
    
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/v1/chat/messages/<int:message_id>/reactions', methods=['POST'])
@login_required
def api_toggle_message_reaction(message_id):
    """Toggle a reaction on a message"""
    data = request.get_json()
    
    if not data or 'emoji' not in data:
        return jsonify({'error': 'Emoji is required'}), 400
    
    emoji = data['emoji']
    
    # Check if message exists and is accessible
    message = ChatMessage.query.join(Video).filter(
        ChatMessage.id == message_id,
        or_(Video.public == True, Video.user_id == request.user_id)
    ).first()
    
    if not message:
        return jsonify({'error': 'Message not found or not accessible'}), 404
    
    # Check if reaction already exists
    existing_reaction = ChatReaction.query.filter_by(
        message_id=message_id,
        user_id=request.user_id,
        emoji=emoji
    ).first()
    
    if existing_reaction:
        # Remove the reaction
        db.session.delete(existing_reaction)
        action = 'removed'
    else:
        # Add the reaction
        reaction = ChatReaction(
            message_id=message_id,
            user_id=request.user_id,
            emoji=emoji
        )
        db.session.add(reaction)
        action = 'added'
    
    db.session.commit()
    
    # Return updated reaction counts
    return jsonify({
        'success': True,
        'action': action,
        'reactions': message.get_reaction_counts()
    })


@bp.route('/v1/chat/messages/<int:message_id>/replies', methods=['GET'])
@login_required
def api_get_message_replies(message_id):
    """Get replies for a message"""
    # Check if message exists and is accessible
    message = ChatMessage.query.join(Video).filter(
        ChatMessage.id == message_id,
        or_(Video.public == True, Video.user_id == request.user_id)
    ).first()
    
    if not message:
        return jsonify({'error': 'Message not found or not accessible'}), 404
    
    replies = ChatReply.query.filter_by(message_id=message_id)\
        .order_by(ChatReply.created_at.asc()).all()
    
    return jsonify({
        'replies': [reply.to_dict() for reply in replies]
    })


@bp.route('/v1/chat/messages/<int:message_id>/replies', methods=['POST'])
@login_required
def api_post_message_reply(message_id):
    """Post a reply to a message"""
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Reply content is required'}), 400
    
    content = data['content'].strip()
    if not content:
        return jsonify({'error': 'Reply content cannot be empty'}), 400
    
    # Check if message exists and is accessible
    message = ChatMessage.query.join(Video).filter(
        ChatMessage.id == message_id,
        or_(Video.public == True, Video.user_id == request.user_id)
    ).first()
    
    if not message:
        return jsonify({'error': 'Message not found or not accessible'}), 404
    
    # Create the reply
    reply = ChatReply(
        message_id=message_id,
        user_id=request.user_id,
        content=content
    )
    
    db.session.add(reply)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'reply': reply.to_dict()
    }), 201


@bp.route('/v1/chat/replies/<int:reply_id>', methods=['PUT'])
@login_required
def api_edit_chat_reply(reply_id):
    """Edit a chat reply"""
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Reply content is required'}), 400
    
    content = data['content'].strip()
    if not content:
        return jsonify({'error': 'Reply content cannot be empty'}), 400
    
    # Check if reply exists and user owns it
    reply = ChatReply.query.filter_by(
        id=reply_id,
        user_id=request.user_id
    ).first()
    
    if not reply:
        return jsonify({'error': 'Reply not found or not authorized'}), 404
    
    # Update the reply
    reply.content = content
    reply.edited = True
    reply.edited_at = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'reply': reply.to_dict()
    })


@bp.route('/v1/chat/replies/<int:reply_id>', methods=['DELETE'])
@login_required
def api_delete_chat_reply(reply_id):
    """Delete a chat reply"""
    # Check if reply exists and user owns it
    reply = ChatReply.query.filter_by(
        id=reply_id,
        user_id=request.user_id
    ).first()
    
    if not reply:
        return jsonify({'error': 'Reply not found or not authorized'}), 404
    
    db.session.delete(reply)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/v1/chat/replies/<int:reply_id>/reactions', methods=['POST'])
@login_required
def api_toggle_reply_reaction(reply_id):
    """Toggle a reaction on a reply"""
    data = request.get_json()
    
    if not data or 'emoji' not in data:
        return jsonify({'error': 'Emoji is required'}), 400
    
    emoji = data['emoji']
    
    # Check if reply exists and is accessible
    reply = ChatReply.query.join(ChatMessage).join(Video).filter(
        ChatReply.id == reply_id,
        or_(Video.public == True, Video.user_id == request.user_id)
    ).first()
    
    if not reply:
        return jsonify({'error': 'Reply not found or not accessible'}), 404
    
    # Check if reaction already exists
    existing_reaction = ChatReaction.query.filter_by(
        reply_id=reply_id,
        user_id=request.user_id,
        emoji=emoji
    ).first()
    
    if existing_reaction:
        # Remove the reaction
        db.session.delete(existing_reaction)
        action = 'removed'
    else:
        # Add the reaction
        reaction = ChatReaction(
            reply_id=reply_id,
            user_id=request.user_id,
            emoji=emoji
        )
        db.session.add(reaction)
        action = 'added'
    
    db.session.commit()
    
    # Return updated reaction counts
    return jsonify({
        'success': True,
        'action': action,
        'reactions': reply.get_reaction_counts()
    })


# =============================================================================
# SEARCH API ENDPOINTS
# =============================================================================

@bp.route('/v1/search', methods=['GET'])
def api_search():
    """Enhanced global search endpoint for videos, users, and tags"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')  # all, videos, users, tags
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 10)), 20)
    
    current_app.logger.info(f"Search request: query='{query}', type='{search_type}', page={page}")
    
    if not query or len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400
    
    results = {
        'query': query,
        'search_type': search_type,
        'page': page,
        'per_page': per_page,
        'videos': [],
        'users': [],
        'tags': [],
        'total_results': 0
    }
    
    # Search videos by prompt, title, description, and tags
    if search_type in ['all', 'videos']:
        current_app.logger.info(f"Searching videos for: {query}")
        
        # First, find videos by direct text match
        direct_videos = Video.query.filter(
            Video.public == True,
            Video.status == 'completed',
            or_(
                Video.prompt.ilike(f'%{query}%'),
                Video.title.ilike(f'%{query}%'),
                Video.description.ilike(f'%{query}%')
            )
        ).order_by(Video.views.desc(), Video.created_at.desc()).limit(per_page).all()
        
        # Also find videos by tag match
        tag_video_ids = db.session.query(VideoTag.video_id).join(Tag).filter(
            Tag.name.ilike(f'%{query}%')
        ).subquery()
        
        tag_videos = Video.query.filter(
            Video.public == True,
            Video.status == 'completed',
            Video.id.in_(tag_video_ids)
        ).order_by(Video.views.desc(), Video.created_at.desc()).limit(per_page).all()
        
        # Combine and deduplicate videos
        all_videos = []
        video_ids_seen = set()
        
        # Add direct matches first (higher priority)
        for video in direct_videos:
            if video.id not in video_ids_seen:
                all_videos.append(video)
                video_ids_seen.add(video.id)
        
        # Add tag matches
        for video in tag_videos:
            if video.id not in video_ids_seen and len(all_videos) < per_page:
                all_videos.append(video)
                video_ids_seen.add(video.id)
        
        current_app.logger.info(f"Found {len(all_videos)} videos")
        
        for video in all_videos:
            # Ensure video has a proper slug
            video.ensure_slug()
            
            # Get video tags
            video_tags = db.session.query(Tag.name).join(VideoTag).filter(
                VideoTag.video_id == video.id
            ).limit(5).all()
        
        # Commit any slug changes
        db.session.commit()
        
        for video in all_videos:
            # Get user profile safely
            user_profile = get_user_profile(video.user)
            
            results['videos'].append({
                'id': video.id,
                'title': video.title or 'Untitled',
                'display_title': video.get_display_title(60),
                'prompt': video.prompt[:200] + '...' if video.prompt and len(video.prompt) > 200 else video.prompt,
                'description': video.description[:150] + '...' if video.description and len(video.description) > 150 else video.description,
                'thumbnail_url': video.thumbnail_url,
                'video_url': video.gcs_signed_url,
                'views': video.views or 0,
                'duration': video.duration,
                'quality': video.quality,
                'created_at': video.created_at.isoformat(),
                'updated_at': video.updated_at.isoformat(),
                'user': {
                    'id': video.user.id,
                    'username': video.user.username,
                    'email': video.user.email,
                    'display_name': user_profile.display_name if user_profile else video.user.username
                },
                'tags': [tag.name for tag in video_tags],
                'slug': video.slug,
                'relevance_score': calculate_video_relevance(video, query)
            })
    
    # Search users by username, email, and display name
    if search_type in ['all', 'users']:
        current_app.logger.info(f"Searching users for: {query}")
        
        users = User.query.join(UserProfile, User.id == UserProfile.user_id, isouter=True).filter(
            or_(
                UserProfile.profile_public == True,
                UserProfile.profile_public.is_(None)  # Handle users without profiles
            ),
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
                UserProfile.display_name.ilike(f'%{query}%'),
                UserProfile.bio.ilike(f'%{query}%')
            )
        ).order_by(
            UserProfile.follower_count.desc().nullslast(), 
            User.created_at.desc()
        ).limit(per_page).all()
        
        current_app.logger.info(f"Found {len(users)} users")
        
        for user in users:
            profile = get_user_profile(user)
            
            # Get user's video count
            video_count = Video.query.filter_by(
                user_id=user.id, 
                public=True, 
                status='completed'
            ).count()
            
            results['users'].append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'display_name': profile.display_name if profile else user.username,
                'bio': profile.bio if profile else None,
                'avatar_url': profile.avatar_url if profile else None,
                'location': profile.location if profile else None,
                'follower_count': profile.follower_count if profile else 0,
                'following_count': profile.following_count if profile else 0,
                'video_count': video_count,
                'total_views': profile.total_views if profile else 0,
                'created_at': user.created_at.isoformat(),
                'profile_public': profile.profile_public if profile else True
            })
    
    # Search tags with usage statistics
    if search_type in ['all', 'tags']:
        current_app.logger.info(f"Searching tags for: {query}")
        
        tags = Tag.query.filter(
            Tag.name.ilike(f'%{query}%')
        ).order_by(Tag.usage_count.desc().nullslast(), Tag.name).limit(10).all()
        
        current_app.logger.info(f"Found {len(tags)} tags")
        
        for tag in tags:
            # Get video count for this tag
            video_count = db.session.query(VideoTag).join(Video).filter(
                VideoTag.tag_id == tag.id,
                Video.public == True,
                Video.status == 'completed'
            ).count()
            
            results['tags'].append({
                'id': tag.id,
                'name': tag.name,
                'usage_count': tag.usage_count or 0,
                'video_count': video_count,
                'created_at': tag.created_at.isoformat() if hasattr(tag, 'created_at') else None
            })
    
    # Calculate total results
    results['total_results'] = len(results['videos']) + len(results['users']) + len(results['tags'])
    
    current_app.logger.info(f"Search completed. Total results: {results['total_results']}")
    return jsonify(results)


def calculate_video_relevance(video, query):
    """Calculate relevance score for search ranking"""
    score = 0
    query_lower = query.lower()
    
    # Title match (highest weight)
    if video.title and query_lower in video.title.lower():
        score += 100
        if video.title.lower().startswith(query_lower):
            score += 50
    
    # Prompt match (high weight)
    if video.prompt and query_lower in video.prompt.lower():
        score += 80
        if video.prompt.lower().startswith(query_lower):
            score += 30
    
    # Description match (medium weight)
    if video.description and query_lower in video.description.lower():
        score += 30
    
    # Views bonus (popularity)
    if video.views:
        score += min(video.views / 100, 20)  # Cap at 20 points
    
    # Recency bonus
    from datetime import datetime, timedelta
    if video.created_at > datetime.utcnow() - timedelta(days=30):
        score += 10
    
    return round(score, 2)


@bp.route('/v1/search/suggestions', methods=['GET'])
def api_search_suggestions():
    """Enhanced search suggestions with prompts, titles, tags, and users"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 1:  # Allow single character suggestions
        return jsonify({'suggestions': []})
    
    suggestions = []
    current_app.logger.info(f"Getting suggestions for: {query}")
    
    # Video title/prompt suggestions (most relevant)
    videos = Video.query.filter(
        Video.public == True,
        Video.status == 'completed',
        or_(
            Video.title.ilike(f'{query}%'),
            Video.prompt.ilike(f'{query}%')
        )
    ).order_by(Video.views.desc()).limit(3).all()
    
    for video in videos:
        if video.title and video.title.lower().startswith(query.lower()):
            suggestions.append({
                'type': 'video_title',
                'text': video.title,
                'display': f'📹 {video.title}',
                'video_id': video.id,
                'views': video.views
            })
        elif video.prompt and video.prompt.lower().startswith(query.lower()):
            # Extract first sentence or 50 chars of prompt
            prompt_preview = video.prompt[:50] + '...' if len(video.prompt) > 50 else video.prompt
            suggestions.append({
                'type': 'video_prompt',
                'text': prompt_preview,
                'display': f'💭 {prompt_preview}',
                'video_id': video.id,
                'views': video.views
            })
    
    # Tag suggestions
    tags = Tag.query.filter(
        Tag.name.ilike(f'{query}%')
    ).order_by(Tag.usage_count.desc().nullslast()).limit(4).all()
    
    for tag in tags:
        suggestions.append({
            'type': 'tag',
            'text': tag.name,
            'display': f"#{tag.name}",
            'usage_count': tag.usage_count or 0,
            'tag_id': tag.id
        })
    
    # User suggestions
    users = User.query.join(UserProfile, User.id == UserProfile.user_id, isouter=True).filter(
        or_(
            UserProfile.profile_public == True,
            UserProfile.profile_public.is_(None)
        ),
        or_(
            User.username.ilike(f'{query}%'),
            UserProfile.display_name.ilike(f'{query}%')
        )
    ).order_by(UserProfile.follower_count.desc().nullslast()).limit(3).all()
    
    for user in users:
        profile = get_user_profile(user)
        display_name = profile.display_name if profile else user.username
        suggestions.append({
            'type': 'user',
            'text': display_name or user.username,
            'display': f"@{display_name or user.username}",
            'user_id': user.id,
            'follower_count': profile.follower_count if profile else 0
        })
    
    # Popular search terms (based on recent prompts)
    if len(suggestions) < 8:
        popular_terms = db.session.query(Video.prompt).filter(
            Video.public == True,
            Video.status == 'completed',
            Video.prompt.ilike(f'%{query}%')
        ).order_by(Video.views.desc()).limit(2).all()
        
        for term in popular_terms:
            if term.prompt:
                # Extract key phrases from prompt
                words = term.prompt.split()[:3]  # First 3 words
                phrase = ' '.join(words)
                if len(phrase) >= len(query) and phrase not in [s['text'] for s in suggestions]:
                    suggestions.append({
                        'type': 'popular_search',
                        'text': phrase,
                        'display': f'🔥 {phrase}',
                        'source': 'trending_prompts'
                    })
    
    # Sort suggestions by relevance
    def suggestion_score(suggestion):
        if suggestion['type'] == 'video_title':
            return 1000 + (suggestion.get('views', 0) / 10)
        elif suggestion['type'] == 'video_prompt':
            return 900 + (suggestion.get('views', 0) / 10)
        elif suggestion['type'] == 'user':
            return 800 + (suggestion.get('follower_count', 0) / 10)
        elif suggestion['type'] == 'tag':
            return 700 + (suggestion.get('usage_count', 0) / 10)
        else:
            return 600
    
    suggestions.sort(key=suggestion_score, reverse=True)
    
    current_app.logger.info(f"Returning {len(suggestions)} suggestions")
    return jsonify({'suggestions': suggestions[:8]})


@bp.route('/v1/search/test', methods=['GET'])
def test_search_data():
    """Test endpoint to check available search data"""
    try:
        # Count available data
        video_count = Video.query.filter(
            Video.public == True,
            Video.status == 'completed'
        ).count()
        
        user_count = User.query.join(UserProfile, User.id == UserProfile.user_id, isouter=True).filter(
            or_(
                UserProfile.profile_public == True,
                UserProfile.profile_public.is_(None)
            )
        ).count()
        
        tag_count = Tag.query.count()
        
        # Get sample data
        sample_videos = Video.query.filter(
            Video.public == True,
            Video.status == 'completed'
        ).limit(3).all()
        
        sample_tags = Tag.query.order_by(Tag.usage_count.desc().nullslast()).limit(5).all()
        
        return jsonify({
            'counts': {
                'videos': video_count,
                'users': user_count,
                'tags': tag_count
            },
            'sample_videos': [{
                'id': v.id,
                'title': v.title,
                'prompt': v.prompt[:100] + '...' if v.prompt and len(v.prompt) > 100 else v.prompt,
                'views': v.views
            } for v in sample_videos],
            'sample_tags': [{
                'id': t.id,
                'name': t.name,
                'usage_count': t.usage_count
            } for t in sample_tags],
            'search_ready': video_count > 0 and tag_count > 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in test_search_data: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# COMMUNITY CHALLENGES API ENDPOINTS
# =============================================================================

@bp.route('/v1/challenges', methods=['GET'])
def api_get_challenges():
    """Get community challenges"""
    status = request.args.get('status', 'all')  # all, active, upcoming, voting, completed
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 10)), 20)
    
    query = CommunityChallenge.query
    
    if status != 'all':
        if status == 'active':
            from datetime import datetime
            now = datetime.utcnow()
            query = query.filter(
                CommunityChallenge.start_date <= now,
                CommunityChallenge.end_date >= now
            )
        elif status in ['upcoming', 'voting', 'completed']:
            query = query.filter(CommunityChallenge.status == status)
    
    challenges = query.order_by(CommunityChallenge.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    result = {
        'challenges': [challenge.to_dict(include_submissions=True) for challenge in challenges.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': challenges.total,
            'pages': challenges.pages
        }
    }
    
    return jsonify(result)


@bp.route('/v1/challenges/<int:challenge_id>', methods=['GET'])
def api_get_challenge(challenge_id):
    """Get specific challenge with submissions"""
    challenge = CommunityChallenge.query.get_or_404(challenge_id)
    
    # Get top submissions
    submissions = ChallengeSubmission.query.filter_by(
        challenge_id=challenge_id
    ).order_by(ChallengeSubmission.vote_count.desc()).limit(20).all()
    
    result = challenge.to_dict()
    result['submissions'] = [submission.to_dict() for submission in submissions]
    
    return jsonify(result)


@bp.route('/v1/challenges/<int:challenge_id>/submit', methods=['POST'])
@login_required
def api_submit_to_challenge(challenge_id):
    """Submit a video to a challenge"""
    challenge = CommunityChallenge.query.get_or_404(challenge_id)
    
    # Check if challenge is active
    if challenge.get_current_status() != 'active':
        return jsonify({'error': 'Challenge is not accepting submissions'}), 400
    
    data = request.get_json()
    video_id = data.get('video_id')
    title = data.get('title', '')
    description = data.get('description', '')
    
    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400
    
    # Verify user owns the video
    video = Video.query.filter_by(id=video_id, user_id=request.user_id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    
    # Check if user already submitted to this challenge
    existing_submission = ChallengeSubmission.query.filter_by(
        challenge_id=challenge_id,
        user_id=request.user_id
    ).first()
    
    if existing_submission:
        return jsonify({'error': 'You have already submitted to this challenge'}), 400
    
    # Create submission
    submission = ChallengeSubmission(
        challenge_id=challenge_id,
        user_id=request.user_id,
        video_id=video_id,
        title=title,
        description=description
    )
    
    db.session.add(submission)
    
    # Update challenge submission count
    challenge.submission_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'submission': submission.to_dict()
    })


@bp.route('/v1/challenges/<int:challenge_id>/vote', methods=['POST'])
@login_required
def api_vote_challenge_submission(challenge_id):
    """Vote for a challenge submission"""
    challenge = CommunityChallenge.query.get_or_404(challenge_id)
    
    # Check if challenge is in voting phase
    if challenge.get_current_status() != 'voting':
        return jsonify({'error': 'Challenge is not in voting phase'}), 400
    
    data = request.get_json()
    submission_id = data.get('submission_id')
    
    if not submission_id:
        return jsonify({'error': 'Submission ID is required'}), 400
    
    # Verify submission belongs to this challenge
    submission = ChallengeSubmission.query.filter_by(
        id=submission_id,
        challenge_id=challenge_id
    ).first()
    
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404
    
    # Check if user already voted in this challenge
    existing_vote = ChallengeVote.query.filter_by(
        challenge_id=challenge_id,
        user_id=request.user_id
    ).first()
    
    if existing_vote:
        if existing_vote.submission_id == submission_id:
            return jsonify({'error': 'You have already voted for this submission'}), 400
        else:
            # Update vote to new submission
            old_submission = ChallengeSubmission.query.get(existing_vote.submission_id)
            old_submission.vote_count -= 1
            
            existing_vote.submission_id = submission_id
            submission.vote_count += 1
            action = 'changed'
    else:
        # Create new vote
        vote = ChallengeVote(
            challenge_id=challenge_id,
            submission_id=submission_id,
            user_id=request.user_id
        )
        db.session.add(vote)
        submission.vote_count += 1
        challenge.total_votes += 1
        action = 'added'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': action,
        'submission': submission.to_dict()
    })


# =============================================================================
# USER PROFILE API ENDPOINTS
# =============================================================================

@bp.route('/v1/profile/<int:user_id>', methods=['GET'])
def api_get_user_profile(user_id):
    """Get user profile with accurate stats"""
    # Use proper selectinload syntax to avoid N+1 queries
    user = User.query.options(selectinload(User.profile)).get_or_404(user_id)
    
    # Get profile safely
    profile = get_user_profile(user)
    if not profile or not profile.profile_public:
        return jsonify({'error': 'Profile not found or private'}), 404
    
    # Calculate accurate stats
    total_videos = Video.query.filter_by(
        user_id=user_id,
        status='completed'
    ).count()
    
    total_views = db.session.query(db.func.sum(Video.views)).filter_by(
        user_id=user_id,
        status='completed'
    ).scalar() or 0
    
    follower_count = UserFollow.query.filter_by(followed_id=user_id).count()
    following_count = UserFollow.query.filter_by(follower_id=user_id).count()
    
    # Get user's public videos
    videos = Video.query.filter_by(
        user_id=user_id,
        public=True,
        status='completed'
    ).order_by(Video.created_at.desc()).limit(6).all()
    
    # Get recent challenge submissions
    submissions = ChallengeSubmission.query.filter_by(
        user_id=user_id
    ).order_by(ChallengeSubmission.created_at.desc()).limit(3).all()
    
    # Get basic profile data with accurate stats
    result = {
        'id': user.id,
        'display_name': profile.display_name or user.username or user.email.split('@')[0],
        'bio': profile.bio,
        'location': profile.location,
        'website_url': profile.website_url,
        'social_links': profile.social_links or {},
        'follower_count': follower_count,
        'following_count': following_count,
        'total_videos': total_videos,
        'total_views': total_views,
        'challenge_wins': profile.challenge_wins or 0,
        'profile_public': profile.profile_public,
        'created_at': user.created_at.isoformat()
    }
    
    # Add video data with better titles
    result['videos'] = [{
        'id': video.id,
        'title': video.title or (video.prompt[:60] + '...' if video.prompt and len(video.prompt) > 60 else video.prompt) or 'Untitled Video',
        'thumbnail_url': video.get_thumbnail_url(),
        'views': video.views or 0,
        'created_at': video.created_at.isoformat(),
        'slug': video.slug or f"video-{video.id}"
    } for video in videos]
    
    # Add submission data with better titles
    result['challenge_submissions'] = [{
        'id': submission.id,
        'title': submission.title or 'Challenge Submission',
        'description': submission.description,
        'created_at': submission.created_at.isoformat(),
        'vote_count': submission.vote_count or 0,
        'rank': submission.rank
    } for submission in submissions]
    
    return jsonify(result)


@bp.route('/v1/profile', methods=['PUT'])
@login_required
def api_update_profile():
    """Update current user's profile"""
    user = User.query.get(request.user_id)
    
    # Get or create profile safely
    profile = get_user_profile(user)
    if not profile:
        # Create profile if it doesn't exist
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.flush()
    
    data = request.get_json()
    
    # Update profile fields
    if 'display_name' in data:
        profile.display_name = data['display_name']
    
    if 'bio' in data:
        profile.bio = data['bio']
    
    if 'location' in data:
        profile.location = data['location']
    
    if 'website_url' in data:
        profile.website_url = data['website_url']
    
    if 'social_links' in data:
        profile.social_links = data['social_links']
    
    if 'profile_public' in data:
        profile.profile_public = data['profile_public']
    
    if 'allow_follows' in data:
        profile.allow_follows = data['allow_follows']
    
    if 'email_notifications' in data:
        profile.email_notifications = data['email_notifications']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'profile': profile.to_dict() if profile else None
    })


@bp.route('/v1/follow/<int:user_id>', methods=['POST'])
@login_required
def api_follow_user(user_id):
    """Follow or unfollow a user"""
    if user_id == request.user_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    target_user = User.query.get_or_404(user_id)
    
    # Get target user profile safely
    target_profile = get_user_profile(target_user)
    if not target_profile or not target_profile.allow_follows:
        return jsonify({'error': 'User does not allow follows'}), 400
    
    existing_follow = UserFollow.query.filter_by(
        follower_id=request.user_id,
        followed_id=user_id
    ).first()
    
    if existing_follow:
        # Unfollow
        db.session.delete(existing_follow)
        action = 'unfollowed'
        
        # Update follower count
        if target_user.profile:
            target_user.profile.follower_count -= 1
    else:
        # Follow
        follow = UserFollow(
            follower_id=request.user_id,
            followed_id=user_id
        )
        db.session.add(follow)
        action = 'followed'
        
        # Update follower count
        if target_user.profile:
            target_user.profile.follower_count += 1
        
        # Create notification
        notification = Notification(
            user_id=user_id,
            type='follow',
            title='New Follower',
            message=f'{User.query.get(request.user_id).profile.display_name or "Someone"} started following you!',
            data={'follower_id': request.user_id}
        )
        db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': action
    })


@bp.route('/v1/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    """Get user notifications"""
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 50)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Notification.query.filter_by(user_id=request.user_id)
    
    if unread_only:
        query = query.filter_by(read=False)
    
    notifications = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    result = {
        'notifications': [notification.to_dict() for notification in notifications.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': notifications.total,
            'pages': notifications.pages
        },
        'unread_count': Notification.query.filter_by(user_id=request.user_id, read=False).count()
    }
    
    return jsonify(result)


@bp.route('/v1/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=request.user_id
    ).first_or_404()
    
    notification.mark_as_read()
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/v1/notifications/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    """Mark all notifications as read"""
    Notification.query.filter_by(
        user_id=request.user_id,
        read=False
    ).update({'read': True})
    
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/v1/test/profile-debug', methods=['GET'])
@login_required
def test_profile_debug():
    """Debug endpoint to test profile access"""
    try:
        user = User.query.get(request.user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        debug_info = {
            'user_id': user.id,
            'user_email': user.email,
            'hasattr_profile': hasattr(user, 'profile'),
            'profile_is_none': user.profile is None if hasattr(user, 'profile') else 'no_attr',
            'profile_type': str(type(user.profile)) if hasattr(user, 'profile') and user.profile else 'None',
            'profile_is_list': isinstance(user.profile, list) if hasattr(user, 'profile') and user.profile else False,
        }
        
        if hasattr(user, 'profile') and user.profile:
            if isinstance(user.profile, list):
                debug_info['profile_list_length'] = len(user.profile)
                debug_info['profile_list_items'] = [str(type(item)) for item in user.profile]
            else:
                debug_info['profile_has_to_dict'] = hasattr(user.profile, 'to_dict')
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e), 'type': str(type(e))})


@bp.route('/v1/auth/me', methods=['GET'])
@login_required
def api_get_current_user():
    """Get current user information"""
    try:
        current_app.logger.info(f"Getting current user info for user_id: {request.user_id}")
        user = User.query.get(request.user_id)
        
        if not user:
            current_app.logger.error(f"User not found for user_id: {request.user_id}")
            return jsonify({'error': 'User not found'}), 404
        
        current_app.logger.info(f"Found user: {user.email} (ID: {user.id})")
        
        # Get or create profile safely
        profile = get_user_profile(user)
        if not profile:
            current_app.logger.info(f"Creating new profile for user {user.id}")
            from app.models import UserProfile
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()
            current_app.logger.info(f"Created profile {profile.id} for user {user.id}")
        
        # Build response safely
        current_app.logger.info(f"Building response for user {user.id} with profile {profile.id if profile else None}")
        
        response_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'credits': user.credits,
            'subscription_tier': user.subscription_tier
        }
        
        # Add profile data safely
        if profile:
            try:
                current_app.logger.info(f"Converting profile {profile.id} to dict")
                response_data['profile'] = profile.to_dict()
                current_app.logger.info(f"Successfully converted profile to dict")
            except Exception as profile_error:
                current_app.logger.error(f"Error converting profile to dict: {str(profile_error)}")
                response_data['profile'] = None
        else:
            response_data['profile'] = None
        
        current_app.logger.info(f"Returning response for user {user.id}")
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in api_get_current_user: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# VEO Image-to-Video API Endpoints
@bp.route('/veo/image-to-video', methods=['POST'])
@login_required
def api_veo_image_to_video():
    """API endpoint for VEO image-to-video generation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['text_prompt', 'image', 'mime_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate image data
        if not data['image'] or not data['mime_type']:
            return jsonify({'error': 'Invalid image data'}), 400
        
        # Validate mime type
        valid_mime_types = ['image/jpeg', 'image/png']
        if data['mime_type'] not in valid_mime_types:
            return jsonify({'error': f'Invalid mime type. Must be one of: {", ".join(valid_mime_types)}'}), 400
        
        # Get parameters with defaults
        model_id = data.get('model_id', 'veo-2.0-generate-001')
        duration = data.get('duration', 8)
        sample_count = data.get('sample_count', 1)
        aspect_ratio = data.get('aspect_ratio', '16:9')
        resolution = data.get('resolution', '1080p')
        negative_prompt = data.get('negative_prompt')
        enhance_prompt = data.get('enhance_prompt', False)
        generate_audio = data.get('generate_audio', False)
        person_generation = data.get('person_generation', 'allow_adult')
        
        # Validate parameters
        if model_id not in ['veo-2.0-generate-001', 'veo-3.0-generate-preview']:
            return jsonify({'error': 'Invalid model ID'}), 400
        
        if duration not in [5, 6, 7, 8]:
            return jsonify({'error': 'Duration must be 5, 6, 7, or 8 seconds'}), 400
        
        if sample_count not in [1, 2, 3, 4]:
            return jsonify({'error': 'Sample count must be 1, 2, 3, or 4'}), 400
        
        if aspect_ratio not in ['16:9', '9:16', '1:1']:
            return jsonify({'error': 'Invalid aspect ratio'}), 400
        
        if person_generation not in ['allow_adult', 'dont_allow']:
            return jsonify({'error': 'Invalid person generation setting'}), 400
        
        # Import VEO client
        from app.veo_client import VeoClient
        
        # Create VEO client
        veo_client = VeoClient()
        veo_client.model_id = model_id
        
        # Prepare the request payload for VEO API
        instances = [{
            'prompt': data['text_prompt'],
            'image': {
                'bytesBase64Encoded': data['image'],
                'mimeType': data['mime_type']
            }
        }]
        
        parameters = {
            'sampleCount': sample_count,
            'durationSeconds': duration,
            'aspectRatio': aspect_ratio,
            'enhancePrompt': enhance_prompt,
            'generateAudio': generate_audio,
            'personGeneration': person_generation
        }
        
        # Add optional parameters
        if negative_prompt:
            parameters['negativePrompt'] = negative_prompt
        
        # Add resolution for Veo 3.0
        if model_id == 'veo-3.0-generate-preview':
            parameters['resolution'] = resolution
        
        # Call VEO API
        current_app.logger.info(f"🎬 Starting VEO image-to-video generation for user {request.user_id}")
        current_app.logger.info(f"📝 Prompt: {data['text_prompt']}")
        current_app.logger.info(f"🤖 Model: {model_id}")
        current_app.logger.info(f"⏱️ Duration: {duration}s")
        current_app.logger.info(f"🎯 Sample count: {sample_count}")
        current_app.logger.info(f"👤 Person generation: {person_generation}")
        
        operation_name = veo_client.generate_image_to_video(instances, parameters)
        
        if operation_name:
            current_app.logger.info(f"✅ VEO image-to-video generation started: {operation_name}")
            return jsonify({
                'success': True,
                'operation_name': operation_name,
                'status': 'processing',
                'estimated_time': '2-5 minutes'
            })
        else:
            current_app.logger.error("❌ VEO image-to-video generation failed")
            return jsonify({'error': 'Failed to start video generation'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in VEO image-to-video generation: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/veo/status/<path:operation_name>', methods=['GET'])
@login_required
def api_veo_status(operation_name):
    """Check the status of a VEO operation"""
    try:
        from app.veo_client import VeoClient
        
        # URL decode the operation name if needed
        import urllib.parse
        operation_name = urllib.parse.unquote(operation_name)
        
        veo_client = VeoClient()
        result = veo_client.check_image_to_video_status(operation_name)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Operation not found or failed'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error checking VEO status: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500 