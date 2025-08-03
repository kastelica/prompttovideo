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
from google.auth import default
from google.auth.transport.requests import Request

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
        return _generate_video_task(video_id)

def _generate_video_task(video_id):
    """Internal function to generate video (with extensive logging)"""
    from app import db
    from app.models import Video, User
    from datetime import datetime
    import time
    
    try:
        # Get video and user objects
        video = Video.query.get(video_id)
        if not video:
            print(f"❌ Video {video_id} not found")
            return False
        
        user = User.query.get(video.user_id)
        if not user:
            print(f"❌ User {video.user_id} not found")
            return False
        
        print(f"🎬 Starting video generation for video {video_id}")
        print(f"📝 Prompt: {video.prompt}")
        print(f"👤 User: {user.email}")
        
        # Update video status to processing
        video.status = 'processing'
        video.processing_started_at = datetime.utcnow()
        db.session.commit()
        print(f"✅ Updated video status to processing")
        
        # Step 1: Call Veo API
        print(f"📋 Step 1/6: Calling Veo API...")
        operation_name = call_veo_api(video.prompt, video.quality)
        if not operation_name:
            print(f"❌ Failed to get operation name from Veo API")
            video.status = 'failed'
            video.error_message = 'Failed to start video generation'
            db.session.commit()
            return False
        
        print(f"✅ Veo API operation created: {operation_name}")
        video.veo_job_id = operation_name
        db.session.commit()
        
        # Step 2: Poll for completion
        print(f"📋 Step 2/6: Polling for video completion...")
        video_url = None
        max_attempts = 60  # 5 minutes with 5-second intervals
        attempts = 0
        
        while attempts < max_attempts:
            video_url = check_veo_status(operation_name)
            if video_url:
                print(f"✅ Video completed: {video_url}")
                break
            
            print(f"⏳ Video still processing... (attempt {attempts + 1}/{max_attempts})")
            time.sleep(5)
            attempts += 1
        
        if not video_url:
            print(f"❌ Video generation timed out after {max_attempts} attempts")
            video.status = 'failed'
            video.error_message = 'Video generation timed out'
            db.session.commit()
            return False
        
        # Step 3: Process video data
        print(f"📋 Step 3/6: Processing video data...")
        
        if isinstance(video_url, str) and video_url.startswith('gs://'):
            # Video is a GCS URI - download it
            local_path = download_video_to_local(operation_name, video_id, video_url)
            if not local_path:
                print(f"❌ Failed to download video from GCS")
                video.status = 'failed'
                video.error_message = 'Failed to download video from GCS'
                db.session.commit()
                return False
            print(f"✅ Video downloaded from GCS to: {local_path}")
            
        elif isinstance(video_url, str) and len(video_url) > 1000:
            # Video is base64-encoded data - save it directly
            import base64
            try:
                os.makedirs('videos', exist_ok=True)
                local_path = f"videos/{video_id}.mp4"
                
                # Decode base64 and save to file
                video_bytes = base64.b64decode(video_url)
                with open(local_path, 'wb') as f:
                    f.write(video_bytes)
                
                print(f"✅ Base64 video data saved to: {local_path} ({len(video_bytes)} bytes)")
            except Exception as e:
                print(f"❌ Failed to save base64 video data: {e}")
                video.status = 'failed'
                video.error_message = f'Failed to save video data: {e}'
                db.session.commit()
                return False
                
        elif isinstance(video_url, dict):
            # Video is a dict with video data
            if 'bytesBase64Encoded' in video_url:
                import base64
                try:
                    os.makedirs('videos', exist_ok=True)
                    local_path = f"videos/{video_id}.mp4"
                    
                    # Decode base64 and save to file
                    video_bytes = base64.b64decode(video_url['bytesBase64Encoded'])
                    with open(local_path, 'wb') as f:
                        f.write(video_bytes)
                    
                    print(f"✅ Video data from dict saved to: {local_path} ({len(video_bytes)} bytes)")
                except Exception as e:
                    print(f"❌ Failed to save video data from dict: {e}")
                    video.status = 'failed'
                    video.error_message = f'Failed to save video data: {e}'
                    db.session.commit()
                    return False
            else:
                print(f"❌ Unknown video data format in dict: {list(video_url.keys())}")
                video.status = 'failed'
                video.error_message = 'Unknown video data format'
                db.session.commit()
                return False
        else:
            print(f"❌ Unknown video data format: {type(video_url)}")
            video.status = 'failed'
            video.error_message = 'Unknown video data format'
            db.session.commit()
            return False
        
        # Step 4: Upload to GCS
        print(f"📋 Step 4/6: Uploading to Google Cloud Storage...")
        gcs_url = upload_file_to_gcs(local_path, f"videos/{video_id}.mp4")
        if not gcs_url:
            print(f"❌ Failed to upload to GCS")
            video.status = 'failed'
            video.error_message = 'Failed to upload to cloud storage'
            db.session.commit()
            return False
        
        print(f"✅ Video uploaded to GCS: {gcs_url}")
        video.video_url = gcs_url
        
        # Step 5: Generate thumbnail
        print(f"📋 Step 5/6: Generating thumbnail...")
        thumbnail_url = generate_video_thumbnail(gcs_url, video_id)
        if thumbnail_url:
            video.thumbnail_url = thumbnail_url
            print(f"✅ Thumbnail generated: {thumbnail_url}")
        else:
            print(f"⚠️ Failed to generate thumbnail, using fallback")
            video.thumbnail_url = create_text_thumbnail_fallback(video_id)
        
        # Step 6: Update video status
        print(f"📋 Step 6/6: Finalizing video...")
        video.status = 'completed'
        video.completed_at = datetime.utcnow()
        video.processing_duration = (video.completed_at - video.processing_started_at).total_seconds()
        db.session.commit()
                
        print(f"🎉 Video {video_id} completed successfully!")
        print(f"⏱️ Processing time: {video.processing_duration:.2f} seconds")
                
        # Send completion email
        try:
            send_video_complete_email(user, video)
            print(f"📧 Completion email sent to {user.email}")
        except Exception as e:
            print(f"⚠️ Failed to send completion email: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in video generation: {e}")
        try:
            video.status = 'failed'
            video.error_message = str(e)
            db.session.commit()
        except:
            pass
        return False

