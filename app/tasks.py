from flask import current_app
from app import create_app, db
from app.models import Video, User, CreditTransaction
from app.email_utils import send_video_complete_email
from app.gcs_utils import generate_video_filename, upload_file_to_gcs, generate_thumbnail_filename, get_gcs_bucket_name, parse_gcs_filename
from app.veo_client import VeoClient # Use the centralized client
import requests
import json
import time
from google.cloud import storage
from datetime import datetime, timedelta
import os
from google.auth import default
from google.auth.transport.requests import Request

def generate_video_task(video_id):
    """Generate video using Veo API"""
    from flask import current_app
    
    if current_app:
        return _generate_video_task(video_id)
    
    from app import create_app
    config_name = 'testing' if os.environ.get('FLASK_ENV') == 'testing' else None
    app = create_app(config_name)
    with app.app_context():
        return _generate_video_task(video_id)

def _generate_video_task(video_id):
    """Internal function to generate video (with extensive logging)"""
    from app import db
    from app.models import Video, User
    from datetime import datetime
    import time
    
    try:
        video = Video.query.get(video_id)
        if not video:
            print(f"❌ Video {video_id} not found")
            return False
        
        user = User.query.get(video.user_id)
        if not user:
            print(f"❌ User {video.user_id} not found")
            return False
        
        # DUPLICATE PREVENTION: Check if video is already being processed
        if video.status == 'processing':
            print(f"⚠️ Video {video_id} is already being processed. Skipping duplicate generation.")
            return True  # Return True to avoid marking as failed
        
        if video.status == 'completed':
            print(f"✅ Video {video_id} is already completed. Skipping duplicate generation.")
            return True
        
        if video.veo_job_id:
            print(f"⚠️ Video {video_id} already has a Veo job ID: {video.veo_job_id}. Skipping duplicate generation.")
            return True
        
        print(f"🎬 Starting video generation for video {video_id}")
        
        video.status = 'processing'
        video.processing_started_at = datetime.utcnow()
        db.session.commit()
        print(f"✅ Updated video status to processing")
        
        # Step 1: Call Veo API using the new VeoClient
        print(f"📋 Step 1/6: Calling Veo API via VeoClient...")
        veo_client = VeoClient()
        result = veo_client.generate_video(video.prompt, video.quality)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to start video generation')
            print(f"❌ Failed to get operation name from Veo API: {error_msg}")
            video.status = 'failed'
            video.error_message = error_msg
            db.session.commit()
            return False
        
        operation_name = result['operation_name']
        print(f"✅ Veo API operation created: {operation_name}")
        video.veo_job_id = operation_name
        db.session.commit()
        
        # Step 2: Poll for completion
        print(f"📋 Step 2/6: Polling for video completion...")
        video_url = None
        max_attempts = 60
        attempts = 0
        
        while attempts < max_attempts:
            # check_veo_status already uses the new client
            status_result = check_veo_status(operation_name)
            if status_result and status_result.get('status') == 'completed':
                video_url = status_result.get('video_url')
                print(f"✅ Video completed: {video_url}")
                break
            elif status_result and status_result.get('status') == 'content_violation':
                print(f"🚫 Content policy violation detected: {status_result.get('details', 'Unknown violation')}")
                video.status = 'content_violation'
                video.error_message = f"Content policy violation: {status_result.get('details', 'Your prompt violated content guidelines. Please try rephrasing it.')}"
                db.session.commit()
                return False
            elif status_result and status_result.get('status') == 'failed':
                print(f"❌ Video generation failed during polling: {status_result.get('error')}")
                video.status = 'failed'
                video.error_message = status_result.get('error', 'Polling failed')
                db.session.commit()
                return False
            
            print(f"⏳ Video still processing... (attempt {attempts + 1}/{max_attempts})")
            time.sleep(5)
            attempts += 1
        
        if not video_url:
            print(f"❌ Video generation timed out after {max_attempts} attempts")
            video.status = 'failed'
            video.error_message = 'Video generation timed out'
            db.session.commit()
            return False
        
        # Step 3: Process video data (download from GCS)
        print(f"📋 Step 3/6: Downloading video from GCS...")
        local_path = download_video_from_gcs(video_url)
        if not local_path:
            print(f"❌ Failed to download video from GCS")
            video.status = 'failed'
            video.error_message = 'Failed to download video from GCS'
            db.session.commit()
            return False
        print(f"✅ Video downloaded from GCS to: {local_path}")
        
        # Step 4: Upload to GCS with organized naming
        print(f"📋 Step 4/6: Re-uploading to organized path in GCS...")
        gcs_path, filename, organized_gcs_url = generate_video_filename(
            video_id=video_id,
            quality=video.quality,
            prompt=video.prompt,
            user_id=video.user_id
        )
        
        print(f"📁 Using organized path: {gcs_path}")
        final_gcs_url = upload_file_to_gcs(local_path, gcs_path)
        if not final_gcs_url:
            print(f"❌ Failed to upload to GCS")
            video.status = 'failed'
            video.error_message = 'Failed to upload to cloud storage'
            db.session.commit()
            return False
        
        print(f"✅ Video uploaded to GCS: {final_gcs_url}")
        video.gcs_url = final_gcs_url
        
        # Generate signed URL for video access
        from app.gcs_utils import generate_signed_url
        signed_url = generate_signed_url(final_gcs_url, duration_days=7)
        if signed_url:
            video.gcs_signed_url = signed_url
            print(f"✅ Signed URL generated: {signed_url[:100]}...")
        else:
            print(f"⚠️ Failed to generate signed URL")
        
        # Step 5: Clean up original Veo API file
        print(f"📋 Step 5/6: Cleaning up original Veo API file...")
        try:
            from app.gcs_utils import delete_gcs_file
            if video_url and video_url != final_gcs_url:
                print(f"🗑️ Deleting original Veo API file: {video_url}")
                delete_gcs_file(video_url)
                print(f"✅ Original Veo API file deleted")
            else:
                print(f"ℹ️ No original file to clean up")
        except Exception as e:
            print(f"⚠️ Failed to clean up original file: {e}")
        
        # Step 6: Generate thumbnail
        print(f"📋 Step 6/7: Generating thumbnail...")
        try:
            thumbnail_url = generate_video_thumbnail_from_gcs(final_gcs_url, video_id, video.quality, video.prompt)
            if thumbnail_url:
                print(f"✅ Thumbnail generated: {thumbnail_url}")
                # Save thumbnail URL to video record
                video.thumbnail_gcs_url = thumbnail_url
                # Generate public URL for the thumbnail
                from app.gcs_utils import generate_signed_url
                thumbnail_public_url = generate_signed_url(thumbnail_url, duration_days=365)
                if thumbnail_public_url:
                    video.thumbnail_url = thumbnail_public_url
                    print(f"✅ Thumbnail public URL generated: {thumbnail_public_url[:100]}...")
            else:
                print(f"⚠️ Failed to generate thumbnail, will use fallback")
                # Set a placeholder thumbnail URL
                video.thumbnail_url = f"https://via.placeholder.com/320x180/000000/FFFFFF?text=Video+{video_id}"
                print(f"✅ Set placeholder thumbnail: {video.thumbnail_url}")
        except Exception as e:
            print(f"⚠️ Error generating thumbnail: {e}")
            # Set a placeholder thumbnail URL as fallback
            video.thumbnail_url = f"https://via.placeholder.com/320x180/000000/FFFFFF?text=Video+{video_id}"
            print(f"✅ Set fallback placeholder thumbnail: {video.thumbnail_url}")
        
        # Step 7: Update video status
        print(f"📋 Step 7/7: Finalizing video...")
        video.status = 'completed'
        video.completed_at = datetime.utcnow()
        video.processing_duration = (video.completed_at - video.processing_started_at).total_seconds()
        db.session.commit()
                
        print(f"🎉 Video {video_id} completed successfully!")
                
        # Send completion email
        try:
            send_video_complete_email(user.email, video.id, final_gcs_url)
            print(f"📧 Completion email sent to {user.email}")
        except Exception as e:
            print(f"⚠️ Failed to send completion email: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in video generation task: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        try:
            video.status = 'failed'
            video.error_message = str(e)
            db.session.commit()
        except:
            pass
        return False

def check_veo_status(operation_name):
    """Check Veo API operation status using the centralized client."""
    try:
        veo_client = VeoClient()
        return veo_client.check_video_status(operation_name)
    except Exception as e:
        print(f"❌ Error checking Veo status: {e}")
        return {'success': False, 'error': str(e)}

def generate_video_thumbnail_from_gcs(gcs_url, video_id, quality='free', prompt=None):
    """Generate thumbnail from GCS video URL and upload to GCS"""
    try:
        from app.video_processor import VideoProcessor
        import tempfile
        
        print(f"🖼️ Generating thumbnail for video {video_id} from GCS: {gcs_url}")
        
        thumbnail_path, _, _ = generate_thumbnail_filename(video_id, quality, prompt)
        
        temp_video_path = download_video_from_gcs(gcs_url)
        if not temp_video_path:
            print(f"❌ Failed to download video from GCS")
            return None
        
        temp_thumbnail_path = tempfile.mktemp(suffix='.jpg')
        
        try:
            # Try different time offsets if the first one fails
            time_offsets = ["00:00:05", "00:00:10", "00:00:15", "00:00:30"]
            
            for offset in time_offsets:
                print(f"🔄 Trying thumbnail generation at {offset}...")
                success = VideoProcessor.generate_thumbnail(temp_video_path, temp_thumbnail_path, offset)
                if success:
                    print(f"✅ Thumbnail generated successfully at {offset}")
                    break
                else:
                    print(f"⚠️ Failed to generate thumbnail at {offset}, trying next...")
            
            if not success:
                print(f"❌ Failed to generate thumbnail at all time offsets")
                return None
            
            # Upload thumbnail to GCS
            thumbnail_gcs_url = upload_file_to_gcs(temp_thumbnail_path, thumbnail_path)
            if thumbnail_gcs_url:
                print(f"✅ Thumbnail uploaded to GCS: {thumbnail_gcs_url}")
                return thumbnail_gcs_url
            else:
                print(f"❌ Failed to upload thumbnail to GCS")
                return None
                
        finally:
            # Clean up temporary files
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
                print(f"🧹 Cleaned up temporary video file")
            if os.path.exists(temp_thumbnail_path):
                os.unlink(temp_thumbnail_path)
                print(f"🧹 Cleaned up temporary thumbnail file")
        
    except Exception as e:
        print(f"❌ Error generating thumbnail from GCS: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return None

def download_video_from_gcs(gcs_url):
    """Download video from GCS to a temporary local file."""
    try:
        import tempfile
        
        parsed = parse_gcs_filename(gcs_url)
        bucket_name = parsed['bucket_name']
        file_path = parsed['full_path']
        
        # storage.Client() will use Application Default Credentials
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            print(f"❌ Video not found in GCS: {gcs_url}")
            return None
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        blob.download_to_filename(temp_file.name)
        temp_file.close()
        
        print(f"✅ Video downloaded to: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        print(f"❌ Error downloading video from GCS: {e}")
        return None

def create_text_thumbnail_fallback(video_id):
    """Create a text-based thumbnail as fallback"""
    return f"https://via.placeholder.com/320x180/000000/FFFFFF?text=Video+{video_id}"

# Note: The functions `download_video_to_local`, `create_mock_video_file`, 
# `generate_video_thumbnail`, `process_priority_queue`, and `get_queue_stats` 
# were either unused, for mock purposes, or have been integrated into the main flow.
# They are removed for clarity and to avoid confusion.
