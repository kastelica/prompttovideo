from flask import request, jsonify, current_app
from app.admin import bp
from app.auth.utils import admin_required
from app.models import db, User, Video, CreditTransaction, PromptPack, ApiUsage
from sqlalchemy import func
from datetime import datetime, timedelta
import sqlalchemy as sa

@bp.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    users = User.query.all()
    videos = Video.query.all()
    
    return render_template('admin/dashboard.html', users=users, videos=videos)

@bp.route('/admin/migrate/add-email-verification-expires', methods=['POST'])
def migrate_add_email_verification_expires():
    """Temporary endpoint to add email_verification_expires column"""
    try:
        # Check if column already exists
        inspector = sa.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'email_verification_expires' in columns:
            return jsonify({'success': True, 'message': 'Column already exists'})
        
        # Add the column
        with db.engine.begin() as conn:
            conn.execute(sa.text('ALTER TABLE users ADD COLUMN email_verification_expires DATETIME'))
        
        return jsonify({'success': True, 'message': 'Column added successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Migration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/analytics/dashboard')
@admin_required
def admin_analytics_dashboard():
    """Admin dashboard analytics"""
    # Get basic stats
    total_users = User.query.count()
    total_videos = Video.query.count()
    completed_videos = Video.query.filter_by(status='completed').count()
    failed_videos = Video.query.filter_by(status='failed').count()
    
    # Revenue stats (from credit transactions)
    total_credits_purchased = db.session.query(
        func.sum(CreditTransaction.amount)
    ).filter_by(
        transaction_type='credit',
        source='purchase'
    ).scalar() or 0
    
    # Queue stats
    pending_videos = Video.query.filter_by(status='pending').count()
    processing_videos = Video.query.filter_by(status='processing').count()
    
    # Subscription tier distribution
    tier_distribution = db.session.query(
        User.subscription_tier,
        func.count(User.id)
    ).group_by(User.subscription_tier).all()
    
    # Recent activity
    recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    return jsonify({
        'stats': {
            'total_users': total_users,
            'total_videos': total_videos,
            'completed_videos': completed_videos,
            'failed_videos': failed_videos,
            'success_rate': (completed_videos / total_videos * 100) if total_videos > 0 else 0,
            'total_credits_purchased': total_credits_purchased,
            'pending_videos': pending_videos,
            'processing_videos': processing_videos
        },
        'subscription_tiers': dict(tier_distribution),
        'recent_videos': [{
            'id': video.id,
            'prompt': video.prompt[:50],
            'status': video.status,
            'priority': video.priority,
            'created_at': video.created_at.isoformat()
        } for video in recent_videos],
        'recent_users': [{
            'id': user.id,
            'email': user.email,
            'credits': user.credits,
            'subscription_tier': user.subscription_tier,
            'created_at': user.created_at.isoformat()
        } for user in recent_users]
    })

@bp.route('/analytics/queue')
@admin_required
def admin_queue_analytics():
    """Queue and priority analytics"""
    # Queue status
    status_counts = db.session.query(
        Video.status,
        func.count(Video.id)
    ).group_by(Video.status).all()
    
    # Priority distribution
    priority_distribution = db.session.query(
        Video.priority,
        func.count(Video.id)
    ).filter_by(status='pending').group_by(Video.priority).all()
    
    # Average wait times by priority
    avg_wait_times = db.session.query(
        Video.priority,
        func.avg(func.extract('epoch', func.now() - Video.queued_at))
    ).filter_by(status='pending').group_by(Video.priority).all()
    
    # Videos by quality and status
    quality_status_counts = db.session.query(
        Video.quality,
        Video.status,
        func.count(Video.id)
    ).group_by(Video.quality, Video.status).all()
    
    # Queue processing over time (last 24 hours)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    hourly_processing = db.session.query(
        func.strftime('%H', Video.started_at),
        func.count(Video.id)
    ).filter(
        Video.started_at >= twenty_four_hours_ago
    ).group_by(
        func.strftime('%H', Video.started_at)
    ).all()
    
    return jsonify({
        'status_counts': dict(status_counts),
        'priority_distribution': dict(priority_distribution),
        'avg_wait_times': {
            str(priority): int(avg_time / 60) if avg_time else 0
            for priority, avg_time in avg_wait_times
        },
        'quality_status_counts': [
            {
                'quality': quality,
                'status': status,
                'count': count
            }
            for quality, status, count in quality_status_counts
        ],
        'hourly_processing': [
            {
                'hour': hour,
                'count': count
            }
            for hour, count in hourly_processing
        ]
    })

