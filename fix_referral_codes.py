#!/usr/bin/env python3
"""
Script to fix referral codes for existing users who don't have them.
Run this script to ensure all users have referral codes.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def fix_referral_codes():
    """Fix referral codes for all users who don't have them"""
    app = create_app()
    
    with app.app_context():
        # Find users without referral codes
        users_without_codes = User.query.filter(
            (User.referral_code.is_(None)) | (User.referral_code == '')
        ).all()
        
        print(f"Found {len(users_without_codes)} users without referral codes")
        
        if not users_without_codes:
            print("All users already have referral codes!")
            return
        
        # Generate referral codes for each user
        for user in users_without_codes:
            old_code = user.referral_code
            user.ensure_referral_code()
            new_code = user.referral_code
            print(f"User {user.email}: {old_code} -> {new_code}")
        
        # Commit all changes
        db.session.commit()
        print(f"Successfully generated referral codes for {len(users_without_codes)} users")

if __name__ == '__main__':
    fix_referral_codes() 