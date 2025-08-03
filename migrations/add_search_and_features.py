#!/usr/bin/env python3
"""
Migration script to add search, community challenges, and enhanced user features
"""

import sys
import os

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (Tag, VideoTag, CommunityChallenge, ChallengeSubmission, 
                      ChallengeVote, UserProfile, UserFollow, Notification)

def create_app_context():
    app = create_app()
    return app

def run_migration():
    app = create_app_context()
    
    with app.app_context():
        print("Creating new tables for search and community features...")
        
        # Create all tables
        db.create_all()
        
        # Create default user profiles for existing users
        from app.models import User
        print("Creating default user profiles for existing users...")
        
        users = User.query.all()
        for user in users:
            if not hasattr(user, 'profile') or user.profile is None:
                profile = UserProfile(
                    user_id=user.id,
                    display_name=user.username or user.email.split('@')[0],
                    profile_public=True,
                    allow_follows=True,
                    email_notifications=True
                )
                db.session.add(profile)
                print(f"Created profile for user: {user.email}")
        
        # Create some default tags
        default_tags = [
            {'name': 'nature', 'description': 'Natural landscapes and environments'},
            {'name': 'urban', 'description': 'City and urban scenes'},
            {'name': 'abstract', 'description': 'Abstract and artistic content'},
            {'name': 'animals', 'description': 'Wildlife and domestic animals'},
            {'name': 'space', 'description': 'Cosmic and space-related content'},
            {'name': 'ocean', 'description': 'Marine and underwater scenes'},
            {'name': 'fantasy', 'description': 'Fantasy and magical themes'},
            {'name': 'technology', 'description': 'Tech and futuristic content'},
            {'name': 'food', 'description': 'Culinary and food-related content'},
            {'name': 'sports', 'description': 'Athletic and sports activities'}
        ]
        
        print("Creating default tags...")
        for tag_data in default_tags:
            existing_tag = Tag.query.filter_by(name=tag_data['name']).first()
            if not existing_tag:
                tag = Tag(**tag_data)
                db.session.add(tag)
                print(f"Created tag: {tag_data['name']}")
        
        # Create a sample community challenge
        admin_user = User.query.filter_by(email='user1@test.com').first()
        if admin_user:
            from datetime import datetime, timedelta
            
            existing_challenge = CommunityChallenge.query.first()
            if not existing_challenge:
                challenge = CommunityChallenge(
                    title="Serene Landscapes Challenge",
                    description="Create the most peaceful and serene landscape video. Think calm lakes, gentle mountains, or quiet forests.",
                    theme="Nature & Tranquility",
                    prompt_guidelines="Focus on peaceful, calming natural scenes. Avoid action or movement. Think meditation and relaxation.",
                    status="active",
                    start_date=datetime.utcnow() - timedelta(days=1),
                    end_date=datetime.utcnow() + timedelta(days=6),
                    voting_end_date=datetime.utcnow() + timedelta(days=10),
                    created_by=admin_user.id,
                    credit_prize_first=100,
                    credit_prize_second=50,
                    credit_prize_third=25
                )
                db.session.add(challenge)
                print("Created sample community challenge")
        
        db.session.commit()
        print("Migration completed successfully!")

if __name__ == '__main__':
    run_migration()