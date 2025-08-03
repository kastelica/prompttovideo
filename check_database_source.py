#!/usr/bin/env python3
"""
Check Database Source Script

This script checks what database the application is using and if there are multiple databases.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from sqlalchemy import and_

def check_database_source():
    """Check what database the application is using"""
    print("🔍 ===== CHECKING DATABASE SOURCE =====")
    print()
    
    app = create_app()
    
    # Check database configuration
    print("📊 ===== DATABASE CONFIGURATION =====")
    print(f"Database URL: {app.config.get('DATABASE_URL', 'Not set')}")
    print(f"SQLAlchemy Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
    print(f"SQLAlchemy Track Modifications: {app.config.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'Not set')}")
    print()
    
    with app.app_context():
        # Check current database
        print("📋 ===== CURRENT DATABASE STATE =====")
        
        # Get all videos with detailed info
        all_videos = Video.query.all()
        print(f"Total videos in current database: {len(all_videos)}")
        print()
        
        if all_videos:
            print("📺 ALL VIDEOS IN CURRENT DATABASE:")
            for video in all_videos:
                print(f"   - ID: {video.id}")
                print(f"     Title: '{video.title}'")
                print(f"     Status: {video.status}")
                print(f"     Public: {video.public}")
                print(f"     User ID: {video.user_id}")
                print(f"     GCS URL: {bool(video.gcs_url)}")
                print(f"     Signed URL: {bool(video.gcs_signed_url)}")
                print(f"     Created: {video.created_at}")
                print(f"     Prompt: '{video.prompt}'")
                print()
        else:
            print("❌ No videos found in current database")
            print()
        
        # Check what videos would show on frontend
        print("🏠 ===== FRONTEND DISPLAY LOGIC =====")
        
        # Index page query
        featured_videos = Video.query.filter(
            and_(
                Video.public == True,
                Video.status == 'completed',
                Video.gcs_signed_url.isnot(None)
            )
        ).limit(12).all()
        
        print(f"Videos that would show on index page: {len(featured_videos)}")
        for video in featured_videos:
            print(f"   - '{video.title}' (ID: {video.id})")
        print()
        
        # Check if there are any videos with the titles from the frontend
        frontend_titles = [
            "Bblyrics in recycle bin",
            "Hockey player flying", 
            "Monkey in space",
            "Monkey in tree",
            "Colorful balloons floating in the sky, vibrant and festive",
            "Ladybug playing tennis"
        ]
        
        print("🔍 ===== CHECKING FOR FRONTEND TITLES =====")
        found_titles = []
        for title in frontend_titles:
            video = Video.query.filter_by(title=title).first()
            if video:
                found_titles.append((title, video.id))
                print(f"✅ Found: '{title}' (ID: {video.id})")
            else:
                print(f"❌ Not found: '{title}'")
        print()
        
        if not found_titles:
            print("🚨 NO FRONTEND TITLES FOUND IN DATABASE!")
            print("This suggests the frontend is using cached data or a different database.")
            print()
            
            # Check environment variables
            print("🌍 ===== ENVIRONMENT VARIABLES =====")
            print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')}")
            print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'Not set')}")
            print(f"FLASK_DEBUG: {os.environ.get('FLASK_DEBUG', 'Not set')}")
            print()
            
            # Check if there are multiple database files
            print("📁 ===== CHECKING FOR DATABASE FILES =====")
            possible_db_files = [
                'instance/prompttovideo.db',
                'prompttovideo.db',
                'app.db',
                'database.db'
            ]
            
            for db_file in possible_db_files:
                if os.path.exists(db_file):
                    print(f"✅ Found database file: {db_file}")
                    # Get file size
                    size = os.path.getsize(db_file)
                    print(f"   Size: {size} bytes ({size/1024/1024:.2f} MB)")
                else:
                    print(f"❌ Not found: {db_file}")
            print()

if __name__ == "__main__":
    check_database_source() 