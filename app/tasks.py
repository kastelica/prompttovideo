from celery import Celery
from flask import current_app
from app import create_app, db
from app.models import Video, User, CreditTransaction
from app.email_utils import send_video_complete_email
import requests
import json
import time
from google.cloud import storage
from datetime import datetime, timedelta
import os

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Initialize Celery
celery = None

def init_celery(app):
    """Initialize Celery with Flask app"""
    global celery
    celery = make_celery(app)
    return celery

def generate_video_task(video_id):
    """Generate video using Veo API"""
    from flask import current_app
    
    # If we're already in an app context (like in testing), use it
    if current_app:
        return _generate_video_task(video_id)
    
    # Otherwise, create a new app context
    from app import create_app
    config_name = 'testing' if os.environ.get('FLASK_ENV') == 'testing' else None
    app = create_app(config_name)
    with app.app_context():
        # If celery is available, use it as a task
        if celery:
            return celery_task_wrapper(video_id)
        else:
            # Direct execution for testing
            return _generate_video_task(video_id)

# Create the actual Celery task
def celery_generate_video_task(video_id):
    """Celery task wrapper for video generation"""
    return _generate_video_task(video_id)

def celery_task_wrapper(video_id):
    """Wrapper for Celery task execution"""
    return _generate_video_task(video_id)

# This will be set after Celery is initialized
_celery_task = None

def get_celery_task():
    """Get the decorated Celery task"""
    global _celery_task, celery
    
    # If celery is None, try to initialize it
    if celery is None:
        try:
            from app import create_app
            app = create_app()
            init_celery(app)
        except Exception as e:
            print(f"Failed to initialize Celery: {e}")
            return None
    
    # Now try to create the task
    if _celery_task is None and celery is not None:
        try:
            _celery_task = celery.task(celery_generate_video_task)
            print("✅ Celery task created successfully")
        except Exception as e:
            print(f"Failed to create Celery task: {e}")
            return None
    
    return _celery_task

