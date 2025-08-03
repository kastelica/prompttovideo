#!/usr/bin/env python3
"""
Test script for Veo integration - Full Pipeline Test
This script tests the complete video generation pipeline including GCS upload.
"""

import os
import sys
import time
import tempfile
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set environment variables directly
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'veo.json'
os.environ['GOOGLE_CLOUD_PROJECT_ID'] = 'dirly-466300'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_full_video_pipeline():
    """Test the complete video generation pipeline"""
    try:
        from app import create_app
        from app.veo_client import VeoClient
        from app.tasks import download_and_upload_video, generate_signed_url
        from google.cloud import storage
        from google.oauth2 import service_account
        
        # Create Flask app context
        app = create_app()
        with app.app_context():
            print("🚀 Testing Full Video Generation Pipeline")
            print("=" * 60)
            
            # Initialize Veo client
            print("🔧 Initializing Veo client...")
            veo_client = VeoClient()
            print(f"✅ Veo client initialized")
            print(f"📊 Project ID: {veo_client.project_id}")
            print(f"🌍 Location: {veo_client.location}")
            print(f"🤖 Model ID: {veo_client.model_id}")
            
            # Test authentication
            print("\n🔐 Testing authentication...")
            token = veo_client._get_auth_token()
            print(f"✅ Authentication successful, token length: {len(token)}")
            
            # Generate a unique test prompt
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_prompt = f"A majestic eagle soaring over snow-capped mountains at sunset - test {timestamp}"
            
            print(f"\n🎬 Starting video generation...")
            print(f"📝 Prompt: {test_prompt}")
            
            # Generate video
            result = veo_client.generate_video(test_prompt, quality='360p', duration=8)
            
            if not result['success']:
                print(f"❌ Video generation failed: {result.get('error')}")
                return False
            
            print("✅ Video generation started successfully")
            operation_name = result['operation_name']
            print(f"📋 Operation name: {operation_name}")
            
            # Poll for completion
            print(f"\n⏳ Polling for completion...")
            max_attempts = 60  # 5 minutes with 5-second intervals
            for attempt in range(max_attempts):
                print(f"🔄 Polling attempt {attempt + 1}/{max_attempts}")
                
                status_result = veo_client.check_video_status(operation_name)
                
                if not status_result.get('success'):
                    error = status_result.get('error', 'Unknown error')
                    print(f"❌ Status check failed: {error}")
                    if '404' not in error:
                        break
                    time.sleep(5)
                    continue
                
                status = status_result.get('status')
                print(f"📊 Status: {status}")
                
                if status == 'completed':
                    print("🎉 Video generation completed!")
                    video_url = status_result.get('video_url')
                    duration = status_result.get('duration', 8)
                    print(f"📹 Video URL: {video_url}")
                    print(f"⏱️ Duration: {duration} seconds")
                    
                    # Test GCS upload
                    print(f"\n📤 Testing GCS upload...")
                    test_video_id = f"test_{timestamp}"
                    
                    try:
                        # Download and upload to GCS
                        gcs_url = download_and_upload_video(operation_name, test_video_id)
                        print(f"✅ Video uploaded to GCS: {gcs_url}")
                        
                        # Generate signed URL
                        signed_url = generate_signed_url(gcs_url)
                        print(f"🔗 Signed URL: {signed_url}")
                        
                        # Test GCS access
                        print(f"\n🔍 Testing GCS access...")
                        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                        if not creds_path:
                            creds_path = os.path.join(os.getcwd(), 'veo.json')
                        
                        credentials = service_account.Credentials.from_service_account_file(
                            creds_path,
                            scopes=['https://www.googleapis.com/auth/cloud-platform']
                        )
                        storage_client = storage.Client(credentials=credentials)
                        
                        # Extract bucket and blob from GCS URL
                        parts = gcs_url.replace('gs://', '').split('/', 1)
                        bucket_name = parts[0]
                        blob_name = parts[1]
                        
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob(blob_name)
                        
                        if blob.exists():
                            print(f"✅ GCS blob exists: {gcs_url}")
                            print(f"📏 File size: {blob.size} bytes")
                            print(f"📅 Created: {blob.time_created}")
                            print(f"🔗 Public URL: {blob.public_url}")
                        else:
                            print(f"❌ GCS blob not found: {gcs_url}")
                        
                        print(f"\n🎉 Full pipeline test completed successfully!")
                        print(f"📁 Video stored at: {gcs_url}")
                        print(f"🔗 Access URL: {signed_url}")
                        
                        return True
                        
                    except Exception as e:
                        print(f"❌ GCS upload failed: {e}")
                        import traceback
                        traceback.print_exc()
                        return False
                    
                elif status == 'failed':
                    error = status_result.get('error', 'Unknown error')
                    print(f"❌ Video generation failed: {error}")
                    return False
                
                else:
                    print(f"⏳ Still processing... (attempt {attempt + 1})")
                    time.sleep(5)
            
            print(f"❌ Video generation timed out after {max_attempts * 5} seconds")
            return False
        
    except Exception as e:
        print(f"❌ Error in full pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gcs_setup():
    """Test GCS setup and permissions"""
    try:
        print("\n🔧 Testing GCS Setup")
        print("=" * 30)
        
        from google.cloud import storage
        from google.oauth2 import service_account
        
        # Check credentials
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            creds_path = os.path.join(os.getcwd(), 'veo.json')
        
        if not os.path.exists(creds_path):
            print(f"❌ Credentials file not found: {creds_path}")
            return False
        
        print(f"✅ Credentials found: {creds_path}")
        
        # Initialize storage client
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        storage_client = storage.Client(credentials=credentials)
        
        # List buckets
        print("📦 Available buckets:")
        buckets = list(storage_client.list_buckets())
        if buckets:
            for bucket in buckets:
                print(f"  - {bucket.name}")
        else:
            print("  No buckets found")
        
        # Check if our bucket exists
        bucket_name = os.environ.get('GCS_BUCKET_NAME', f"{os.environ.get('GOOGLE_CLOUD_PROJECT_ID')}-veo-videos")
        bucket = storage_client.bucket(bucket_name)
        
        if bucket.exists():
            print(f"✅ Target bucket exists: {bucket_name}")
            
            # Test upload
            print("📤 Testing upload...")
            test_blob_name = f"test/upload_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            blob = bucket.blob(test_blob_name)
            
            test_content = f"Test upload at {datetime.now()}"
            blob.upload_from_string(test_content)
            print(f"✅ Test upload successful: gs://{bucket_name}/{test_blob_name}")
            
            # Clean up test file
            blob.delete()
            print(f"🧹 Test file cleaned up")
            
        else:
            print(f"❌ Target bucket not found: {bucket_name}")
            print("💡 Run 'python setup_gcs.py' to create the bucket")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ GCS setup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Veo Full Pipeline Test")
    print("=" * 50)
    
    # Test GCS setup first
    if not test_gcs_setup():
        print("\n❌ GCS setup test failed. Please fix GCS configuration first.")
        return
    
    # Test full pipeline
    success = test_full_video_pipeline()
    
    if success:
        print("\n🎉 All tests passed! Your Veo + GCS setup is working correctly.")
    else:
        print("\n❌ Pipeline test failed. Check the logs above for details.")

if __name__ == "__main__":
    main() 