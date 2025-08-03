#!/usr/bin/env python3
"""
Script to generate thumbnails for existing videos that don't have thumbnails.
This will process all videos with GCS URLs but no thumbnails.
"""

import os
import sys
from app import create_app, db
from app.models import Video
from app.tasks import generate_video_thumbnail_from_gcs

def main():
    """Generate thumbnails for existing videos"""
    app = create_app()
    
    with app.app_context():
        # Get videos that have GCS URLs but no thumbnails
        videos = Video.query.filter(
            Video.gcs_signed_url.isnot(None),
            Video.gcs_signed_url != '',
            (Video.thumbnail_url.is_(None) | (Video.thumbnail_url == ''))
        ).all()
        
        print(f"Found {len(videos)} videos without thumbnails")
        
        if not videos:
            print("No videos need thumbnails!")
            return
        
        successful = 0
        failed = 0
        
        for video in videos:
            print(f"\nProcessing video ID {video.id}: {video.prompt[:50]}...")
            
            try:
                # Generate thumbnail from GCS video
                thumbnail_url = generate_video_thumbnail_from_gcs(video.gcs_url, video.id)
                
                if thumbnail_url:
                    # Update database
                    video.thumbnail_url = thumbnail_url
                    db.session.commit()
                    
                    print(f"  ✅ Success! Thumbnail: {thumbnail_url}")
                    successful += 1
                else:
                    print(f"  ❌ Failed to generate thumbnail")
                    failed += 1
                    
            except Exception as e:
                print(f"  ❌ Error processing video: {e}")
                failed += 1
        
        print(f"\n🎉 Thumbnail generation complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        
        # Show final stats
        total_with_thumbnails = Video.query.filter(
            Video.thumbnail_url.isnot(None),
            Video.thumbnail_url != ''
        ).count()
        
        total_videos = Video.query.filter(
            Video.gcs_signed_url.isnot(None),
            Video.gcs_signed_url != ''
        ).count()
        
        print(f"\n📊 Final Statistics:")
        print(f"   Total videos with GCS URLs: {total_videos}")
        print(f"   Videos with thumbnails: {total_with_thumbnails}")
        print(f"   Coverage: {(total_with_thumbnails/total_videos)*100:.1f}%")

if __name__ == "__main__":
    main() 