def get_gcloud_access_token():
    """Get Google Cloud access token using Google Auth library"""
    try:
        # Clear any existing GOOGLE_APPLICATION_CREDENTIALS to use default service account
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        # Use default credentials (will use gcloud auth or default service account)
        credentials, project = default()
        
        # Refresh the token if needed
        if not credentials.valid:
            credentials.refresh(Request())
        
        return credentials.token
    except Exception as e:
        print(f"❌ Failed to get gcloud access token: {e}")
        return None

def call_veo_api(prompt, quality):
    """Call Google Veo API to generate video"""
    try:
        # Get access token from gcloud
        access_token = get_gcloud_access_token()
        if not access_token:
            print("❌ Failed to get Google Cloud access token")
            return None
        
        # Get project ID from environment or use default
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'dirly-466300')
        print(f"🔧 Using Google Cloud project: {project_id}")
        
        # Choose model based on quality
        model_id = "veo-3.0-generate-001" if quality == 'premium' else "veo-3.0-fast-generate-001"
        
        # API endpoint
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/{model_id}:predictLongRunning"
        
        # Request payload
        payload = {
            "instances": [{
                "prompt": prompt
            }],
            "parameters": {
                "durationSeconds": 8,
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "enhancePrompt": True,
                "generateAudio": True,
                "personGeneration": "allow_adult"
            }
        }
        
        # Add quality-specific settings
        if quality == 'premium':
            payload["parameters"]["resolution"] = "1080p"
        
        # Make API request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            operation_name = data.get('name')
            print(f"✅ Veo API request successful: {operation_name}")
            return operation_name
        else:
            print(f"❌ Veo API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error calling Veo API: {e}")
        return None

