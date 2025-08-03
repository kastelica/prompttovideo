#!/usr/bin/env python3
"""
Test script to check current operation status (Video 5)
"""
import os
import requests
import json
from google.auth import default
from google.auth.transport.requests import Request

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

def check_veo_status_simple(operation_name):
    """Check Veo API operation status without verbose logging"""
    access_token = get_gcloud_access_token()
    if not access_token:
        return None
    
    # Extract project_id and model_id from operation_name
    # Format: projects/PROJECT_ID/locations/LOCATION/publishers/google/models/MODEL_ID/operations/OPERATION_ID
    parts = operation_name.split('/')
    project_id = parts[1]
    model_id = parts[7]  # MODEL_ID is the 8th part (index 7)
    
    print(f"🔍 Parsed - Project: {project_id}, Model: {model_id}")
    
    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/{model_id}:fetchPredictOperation"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'operationName': operation_name
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Operation status response received")
            print(f"🔍 Operation done: {data.get('done', False)}")
            
            if data.get('done', False):
                response_data = data.get('response', {})
                print(f"🔍 Response type: {response_data.get('@type', 'Unknown')}")
                
                # Check for videos in different possible locations
                videos = response_data.get('videos', [])
                if videos:
                    print(f"✅ Found {len(videos)} videos")
                    for i, video in enumerate(videos):
                        if 'gcsUri' in video:
                            print(f"  Video {i}: GCS URI = {video['gcsUri']}")
                        elif 'bytesBase64Encoded' in video:
                            # Don't print the actual base64 data, just show it exists
                            print(f"  Video {i}: Base64 encoded (length: {len(video['bytesBase64Encoded'])} chars)")
                            print(f"  Video {i}: First 50 chars: {video['bytesBase64Encoded'][:50]}...")
                        else:
                            print(f"  Video {i}: Unknown format - keys: {list(video.keys())}")
                    
                    # Return the first video data without printing it
                    first_video = videos[0]
                    if 'gcsUri' in first_video:
                        return first_video['gcsUri']
                    elif 'bytesBase64Encoded' in first_video:
                        return f"base64_data_{len(first_video['bytesBase64Encoded'])}_chars"
                    else:
                        return "unknown_format"
                else:
                    print("❌ No videos found in response")
                    print(f"🔍 Available keys in response: {list(response_data.keys())}")
                    return None
            else:
                print("⏳ Operation still running")
                return None
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking operation status: {e}")
        return None

if __name__ == "__main__":
    # Get the operation name from Video 5
    from app import create_app
    from app.models import Video
    
    app = create_app()
    with app.app_context():
        video = Video.query.get(5)
        if video and video.veo_job_id:
            print(f"🔍 Checking operation: {video.veo_job_id}")
            result = check_veo_status_simple(video.veo_job_id)
            print(f"Result: {result}")
        else:
            print("❌ Video 5 not found or no operation ID") 