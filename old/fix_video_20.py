#!/usr/bin/env python3
"""
Fix video ID 20 to make it public and accessible
"""

from app import create_app, db
from app.models import Video

def fix_video_20():
    """Fix video ID 20"""
    app = create_app()
    
    with app.app_context():
        video = Video.query.get(20)
        if not video:
            print("❌ Video ID 20 not found")
            return
        
        print(f"🔧 Fixing video ID 20:")
        print(f"Current status: {video.status}")
        print(f"Current slug: {video.slug}")
        print(f"Current public: {video.public}")
        
        # Make it public
        video.public = True
        
        # Ensure proper slug
        if video.slug.startswith('temp-') or not video.slug:
            video.ensure_slug()
        
        db.session.commit()
        
        print(f"✅ Fixed video ID 20:")
        print(f"New slug: {video.slug}")
        print(f"New public: {video.public}")
        print(f"Watch URL: /watch/{video.id}-{video.slug}")

if __name__ == '__main__':
    fix_video_20() 