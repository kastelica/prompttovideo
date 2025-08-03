#!/usr/bin/env python3
"""
Update gcs_signed_url field for all videos to fix video playback.
"""

import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set production environment variables for Cloud SQL
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Set the Cloud SQL database URL
CLOUD_SQL_URL = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"
os.environ['DATABASE_URL'] = CLOUD_SQL_URL

print(f"🔗 Connecting to Cloud SQL database...")
print(f"   URL: {CLOUD_SQL_URL}")

from app import create_app, db
from app.models import Video, User
from app.gcs_utils import generate_signed_url

def update_signed_urls():
    """Update gcs_signed_url for all videos with gcs_url."""
    app = create_app()
    
    with app.app_context():
        print("🔧 UPDATING SIGNED URLS")
        print("=" * 50)
        
        # Get all videos with gcs_url but missing or old gcs_signed_url
        videos = Video.query.filter(
            Video.gcs_url.isnot(None),
            Video.gcs_url != ''
        ).all()
        
        print(f"📊 Found {len(videos)} videos with GCS URLs")
        
        success_count = 0
        error_count = 0
        
        for video in videos:
            try:
                print(f"\n🎬 Processing Video ID {video.id}: {video.prompt[:40]}...")
                print(f"   Current GCS URL: {video.gcs_url}")
                print(f"   Current Signed URL: {video.gcs_signed_url[:100] if video.gcs_signed_url else 'None'}...")
                
                # Generate new signed URL
                new_signed_url = generate_signed_url(video.gcs_url, duration_days=365)
                print(f"   New Signed URL: {new_signed_url[:100]}...")
                
                # Update the video record
                video.gcs_signed_url = new_signed_url
                db.session.commit()
                
                print(f"   ✅ Database updated successfully")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Error updating video {video.id}: {e}")
                error_count += 1
                db.session.rollback()
        
        print(f"\n📊 UPDATE SUMMARY:")
        print(f"   Successfully updated: {success_count}")
        print(f"   Errors: {error_count}")

def check_signed_urls():
    """Check the status of signed URLs."""
    app = create_app()
    
    with app.app_context():
        print("🔍 CHECKING SIGNED URLS")
        print("=" * 50)
        
        # Get all videos
        videos = Video.query.all()
        
        with_signed_url = 0
        without_signed_url = 0
        with_gcs_url = 0
        without_gcs_url = 0
        
        for video in videos:
            if video.gcs_url:
                with_gcs_url += 1
                if video.gcs_signed_url:
                    with_signed_url += 1
                    print(f"   ✅ Video {video.id}: Has both GCS and signed URL")
                else:
                    without_signed_url += 1
                    print(f"   ❌ Video {video.id}: Has GCS URL but no signed URL")
            else:
                without_gcs_url += 1
                print(f"   ⚠️  Video {video.id}: No GCS URL")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total videos: {len(videos)}")
        print(f"   With GCS URL: {with_gcs_url}")
        print(f"   Without GCS URL: {without_gcs_url}")
        print(f"   With signed URL: {with_signed_url}")
        print(f"   Without signed URL: {without_signed_url}")

def main():
    """Main menu for signed URL management."""
    while True:
        print("\n🔧 SIGNED URL MANAGEMENT")
        print("=" * 40)
        print("1. Check signed URL status")
        print("2. Update all signed URLs")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            check_signed_urls()
        elif choice == '2':
            response = input("🗺️  Update signed URLs for all videos? (y/N): ").strip()
            if response.lower() == 'y':
                update_signed_urls()
                print("\n✅ Signed URL update completed!")
            else:
                print("❌ Update cancelled")
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main() 