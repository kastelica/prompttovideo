#!/usr/bin/env python3
"""
Reset rate limits for development testing
"""

from app import create_app, db
from app.models import User
from datetime import datetime

def reset_rate_limits():
    """Reset API call counts for all users in development mode"""
    app = create_app()
    
    with app.app_context():
        # Reset API calls for all users
        users = User.query.all()
        for user in users:
            user.api_calls_today = 0
            user.last_api_call = None
            print(f"Reset rate limits for user: {user.email}")
        
        db.session.commit()
        print(f"✅ Reset rate limits for {len(users)} users")
        print("🎯 You can now generate videos without hitting rate limits!")

if __name__ == '__main__':
    reset_rate_limits() 