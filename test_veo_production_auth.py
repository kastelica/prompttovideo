#!/usr/bin/env python3
"""
Test script to trigger VEO API call in production with authentication
"""

import requests
import json

def test_veo_production_with_auth():
    """Test VEO API call in production with authentication"""
    
    # Production URL
    url = "https://slopvids.com/api/v1/generate"
    
    # Test data
    data = {
        "prompt": "A beautiful sunset over the ocean",
        "quality": "free"
    }
    
    # First, let's try to get an auth token by logging in
    login_url = "https://slopvids.com/auth/login"
    login_data = {
        "email": "user1@test.com",
        "password": "password123"
    }
    
    session = requests.Session()
    
    try:
        print("🔐 Attempting to authenticate...")
        
        # Get the login page to get any CSRF tokens
        login_page = session.get(login_url)
        print(f"📡 Login page status: {login_page.status_code}")
        
        # Try to login
        login_response = session.post(login_url, data=login_data, allow_redirects=True)
        print(f"📡 Login response status: {login_response.status_code}")
        
        # Check if we're authenticated by trying to access a protected page
        dashboard_response = session.get("https://slopvids.com/dashboard")
        print(f"📡 Dashboard access status: {dashboard_response.status_code}")
        
        if dashboard_response.status_code == 200:
            print("✅ Successfully authenticated!")
            
            # Now try the VEO API call
            print("\n🎬 Testing VEO API call with authentication...")
            print(f"📡 URL: {url}")
            print(f"📋 Data: {json.dumps(data, indent=2)}")
            
            headers = {
                'Content-Type': 'application/json'
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
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing VEO Production API with Authentication...")
    print("=" * 60)
    
    success = test_veo_production_with_auth()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ VEO API call completed successfully!")
    else:
        print("❌ VEO API call failed.")
        print("💡 Check the Cloud Run logs for detailed authentication debugging.") 