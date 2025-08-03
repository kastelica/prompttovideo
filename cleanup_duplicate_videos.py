#!/usr/bin/env python3
"""
Script to identify and clean up duplicate video operations.
This helps resolve the issue where multiple sample_0.mp4 files are being created.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User

def cleanup_duplicate_videos():
    """Identify and clean up duplicate video operations"""
    
    app = create_app()
    with app.app_context():
        print("🔍 Checking for duplicate video operations...")
        
        # Find videos that might have duplicates
        # Look for videos with the same prompt, user, and recent creation time
        recent_videos = Video.query.filter(
            Video.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(Video.created_at.desc()).all()
        
        print(f"📊 Found {len(recent_videos)} videos created in the last 24 hours")
        
        # Group videos by user and prompt
        video_groups = {}
        for video in recent_videos:
            key = (video.user_id, video.prompt.strip().lower())
            if key not in video_groups:
                video_groups[key] = []
            video_groups[key].append(video)
        
        # Find groups with multiple videos
        duplicates_found = 0
        for (user_id, prompt), videos in video_groups.items():
            if len(videos) > 1:
                duplicates_found += 1
                print(f"\n🔍 Potential duplicates found for user {user_id}, prompt: '{prompt[:50]}...'")
                print(f"   Found {len(videos)} videos:")
                
                # Sort by creation time
                videos.sort(key=lambda v: v.created_at)
                
                for i, video in enumerate(videos):
                    status_icon = {
                        'pending': '⏳',
                        'processing': '🔄',
                        'completed': '✅',
                        'failed': '❌'
                    }.get(video.status, '❓')
                    
                    print(f"   {i+1}. {status_icon} Video ID: {video.id}, Status: {video.status}, Created: {video.created_at}")
                    if video.veo_job_id:
                        print(f"      Veo Job ID: {video.veo_job_id}")
                    if video.gcs_url:
                        print(f"      GCS URL: {video.gcs_url}")
                
                # Suggest cleanup strategy
                completed_videos = [v for v in videos if v.status == 'completed']
                processing_videos = [v for v in videos if v.status == 'processing']
                failed_videos = [v for v in videos if v.status == 'failed']
                pending_videos = [v for v in videos if v.status == 'pending']
                
                if completed_videos:
                    print(f"   💡 Keep: {len(completed_videos)} completed video(s)")
                    # Mark others as failed to prevent further processing
                    for video in videos:
                        if video.status != 'completed':
                            video.status = 'failed'
                            video.error_message = 'Duplicate video - keeping completed version'
                            print(f"   🗑️  Marking video {video.id} as failed (duplicate)")
                    
                elif processing_videos:
                    print(f"   💡 Keep: {len(processing_videos)} processing video(s)")
                    # Mark others as failed
                    for video in videos:
                        if video.status != 'processing':
                            video.status = 'failed'
                            video.error_message = 'Duplicate video - keeping processing version'
                            print(f"   🗑️  Marking video {video.id} as failed (duplicate)")
                
                elif failed_videos:
                    print(f"   💡 All videos failed - keeping most recent")
                    # Keep the most recent failed video, mark others as failed with duplicate message
                    for i, video in enumerate(videos):
                        if i > 0:  # Keep first (most recent) one
                            video.status = 'failed'
                            video.error_message = 'Duplicate video - keeping most recent failed version'
                            print(f"   🗑️  Marking video {video.id} as failed (duplicate)")
                
                elif pending_videos:
                    print(f"   💡 All videos pending - keeping most recent")
                    # Keep the most recent pending video, mark others as failed
                    for i, video in enumerate(videos):
                        if i > 0:  # Keep first (most recent) one
                            video.status = 'failed'
                            video.error_message = 'Duplicate video - keeping most recent pending version'
                            print(f"   🗑️  Marking video {video.id} as failed (duplicate)")
        
        if duplicates_found > 0:
            print(f"\n💾 Committing changes to database...")
            db.session.commit()
            print(f"✅ Cleaned up {duplicates_found} duplicate video groups")
        else:
            print("✅ No duplicate videos found")
        
        # Also check for videos with multiple Veo job IDs
        print("\n🔍 Checking for videos with multiple Veo job IDs...")
        videos_with_jobs = Video.query.filter(
            Video.veo_job_id.isnot(None),
            Video.veo_job_id != ''
        ).all()
        
        job_id_counts = {}
        for video in videos_with_jobs:
            if video.veo_job_id in job_id_counts:
                job_id_counts[video.veo_job_id].append(video)
            else:
                job_id_counts[video.veo_job_id] = [video]
        
        duplicate_jobs = {job_id: videos for job_id, videos in job_id_counts.items() if len(videos) > 1}
        
        if duplicate_jobs:
            print(f"⚠️  Found {len(duplicate_jobs)} Veo job IDs used by multiple videos:")
            for job_id, videos in duplicate_jobs.items():
                print(f"   Job ID: {job_id}")
                for video in videos:
                    print(f"     - Video ID: {video.id}, Status: {video.status}")
        else:
            print("✅ No duplicate Veo job IDs found")

if __name__ == '__main__':
    cleanup_duplicate_videos() 