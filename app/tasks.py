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
        job_id = call_veo_api(video.prompt, video.quality)
        if not job_id:
            print(f"❌ Failed to get job ID from Veo API")
            video.status = 'failed'
            video.error_message = 'Failed to start video generation'
            db.session.commit()
            return False
        
        print(f"✅ Veo API job created: {job_id}")
        video.veo_job_id = job_id
        db.session.commit()
        
        # Step 2: Poll for completion
        print(f"📋 Step 2/6: Polling for video completion...")
        video_url = None
        max_attempts = 60  # 5 minutes with 5-second intervals
        attempts = 0
        
        while attempts < max_attempts:
            video_url = check_veo_status(job_id)
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
        
        # Step 3: Download video
        print(f"📋 Step 3/6: Downloading video...")
        local_path = download_video_to_local(job_id, video_id, video_url)
        if not local_path:
            print(f"❌ Failed to download video")
            video.status = 'failed'
            video.error_message = 'Failed to download video'
            db.session.commit()
            return False
        
        print(f"✅ Video downloaded to: {local_path}")
        
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

def call_veo_api(prompt, quality):
    """Call Google Veo API to generate video"""
    try:
        # Get API key from environment
        api_key = os.environ.get('VEO_API_KEY')
        if not api_key:
            print("❌ VEO_API_KEY not found in environment")
            return None
        
        # API endpoint
        url = "https://generativelanguage.googleapis.com/v1/models/veo:generateContent"
        
        # Request payload
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 2048,
            }
        }
        
        # Add quality-specific settings
        if quality == 'premium':
            payload["generationConfig"]["temperature"] = 0.2
            payload["generationConfig"]["topK"] = 16
        
        # Make API request
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Extract job ID from response
            # Note: This is a simplified version - actual Veo API response structure may differ
            job_id = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return job_id if job_id else 'mock_job_id'
        else:
            print(f"❌ Veo API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error calling Veo API: {e}")
        return None

def check_veo_status(job_id):
    """Check Veo API job status"""
    try:
        # For now, return a mock URL after a short delay
        # In production, this would poll the actual Veo API
        time.sleep(2)
        return f"https://example.com/video_{job_id}.mp4"
    except Exception as e:
        print(f"❌ Error checking Veo status: {e}")
        return None

def download_video_to_local(job_id, video_id, video_url=None):
    """Download video to local storage"""
    try:
        # Create videos directory if it doesn't exist
        os.makedirs('videos', exist_ok=True)
        
        # For now, create a mock video file
        # In production, this would download from the actual URL
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