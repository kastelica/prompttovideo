#!/usr/bin/env python3
"""
Test script to check VEO model access using the correct endpoint
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

def test_veo_model_access(token):
    """Test if we can access specific VEO models"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test different VEO model endpoints
    veo_models = [
        'veo-2.0-generate-001',
        'veo-3.0-generate-001', 
        'veo-3.0-fast-generate-001',
        'veo-3.0-generate-preview'
    ]
    
    for model in veo_models:
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/dirly-466300/locations/us-central1/publishers/google/models/{model}"
        
        try:
            print(f"📡 Testing access to {model}...")
            response = requests.get(url, headers=headers, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                model_info = response.json()
                print(f"   ✅ Successfully accessed {model}")
                print(f"   📋 Model name: {model_info.get('name', 'N/A')}")
                print(f"   📋 Display name: {model_info.get('displayName', 'N/A')}")
                print(f"   📋 Description: {model_info.get('description', 'N/A')[:100]}...")
            elif response.status_code == 404:
                print(f"   ⚠️  Model {model} not found (404)")
            else:
                print(f"   ❌ Error accessing {model}: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Exception accessing {model}: {e}")

def test_veo_generation_with_different_models(token):
    """Test VEO video generation with different models"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test with veo-2.0-generate-001 (which we know works)
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
        print("\n🎬 Testing VEO video generation with veo-2.0-generate-001...")
        response = requests.post(url, headers=headers, json=request_data, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            operation_name = result.get('name')
            if operation_name:
                print(f"✅ Successfully started video generation: {operation_name}")
                return operation_name
            else:
                print(f"❌ No operation name in response: {result}")
                return None
        else:
            print(f"❌ Generation API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing generation API: {e}")
        return None

if __name__ == "__main__":
    print("🧪 Testing VEO Model Access...")
    print("=" * 50)
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Exiting.")
        exit(1)
    
    # Test 1: Check access to specific VEO models
    print("\n1️⃣ Testing VEO Model Access:")
    test_veo_model_access(token)
    
    # Test 2: Test video generation
    print("\n2️⃣ Testing Video Generation:")
    operation_name = test_veo_generation_with_different_models(token)
    
    print("\n" + "=" * 50)
    if operation_name:
        print("✅ VEO API is working correctly!")
        print(f"🎬 Operation started: {operation_name}")
    else:
        print("❌ VEO API tests failed.") 