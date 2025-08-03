#!/usr/bin/env python3
"""
Clear GCS URLs Script

This script clears GCS URLs from videos so they won't show in the frontend,
without deleting the database records.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video

def clear_gcs_urls():
    """Clear GCS URLs from videos"""
    print("🧹 ===== CLEARING GCS URLS =====")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos
        videos = Video.query.all()
        
        print(f"📊 Total videos in database: {len(videos)}")
        
        # Clear GCS URLs from videos
        videos_to_clear = []
        for video in videos:
            if video.gcs_url and video.gcs_url.startswith('gs://'):
                videos_to_clear.append(video)
        
        print(f"🗑️ Videos with GCS URLs to clear: {len(videos_to_clear)}")
        
        if videos_to_clear:
            print("🗑️ Clearing GCS URLs...")
            
            for video in videos_to_clear:
                try:
                    print(f"   🗑️ Clearing GCS URL for video ID: {video.id}")
                    print(f"      Old GCS URL: {video.gcs_url}")
                    
                    # Clear GCS URLs
                    video.gcs_url = None
                    video.gcs_signed_url = None
                    video.thumbnail_url = None
                    
                    print(f"      ✅ Cleared GCS URLs")
                    
                except Exception as e:
                    print(f"   ❌ Error clearing video ID {video.id}: {e}")
                    continue
            
            try:
                db.session.commit()
                print(f"✅ Successfully cleared GCS URLs from {len(videos_to_clear)} videos")
            except Exception as e:
                print(f"❌ Error committing changes: {e}")
                db.session.rollback()
        else:
            print("✅ No videos with GCS URLs to clear!")
        
        # Verify cleanup
        remaining_videos_with_gcs = Video.query.filter(
            Video.gcs_url.isnot(None),
            Video.gcs_url.startswith('gs://')
        ).all()
        
        print(f"\n📊 Final database state:")
        print(f"   Videos with GCS URLs: {len(remaining_videos_with_gcs)}")
        print(f"   Videos without GCS URLs: {len(videos) - len(remaining_videos_with_gcs)}")
        
        if remaining_videos_with_gcs:
            print("📁 Videos still with GCS URLs:")
            for video in remaining_videos_with_gcs:
                print(f"   - ID: {video.id}, Status: {video.status}, Quality: {video.quality}")
                print(f"     GCS: {video.gcs_url}")
                print()
        else:
            print("✅ All videos have GCS URLs cleared!")
            print("🎉 Frontend will now show no videos (clean slate)")

if __name__ == "__main__":
    clear_gcs_urls() 