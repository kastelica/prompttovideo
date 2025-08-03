#!/usr/bin/env python3
"""
Test script to verify VEO API access and authentication
"""

import os
import requests
import subprocess
import json

def get_access_token():
    """Get access token using gcloud"""
    try:
        result = subprocess.run(['gcloud', 'auth', 'print-access-token'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting access token: {e}")
        return None

def test_veo_models():
    """Test if we can access VEO models"""
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: List available models
    url = "https://us-central1-aiplatform.googleapis.com/v1/projects/dirly-466300/locations/us-central1/publishers/google/models"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"📡 Models API Response Status: {response.status_code}")
        
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

def test_veo_generation():
    """Test VEO video generation endpoint"""
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test with a simple prompt
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
        print(f"📡 Generation API Response Status: {response.status_code}")
        
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
    
    # Test 1: Check if we can access models
    print("\n1️⃣ Testing Models API Access:")
    models_ok = test_veo_models()
    
    # Test 2: Check if we can start video generation
    print("\n2️⃣ Testing Video Generation API:")
    generation_ok = test_veo_generation()
    
    print("\n" + "=" * 50)
    if models_ok and generation_ok:
        print("✅ All tests passed! VEO API is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above for details.") 