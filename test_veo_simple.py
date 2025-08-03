#!/usr/bin/env python3
"""
Simple test script to verify VEO API access using existing Google Cloud libraries
"""

import os
import requests
import json

# Set up environment
os.environ['GOOGLE_CLOUD_PROJECT'] = 'dirly-466300'

try:
    import google.auth
    from google.auth.transport.requests import Request
    print("✅ Google Cloud libraries imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Google Cloud libraries: {e}")
    exit(1)

def get_auth_token():
    """Get authentication token using Application Default Credentials"""
    try:
        print("🔑 Getting authentication token...")
        credentials, project = google.auth.default(
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/aiplatform.googleapis.com'
            ]
        )
        
        # Refresh the token
        credentials.refresh(Request())
        
        if credentials.valid and credentials.token:
            print("✅ Successfully obtained authentication token")
            return credentials.token
        else:
            print("❌ Authentication token is not valid")
            return None
            
    except Exception as e:
        print(f"❌ Failed to get authentication token: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def test_veo_models(token):
    """Test if we can access VEO models"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = "https://us-central1-aiplatform.googleapis.com/v1/projects/dirly-466300/locations/us-central1/publishers/google/models"
    
    try:
        print("📡 Testing models API...")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Successfully accessed models API")
            print(f"📋 Found {len(models.get('models', []))} models")
            
            # Look for VEO models
            veo_models = [m for m in models.get('models', []) if 'veo' in m.get('name', '').lower()]
            if veo_models:
                print(f"🎬 Found {len(veo_models)} VEO models:")
                for model in veo_models:
                    print(f"   - {model.get('name')}")
            else:
                print("⚠️  No VEO models found in the list")
            
            return True
        else:
            print(f"❌ Models API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing models API: {e}")
        return False

def test_veo_generation(token):
    """Test VEO video generation endpoint"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = "https://us-central1-aiplatform.googleapis.com/v1/projects/dirly-466300/locations/us-central1/publishers/google/models/veo-2.0-generate-001:predictLongRunning"
    
    request_data = {
        "instances": [{"prompt": "A beautiful sunset over the ocean"}],
        "parameters": {
            "durationSeconds": 5,
            "aspectRatio": "16:9",
            "enhancePrompt": True,
            "sampleCount": 1,
            "personGeneration": "allow_adult",
            "storageUri": "gs://prompt-veo-videos/videos/"
        }
    }
    
    try:
        print("🎬 Testing VEO video generation...")
        response = requests.post(url, headers=headers, json=request_data, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            operation_name = result.get('name')
            if operation_name:
                print(f"✅ Successfully started video generation: {operation_name}")
                return True
            else:
                print(f"❌ No operation name in response: {result}")
                return False
        else:
            print(f"❌ Generation API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing generation API: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing VEO API Access...")
    print("=" * 50)
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Exiting.")
        exit(1)
    
    # Test 1: Check if we can access models
    print("\n1️⃣ Testing Models API Access:")
    models_ok = test_veo_models(token)
    
    # Test 2: Check if we can start video generation
    print("\n2️⃣ Testing Video Generation API:")
    generation_ok = test_veo_generation(token)
    
    print("\n" + "=" * 50)
    if models_ok and generation_ok:
        print("✅ All tests passed! VEO API is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above for details.") 