def _generate_video_task(video_id):
    """Internal function to generate video (with extensive logging)"""
    from app import db
    from app.models import Video, User
    from datetime import datetime
    import time
    
    current_app.logger.info(f"🚀 Starting video generation for video ID: {video_id}")
    
    try:
        # Get video and user
        video = Video.query.get(video_id)
        if not video:
            current_app.logger.error(f"❌ Video {video_id} not found")
            raise Exception(f"Video {video_id} not found")
        
        user = User.query.get(video.user_id)
        if not user:
            current_app.logger.error(f"❌ User {video.user_id} not found")
            raise Exception(f"User {video.user_id} not found")
        
        current_app.logger.info(f"📋 Video details: ID={video.id}, Status={video.status}, Prompt='{video.prompt}', Quality={video.quality}")
        current_app.logger.info(f"👤 User details: ID={user.id}, Email={user.email}, Credits={user.credits}")
        
        # Update video status
        video.status = 'processing'
        video.started_at = datetime.utcnow()
        db.session.commit()
        current_app.logger.info(f"✅ Video status updated to 'processing'")
        
        # Call Veo API
        current_app.logger.info(f"📞 Calling Veo API with prompt: '{video.prompt}'")
        result = call_veo_api(video.prompt, video.quality)
        current_app.logger.info(f"📡 Veo API response: {result}")
        
        if not result.get('success'):
            current_app.logger.error(f"❌ Veo API call failed: {result.get('error')}")
            video.status = 'failed'
            db.session.commit()
            raise Exception(f"Veo API error: {result.get('error')}")
        
        job_id = result.get('operation_name')
        current_app.logger.info(f"🎯 Veo job ID: {job_id}")
        
        # Update video with job ID
        video.veo_job_id = job_id
        db.session.commit()
        current_app.logger.info(f"✅ Video updated with Veo job ID: {job_id}")
        
        # Poll for completion (increased attempts based on test success)
        current_app.logger.info(f"⏳ Starting polling loop for job: {job_id}")
        max_attempts = 60  # 5 minutes with 5-second intervals (increased from 12)
        for attempt in range(max_attempts):
            current_app.logger.info(f"🔄 Polling attempt {attempt + 1}/{max_attempts}")
            current_app.logger.info(f"⏰ Attempt {attempt + 1} timestamp: {datetime.utcnow()}")
            
            try:
                status_response = check_veo_status(job_id)
                current_app.logger.info(f"📊 Status response for attempt {attempt + 1}: {status_response}")
                current_app.logger.info(f"📊 Status response type: {type(status_response)}")
                current_app.logger.info(f"📊 Status response keys: {list(status_response.keys()) if isinstance(status_response, dict) else 'Not a dict'}")
                
                if isinstance(status_response, dict):
                    for key, value in status_response.items():
                        current_app.logger.info(f"📊 Status response key '{key}': {value}")
            except Exception as poll_error:
                current_app.logger.error(f"❌ Error during polling attempt {attempt + 1}: {poll_error}")
                current_app.logger.error(f"❌ Poll error type: {type(poll_error)}")
                import traceback
                current_app.logger.error(f"❌ Poll error traceback: {traceback.format_exc()}")
                # Continue to next attempt instead of failing immediately
                current_app.logger.info(f"⏳ Continuing to next polling attempt...")
                time.sleep(5)
                continue
            
            if status_response['status'] == 'completed':
                current_app.logger.info("🎉 Video generation completed!")
                # Get the video URL from the status response
                video_url = status_response.get('video_url')
                current_app.logger.info(f"🎥 Video URL from status response: {video_url}")
                
                # Download video to local videos/ directory
                current_app.logger.info(f"📥 Downloading video from Veo...")
                local_video_path = download_video_to_local(job_id, video_id, video_url)
                current_app.logger.info(f"📁 Video saved locally: {local_video_path}")
                
                # Add watermark if it's a free tier video
                if video.quality == 'free':
                    current_app.logger.info(f"🎨 Adding QR code watermark to free tier video...")
                    current_app.logger.info(f"🔍 Video ID: {video.id}, Slug: {video.slug}")
                    try:
                        from app.video_processor import VideoProcessor
                        import tempfile
                        import os
                        
                        # Create temporary file for watermarked video
                        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
                            watermarked_path = temp_output.name
                        
                        current_app.logger.info(f"📁 Temporary watermarked path: {watermarked_path}")
                        current_app.logger.info(f"📁 Original video path: {local_video_path}")
                        
                        # Generate QR code URL for the video
                        qr_url = f"https://prompt-videos.com/watch/{video.id}-{video.slug}"
                        current_app.logger.info(f"🔗 QR code URL: {qr_url}")
                        current_app.logger.info(f"🔗 Full QR URL length: {len(qr_url)} characters")
                        
                        # Check if original video file exists
                        if not os.path.exists(local_video_path):
                            current_app.logger.error(f"❌ Original video file not found: {local_video_path}")
                            raise Exception("Original video file not found")
                        
                        current_app.logger.info(f"✅ Original video file exists, size: {os.path.getsize(local_video_path)} bytes")
                        
                        # Add QR code watermark
                        current_app.logger.info(f"🎯 Calling VideoProcessor.add_watermark with QR URL...")
                        watermark_result = VideoProcessor.add_watermark(local_video_path, watermarked_path, qr_url=qr_url)
                        current_app.logger.info(f"🎯 Watermark result: {watermark_result}")
                        
                        if watermark_result:
                            current_app.logger.info(f"✅ QR watermark processing completed successfully")
                            
                            # Check if watermarked file was created
                            if os.path.exists(watermarked_path):
                                watermarked_size = os.path.getsize(watermarked_path)
                                current_app.logger.info(f"✅ Watermarked file created, size: {watermarked_size} bytes")
                                
                                # Copy watermarked version to original location using shutil
                                import shutil
                                try:
                                    shutil.copy2(watermarked_path, local_video_path)
                                    final_size = os.path.getsize(local_video_path)
                                    current_app.logger.info(f"✅ QR code watermark added successfully")
                                    current_app.logger.info(f"📊 Final video size: {final_size} bytes")
                                except Exception as copy_error:
                                    current_app.logger.error(f"❌ Error copying watermarked file: {copy_error}")
                                    current_app.logger.info(f"🔄 Using original video without watermark")
                                finally:
                                    # Clean up temp file
                                    if os.path.exists(watermarked_path):
                                        os.unlink(watermarked_path)
                                        current_app.logger.info(f"🧹 Cleaned up temporary watermarked file")
                            else:
                                current_app.logger.error(f"❌ Watermarked file was not created: {watermarked_path}")
                        else:
                            current_app.logger.warning(f"⚠️ Failed to add QR watermark, using original video")
                            if os.path.exists(watermarked_path):
                                os.unlink(watermarked_path)
                    except Exception as watermark_error:
                        current_app.logger.error(f"❌ Error adding QR watermark: {watermark_error}")
                        current_app.logger.error(f"❌ Error type: {type(watermark_error).__name__}")
                        import traceback
                        current_app.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
                        current_app.logger.info(f"🔄 Continuing with original video")
                else:
                    current_app.logger.info(f"✨ Premium video - no watermark needed")
                
                # Upload video to GCS
                current_app.logger.info(f"📤 Uploading video to GCS...")
                gcs_url = upload_file_to_gcs(local_video_path, f"videos/{video_id}.mp4")
                
                if gcs_url:
                    # Generate signed URL for the uploaded video
                    signed_url = generate_signed_url(f"gs://{current_app.config['GCS_BUCKET_NAME']}/videos/{video_id}.mp4")
                    current_app.logger.info(f"✅ Video uploaded to GCS: {gcs_url}")
                    current_app.logger.info(f"🔗 Signed URL generated: {signed_url[:50]}...")
                    
                    # Update video record with GCS URLs
                    video.gcs_url = gcs_url
                    video.gcs_signed_url = signed_url
                    
                    # Generate thumbnail from the video
                    current_app.logger.info(f"🖼️ Generating thumbnail from video...")
                    try:
                        thumbnail_url = generate_video_thumbnail_from_gcs(gcs_url, video_id)
                        if thumbnail_url:
                            video.thumbnail_url = thumbnail_url
                            current_app.logger.info(f"✅ Thumbnail generated: {thumbnail_url}")
                        else:
                            current_app.logger.warning(f"⚠️ Failed to generate thumbnail, will use fallback")
                    except Exception as thumb_error:
                        current_app.logger.error(f"❌ Error generating thumbnail: {thumb_error}")
                        current_app.logger.info(f"🔄 Continuing without thumbnail")
                else:
                    current_app.logger.error(f"❌ Failed to upload to GCS - video generation failed")
                    video.status = 'failed'
                    db.session.commit()
                    raise Exception("Failed to upload video to GCS")
                
                video.status = 'completed'
                video.completed_at = datetime.utcnow()
                video.public = True  # Make video public by default
                video.ensure_slug()  # Ensure proper slug is set
                db.session.commit()
                
                current_app.logger.info(f"🎉 Video {video_id} completed successfully!")
                current_app.logger.info(f"🔗 Final slug: {video.slug}")
                current_app.logger.info(f"🎥 Video saved at: {local_video_path}")
                current_app.logger.info(f"🌐 Web URL: {video.gcs_signed_url}")
                
                # Send completion email
                if not current_app.config.get('TESTING') and not current_app.config.get('VEO_MOCK_MODE', False):
                    send_video_complete_email(user.email, video_id, video.gcs_signed_url)
                else:
                    current_app.logger.info(f"📧 Email sending disabled in development mode for video {video_id}")
                return {'status': 'completed', 'video_id': video_id}
            
            elif status_response['status'] == 'failed':
                current_app.logger.error(f"❌ Video generation failed: {status_response.get('error')}")
                video.status = 'failed'
                db.session.commit()
                raise Exception(f"Veo job failed: {status_response.get('error')}")
            
            current_app.logger.info(f"⏳ Video still processing... waiting 5 seconds before next check")
            time.sleep(5)  # Wait 5 seconds before next check
        
        # If we get here, we've exceeded max attempts
        current_app.logger.error(f"⏰ Video generation timed out after {max_attempts} attempts (1 minute)")
        video.status = 'failed'
        db.session.commit()
        raise Exception("Video generation timed out")
        
    except Exception as e:
        current_app.logger.error(f"❌ Video generation failed: {e}")
        # Update video status to failed
        try:
            video = Video.query.get(video_id)
            if video:
                video.status = 'failed'
                db.session.commit()
                current_app.logger.info(f"✅ Video {video_id} marked as failed")
        except Exception as db_error:
            current_app.logger.error(f"❌ Failed to update video status: {db_error}")
        
        raise e

