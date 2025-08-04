#!/usr/bin/env python3
"""
Test script to trigger VEO API call in production with JWT authentication
"""

import requests
import json
import re

def test_veo_production_with_jwt():
    """Test VEO API call in production with JWT authentication"""
    
    # Production URL
    url = "https://slopvids.com/api/v1/generate"
    
    # Test data
    data = {
        "prompt": "A beautiful sunset over the ocean",
        "quality": "free"
    }
    
    session = requests.Session()
    
    try:
        print("🔐 Attempting to get JWT token...")
        
        # Step 1: Get the login page
        login_url = "https://slopvids.com/auth/login"
        login_page = session.get(login_url)
        print(f"📡 Login page status: {login_page.status_code}")
        
        # Step 2: Try to login (this should set the auth_token cookie)
        login_data = {
            "email": "user1@test.com",
            "password": "password123"
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        login_response = session.post(login_url, json=login_data, headers=headers, allow_redirects=True)
        print(f"📡 Login response status: {login_response.status_code}")
        
        # Step 3: Check if we have an auth_token cookie
        auth_token = session.cookies.get('auth_token')
        if auth_token:
            print(f"✅ Got auth token: {auth_token[:20]}...")
        else:
            print("❌ No auth token found in cookies")
            return False
        
        # Step 4: Now try the VEO API call with the JWT token
        print("\n🎬 Testing VEO API call with JWT authentication...")
        print(f"📡 URL: {url}")
        print(f"📋 Data: {json.dumps(data, indent=2)}")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }
        
        response = session.post(url, headers=headers, json=data, timeout=60)
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"📡 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📄 Response Text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing VEO Production API with JWT Authentication...")
    print("=" * 60)
    
    success = test_veo_production_with_jwt()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ VEO API call completed successfully!")
    else:
        print("❌ VEO API call failed.")
        print("💡 Check the Cloud Run logs for detailed authentication debugging.") 