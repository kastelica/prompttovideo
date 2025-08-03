#!/usr/bin/env python3
"""
Simple Database Cleanup Script

This script removes videos from the database that don't have working GCS URLs.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video

def cleanup_database():
    """Clean up the database by removing videos without GCS URLs"""
    print("🧹 ===== CLEANING UP DATABASE =====")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos
        videos = Video.query.all()
        
        print(f"📊 Total videos in database: {len(videos)}")
        
        # Remove videos without GCS URLs
        videos_to_remove = []
        for video in videos:
            if not video.gcs_url or not video.gcs_url.startswith('gs://'):
                videos_to_remove.append(video)
        
        print(f"🗑️ Videos to remove: {len(videos_to_remove)}")
        
        if videos_to_remove:
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
            print("✅ No videos to remove - database is clean!")
        
        # Verify cleanup
        remaining_videos = Video.query.all()
        print(f"\n📊 Final database state:")
        print(f"   Total videos: {len(remaining_videos)}")
        
        if remaining_videos:
            print("📁 Remaining videos:")
            for video in remaining_videos:
                print(f"   - ID: {video.id}, Status: {video.status}, Quality: {video.quality}")
                if video.gcs_url:
                    print(f"     GCS: {video.gcs_url}")
                print()
        else:
            print("✅ Database is empty - no videos remaining")

if __name__ == "__main__":
    cleanup_database() 