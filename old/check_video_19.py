#!/usr/bin/env python3
"""
Check detailed status of video ID 19 (real Veo API)
"""

from app import create_app, db
from app.models import Video
from app.veo_client import VeoClient

def check_video_19():
    """Check video ID 19 status"""
    app = create_app()
    
    with app.app_context():
        video = Video.query.get(19)
        if not video:
            print("❌ Video ID 19 not found")
            return
        
        print(f"🎬 Video ID 19 Details:")
        print(f"Status: {video.status}")
        print(f"Prompt: {video.prompt}")
        print(f"Quality: {video.quality}")
        print(f"Slug: {video.slug}")
        print(f"Veo Job ID: {video.veo_job_id}")
        print(f"Created: {video.created_at}")
        print(f"Started: {video.started_at}")
        print(f"Completed: {video.completed_at}")
        print()
        
        if video.veo_job_id:
            print("🔍 Checking Veo API status...")
            try:
                veo_client = VeoClient()
                status_result = veo_client.check_video_status(video.veo_job_id)
                print(f"Veo API Status: {status_result}")
            except Exception as e:
                print(f"Error checking Veo status: {e}")

if __name__ == '__main__':
    check_video_19() 