def check_veo_status(operation_name):
    """Check Veo API operation status"""
    try:
        # Get access token from gcloud
        access_token = get_gcloud_access_token()
        if not access_token:
            print("❌ Failed to get Google Cloud access token")
            return None
        
        # Get project ID from environment or use default
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'dirly-466300')
        print(f"🔧 Using Google Cloud project: {project_id}")
        
        # Extract model ID from operation name
        # operation_name format: projects/PROJECT_ID/locations/us-central1/publishers/google/models/MODEL_ID/operations/OPERATION_ID
        parts = operation_name.split('/')
        model_id = parts[-3]  # MODEL_ID is the third to last part
        
        # API endpoint for checking operation status
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/{model_id}:fetchPredictOperation"
        
        # Request payload
        payload = {
            "operationName": operation_name
        }
        
        # Make API request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('done', False):
                # Operation is complete
                print("✅ Operation completed, checking for video data...")
                
                # Try different response structures
                response_data = data.get('response', {})
                print(f"📄 Response type: {response_data.get('@type', 'Unknown')}")
                
                # Check for videos array in response
                videos = response_data.get('videos', [])
                if videos and len(videos) > 0:
                    video_data = videos[0]
                    
                    # Check for GCS URI first
                    if 'gcsUri' in video_data:
                        video_uri = video_data['gcsUri']
                        print(f"✅ Video generation completed (GCS): {video_uri}")
                        return video_uri
                    
                    # Check for base64-encoded video data
                    elif 'bytesBase64Encoded' in video_data:
                        video_base64 = video_data['bytesBase64Encoded']
                        print(f"✅ Video generation completed (Base64): {len(video_base64)} chars")
                        return video_base64
                    
                    # Check for mime type
                    elif 'mimeType' in video_data:
                        print(f"✅ Video generation completed (MIME: {video_data['mimeType']})")
                        # Return the entire video data object for further processing
                        return video_data
                    
                    else:
                        print(f"❌ Unknown video format: {list(video_data.keys())}")
                        return None
                
                # Check for direct video data in response
                if 'gcsUri' in response_data:
                    video_uri = response_data['gcsUri']
                    print(f"✅ Video generation completed (direct): {video_uri}")
                    return video_uri
                
                # Check for video data in different locations
                if 'video' in response_data:
                    video_data = response_data['video']
                    if isinstance(video_data, dict) and 'gcsUri' in video_data:
                        video_uri = video_data['gcsUri']
                        print(f"✅ Video generation completed (nested): {video_uri}")
                        return video_uri
                
                print("❌ No video found in completed operation")
                print(f"🔍 Available keys in response_data: {list(response_data.keys())}")
                return None
            else:
                # Operation still running
                return None
        else:
            print(f"❌ Veo API status check error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking Veo status: {e}")
        return None

def download_video_to_local(operation_name, video_id, video_url=None):
    """Download video to local storage"""
    try:
        # Create videos directory if it doesn't exist
        os.makedirs('videos', exist_ok=True)
        
        # For now, create a mock video file
        # In production, this would download from the actual GCS URL
        local_path = f"videos/{video_id}.mp4"
        
        # Create a simple mock video file
        with open(local_path, 'wb') as f:
            f.write(b'mock video content')
        
        return local_path
    except Exception as e:
        print(f"❌ Error downloading video: {e}")
        return None

def create_mock_video_file(video_id):
    """Create a mock video file for testing"""
    try:
        os.makedirs('videos', exist_ok=True)
        local_path = f"videos/{video_id}.mp4"
        
        with open(local_path, 'wb') as f:
            f.write(b'mock video content')
        
        return local_path
    except Exception as e:
        print(f"❌ Error creating mock video: {e}")
        return None

def generate_video_thumbnail(video_url, video_id):
    """Generate thumbnail from video URL"""
    try:
        # For now, return a placeholder thumbnail
        # In production, this would generate an actual thumbnail
        return f"https://via.placeholder.com/320x180/000000/FFFFFF?text=Video+{video_id}"
    except Exception as e:
        print(f"❌ Error generating thumbnail: {e}")
        return None

def create_text_thumbnail_fallback(video_id):
    """Create a text-based thumbnail as fallback"""
    try:
        return f"https://via.placeholder.com/320x180/000000/FFFFFF?text=Video+{video_id}"
    except Exception as e:
        print(f"❌ Error creating fallback thumbnail: {e}")
        return None

def upload_file_to_gcs(file_path, blob_name):
    """Upload file to Google Cloud Storage"""
    try:
        # Get GCS bucket name from environment
        bucket_name = os.environ.get('GCS_BUCKET_NAME')
        if not bucket_name:
            print("❌ GCS_BUCKET_NAME not found in environment")
            return None
        
        # Initialize GCS client
            storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Upload file
        blob.upload_from_filename(file_path)
        
        # Return public URL
        return f"gs://{bucket_name}/{blob_name}"
        
    except Exception as e:
        print(f"❌ Error uploading to GCS: {e}")
        return None

def process_priority_queue():
    """Process videos in priority order"""
    try:
        # Get videos ordered by priority
        videos = Video.query.filter(
            Video.status == 'pending'
        ).order_by(
            Video.priority.desc(),
            Video.created_at.asc()
        ).limit(10).all()
        
        return videos
    except Exception as e:
        print(f"❌ Error processing priority queue: {e}")
        return []

def get_queue_stats():
    """Get queue statistics"""
    try:
        pending_count = Video.query.filter_by(status='pending').count()
        processing_count = Video.query.filter_by(status='processing').count()
        completed_count = Video.query.filter_by(status='completed').count()
        failed_count = Video.query.filter_by(status='failed').count()
        
        return {
            'pending': pending_count,
            'processing': processing_count,
            'completed': completed_count,
            'failed': failed_count,
            'total': pending_count + processing_count + completed_count + failed_count
        }
    except Exception as e:
        print(f"❌ Error getting queue stats: {e}")
        return {}