@bp.route('/analytics/api-usage')
@admin_required
def admin_api_usage_analytics():
    """API usage analytics"""
    # API calls by endpoint
    endpoint_usage = db.session.query(
        ApiUsage.endpoint,
        func.count(ApiUsage.id)
    ).group_by(ApiUsage.endpoint).all()
    
    # API calls by user tier
    tier_usage = db.session.query(
        User.subscription_tier,
        func.count(ApiUsage.id)
    ).join(ApiUsage).group_by(User.subscription_tier).all()
    
    # Average response times by endpoint
    avg_response_times = db.session.query(
        ApiUsage.endpoint,
        func.avg(ApiUsage.response_time)
    ).group_by(ApiUsage.endpoint).all()
    
    # API usage over time (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_usage = db.session.query(
        func.date(ApiUsage.created_at),
        func.count(ApiUsage.id)
    ).filter(
        ApiUsage.created_at >= seven_days_ago
    ).group_by(
        func.date(ApiUsage.created_at)
    ).order_by(
        func.date(ApiUsage.created_at)
    ).all()
    
    # Error rates by endpoint
    error_rates = db.session.query(
        ApiUsage.endpoint,
        func.count(ApiUsage.id).filter(ApiUsage.status_code >= 400).label('errors'),
        func.count(ApiUsage.id).label('total')
    ).group_by(ApiUsage.endpoint).all()
    
    return jsonify({
        'endpoint_usage': dict(endpoint_usage),
        'tier_usage': dict(tier_usage),
        'avg_response_times': {
            endpoint: round(avg_time, 3) if avg_time else 0
            for endpoint, avg_time in avg_response_times
        },
        'daily_usage': [
            {
                'date': str(date),
                'count': count
            }
            for date, count in daily_usage
        ],
        'error_rates': [
            {
                'endpoint': endpoint,
                'error_rate': round((errors / total * 100), 2) if total > 0 else 0,
                'total_calls': total,
                'error_calls': errors
            }
            for endpoint, errors, total in error_rates
        ]
    })

@bp.route('/analytics/rate-limits')
@admin_required
def admin_rate_limit_analytics():
    """Rate limiting analytics"""
    # Users hitting rate limits
    rate_limited_users = db.session.query(
        User.subscription_tier,
        func.count(User.id)
    ).filter(
        User.api_calls_today > 0
    ).group_by(User.subscription_tier).all()
    
    # Average API calls per user by tier
    avg_calls_by_tier = db.session.query(
        User.subscription_tier,
        func.avg(User.api_calls_today)
    ).group_by(User.subscription_tier).all()
    
    # Users approaching limits
    approaching_limit = db.session.query(
        User.subscription_tier,
        func.count(User.id)
    ).filter(
        User.api_calls_today >= 8  # 80% of free tier limit
    ).group_by(User.subscription_tier).all()
    
    return jsonify({
        'rate_limited_users': dict(rate_limited_users),
        'avg_calls_by_tier': {
            tier: round(avg_calls, 2) if avg_calls else 0
            for tier, avg_calls in avg_calls_by_tier
        },
        'approaching_limit': dict(approaching_limit)
    })

@bp.route('/prompt-packs', methods=['GET'])
@admin_required
def admin_list_prompt_packs():
    """List all prompt packs"""
    packs = PromptPack.query.all()
    
    return jsonify({
        'packs': [{
            'id': pack.id,
            'name': pack.name,
            'description': pack.description,
            'category': pack.category,
            'featured': pack.featured,
            'prompt_count': len(pack.prompts) if pack.prompts else 0
        } for pack in packs]
    })

@bp.route('/prompt-packs', methods=['POST'])
@admin_required
def admin_create_prompt_pack():
    """Create a new prompt pack"""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    pack = PromptPack(
        name=data['name'],
        description=data.get('description', ''),
        prompts=data.get('prompts', []),
        category=data.get('category', ''),
        featured=data.get('featured', False)
    )
    
    db.session.add(pack)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'pack_id': pack.id
    }), 201

@bp.route('/prompt-packs/<int:pack_id>', methods=['PUT'])
@admin_required
def admin_update_prompt_pack(pack_id):
    """Update a prompt pack"""
    pack = PromptPack.query.get_or_404(pack_id)
    data = request.get_json()
    
    if 'name' in data:
        pack.name = data['name']
    if 'description' in data:
        pack.description = data['description']
    if 'prompts' in data:
        pack.prompts = data['prompts']
    if 'category' in data:
        pack.category = data['category']
    if 'featured' in data:
        pack.featured = data['featured']
    
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/prompt-packs/<int:pack_id>', methods=['DELETE'])
@admin_required
def admin_delete_prompt_pack(pack_id):
    """Delete a prompt pack"""
    pack = PromptPack.query.get_or_404(pack_id)
    db.session.delete(pack)
    db.session.commit()
    
    return jsonify({'success': True}) 