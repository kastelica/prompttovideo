import os
import sys
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User

# Force production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Set Cloud SQL connection string
os.environ['DATABASE_URL'] = 'postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo'

def fix_missing_thumbnail_gcs_urls():
    """Fix videos missing thumbnail_gcs_url entries"""
    print("🔧 FIXING MISSING THUMBNAIL GCS URLS")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # Get videos missing thumbnail_gcs_url
        videos_without_gcs = Video.query.filter(
            Video.thumbnail_url.isnot(None),
            Video.thumbnail_gcs_url.is_(None)
        ).all()
        
        if not videos_without_gcs:
            print("✅ No videos found missing thumbnail_gcs_url")
            return
        
        print(f"📋 Found {len(videos_without_gcs)} videos missing thumbnail_gcs_url")
        print()
        
        # Track changes
        updated_count = 0
        errors = []
        
        for video in videos_without_gcs:
            print(f"🎬 Processing Video ID {video.id}: {video.title or video.prompt[:50]}...")
            print(f"   Current thumbnail_url: {video.thumbnail_url}")
            
            # Extract GCS URL from the public URL
            # Handle the pattern: https://storage.googleapis.com/prompt-veo-videos/archive/20250803_050844/thumbnails/15.jpg
            # Convert to: gs://prompt-veo-videos/thumbnails/15.jpg
            
            if video.thumbnail_url and 'storage.googleapis.com' in video.thumbnail_url:
                # Remove query parameters
                clean_url = video.thumbnail_url.split('?')[0]
                
                # Extract the filename from the archive path
                if '/archive/' in clean_url and '/thumbnails/' in clean_url:
                    # Split by /thumbnails/ to get the filename
                    parts = clean_url.split('/thumbnails/')
                    if len(parts) > 1:
                        thumbnail_filename = parts[1]
                        gcs_url = f"gs://prompt-veo-videos/thumbnails/{thumbnail_filename}"
                        
                        print(f"   Generated GCS URL: {gcs_url}")
                        
                        try:
                            # Update the database
                            video.thumbnail_gcs_url = gcs_url
                            video.updated_at = datetime.now(timezone.utc)
                            db.session.commit()
                            
                            print(f"   ✅ Successfully updated thumbnail_gcs_url")
                            updated_count += 1
                            
                        except Exception as e:
                            print(f"   ❌ Error updating database: {str(e)}")
                            db.session.rollback()
                            errors.append({
                                'video_id': video.id,
                                'error': str(e)
                            })
                    else:
                        print(f"   ⚠️ Could not parse thumbnail URL structure")
                        errors.append({
                            'video_id': video.id,
                            'error': 'Could not parse thumbnail URL structure'
                        })
                else:
                    print(f"   ⚠️ Unexpected thumbnail URL format: {clean_url}")
                    errors.append({
                        'video_id': video.id,
                        'error': f'Unexpected thumbnail URL format: {clean_url}'
                    })
            else:
                print(f"   ⚠️ No valid thumbnail URL found")
                errors.append({
                    'video_id': video.id,
                    'error': 'No valid thumbnail URL found'
                })
            
            print()
        
        # Print summary
        print("📊 UPDATE SUMMARY")
        print("=" * 50)
        print(f"Successfully updated: {updated_count}")
        print(f"Errors: {len(errors)}")
        
        if errors:
            print("\n❌ ERRORS:")
            for error in errors:
                print(f"   - Video ID {error['video_id']}: {error['error']}")
        
        if updated_count > 0:
            print(f"\n✅ Successfully fixed {updated_count} videos!")
            print("🎯 Next steps:")
            print("   • Run the comparison script again to verify fixes")
            print("   • Consider updating signed URLs if needed")
        else:
            print("\n⚠️ No videos were updated. Check the errors above.")

def main():
    print("🔧 FIX MISSING THUMBNAIL GCS URLS")
    print("=" * 50)
    
    try:
        fix_missing_thumbnail_gcs_urls()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 