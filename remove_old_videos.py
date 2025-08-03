#!/usr/bin/env python3
"""
Safely remove old videos with confirmation prompts.
"""

import os
import sys
from sqlalchemy import and_, or_

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from app.gcs_utils import delete_gcs_file

def remove_videos_by_ids(video_ids, reason="manual removal"):
    """Remove videos by their IDs with GCS cleanup."""
    
    app = create_app()
    
    with app.app_context():
        print(f"🗑️  REMOVING {len(video_ids)} VIDEOS")
        print("=" * 40)
        
        removed_count = 0
        errors = []
        
        for video_id in video_ids:
            try:
                video = Video.query.get(video_id)
                if not video:
                    print(f"❌ Video ID {video_id} not found")
                    continue
                
                print(f"\n🎬 Processing Video ID {video_id}:")
                print(f"   Prompt: {video.prompt[:50]}...")
                print(f"   Status: {video.status}")
                print(f"   Views: {video.views}")
                print(f"   Created: {video.created_at}")
                print(f"   User: {video.user.email if video.user else 'Unknown'}")
                
                # Delete GCS files if they exist
                if video.gcs_url:
                    print(f"   🗂️  Deleting GCS video: {video.gcs_url}")
                    try:
                        delete_gcs_file(video.gcs_url)
                        print(f"   ✅ GCS video deleted")
                    except Exception as e:
                        print(f"   ⚠️  Could not delete GCS video: {e}")
                
                if video.thumbnail_gcs_url:
                    print(f"   🖼️  Deleting GCS thumbnail: {video.thumbnail_gcs_url}")
                    try:
                        delete_gcs_file(video.thumbnail_gcs_url)
                        print(f"   ✅ GCS thumbnail deleted")
                    except Exception as e:
                        print(f"   ⚠️  Could not delete GCS thumbnail: {e}")
                
                # Delete from database
                db.session.delete(video)
                db.session.commit()
                print(f"   ✅ Database record deleted")
                removed_count += 1
                
            except Exception as e:
                print(f"   ❌ Error removing video {video_id}: {e}")
                errors.append((video_id, str(e)))
                db.session.rollback()
        
        print(f"\n📊 REMOVAL SUMMARY:")
        print(f"   Successfully removed: {removed_count} videos")
        print(f"   Errors: {len(errors)}")
        
        if errors:
            print(f"\n❌ ERRORS:")
            for video_id, error in errors:
                print(f"   Video {video_id}: {error}")

def remove_failed_videos():
    """Remove all failed videos."""
    app = create_app()
    
    with app.app_context():
        failed_videos = Video.query.filter(Video.status.in_(['failed', 'error', 'content_violation'])).all()
        
        if not failed_videos:
            print("✅ No failed videos found")
            return
        
        print(f"🔴 Found {len(failed_videos)} failed videos:")
        for video in failed_videos:
            print(f"   ID {video.id}: {video.prompt[:40]}... (Status: {video.status})")
        
        response = input(f"\n🗑️  Remove {len(failed_videos)} failed videos? (y/N): ")
        if response.lower() == 'y':
            video_ids = [v.id for v in failed_videos]
            remove_videos_by_ids(video_ids, "failed videos")
        else:
            print("❌ Cancelled")

def remove_test_videos():
    """Remove test videos."""
    app = create_app()
    
    with app.app_context():
        test_videos = Video.query.filter(Video.prompt.ilike('%test%')).all()
        
        if not test_videos:
            print("✅ No test videos found")
            return
        
        print(f"🔴 Found {len(test_videos)} test videos:")
        for video in test_videos:
            print(f"   ID {video.id}: {video.prompt} (Views: {video.views})")
        
        response = input(f"\n🗑️  Remove {len(test_videos)} test videos? (y/N): ")
        if response.lower() == 'y':
            video_ids = [v.id for v in test_videos]
            remove_videos_by_ids(video_ids, "test videos")
        else:
            print("❌ Cancelled")

def remove_specific_videos():
    """Remove specific videos by ID."""
    print("🎯 REMOVE SPECIFIC VIDEOS")
    print("Enter video IDs separated by commas (e.g., 1,2,3):")
    
    try:
        video_ids_input = input("Video IDs: ").strip()
        if not video_ids_input:
            print("❌ No video IDs provided")
            return
        
        video_ids = [int(x.strip()) for x in video_ids_input.split(',')]
        
        app = create_app()
        with app.app_context():
            videos = Video.query.filter(Video.id.in_(video_ids)).all()
            
            if not videos:
                print("❌ No videos found with those IDs")
                return
            
            print(f"\n🔴 Found {len(videos)} videos:")
            for video in videos:
                print(f"   ID {video.id}: {video.prompt[:40]}... (Status: {video.status}, Views: {video.views})")
            
            response = input(f"\n🗑️  Remove {len(videos)} videos? (y/N): ")
            if response.lower() == 'y':
                remove_videos_by_ids(video_ids, "specific videos")
            else:
                print("❌ Cancelled")
                
    except ValueError:
        print("❌ Invalid video IDs format")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main menu for video removal."""
    while True:
        print("\n🗑️  VIDEO REMOVAL TOOL")
        print("=" * 30)
        print("1. Remove failed videos")
        print("2. Remove test videos") 
        print("3. Remove specific videos by ID")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            remove_failed_videos()
        elif choice == '2':
            remove_test_videos()
        elif choice == '3':
            remove_specific_videos()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main() 