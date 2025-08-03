from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from app.models import User, Referral, db
from app.auth.utils import login_required, verify_token
from datetime import datetime, timedelta

bp = Blueprint('referral', __name__)

@bp.route('/ref/<referral_code>')
def referral_landing(referral_code):
    """Landing page for referral links"""
    # Find the user with this referral code
    referrer = User.query.filter_by(referral_code=referral_code).first()
    
    if not referrer:
        flash('Invalid referral code', 'error')
        return redirect(url_for('main.index'))
    
    # Ensure referrer has a valid referral code
    if not referrer.referral_code:
        referrer.ensure_referral_code()
        db.session.commit()
    
    # Store referral code in session for signup
    from flask import session
    session['referral_code'] = referral_code
    
    return render_template('main/referral_landing.html', 
                         referrer=referrer, 
                         referral_code=referral_code)

@bp.route('/api/referral/stats')
@login_required
def referral_stats():
    """Get current user's referral statistics"""
    user = User.query.get(request.user_id)
    stats = user.get_referral_stats()
    
    # Get recent referrals
    recent_referrals = Referral.query.filter_by(
        referrer_id=user.id
    ).order_by(Referral.created_at.desc()).limit(10).all()
    
    recent_data = []
    for ref in recent_referrals:
        referred_user = User.query.get(ref.referred_id)
        if referred_user:
            recent_data.append({
                'email': referred_user.email,
                'joined_at': ref.created_at.isoformat(),
                'credits_earned': 5  # Fixed amount per referral
            })
    
    return jsonify({
        'stats': stats,
        'recent_referrals': recent_data
    })

@bp.route('/api/referral/validate')
def validate_referral_code():
    """Validate a referral code"""
    code = request.args.get('code')
    if not code:
        return jsonify({'valid': False, 'error': 'No code provided'})
    
    user = User.query.filter_by(referral_code=code.upper()).first()
    if user:
        return jsonify({
            'valid': True,
            'referrer_email': user.email
        })
    else:
        return jsonify({
            'valid': False,
            'error': 'Invalid referral code'
        })

@bp.route('/referral/dashboard')
def referral_dashboard():
    """User's referral dashboard"""
    # Try to get user from JWT token if available
    user = None
    
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
    
    if not user:
        return redirect(url_for('auth.login_page'))
    
    stats = user.get_referral_stats()
    
    # Get all referrals with user details
    referrals = Referral.query.filter_by(
        referrer_id=user.id
    ).order_by(Referral.created_at.desc()).all()
    
    referral_data = []
    for ref in referrals:
        referred_user = User.query.get(ref.referred_id)
        if referred_user:
            referral_data.append({
                'id': ref.id,
                'email': referred_user.email,
                'joined_at': ref.created_at,
                'credits_earned': 5
            })
    
    return render_template('main/referral_dashboard.html',
                         stats=stats,
                         referrals=referral_data)

@bp.route('/api/referral/share')
@login_required
def share_referral():
    """Generate shareable referral content"""
    user = User.query.get(request.user_id)
    stats = user.get_referral_stats()
    
    # Generate social media content
    share_content = {
        'twitter': f"🎬 Create amazing AI videos with PromptToVideo! Use my referral code {stats['referral_code']} to get 5 free credits: {stats['referral_url']}",
        'facebook': f"🎬 I've been creating amazing AI-generated videos with PromptToVideo! Use my referral code {stats['referral_code']} to get 5 free credits when you sign up: {stats['referral_url']}",
        'linkedin': f"🎬 Excited to share PromptToVideo - an AI video generation platform. Use my referral code {stats['referral_code']} to get 5 free credits: {stats['referral_url']}",
        'email': f"Hi! I've been using PromptToVideo to create amazing AI-generated videos. You can get 5 free credits when you sign up using my referral code: {stats['referral_code']}",
        'url': stats['referral_url']
    }
    
    return jsonify(share_content) 