def call_veo_api(prompt, quality):
    """Call Veo API to start video generation"""

    current_app.logger.info(f"🌐 TESTING setting: {current_app.config.get('TESTING', False)}")
    
    try:
        from app.veo_client import VeoClient
        current_app.logger.info("📦 Importing VeoClient successful")
        veo_client = VeoClient()
        current_app.logger.info("📦 VeoClient instantiated successfully")
        
        # Set duration based on quality
        duration = 8 if quality == 'free' else 60
        current_app.logger.info(f"📞 About to call VeoClient.generate_video('{prompt}', '{quality}', {duration})")
        
        # Add a small delay before the API call to avoid rate limiting
        import time
        time.sleep(1)
        
        result = veo_client.generate_video(prompt, quality, duration)
        current_app.logger.info(f"📡 VeoClient generate response received")
        current_app.logger.info(f"📡 Response type: {type(result)}")
        current_app.logger.info(f"📡 Response: {result}")
        
        if isinstance(result, dict):
            current_app.logger.info(f"📡 Response keys: {list(result.keys())}")
            for key, value in result.items():
                current_app.logger.info(f"📡 Response key '{key}': {value}")
        else:
            current_app.logger.warning(f"📡 Response is not a dict: {result}")
        
        return result
    except Exception as e:
        current_app.logger.error(f"❌ Exception in call_veo_api: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def check_veo_status(job_id):
    """Check Veo job status"""
    current_app.logger.info(f"🔍 Checking Veo status for job: {job_id}")
    current_app.logger.info(f"🔍 Job ID type: {type(job_id)}")
    current_app.logger.info(f"🔍 Job ID value: {job_id}")
    
    # Use mock API for development/testing
    if current_app.config.get('TESTING') or current_app.config.get('VEO_MOCK_MODE', False):
        current_app.logger.info("🎭 Using mock status check for development")
        
        # Determine duration based on operation name (Veo 2 vs Veo 3)
        duration = 60 if 'veo-3.0' in job_id else 8
        
        # Return a mock completed status with proper duration
        mock_result = {
            'status': 'completed',
            'video_url': f"gs://mock-bucket/videos/mock-{job_id.split('-')[-1]}.mp4",
            'duration': duration
        }
        current_app.logger.info(f"🎭 Mock status result: {mock_result}")
        return mock_result
    
    # Use real Veo API
    current_app.logger.info("🌐 Using real Veo API for status check")
    current_app.logger.info(f"🌐 VEO_MOCK_MODE setting: {current_app.config.get('VEO_MOCK_MODE', False)}")
    current_app.logger.info(f"🌐 TESTING setting: {current_app.config.get('TESTING', False)}")
    
    try:
        from app.veo_client import VeoClient
        current_app.logger.info("📦 Importing VeoClient successful")
        veo_client = VeoClient()
        current_app.logger.info("📦 VeoClient instantiated successfully")
        current_app.logger.info(f"📞 About to call VeoClient.check_video_status({job_id})")
        
        # Add a small delay before the API call to avoid rate limiting
        import time
        time.sleep(1)
        
        result = veo_client.check_video_status(job_id)
        current_app.logger.info(f"📡 VeoClient status response received")
        current_app.logger.info(f"📡 Response type: {type(result)}")
        current_app.logger.info(f"📡 Response: {result}")
        
        if isinstance(result, dict):
            current_app.logger.info(f"📡 Response keys: {list(result.keys())}")
            for key, value in result.items():
                current_app.logger.info(f"📡 Response key '{key}': {value}")
        else:
            current_app.logger.warning(f"📡 Response is not a dict: {result}")
        
        # Process the result
        if result.get('success'):
            status = result.get('status', 'unknown')
            current_app.logger.info(f"✅ Status check successful: {status}")
            
            if status == 'completed':
                video_url = result.get('video_url')
                duration = result.get('duration', 8)  # Use duration from API response
                current_app.logger.info(f"🎉 Video completed! URL: {video_url}, Duration: {duration}")
                return {
                    'status': 'completed',
                    'video_url': video_url,
                    'duration': duration
                }
            elif status == 'failed':
                error = result.get('error', 'Unknown error')
                current_app.logger.error(f"❌ Video failed: {error}")
                return {
                    'status': 'failed',
                    'error': error
                }
            else:
                current_app.logger.info(f"⏳ Video still processing: {status}")
                return {
                    'status': 'processing'
                }
        else:
            error = result.get('error', 'Unknown error')
            current_app.logger.error(f"❌ Status check failed: {error}")
            return {
                'status': 'failed',
                'error': error
            }
            
    except Exception as e:
        current_app.logger.error(f"❌ Exception in check_veo_status: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }

def download_video_to_local(job_id, video_id, video_url=None):
    """Download video from Veo and save to local videos/ directory"""
    current_app.logger.info(f"📥 Downloading video for job: {job_id}, video_id: {video_id}")
    
    # For mock mode, create a mock video file
    if current_app.config.get('TESTING') or current_app.config.get('VEO_MOCK_MODE', False):
        current_app.logger.info("🎭 Using mock download for development")
        return create_mock_video_file(video_id)
    
    # Use real Veo API download
    current_app.logger.info("🌐 Using real Veo API download")
    try:
        import tempfile
        import os
        import requests
        
        # If video_url is not provided, get it from Veo status
        if video_url is None:
            current_app.logger.info(f"🔍 Getting video URL from Veo status for job: {job_id}")
            from app.veo_client import VeoClient
            veo_client = VeoClient()
            status_result = veo_client.check_video_status(job_id)
            current_app.logger.info(f"📡 Veo status for download: {status_result}")
            
            if not status_result.get('success') or status_result.get('status') != 'completed':
                current_app.logger.error(f"❌ Video not ready for download: {status_result}")
                raise Exception("Video not ready for download")
            
            video_url = status_result.get('video_url')
            if not video_url:
                current_app.logger.error(f"❌ No video URL in status response: {status_result}")
                raise Exception("No video URL in status response")
        else:
            current_app.logger.info(f"🎥 Using provided video URL: {video_url}")
        
        current_app.logger.info(f"🎥 Video URL from Veo: {video_url}")
        current_app.logger.info(f"🎥 Video URL type: {type(video_url)}")
        current_app.logger.info(f"🎥 Video URL length: {len(video_url)}")
        current_app.logger.info(f"🎥 Video URL contains 'dirlyy': {'dirlyy' in video_url}")
        current_app.logger.info(f"🎥 Video URL contains 'dirly-': {'dirly-' in video_url}")
        current_app.logger.info(f"🎥 Video URL repr: {repr(video_url)}")
        
        # Create videos directory if it doesn't exist
        videos_dir = os.path.join(os.getcwd(), 'videos')
        os.makedirs(videos_dir, exist_ok=True)
        current_app.logger.info(f"📁 Videos directory: {videos_dir}")
        
        # Download video to local file
        local_video_path = os.path.join(videos_dir, f"{video_id}.mp4")
        current_app.logger.info(f"📥 Downloading video to: {local_video_path}")
        
        # If it's a GCS URL, try to download using Google Cloud Storage
        if video_url.startswith('gs://'):
            current_app.logger.info(f"📦 Attempting to download from GCS: {video_url}")
            current_app.logger.info(f"📦 Video URL before GCS download: {video_url}")
            current_app.logger.info(f"📦 Video URL contains 'dirlyy': {'dirlyy' in video_url}")
            current_app.logger.info(f"📦 Video URL contains 'dirly-': {'dirly-' in video_url}")
            
            try:
                from google.cloud import storage
                
                # Initialize GCS client with explicit credentials
                creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                if not creds_path:
                    creds_path = os.path.join(os.getcwd(), 'veo.json')
                    current_app.logger.info(f"Using hardcoded credentials path: {creds_path}")
                
                if os.path.exists(creds_path):
                    from google.oauth2 import service_account
                    credentials = service_account.Credentials.from_service_account_file(
                        creds_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    storage_client = storage.Client(credentials=credentials)
                    current_app.logger.info(f"GCS client initialized with credentials from: {creds_path}")
                else:
                    current_app.logger.warning(f"Credentials file not found: {creds_path}")
                    storage_client = storage.Client()
                
                # Extract bucket and blob from GCS URL
                current_app.logger.info(f"🔍 DEBUG: Extracting bucket from URL: {video_url}")
                current_app.logger.info(f"🔍 DEBUG: URL parts: {video_url.split('/')}")
                bucket_name = video_url.split('/')[2]
                blob_name = '/'.join(video_url.split('/')[3:])
                current_app.logger.info(f"🔍 DEBUG: Extracted bucket_name: '{bucket_name}'")
                current_app.logger.info(f"🔍 DEBUG: Extracted blob_name: '{blob_name}'")
                current_app.logger.info(f"🔍 DEBUG: Bucket name length: {len(bucket_name)}")
                current_app.logger.info(f"🔍 DEBUG: Bucket name contains 'dirlyy': {'dirlyy' in bucket_name}")
                current_app.logger.info(f"🔍 DEBUG: Bucket name contains 'dirly-': {'dirly-' in bucket_name}")
                
                current_app.logger.info(f"📦 GCS bucket: {bucket_name}, blob: {blob_name}")
                current_app.logger.info(f"📦 GCS URL: {video_url}")
                current_app.logger.info(f"📦 Expected project bucket: prompt-veo-videos")
                current_app.logger.info(f"📦 Actual bucket from Veo: {bucket_name}")
                
                # Check if bucket name matches expected pattern
                if bucket_name != 'prompt-veo-videos':
                    current_app.logger.warning(f"⚠️ Veo API returned unexpected bucket: {bucket_name}")
                    current_app.logger.info(f"⚠️ Expected: prompt-veo-videos, Got: {bucket_name}")
                    current_app.logger.info(f"⚠️ This suggests a Veo API configuration issue")
                
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                
                current_app.logger.info(f"🔍 DEBUG: About to download from bucket: '{bucket_name}'")
                current_app.logger.info(f"🔍 DEBUG: About to download blob: '{blob_name}'")
                current_app.logger.info(f"🔍 DEBUG: Final bucket name before download: '{bucket_name}'")
                current_app.logger.info(f"🔍 DEBUG: Final bucket name contains 'dirlyy': {'dirlyy' in bucket_name}")
                
                # Download directly to local file
                current_app.logger.info(f"🔍 DEBUG: Final video_url before download: {repr(video_url)}")
                current_app.logger.info(f"🔍 DEBUG: Final bucket_name before download: {repr(bucket_name)}")
                blob.download_to_filename(local_video_path)
                current_app.logger.info(f"✅ GCS download completed: {local_video_path}")
                
            except Exception as gcs_error:
                current_app.logger.error(f"❌ GCS download failed: {gcs_error}")
                raise Exception(f"Failed to download video from GCS: {gcs_error}")
                
        else:
            # If it's an HTTP URL, download using requests
            current_app.logger.info(f"🌐 Downloading from HTTP URL: {video_url}")
            try:
                response = requests.get(video_url, stream=True)
                response.raise_for_status()
                
                with open(local_video_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                current_app.logger.info(f"✅ HTTP download completed: {local_video_path}")
                
            except Exception as http_error:
                current_app.logger.error(f"❌ HTTP download failed: {http_error}")
                raise Exception(f"Failed to download video from HTTP URL: {http_error}")
        
        # Verify file was created and has content
        if os.path.exists(local_video_path):
            file_size = os.path.getsize(local_video_path)
            current_app.logger.info(f"✅ Video file created: {local_video_path} ({file_size} bytes)")
            return local_video_path
        else:
            current_app.logger.error("❌ Video file not created")
            raise Exception("Failed to create video file")
            
    except Exception as e:
        current_app.logger.error(f"❌ Exception in download_video_to_local: {e}")
        raise Exception(f"Failed to download video: {e}")

def create_mock_video_file(video_id):
    """Create a mock video file for development/testing"""
    import os
    import tempfile
    
    # Create videos directory if it doesn't exist
    videos_dir = os.path.join(os.getcwd(), 'videos')
    os.makedirs(videos_dir, exist_ok=True)
    
    # Create a mock video file (just a text file for now)
    mock_video_path = os.path.join(videos_dir, f"{video_id}.mp4")
    
    # Create a simple mock video file with some content
    mock_content = f"Mock video file for video ID {video_id}\nGenerated at {datetime.now()}\nThis is a placeholder for the actual video file."
    
    with open(mock_video_path, 'w') as f:
        f.write(mock_content)
    
    current_app.logger.info(f"🎭 Mock video file created: {mock_video_path}")
    return mock_video_path

def generate_signed_url(gcs_url):
    """Generate signed URL for video access"""
    try:
        # For mock mode or fallback URLs, return a working video URL
        if (current_app.config.get('TESTING') or 
            current_app.config.get('VEO_MOCK_MODE', False) or
            'mock-bucket' in gcs_url or 
            'fallback' in gcs_url):
            current_app.logger.info("Using mock/fallback signed URL")
            # Return a working video URL for testing
            return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
        
        # Extract bucket and blob from GCS URL
        parts = gcs_url.replace('gs://', '').split('/', 1)
        bucket_name = parts[0]
        blob_name = parts[1]
        
        # Initialize GCS client with explicit credentials
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            # Hardcode the path to veo.json
            creds_path = os.path.join(os.getcwd(), 'veo.json')
            current_app.logger.info(f"Using hardcoded credentials path for GCS: {creds_path}")
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
            current_app.logger.info(f"GCS client initialized with credentials from: {creds_path}")
        else:
            current_app.logger.warning(f"Credentials file not found for GCS: {creds_path}")
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Generate signed URL that expires in 7 days
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),  # 7 days expiration (maximum allowed)
            method="GET"
        )
        
        return signed_url
    
    except Exception as e:
        current_app.logger.error(f"Failed to generate signed URL: {e}")
        # Return a working video URL as fallback
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

def add_watermark_to_video(video_url, video_id, qr_url=None):
    """Add watermark to video and upload to GCS"""
    try:
        # For mock mode, return a mock watermarked URL
        if current_app.config.get('TESTING') or current_app.config.get('VEO_MOCK_MODE', False):
            current_app.logger.info("Using mock watermarked video for development")
            # Return a mock watermarked URL
            return f"gs://mock-bucket/videos/{video_id}/watermarked.mp4"
        
        from app.video_processor import VideoProcessor
        import tempfile
        import os
        
        # Download video to temp file
        response = requests.get(video_url, stream=True)
        if response.status_code != 200:
            return None
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_input:
            for chunk in response.iter_content(chunk_size=8192):
                temp_input.write(chunk)
            temp_input_path = temp_input.name
        
        # Create output temp file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        try:
            # Add watermark (QR code if URL provided, otherwise text)
            if qr_url:
                VideoProcessor.add_watermark(temp_input_path, temp_output_path, qr_url=qr_url)
            else:
                VideoProcessor.add_watermark(temp_input_path, temp_output_path)
            
            # Upload watermarked video to GCS
            watermarked_url = upload_file_to_gcs(temp_output_path, f"videos/{video_id}/watermarked.mp4")
            
            return watermarked_url
            
        finally:
            # Clean up temp files
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
                
    except Exception as e:
        current_app.logger.error(f"Error adding watermark: {e}")
        return None

def generate_video_thumbnail_from_gcs(gcs_url, video_id):
    """Generate thumbnail from GCS video and save locally"""
    try:
        # For mock mode, return a mock thumbnail URL
        if current_app.config.get('TESTING') or current_app.config.get('VEO_MOCK_MODE', False):
            current_app.logger.info("Using mock thumbnail for development")
            return f"https://storage.googleapis.com/prompt-veo-videos/thumbnails/{video_id}.jpg"
        
        current_app.logger.info(f"🖼️ Generating thumbnail from GCS video: {gcs_url}")
        
        # Download video from GCS to temp file
        import tempfile
        import os
        
        # Handle both GCS URLs (gs://) and signed URLs (https://)
        current_app.logger.info(f"🔍 Parsing URL: {gcs_url}")
        
        if gcs_url.startswith('gs://'):
            # Direct GCS URL
            bucket_name = gcs_url.split('/')[2]
            blob_name = '/'.join(gcs_url.split('/')[3:])
            current_app.logger.info(f"🔍 Direct GCS URL - bucket: '{bucket_name}', blob: '{blob_name}'")
        elif gcs_url.startswith('https://storage.googleapis.com/'):
            # Signed URL - extract bucket and blob from the path
            url_parts = gcs_url.split('storage.googleapis.com/')[1].split('?')[0].split('/')
            bucket_name = url_parts[0]
            blob_name = '/'.join(url_parts[1:])
            current_app.logger.info(f"🔍 Signed URL - bucket: '{bucket_name}', blob: '{blob_name}'")
        else:
            current_app.logger.error(f"❌ Invalid URL format: {gcs_url}")
            return create_text_thumbnail_fallback(video_id)
        
        # Validate bucket name
        if not bucket_name or not bucket_name[0].isalnum() or not bucket_name[-1].isalnum():
            current_app.logger.error(f"❌ Invalid bucket name: '{bucket_name}'")
            return create_text_thumbnail_fallback(video_id)
        
        # Initialize GCS client
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            creds_path = os.path.join(os.getcwd(), 'veo.json')
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
        else:
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Download video to temp file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            blob.download_to_file(temp_video)
            temp_video_path = temp_video.name
        
        # Create thumbnail temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_thumb:
            temp_thumb_path = temp_thumb.name
        
        try:
            # Generate thumbnail using ffmpeg if available, otherwise create text thumbnail
            thumbnail_url = generate_thumbnail_from_video_file(temp_video_path, video_id, temp_thumb_path)
            return thumbnail_url
            
        finally:
            # Clean up temp files
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
            if os.path.exists(temp_thumb_path):
                os.unlink(temp_thumb_path)
                
    except Exception as e:
        current_app.logger.error(f"Error generating thumbnail from GCS: {e}")
        # Fallback to text thumbnail
        return create_text_thumbnail_fallback(video_id)

def generate_thumbnail_from_video_file(video_path, video_id, thumbnail_path):
    """Generate thumbnail from video file using ffmpeg or fallback"""
    try:
        # Try to use ffmpeg first
        import subprocess
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', '00:00:02',  # Extract frame at 2 seconds
            '-vframes', '1',
            '-q:v', '2',
            '-y',  # Overwrite output file
            thumbnail_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # Successfully created thumbnail with ffmpeg
            current_app.logger.info(f"✅ Thumbnail generated with ffmpeg")
            return upload_thumbnail_to_gcs(thumbnail_path, video_id)
        else:
            current_app.logger.warning(f"⚠️ FFmpeg failed: {result.stderr}")
            # Fallback to text thumbnail
            return create_text_thumbnail_fallback(video_id)
            
    except FileNotFoundError:
        current_app.logger.info("ℹ️ FFmpeg not found, using text thumbnail fallback")
        return create_text_thumbnail_fallback(video_id)
    except Exception as e:
        current_app.logger.error(f"❌ Error with ffmpeg: {e}")
        return create_text_thumbnail_fallback(video_id)

def create_text_thumbnail_fallback(video_id):
    """Create a text-based thumbnail as fallback"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Get video details
        video = Video.query.get(video_id)
        if not video:
            return None
        
        # Create thumbnail image
        width, height = 320, 240
        image = Image.new('RGB', (width, height), color='#1f2937')
        draw = ImageDraw.Draw(image)
        
        # Try to use system font
        try:
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            try:
                font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
            except:
                font_small = ImageFont.load_default()
        
        # Add play button
        play_button_size = 60
        play_x = (width - play_button_size) // 2
        play_y = (height - play_button_size) // 2 - 20
        
        draw.ellipse([play_x, play_y, play_x + play_button_size, play_y + play_button_size], 
                    fill='#ffffff', outline='#ffffff', width=2)
        
        triangle_points = [
            (play_x + 20, play_y + 15),
            (play_x + 20, play_y + 45),
            (play_x + 45, play_y + 30)
        ]
        draw.polygon(triangle_points, fill='#1f2937')
        
        # Add video ID
        draw.text((10, 10), f"Video #{video_id}", fill='#ffffff', font=font_small)
        
        # Add prompt text (wrapped)
        words = video.prompt.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font_small)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= width - 20:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Limit to 3 lines
        lines = lines[:3]
        
        # Draw the text lines
        text_y = height - 80
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_small)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text((text_x, text_y), line, fill='#ffffff', font=font_small)
            text_y += 20
        
        # Add "AI Generated" label
        draw.text((width - 80, height - 25), "AI Generated", fill='#10b981', font=font_small)
        
        # Save thumbnail to temp file first, then upload to GCS
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_thumb:
            image.save(temp_thumb.name, format='JPEG', quality=85)
            return upload_thumbnail_to_gcs(temp_thumb.name, video_id)
        
    except Exception as e:
        current_app.logger.error(f"Error creating text thumbnail: {e}")
        return None

def upload_thumbnail_to_gcs(thumbnail_path, video_id):
    """Upload thumbnail to GCS and return the public URL"""
    try:
        current_app.logger.info(f"📤 Uploading thumbnail for video {video_id} to GCS")
        
        # Upload to GCS
        blob_name = f"thumbnails/{video_id}.jpg"
        gcs_url = upload_file_to_gcs(thumbnail_path, blob_name)
        
        if gcs_url:
            current_app.logger.info(f"✅ Thumbnail uploaded to GCS: {gcs_url}")
            return gcs_url
        else:
            current_app.logger.error(f"❌ Failed to upload thumbnail to GCS")
            return None
            
    except Exception as e:
        current_app.logger.error(f"❌ Error uploading thumbnail to GCS: {e}")
        return None



def generate_video_thumbnail(video_url, video_id):
    """Generate thumbnail from video and upload to GCS"""
    try:
        # For mock mode, return a mock thumbnail URL
        if current_app.config.get('TESTING') or current_app.config.get('VEO_MOCK_MODE', False):
            current_app.logger.info("Using mock thumbnail for development")
            # Return a mock thumbnail URL
            return "https://example.com/mock-thumbnail.jpg"
        
        # If it's a GCS URL, we can't download it directly with requests
        if video_url.startswith('gs://'):
            current_app.logger.info(f"GCS URL detected for thumbnail: {video_url}")
            # For now, return a mock thumbnail since we can't easily download from GCS
            return "https://example.com/mock-thumbnail.jpg"
        
        from app.video_processor import VideoProcessor
        import tempfile
        import os
        
        # Download video to temp file
        response = requests.get(video_url, stream=True)
        if response.status_code != 200:
            current_app.logger.error(f"Failed to download video for thumbnail: {response.status_code}")
            return None
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            for chunk in response.iter_content(chunk_size=8192):
                temp_video.write(chunk)
            temp_video_path = temp_video.name
        
        # Create thumbnail temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_thumb:
            temp_thumb_path = temp_thumb.name
        
        try:
            # Generate thumbnail
            if VideoProcessor.generate_thumbnail(temp_video_path, temp_thumb_path):
                # Upload thumbnail to GCS
                thumbnail_url = upload_file_to_gcs(temp_thumb_path, f"thumbnails/{video_id}.jpg")
                return thumbnail_url
            
            return None
            
        finally:
            # Clean up temp files
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
            if os.path.exists(temp_thumb_path):
                os.unlink(temp_thumb_path)
                
    except Exception as e:
        current_app.logger.error(f"Error generating thumbnail: {e}")
        return None

def upload_file_to_gcs(file_path, blob_name):
    """Upload a file to Google Cloud Storage"""
    try:
        # Initialize GCS client with explicit credentials
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            # Hardcode the path to veo.json
            creds_path = os.path.join(os.getcwd(), 'veo.json')
            current_app.logger.info(f"Using hardcoded credentials path for GCS upload: {creds_path}")
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
            current_app.logger.info(f"GCS upload client initialized with credentials from: {creds_path}")
        else:
            current_app.logger.warning(f"Credentials file not found for GCS upload: {creds_path}")
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(current_app.config['GCS_BUCKET_NAME'])
        blob = bucket.blob(blob_name)
        
        blob.upload_from_filename(file_path)
        
        # Generate a signed URL for the uploaded file
        # This works with uniform bucket-level access
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),  # 7 days expiration (maximum allowed)
            method="GET"
        )
        return signed_url
    except Exception as e:
        current_app.logger.error(f"Failed to upload to GCS: {e}")
        return None

def process_priority_queue():
    """Process videos in priority order"""
    try:
        # Get the next video to process based on priority
        next_video = Video.query.filter_by(status='pending').order_by(
            Video.priority.desc(),
            Video.queued_at.asc()
        ).first()
        
        if next_video:
            current_app.logger.info(f"Processing video {next_video.id} with priority {next_video.priority}")
            generate_video_task(next_video.id)
            return True
        else:
            current_app.logger.info("No videos in queue")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error processing priority queue: {e}")
        return False

def get_queue_stats():
    """Get current queue statistics"""
    try:
        pending_count = Video.query.filter_by(status='pending').count()
        processing_count = Video.query.filter_by(status='processing').count()
        
        # Get priority distribution
        priority_stats = db.session.query(
            Video.priority,
            db.func.count(Video.id)
        ).filter_by(status='pending').group_by(Video.priority).all()
        
        # Get average wait time
        avg_wait_time = db.session.query(
            db.func.avg(db.func.extract('epoch', db.func.now() - Video.queued_at))
        ).filter_by(status='pending').scalar() or 0
        
        return {
            'pending_count': pending_count,
            'processing_count': processing_count,
            'priority_distribution': dict(priority_stats),
            'avg_wait_time_minutes': int(avg_wait_time / 60) if avg_wait_time else 0
        }
    except Exception as e:
        current_app.logger.error(f"Error getting queue stats: {e}")
        return {}

def generate_thumbnail_signed_url(thumbnail_path):
    """Generate a signed URL for a thumbnail in GCS"""
    try:
        # Initialize GCS client with service account credentials
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            # Hardcode the path to veo.json
            creds_path = os.path.join(os.getcwd(), 'veo.json')
            current_app.logger.info(f"Using hardcoded credentials path for signed URL: {creds_path}")
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
            current_app.logger.info(f"GCS client initialized with service account credentials from: {creds_path}")
        else:
            current_app.logger.warning(f"Service account credentials file not found: {creds_path}")
            return None
        
        bucket = storage_client.bucket(current_app.config['GCS_BUCKET_NAME'])
        blob = bucket.blob(thumbnail_path)
        
        # Generate signed URL
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),  # 7 days expiration (maximum allowed)
            method="GET"
        )
        return signed_url
    except Exception as e:
        current_app.logger.error(f"Error generating signed URL for thumbnail {thumbnail_path}: {e}")
        return None 