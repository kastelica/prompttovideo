#!/usr/bin/env python3
"""
Cancel video ID 19 manually
"""

from app import create_app, db
from app.models import Video

def cancel_video_19():
    """Cancel video ID 19"""
    app = create_app()
    
    with app.app_context():
        video = Video.query.get(19)
        if not video:
            print("❌ Video ID 19 not found")
            return
        
        print(f"🎬 Canceling video ID 19:")
        print(f"Current status: {video.status}")
        print(f"Prompt: {video.prompt}")
        print(f"Veo Job ID: {video.veo_job_id}")
        print()
        
        # Cancel the video by setting it to failed status
        video.status = 'failed'
        video.completed_at = None
        # Keep the veo_job_id for reference but mark as canceled
        
        db.session.commit()
        
        print(f"✅ Video ID 19 canceled:")
        print(f"New status: {video.status}")
        print(f"Veo Job ID: {video.veo_job_id} (kept for reference)")
        print()
        print("🎯 The video has been manually canceled.")
        print("💡 You can now generate a new video without conflicts.")

if __name__ == '__main__':
    cancel_video_19() 