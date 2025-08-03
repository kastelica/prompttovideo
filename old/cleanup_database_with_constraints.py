#!/usr/bin/env python3
"""
Database Cleanup with Foreign Key Constraints

This script removes videos from the database while properly handling foreign key constraints.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, ChallengeSubmission, ChatMessage, VideoTag

def cleanup_database():
    """Clean up the database by removing videos without GCS URLs"""
    print("🧹 ===== CLEANING UP DATABASE WITH CONSTRAINTS =====")
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
            print("🗑️ Removing videos and related data...")
            
            for video in videos_to_remove:
                try:
                    print(f"   🗑️ Processing video ID: {video.id}")
                    
                    # First, remove related data that has foreign key constraints
                    
                    # 1. Remove challenge submissions
                    submissions = ChallengeSubmission.query.filter_by(video_id=video.id).all()
                    for submission in submissions:
                        print(f"      - Removing challenge submission ID: {submission.id}")
                        db.session.delete(submission)
                    
                    # 2. Remove chat messages
                    chat_messages = ChatMessage.query.filter_by(video_id=video.id).all()
                    for message in chat_messages:
                        print(f"      - Removing chat message ID: {message.id}")
                        db.session.delete(message)
                    
                    # 3. Remove video tags
                    video_tags = VideoTag.query.filter_by(video_id=video.id).all()
                    for video_tag in video_tags:
                        print(f"      - Removing video tag ID: {video_tag.id}")
                        db.session.delete(video_tag)
                    
                    # 4. Finally remove the video itself
                    print(f"      - Removing video ID: {video.id}")
                    db.session.delete(video)
                    
                except Exception as e:
                    print(f"   ❌ Error removing video ID {video.id}: {e}")
                    db.session.rollback()
                    continue
            
            try:
                db.session.commit()
                print(f"✅ Successfully removed {len(videos_to_remove)} videos and related data from database")
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
        
        # Check for orphaned data
        orphaned_submissions = ChallengeSubmission.query.filter(
            ~ChallengeSubmission.video_id.in_([v.id for v in remaining_videos])
        ).all()
        
        orphaned_messages = ChatMessage.query.filter(
            ~ChatMessage.video_id.in_([v.id for v in remaining_videos])
        ).all()
        
        orphaned_tags = VideoTag.query.filter(
            ~VideoTag.video_id.in_([v.id for v in remaining_videos])
        ).all()
        
        if orphaned_submissions or orphaned_messages or orphaned_tags:
            print("⚠️ Found orphaned data:")
            if orphaned_submissions:
                print(f"   - Orphaned challenge submissions: {len(orphaned_submissions)}")
            if orphaned_messages:
                print(f"   - Orphaned chat messages: {len(orphaned_messages)}")
            if orphaned_tags:
                print(f"   - Orphaned video tags: {len(orphaned_tags)}")
        else:
            print("✅ No orphaned data found")

if __name__ == "__main__":
    cleanup_database() 