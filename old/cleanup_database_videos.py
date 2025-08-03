#!/usr/bin/env python3
"""
Cleanup Database Videos Script

This script removes videos from the database that don't have working GCS URLs,
so the frontend only shows videos that actually exist and are accessible.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from app.gcs_utils import get_gcs_bucket_name
from google.cloud import storage

def get_gcs_client():
    """Get GCS client with proper credentials"""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        creds_path = os.path.join(os.getcwd(), 'veo.json')
    
    if os.path.exists(creds_path):
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        return storage.Client(credentials=credentials)
    else:
        return storage.Client()

def check_video_exists_in_gcs(gcs_url):
    """Check if a video file actually exists in GCS"""
    if not gcs_url or not gcs_url.startswith('gs://'):
        return False
    
    try:
        # Parse GCS URL
        bucket_name = gcs_url.split('/')[2]
        blob_name = '/'.join(gcs_url.split('/')[3:])
        
        # Get GCS client
        storage_client = get_gcs_client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Check if blob exists
        return blob.exists()
    except Exception as e:
        print(f"❌ Error checking GCS URL {gcs_url}: {e}")
        return False

def analyze_database_videos():
    """Analyze all videos in the database"""
    print("🔍 ===== ANALYZING DATABASE VIDEOS =====")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos
        videos = Video.query.all()
        
        print(f"📊 Total videos in database: {len(videos)}")
        print()
        
        # Categorize videos
        videos_with_gcs = []
        videos_without_gcs = []
        videos_with_broken_gcs = []
        
        for video in videos:
            if video.gcs_url and video.gcs_url.startswith('gs://'):
                if check_video_exists_in_gcs(video.gcs_url):
                    videos_with_gcs.append(video)
                else:
                    videos_with_broken_gcs.append(video)
            else:
                videos_without_gcs.append(video)
        
        print(f"✅ Videos with working GCS URLs: {len(videos_with_gcs)}")
        print(f"❌ Videos with broken GCS URLs: {len(videos_with_broken_gcs)}")
        print(f"⚠️ Videos without GCS URLs: {len(videos_without_gcs)}")
        print()
        
        # Show details
        if videos_with_gcs:
            print("✅ Videos with working GCS URLs:")
            for video in videos_with_gcs:
                print(f"   - ID: {video.id}, Status: {video.status}, Quality: {video.quality}")
                print(f"     Prompt: {video.prompt[:50]}...")
                print(f"     GCS: {video.gcs_url}")
                print()
        
        if videos_with_broken_gcs:
            print("❌ Videos with broken GCS URLs:")
            for video in videos_with_broken_gcs:
                print(f"   - ID: {video.id}, Status: {video.status}, Quality: {video.quality}")
                print(f"     Prompt: {video.prompt[:50]}...")
                print(f"     GCS: {video.gcs_url}")
                print()
        
        if videos_without_gcs:
            print("⚠️ Videos without GCS URLs:")
            for video in videos_without_gcs:
                print(f"   - ID: {video.id}, Status: {video.status}, Quality: {video.quality}")
                print(f"     Prompt: {video.prompt[:50]}...")
                print()
        
        return videos_with_gcs, videos_with_broken_gcs, videos_without_gcs

def cleanup_database():
    """Clean up the database by removing videos without working GCS URLs"""
    print("🧹 ===== CLEANING UP DATABASE =====")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos
        videos = Video.query.all()
        
        videos_to_keep = []
        videos_to_remove = []
        
        for video in videos:
            if video.gcs_url and video.gcs_url.startswith('gs://'):
                if check_video_exists_in_gcs(video.gcs_url):
                    videos_to_keep.append(video)
                else:
                    videos_to_remove.append(video)
            else:
                videos_to_remove.append(video)
        
        print(f"📊 Analysis:")
        print(f"   Videos to keep: {len(videos_to_keep)}")
        print(f"   Videos to remove: {len(videos_to_remove)}")
        print()
        
        if videos_to_remove:
            print("🗑️ Videos that will be removed:")
            for video in videos_to_remove:
                print(f"   - ID: {video.id}, Status: {video.status}")
                print(f"     Prompt: {video.prompt[:50]}...")
                if video.gcs_url:
                    print(f"     GCS: {video.gcs_url}")
                print()
            
            # Confirm deletion
            confirm = input(f"⚠️ Do you want to remove {len(videos_to_remove)} videos? (y/n): ").strip().lower()
            
            if confirm == 'y':
                print("🗑️ Removing videos...")
                for video in videos_to_remove:
                    try:
                        db.session.delete(video)
                        print(f"   ✅ Removed video ID: {video.id}")
                    except Exception as e:
                        print(f"   ❌ Error removing video ID {video.id}: {e}")
                
                try:
                    db.session.commit()
                    print(f"✅ Successfully removed {len(videos_to_remove)} videos from database")
                except Exception as e:
                    print(f"❌ Error committing changes: {e}")
                    db.session.rollback()
            else:
                print("❌ Cleanup cancelled")
        else:
            print("✅ No videos to remove - database is clean!")

def verify_cleanup():
    """Verify the cleanup was successful"""
    print("🔍 ===== VERIFYING CLEANUP =====")
    print()
    
    app = create_app()
    with app.app_context():
        videos = Video.query.all()
        
        print(f"📊 Final database state:")
        print(f"   Total videos: {len(videos)}")
        
        if videos:
            print("📁 Remaining videos:")
            for video in videos:
                print(f"   - ID: {video.id}, Status: {video.status}, Quality: {video.quality}")
                print(f"     Prompt: {video.prompt[:50]}...")
                if video.gcs_url:
                    print(f"     GCS: {video.gcs_url}")
                print()
        else:
            print("✅ Database is empty - no videos remaining")

def main():
    """Main function"""
    print("🚀 Starting Database Video Cleanup...")
    print()
    
    try:
        # Step 1: Analyze current state
        videos_with_gcs, videos_with_broken_gcs, videos_without_gcs = analyze_database_videos()
        
        # Step 2: Clean up database
        cleanup_database()
        
        # Step 3: Verify cleanup
        verify_cleanup()
        
        print(f"\n✅ Database cleanup complete!")
        print(f"📝 Next steps:")
        print(f"   1. Restart your Flask application")
        print(f"   2. Check the frontend - should only show videos with working GCS URLs")
        print(f"   3. Generate new videos to test the organized naming system")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 