#!/usr/bin/env python3
"""
Search Cloud SQL Database Script

This script connects to the Cloud SQL production database and searches for videos.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from sqlalchemy import or_, and_

def search_cloudsql():
    """Search for videos in Cloud SQL database"""
    print("☁️ ===== SEARCHING CLOUD SQL DATABASE =====")
    print()
    
    # Set environment to production to use Cloud SQL
    os.environ['FLASK_ENV'] = 'production'
    
    try:
        app = create_app('production')
        
        # Check database configuration
        print("📊 ===== CLOUD SQL CONFIGURATION =====")
        print(f"Database URL: {app.config.get('DATABASE_URL', 'Not set')}")
        print(f"SQLAlchemy Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
        print()
        
        with app.app_context():
            # Test database connection
            try:
                # Simple query to test connection
                video_count = Video.query.count()
                print(f"✅ Successfully connected to Cloud SQL")
                print(f"📊 Total videos in Cloud SQL: {video_count}")
                print()
            except Exception as e:
                print(f"❌ Failed to connect to Cloud SQL: {e}")
                print("Make sure DATABASE_URL is set to your Cloud SQL connection string")
                return
            
            # Search for the specific video
            print("🔍 ===== SEARCHING FOR 'Bblyrics in recycle bin' =====")
            
            # Exact match
            exact_match = Video.query.filter_by(title='Bblyrics in recycle bin').first()
            
            # Case-insensitive search
            case_insensitive_match = Video.query.filter(
                Video.title.ilike('%bblyrics%recycle%bin%')
            ).first()
            
            # Partial matches
            partial_matches = Video.query.filter(
                or_(
                    Video.title.contains('Bblyrics'),
                    Video.title.contains('bblyrics'),
                    Video.title.contains('recycle'),
                    Video.title.contains('bin')
                )
            ).all()
            
            if exact_match:
                print("✅ EXACT MATCH FOUND:")
                print(f"   - ID: {exact_match.id}")
                print(f"   - Title: '{exact_match.title}'")
                print(f"   - Status: {exact_match.status}")
                print(f"   - User ID: {exact_match.user_id}")
                print(f"   - Public: {exact_match.public}")
                print(f"   - GCS URL: {bool(exact_match.gcs_url)}")
                print(f"   - Signed URL: {bool(exact_match.gcs_signed_url)}")
                print(f"   - Created: {exact_match.created_at}")
                print(f"   - Prompt: '{exact_match.prompt}'")
                print()
            elif case_insensitive_match:
                print("✅ CASE-INSENSITIVE MATCH FOUND:")
                print(f"   - ID: {case_insensitive_match.id}")
                print(f"   - Title: '{case_insensitive_match.title}'")
                print(f"   - Status: {case_insensitive_match.status}")
                print()
            else:
                print("❌ No exact or case-insensitive match found")
                print()
            
            if partial_matches:
                print("🔍 PARTIAL MATCHES:")
                for video in partial_matches:
                    print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}")
                print()
            else:
                print("❌ No partial matches found")
                print()
            
            # Search for other videos from the frontend image
            frontend_titles = [
                "Hockey player flying",
                "Monkey in space", 
                "Monkey in tree",
                "Colorful balloons floating in the sky, vibrant and festive",
                "Ladybug playing tennis"
            ]
            
            print("🔍 ===== SEARCHING FOR OTHER FRONTEND VIDEOS =====")
            found_frontend_videos = []
            for title in frontend_titles:
                video = Video.query.filter_by(title=title).first()
                if video:
                    found_frontend_videos.append(video)
                    print(f"✅ Found: '{title}' (ID: {video.id})")
                else:
                    print(f"❌ Not found: '{title}'")
            print()
            
            # Show recent videos for comparison
            print("📺 ===== RECENT VIDEOS IN CLOUD SQL =====")
            recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
            for video in recent_videos:
                print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}, Created: {video.created_at}")
            print()
            
            # Summary
            print("🎯 ===== SUMMARY =====")
            print(f"Total videos in Cloud SQL: {video_count}")
            print(f"Exact match found: {'Yes' if exact_match else 'No'}")
            print(f"Case-insensitive match found: {'Yes' if case_insensitive_match else 'No'}")
            print(f"Partial matches found: {len(partial_matches)}")
            print(f"Frontend videos found: {len(found_frontend_videos)}")
            
    except Exception as e:
        print(f"❌ Error connecting to Cloud SQL: {e}")
        print()
        print("💡 TROUBLESHOOTING:")
        print("1. Make sure DATABASE_URL environment variable is set")
        print("2. Check if Cloud SQL instance is running")
        print("3. Verify network connectivity to Cloud SQL")
        print("4. Check if Cloud SQL proxy is running (if needed)")

if __name__ == "__main__":
    search_cloudsql() 