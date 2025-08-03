#!/usr/bin/env python3
"""
Script to rename video titles in Cloud SQL database
Shows existing titles with video info and allows interactive renaming
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set production environment variables for Cloud SQL
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Set the Cloud SQL database URL - using the actual production database
CLOUD_SQL_URL = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"

os.environ['DATABASE_URL'] = CLOUD_SQL_URL

print(f"🔗 Connecting to Cloud SQL database...")
print(f"   URL: {CLOUD_SQL_URL}")

from app import create_app, db
from app.models import Video, User

def get_videos_with_titles():
    """Get all videos with their titles and basic info"""
    try:
        videos = Video.query.filter(
            Video.title.isnot(None),
            Video.title != ''
        ).order_by(Video.id).all()
        
        video_list = []
        for video in videos:
            video_info = {
                'id': video.id,
                'title': video.title,
                'prompt': video.prompt,
                'gcs_url': video.gcs_url,
                'created_at': video.created_at,
                'views': video.views or 0
            }
            video_list.append(video_info)
            
        return video_list
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return []

def display_video_info(video, index, total):
    """Display video information in a formatted way"""
    print(f"\n{'='*80}")
    print(f"📹 Video {index + 1} of {total}")
    print(f"{'='*80}")
    print(f"🆔 ID: {video['id']}")
    print(f"📝 Current Title: {video['title']}")
    print(f"💭 Prompt: {video['prompt'][:100]}{'...' if len(video['prompt']) > 100 else ''}")
    print(f"🔗 GCS URL: {video['gcs_url']}")
    print(f"📅 Created: {video['created_at']}")
    print(f"👁️ Views: {video['views']}")
    print(f"{'='*80}")

def update_video_title(video_id, new_title):
    """Update video title in database"""
    try:
        video = Video.query.get(video_id)
        if not video:
            print(f"❌ Video ID {video_id} not found")
            return False
            
        video.title = new_title
        db.session.commit()
        return True
    except Exception as e:
        print(f"❌ Error updating title: {e}")
        db.session.rollback()
        return False

def main():
    print("🎬 VIDEO TITLE RENAMER - CLOUD SQL")
    print("=" * 50)
    
    # Create Flask app and get database connection
    app = create_app()
    
    with app.app_context():
        # Get videos with titles
        print("\n📋 Fetching videos with titles...")
        videos = get_videos_with_titles()
        
        if not videos:
            print("❌ No videos with titles found")
            return
        
        print(f"✅ Found {len(videos)} videos with titles")
        
        # Track changes
        changes_made = []
        skipped = []
        
        # Process each video
        for i, video in enumerate(videos):
            display_video_info(video, i, len(videos))
            
            # Get user input
            while True:
                new_title = input(f"\n📝 Enter new title for video {video['id']} (or press Enter to keep '{video['title']}'): ").strip()
                
                if new_title == "":
                    print(f"⏭️ Keeping existing title: '{video['title']}'")
                    skipped.append(video)
                    break
                elif new_title.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Exiting...")
                    return
                elif len(new_title) > 200:
                    print("❌ Title too long (max 200 characters)")
                    continue
                else:
                    # Confirm the change
                    confirm = input(f"✅ Confirm change from '{video['title']}' to '{new_title}'? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        if update_video_title(video['id'], new_title):
                            print(f"✅ Updated video {video['id']} title to: '{new_title}'")
                            changes_made.append({
                                'id': video['id'],
                                'old_title': video['title'],
                                'new_title': new_title
                            })
                            break
                        else:
                            print("❌ Failed to update title, please try again")
                    else:
                        print("🔄 Let's try again...")
                        continue
        
        # Summary
        print(f"\n{'='*80}")
        print("📊 RENAMING SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Changes made: {len(changes_made)}")
        print(f"⏭️ Skipped: {len(skipped)}")
        
        if changes_made:
            print(f"\n📝 CHANGES MADE:")
            for change in changes_made:
                print(f"  Video {change['id']}: '{change['old_title']}' → '{change['new_title']}'")
        
        if skipped:
            print(f"\n⏭️ SKIPPED VIDEOS:")
            for video in skipped:
                print(f"  Video {video['id']}: '{video['title']}'")
        
        print(f"\n🎉 Title renaming completed!")

if __name__ == "__main__":
    main() 