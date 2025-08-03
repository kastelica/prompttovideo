#!/usr/bin/env python3
"""
Script to identify and clean up stuck processing videos
"""

from app import create_app
from app.models import Video, User, db
from datetime import datetime, timedelta
import os

def cleanup_stuck_videos():
    """Identify and clean up videos stuck in processing state"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Checking for stuck processing videos...")
        
        # Find videos that have been processing for more than 30 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        
        stuck_videos = Video.query.filter(
            Video.status == 'processing',
            Video.started_at < cutoff_time
        ).all()
        
        print(f"📊 Found {len(stuck_videos)} videos stuck in processing:")
        
        for video in stuck_videos:
            user = User.query.get(video.user_id)
            processing_duration = datetime.utcnow() - video.started_at if video.started_at else "Unknown"
            print(f"  - Video {video.id}: '{video.prompt[:50]}...' (User: {user.email if user else 'Unknown'})")
            print(f"    Processing for: {processing_duration}")
            print(f"    Started at: {video.started_at}")
            print(f"    Veo Job ID: {video.veo_job_id}")
            print()
        
        if stuck_videos:
            print("🛠️  Options to fix stuck videos:")
            print("1. Mark as failed and refund credits")
            print("2. Reset to pending to retry")
            print("3. Mark as completed (if you know they're done)")
            print("4. Delete the videos")
            
            choice = input("\nEnter your choice (1-4) or 'q' to quit: ").strip()
            
            if choice == '1':
                # Mark as failed and refund credits
                for video in stuck_videos:
                    user = User.query.get(video.user_id)
                    if user:
                        # Refund credits (1 for free, 3 for premium)
                        credit_cost = 1 if video.quality == 'free' else 3
                        user.credits += credit_cost
                        print(f"  ✅ Refunded {credit_cost} credits to {user.email}")
                    
                    video.status = 'failed'
                    video.error_message = 'Video processing timed out - automatically marked as failed'
                    print(f"  ❌ Marked video {video.id} as failed")
                
                db.session.commit()
                print("✅ All stuck videos marked as failed and credits refunded")
                
            elif choice == '2':
                # Reset to pending
                for video in stuck_videos:
                    video.status = 'pending'
                    video.started_at = None
                    video.veo_job_id = None
                    print(f"  🔄 Reset video {video.id} to pending")
                
                db.session.commit()
                print("✅ All stuck videos reset to pending")
                
            elif choice == '3':
                # Mark as completed (use with caution)
                for video in stuck_videos:
                    video.status = 'completed'
                    video.completed_at = datetime.utcnow()
                    print(f"  ✅ Marked video {video.id} as completed")
                
                db.session.commit()
                print("✅ All stuck videos marked as completed")
                
            elif choice == '4':
                # Delete videos
                confirm = input("Are you sure you want to DELETE these videos? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    for video in stuck_videos:
                        db.session.delete(video)
                        print(f"  🗑️  Deleted video {video.id}")
                    
                    db.session.commit()
                    print("✅ All stuck videos deleted")
                else:
                    print("❌ Deletion cancelled")
            
            elif choice.lower() == 'q':
                print("👋 Exiting without changes")
            else:
                print("❌ Invalid choice")
        else:
            print("✅ No stuck videos found!")
        
        # Also check for videos in pending for too long
        print("\n🔍 Checking for videos stuck in pending...")
        pending_cutoff = datetime.utcnow() - timedelta(hours=2)
        
        stuck_pending = Video.query.filter(
            Video.status == 'pending',
            Video.created_at < pending_cutoff
        ).all()
        
        if stuck_pending:
            print(f"📊 Found {len(stuck_pending)} videos stuck in pending:")
            for video in stuck_pending:
                user = User.query.get(video.user_id)
                pending_duration = datetime.utcnow() - video.created_at
                print(f"  - Video {video.id}: '{video.prompt[:50]}...' (User: {user.email if user else 'Unknown'})")
                print(f"    Pending for: {pending_duration}")
                print(f"    Created at: {video.created_at}")
                print()
        else:
            print("✅ No videos stuck in pending!")

def show_video_stats():
    """Show statistics about video statuses"""
    app = create_app()
    
    with app.app_context():
        print("📊 Video Status Statistics:")
        print("=" * 40)
        
        total = Video.query.count()
        completed = Video.query.filter_by(status='completed').count()
        processing = Video.query.filter_by(status='processing').count()
        pending = Video.query.filter_by(status='pending').count()
        failed = Video.query.filter_by(status='failed').count()
        
        print(f"Total videos: {total}")
        print(f"Completed: {completed}")
        print(f"Processing: {processing}")
        print(f"Pending: {pending}")
        print(f"Failed: {failed}")
        print()
        
        if total > 0:
            print("Percentages:")
            print(f"Completed: {(completed/total)*100:.1f}%")
            print(f"Processing: {(processing/total)*100:.1f}%")
            print(f"Pending: {(pending/total)*100:.1f}%")
            print(f"Failed: {(failed/total)*100:.1f}%")

if __name__ == "__main__":
    print("🧹 Video Cleanup Tool")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. Show video statistics")
        print("2. Clean up stuck processing videos")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            show_video_stats()
        elif choice == '2':
            cleanup_stuck_videos()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice") 