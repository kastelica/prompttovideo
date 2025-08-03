from app import create_app, db
from app.models import Video
from app.tasks import generate_video_thumbnail_from_gcs
import os

app = create_app()

with app.app_context():
    print("🔄 Regenerating thumbnails for existing videos and uploading to GCS...")
    
    # Get all completed videos with GCS URLs
    videos = Video.query.filter_by(status='completed', public=True).filter(
        Video.gcs_signed_url.isnot(None),
        Video.gcs_signed_url != ''
    ).all()
    
    print(f"📊 Found {len(videos)} videos with GCS URLs")
    
    updated_count = 0
    error_count = 0
    
    for video in videos:
        try:
            print(f"🖼️ Processing video {video.id}: {video.prompt[:50]}...")
            
            # Generate new thumbnail and upload to GCS
            new_thumbnail_url = generate_video_thumbnail_from_gcs(video.gcs_url, video.id)
            
            if new_thumbnail_url:
                # Update the video record
                video.thumbnail_url = new_thumbnail_url
                db.session.commit()
                print(f"✅ Video {video.id}: Thumbnail updated to {new_thumbnail_url}")
                updated_count += 1
            else:
                print(f"❌ Video {video.id}: Failed to generate thumbnail")
                error_count += 1
                
        except Exception as e:
            print(f"❌ Video {video.id}: Error - {e}")
            error_count += 1
            db.session.rollback()
    
    print(f"\n📈 Summary:")
    print(f"✅ Successfully updated: {updated_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total processed: {len(videos)}")
    
    # Verify the results
    videos_with_gcs = Video.query.filter_by(status='completed', public=True).filter(
        Video.gcs_signed_url.isnot(None),
        Video.gcs_signed_url != ''
    ).all()
    
    videos_with_thumbnails = [v for v in videos_with_gcs if v.thumbnail_url and v.thumbnail_url.startswith('https://storage.googleapis.com/')]
    
    print(f"\n🔍 Verification:")
    print(f"Videos with GCS URLs: {len(videos_with_gcs)}")
    print(f"Videos with GCS thumbnails: {len(videos_with_thumbnails)}")
    print(f"Coverage: {len(videos_with_thumbnails)}/{len(videos_with_gcs)} = {len(videos_with_thumbnails)/len(videos_with_gcs)*100:.1f}%") 