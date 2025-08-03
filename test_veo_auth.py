#!/usr/bin/env python3
"""
Test script to verify Veo API authentication
"""

import os
import sys
import requests
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.veo_client import VeoClient

def test_veo_auth():
    """Test Veo API authentication"""
    print("🔍 Testing Veo API Authentication")
    print("=" * 50)
    
    try:
        # Create Flask app and context
        app = create_app('testing')
        
        with app.app_context():
            # Create VeoClient instance
            veo_client = VeoClient()
            
            # Test authentication
            print("🔑 Testing authentication...")
            token = veo_client._get_auth_token()
            
            if not token or token == "mock_token_for_development":
                print("❌ Authentication failed - no valid token obtained")
                return False
            
            print(f"✅ Authentication successful!")
            print(f"🔍 Token type: {type(token)}")
            print(f"🔍 Token length: {len(token)}")
            print(f"🔍 Token preview: {token[:20]}...")
            
            # Test a simple API call to verify the token works
            print("\n🌐 Testing API connectivity...")
            
            # Use the same headers as the VeoClient
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Test with a simple Vertex AI API call (list models)
            test_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{veo_client.project_id}/locations/us-central1/models"
            
            print(f"🔗 Testing URL: {test_url}")
            
            response = requests.get(test_url, headers=headers, timeout=30)
            
            print(f"📡 Response status: {response.status_code}")
            print(f"📡 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ API connectivity test successful!")
                return True
            else:
                print(f"❌ API connectivity test failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_veo_generate():
    """Test Veo video generation (without actually generating)"""
    print("\n🎬 Testing Veo video generation setup")
    print("=" * 50)
    
    try:
        # Create Flask app and context
        app = create_app('testing')
        
        with app.app_context():
            # Create VeoClient instance
            veo_client = VeoClient()
            
            # Test the generate_video method setup (without making the actual API call)
            print("🔧 Testing generate_video method setup...")
            
            # This will test the authentication and request preparation
            result = veo_client.generate_video(
                prompt="A beautiful sunset over the ocean",
                quality='free',
                duration=8
            )
            
            print(f"📤 Generate result: {result}")
            
            if result.get('success'):
                print("✅ Video generation setup successful!")
                return True
            else:
                print(f"❌ Video generation setup failed: {result.get('error')}")
                return False
                
    except Exception as e:
        print(f"❌ Generate test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Veo API Authentication Test")
    print("=" * 50)
    
    # Test authentication
    auth_success = test_veo_auth()
    
    if auth_success:
        # Test generation setup
        generate_success = test_veo_generate()
        
        if generate_success:
            print("\n🎉 All tests passed! Veo API should work correctly.")
        else:
            print("\n⚠️ Authentication works but generation setup failed.")
    else:
        print("\n❌ Authentication failed. Check your Google Cloud setup.")
    
    print("\n" + "=" * 50) 