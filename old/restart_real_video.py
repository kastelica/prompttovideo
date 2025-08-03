#!/usr/bin/env python3
"""
Restart real video generation for video ID 19
"""

from app import create_app, db
from app.models import Video
from app.tasks import generate_video_task

def restart_real_video():
    """Restart video generation for ID 19"""
    app = create_app()
    
    with app.app_context():
        video = Video.query.get(19)
        if not video:
            print("❌ Video ID 19 not found")
            return
        
        print(f"🎬 Restarting video generation for ID 19:")
        print(f"Current status: {video.status}")
        print(f"Prompt: {video.prompt}")
        print(f"Veo Job ID: {video.veo_job_id}")
        print()
        
        # Reset the video to pending status
        video.status = 'pending'
        video.veo_job_id = None
        video.started_at = None
        video.completed_at = None
        db.session.commit()
        
        print("🚀 Starting real video generation with detailed logging...")
        print("⚠️  This will make actual API calls and may incur charges!")
        print()
        
        try:
            result = generate_video_task(video.id)
            print(f"✅ Video generation result: {result}")
            
            # Check final status
            video = Video.query.get(19)
            print(f"📊 Final status: {video.status}")
            print(f"🔗 Final slug: {video.slug}")
            print(f"🎥 Video URL: {video.gcs_signed_url}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    restart_real_video() 