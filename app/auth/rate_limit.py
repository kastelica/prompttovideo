from functools import wraps
from flask import request, jsonify, current_app
from app.models import User, ApiUsage, db
from app.auth.utils import verify_token
import time

def rate_limit(max_requests=None):
    """
    Rate limiting decorator that checks user's API limits
    If max_requests is None, uses user's subscription tier limits
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user from JWT token
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
            
            # Check rate limits
            if not user.can_make_api_call():
                rate_info = user.get_rate_limit_info()
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'rate_limit_info': rate_info
                }), 429
            
            # Record API call
            user.record_api_call()
            
            # Record API usage for analytics
            start_time = time.time()
            
            try:
                # Execute the function
                response = f(*args, **kwargs)
                
                # Record successful API call
                record_api_usage(user.id, request.endpoint, request.method, 
                               time.time() - start_time, 
                               response[1] if isinstance(response, tuple) else 200)
                
                return response
                
            except Exception as e:
                # Record failed API call
                record_api_usage(user.id, request.endpoint, request.method, 
                               time.time() - start_time, 500)
                raise
            
        return decorated_function
    return decorator

def record_api_usage(user_id, endpoint, method, response_time, status_code):
    """Record API usage for analytics"""
    try:
        usage = ApiUsage(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            response_time=response_time,
            status_code=status_code,
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )
        db.session.add(usage)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to record API usage: {e}")

def get_user_rate_limit_info(user_id):
    """Get rate limit information for a user"""
    user = User.query.get(user_id)
    if not user:
        return None
    
    return user.get_rate_limit_info()

def update_user_subscription_tier(user_id, tier):
    """Update user's subscription tier"""
    user = User.query.get(user_id)
    if not user:
        return False
    
    valid_tiers = ['free', 'basic', 'pro', 'enterprise']
    if tier not in valid_tiers:
        return False
    
    user.subscription_tier = tier
    db.session.commit()
    return True 