from flask import request, jsonify, current_app, render_template
from app.auth import bp
from app.auth.utils import generate_token
from app.models import db, User
from app.email_utils import send_auth_email
import uuid
from datetime import datetime, timedelta

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    
    email = data['email'].lower().strip()
    password = data.get('password')
    referral_code = data.get('referral_code')
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'User already exists'}), 409
    
    # Create new user
    user = User(email=email)
    
    if password:
        user.set_password(password)
        user.email_verified = True  # Auto-verify if password provided
    else:
        # Passwordless auth - send verification email
        user.email_verification_token = str(uuid.uuid4())
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=1)
        send_auth_email(user.email, 'verify_email', user.email_verification_token)
    
    # Handle referral
    if referral_code:
        referrer = User.query.filter_by(referral_code=referral_code.upper()).first()
        if referrer and referrer.id != user.id:  # Can't refer yourself
            user.referred_by = referral_code.upper()
            # Process referral using the new method
            referrer.process_referral_signup(user)
    
    # Give initial credits
    user.add_credits(current_app.config['DAILY_FREE_CREDITS'], 'daily_free')
    
    db.session.add(user)
    db.session.commit()
    
    # Generate token
    token = generate_token(user.id)
    
    response = jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'credits': user.credits
        }
    })
    
    # Set token as HTTP-only cookie for web interface
    response.set_cookie('auth_token', token, httponly=True, secure=False, samesite='Lax', max_age=3600)
    
    return response, 201

@bp.route('/login', methods=['POST'])
def login():
    """Login user with email/password or passwordless"""
    data = request.get_json()
    
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    
    email = data['email'].lower().strip()
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if password:
        # Password-based login
        if not user.check_password(password):
            return jsonify({'error': 'Invalid password'}), 401
        
        if not user.email_verified:
            return jsonify({'error': 'Email not verified'}), 401
    else:
        # Passwordless login - send magic link
        user.email_verification_token = str(uuid.uuid4())
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        
        # Send magic link email
        email_sent = send_auth_email(user.email, 'magic_link', user.email_verification_token)
        
        if email_sent:
            return jsonify({
                'success': True,
                'message': 'Magic link sent to your email'
            })
        else:
            return jsonify({
                'error': 'Failed to send magic link. Please try again.'
            }), 500
    
    # Generate token
    token = generate_token(user.id)
    
    response = jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'credits': user.credits
        }
    })
    
    # Set token as HTTP-only cookie for web interface
    response.set_cookie('auth_token', token, httponly=True, secure=False, samesite='Lax', max_age=3600)
    
    return response

@bp.route('/verify/<token>')
def verify_email(token):
    """Verify email with token (for both registration and magic links)"""
    user = User.query.filter_by(email_verification_token=token).first()
    
    if not user:
        return render_template('auth/verify_error.html', 
                             error='Invalid or expired token',
                             message='The verification link is invalid or has expired.')
    
    # Check if token has expired
    if hasattr(user, 'email_verification_expires') and user.email_verification_expires:
        if user.email_verification_expires < datetime.utcnow():
            return render_template('auth/verify_error.html',
                                 error='Token expired',
                                 message='The verification link has expired. Please request a new one.')
    
    # Mark email as verified
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    db.session.commit()
    
    # Generate token
    auth_token = generate_token(user.id)
    
    # Create response with token
    response = jsonify({
        'success': True,
        'token': auth_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'credits': user.credits
        }
    })
    
    # Set token as HTTP-only cookie for web interface
    response.set_cookie('auth_token', auth_token, httponly=True, secure=False, samesite='Lax', max_age=3600)
    
    # For web interface, redirect to dashboard
    if request.headers.get('Accept', '').startswith('text/html'):
        response = current_app.make_response(render_template('auth/verify_success.html', user=user))
        response.set_cookie('auth_token', auth_token, httponly=True, secure=False, samesite='Lax', max_age=3600)
        return response
    
    return response

@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Send password reset email"""
    data = request.get_json()
    
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    
    email = data['email'].lower().strip()
    user = User.query.filter_by(email=email).first()
    
    if user:
        user.reset_password_token = str(uuid.uuid4())
        user.reset_password_expires = datetime.utcnow() + timedelta(hours=1)
        send_auth_email(user.email, 'reset_password', user.reset_password_token)
        db.session.commit()
    
    # Always return success to prevent email enumeration
    return jsonify({
        'success': True,
        'message': 'If the email exists, a reset link has been sent'
    })

@bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Reset password with token"""
    data = request.get_json()
    
    if not data or 'password' not in data:
        return jsonify({'error': 'Password is required'}), 400
    
    user = User.query.filter_by(reset_password_token=token).first()
    
    if not user or user.reset_password_expires < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    user.set_password(data['password'])
    user.reset_password_token = None
    user.reset_password_expires = None
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Password reset successfully'
    })

@bp.route('/logout')
def logout():
    """Logout user"""
    response = jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })
    
    # Clear the auth token cookie
    response.delete_cookie('auth_token')
    
    return response

@bp.route('/profile')
def profile():
    """Get user profile"""
    # This would be protected by login_required in a real app
    return jsonify({
        'success': True,
        'message': 'Profile endpoint'
    })

# Template routes
@bp.route('/login-page')
def login_page():
    """Show login page"""
    return render_template('auth/login.html')

@bp.route('/register-page')
def register_page():
    """Show registration page"""
    return render_template('auth/register.html')

@bp.route('/forgot-password-page')
def forgot_password_page():
    """Show forgot password page"""
    return render_template('auth/forgot_password.html') 