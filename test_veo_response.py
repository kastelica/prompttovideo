#!/usr/bin/env python3
"""
Test script to check Veo API response structure for completed video
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
    """Check Veo API operation status with minimal logging"""
    try:
        # Get access token from gcloud
        access_token = get_gcloud_access_token()
        if not access_token:
            print("❌ Failed to get Google Cloud access token")
            return None
        
        # Get project ID from environment or use default
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'dirly-466300')
        
        # Extract model ID from operation name
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
            
            print("=== RESPONSE STRUCTURE ===")
            print(f"Top level keys: {list(data.keys())}")
            
            if data.get('done', False):
                print("✅ Operation completed")
                
                response_data = data.get('response', {})
                print(f"Response data keys: {list(response_data.keys())}")
                
                # Check for videos array
                if 'videos' in response_data:
                    videos = response_data['videos']
                    print(f"Videos array length: {len(videos)}")
                    if videos:
                        print(f"First video keys: {list(videos[0].keys())}")
                        print(f"First video data: {videos[0]}")
                
                # Check for direct video data
                if 'gcsUri' in response_data:
                    print(f"Direct gcsUri found: {response_data['gcsUri']}")
                
                # Check for video object
                if 'video' in response_data:
                    video_data = response_data['video']
                    print(f"Video object keys: {list(video_data.keys())}")
                
                return data
            else:
                print("⏳ Operation still running")
                return None
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # Test with the operation from Video 10 (completed video)
    operation_name = "projects/dirly-466300/locations/us-central1/publishers/google/models/veo-2.0-generate-001/operations/b0647880-cdb9-4acb-85fd-014f5afdfdf0"
    
    print("🔍 Checking Veo operation status for completed video...")
    result = check_veo_status_simple(operation_name)
    
    if result:
        print("\n=== FULL RESPONSE ===")
        print(json.dumps(result, indent=2)) 