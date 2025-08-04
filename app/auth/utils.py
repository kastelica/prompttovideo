from functools import wraps
from flask import request, jsonify, current_app
import jwt
from datetime import datetime, timedelta
from app.models import User

def generate_token(user_id, expires_in=3600):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        current_app.logger.info(f"DEBUG: Verifying token: {token[:20]}...")
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['user_id']
        current_app.logger.info(f"DEBUG: Token verified successfully, user_id: {user_id}")
        return user_id
    except jwt.ExpiredSignatureError:
        current_app.logger.error("DEBUG: Token expired")
        return None
    except jwt.InvalidTokenError as e:
        current_app.logger.error(f"DEBUG: Invalid token: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"DEBUG: Token verification error: {e}")
        return None

def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Add debugging output
        current_app.logger.info("=== LOGIN_REQUIRED DEBUG ===")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        current_app.logger.info(f"Request cookies: {dict(request.cookies)}")
        
        # Check for token in Authorization header first
        token = request.headers.get('Authorization')
        current_app.logger.info(f"Authorization header: {token}")
        
        # If no Authorization header, check for token in cookies (for web requests)
        if not token:
            token = request.cookies.get('auth_token')
            current_app.logger.info(f"Auth token from cookies: {token[:20] if token else 'None'}...")
        
        if not token:
            current_app.logger.error("No Authorization header or auth_token cookie found")
            # Check if this is an API request (expects JSON) or web request (should redirect)
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please log in to access this feature',
                    'code': 'AUTH_REQUIRED',
                    'redirect': '/auth/login-page?auth_required=true'
                }), 401
            else:
                # For web requests, redirect to login page
                from flask import redirect, url_for
                return redirect(url_for('auth.login_page', auth_required='true'))
        
        if token.startswith('Bearer '):
            token = token[7:]
            current_app.logger.info(f"Extracted token: {token[:20]}...")
        else:
            current_app.logger.info(f"Token (no Bearer prefix): {token[:20]}...")
        
        user_id = verify_token(token)
        current_app.logger.info(f"Token verification result - User ID: {user_id}")
        
        if not user_id:
            current_app.logger.error("Token verification failed - invalid or expired token")
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Session expired',
                    'message': 'Your session has expired. Please log in again.',
                    'code': 'TOKEN_EXPIRED',
                    'redirect': '/auth/login-page?session_expired=true'
                }), 401
            else:
                from flask import redirect, url_for
                return redirect(url_for('auth.login_page', session_expired='true'))
        
        user = User.query.get(user_id)
        current_app.logger.info(f"User lookup result: {user.email if user else 'NOT FOUND'}")
        
        if not user:
            current_app.logger.error(f"User not found for ID: {user_id}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'User not found',
                    'message': 'Your account could not be found. Please log in again.',
                    'code': 'USER_NOT_FOUND',
                    'redirect': '/auth/login-page?session_expired=true'
                }), 401
            else:
                from flask import redirect, url_for
                return redirect(url_for('auth.login_page', session_expired='true'))
        
        # Check if email is verified (required for all users)
        if not user.email_verified:
            current_app.logger.error(f"Email not verified for user: {user.email}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Email not verified',
                    'message': 'Please verify your email address to access this feature. Check your inbox for a verification link.',
                    'code': 'EMAIL_NOT_VERIFIED',
                    'redirect': '/auth/verify-email'
                }), 401
            else:
                from flask import redirect, url_for
                return redirect(url_for('auth.verify_email'))
        
        request.user_id = user_id
        request.current_user = user
        current_app.logger.info(f"Authentication successful - User: {user.email}")
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please log in to access this feature',
                'code': 'AUTH_REQUIRED',
                'redirect': '/auth/login-page?auth_required=true'
            }), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({
                'error': 'Session expired',
                'message': 'Your session has expired. Please log in again.',
                'code': 'TOKEN_EXPIRED',
                'redirect': '/auth/login-page?session_expired=true'
            }), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'Your account could not be found. Please log in again.',
                'code': 'USER_NOT_FOUND',
                'redirect': '/auth/login-page?session_expired=true'
            }), 401
        
        # Check if user is admin (you'll need to add admin field to User model)
        if not hasattr(user, 'is_admin') or not user.is_admin:
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access this feature.',
                'code': 'ADMIN_REQUIRED'
            }), 403
        
        request.user_id = user_id
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function 