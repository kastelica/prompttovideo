#!/usr/bin/env python3
"""
Test script for Veo API integration
"""
import os
import requests
import json
from google.auth import default
from google.auth.transport.requests import Request

def get_gcloud_access_token():
    """Get Google Cloud access token using Google Auth library"""
    try:
        # Use default credentials (will use gcloud auth)
        credentials, project = default()
        
        # Refresh the token if needed
        if not credentials.valid:
            credentials.refresh(Request())
        
        return credentials.token
    except Exception as e:
        print(f"❌ Failed to get gcloud access token: {e}")
        return None

def test_veo_api():
    """Test Veo API integration"""
    print("🧪 Testing Veo API Integration...")
    
    # Get access token
    access_token = get_gcloud_access_token()
    if not access_token:
        print("❌ Failed to get access token")
        return False
    
    print("✅ Got access token")
    
    # Get project ID
    project_id = "dirly-466300"  # Your project ID
    model_id = "veo-3.0-fast-generate-001"  # Use fast model for testing
    
    # API endpoint
    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/{model_id}:predictLongRunning"
    
    # Test payload
    payload = {
        "instances": [{
            "prompt": "A beautiful sunset over the ocean with gentle waves"
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
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print(f"📡 Making request to: {url}")
    print(f"📝 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📄 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            operation_name = data.get('name')
            print(f"✅ Veo API request successful!")
            print(f"🔗 Operation name: {operation_name}")
            return operation_name
        else:
            print(f"❌ Veo API error: {response.status_code}")
            print(f"📄 Response text: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error calling Veo API: {e}")
        return None

def test_operation_status(operation_name):
    """Test checking operation status"""
    if not operation_name:
        print("❌ No operation name provided")
        return False
    
    print(f"\n🔍 Testing operation status for: {operation_name}")
    
    # Get access token
    access_token = get_gcloud_access_token()
    if not access_token:
        print("❌ Failed to get access token")
        return False
    
    # Get project ID
    project_id = "dirly-466300"
    
    # Extract model ID from operation name
    parts = operation_name.split('/')
    model_id = parts[-3]
    
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
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"📊 Status check response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📄 Response data: {json.dumps(data, indent=2)}")
            
            if data.get('done', False):
                print("✅ Operation completed!")
                response_data = data.get('response', {})
                videos = response_data.get('videos', [])
                
                if videos and len(videos) > 0:
                    video_uri = videos[0].get('gcsUri')
                    print(f"🎬 Video URI: {video_uri}")
                    return True
                else:
                    print("❌ No videos found in response")
                    return False
            else:
                print("⏳ Operation still running...")
                return False
        else:
            print(f"❌ Status check error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking operation status: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Veo API Integration Test")
    print("=" * 50)
    
    # Test 1: Create video generation request
    operation_name = test_veo_api()
    
    if operation_name:
        print("\n" + "=" * 50)
        print("✅ Step 1: Video generation request successful!")
        
        # Test 2: Check operation status (this will likely still be running)
        print("\n" + "=" * 50)
        print("🔄 Step 2: Checking operation status...")
        test_operation_status(operation_name)
        
        print("\n" + "=" * 50)
        print("📝 Note: Video generation takes time. You can check the status later using:")
        print(f"   python test_veo_integration.py --check-status {operation_name}")
    else:
        print("\n" + "=" * 50)
        print("❌ Step 1: Video generation request failed!")
        print("💡 Check your Google Cloud setup and API permissions") 