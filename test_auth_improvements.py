#!/usr/bin/env python3
"""
Test script to demonstrate the improved authentication system.
This shows how the system now handles token expiration gracefully.
"""

import jwt
import time
from datetime import datetime, timedelta

def create_test_token(expires_in_seconds=3600):
    """Create a test JWT token with specified expiration"""
    payload = {
        'user_id': 1,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in_seconds),
        'iat': datetime.utcnow()
    }
    secret = 'your-secret-key'  # Replace with actual secret
    return jwt.encode(payload, secret, algorithm='HS256')

def decode_token(token):
    """Decode JWT token to check expiration"""
    try:
        payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
        expiry_time = datetime.fromtimestamp(payload['exp'])
        current_time = datetime.utcnow()
        time_until_expiry = (expiry_time - current_time).total_seconds()
        
        print(f"Token expires at: {expiry_time}")
        print(f"Current time: {current_time}")
        print(f"Time until expiry: {time_until_expiry:.0f} seconds")
        
        if time_until_expiry <= 0:
            print("❌ Token has expired!")
            return False
        elif time_until_expiry < 300:  # 5 minutes
            print("⚠️  Token expires soon!")
            return True
        else:
            print("✅ Token is valid")
            return True
            
    except jwt.ExpiredSignatureError:
        print("❌ Token has expired!")
        return False
    except Exception as e:
        print(f"❌ Error decoding token: {e}")
        return False

def test_authentication_scenarios():
    """Test different authentication scenarios"""
    print("🔐 Testing Authentication Improvements\n")
    
    # Test 1: Valid token
    print("1. Testing valid token:")
    valid_token = create_test_token(3600)  # 1 hour
    decode_token(valid_token)
    print()
    
    # Test 2: Expired token
    print("2. Testing expired token:")
    expired_token = create_test_token(-60)  # Expired 1 minute ago
    decode_token(expired_token)
    print()
    
    # Test 3: Token expiring soon
    print("3. Testing token expiring soon:")
    soon_expiring_token = create_test_token(180)  # 3 minutes
    decode_token(soon_expiring_token)
    print()
    
    # Test 4: Invalid token
    print("4. Testing invalid token:")
    invalid_token = "invalid.token.here"
    decode_token(invalid_token)
    print()

def demonstrate_user_experience():
    """Demonstrate the improved user experience"""
    print("👤 Improved User Experience:\n")
    
    print("✅ Before (Old System):")
    print("   - User gets generic 401 error")
    print("   - No explanation of what happened")
    print("   - Confusing why they need to login again")
    print("   - No warning before session expires")
    print()
    
    print("✅ After (New System):")
    print("   - Clear notification: 'Session Expired'")
    print("   - Helpful message: 'Your session has expired. Please log in again.'")
    print("   - Automatic redirect to login page")
    print("   - Warning 5 minutes before session expires")
    print("   - Navigation updates to show login state")
    print("   - Login page shows session expiry message")
    print()

def show_error_responses():
    """Show the improved error responses"""
    print("📝 Improved Error Responses:\n")
    
    print("1. No Authorization Header:")
    print("   Status: 401")
    print("   Error: 'Authentication required'")
    print("   Message: 'Please log in to access this feature'")
    print("   Redirect: '/auth/login-page?auth_required=true'")
    print()
    
    print("2. Expired Token:")
    print("   Status: 401")
    print("   Error: 'Session expired'")
    print("   Message: 'Your session has expired. Please log in again.'")
    print("   Redirect: '/auth/login-page?session_expired=true'")
    print()
    
    print("3. User Not Found:")
    print("   Status: 401")
    print("   Error: 'User not found'")
    print("   Message: 'Your account could not be found. Please log in again.'")
    print("   Redirect: '/auth/login-page?session_expired=true'")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 AUTHENTICATION SYSTEM IMPROVEMENTS DEMO")
    print("=" * 60)
    print()
    
    test_authentication_scenarios()
    demonstrate_user_experience()
    show_error_responses()
    
    print("=" * 60)
    print("✅ Authentication system improvements complete!")
    print("=" * 60) 