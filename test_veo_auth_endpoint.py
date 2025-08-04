#!/usr/bin/env python3
"""
Test script to call the VEO authentication test endpoint
"""

import requests
import json

def test_veo_auth_endpoint():
    """Test the VEO authentication test endpoint"""
    
    # Production URL
    url = "https://slopvids.com/api/v1/test-veo-auth"
    
    try:
        print("🎬 Testing VEO authentication endpoint...")
        print(f"📡 URL: {url}")
        
        response = requests.get(url, timeout=60)
        
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
    print("🧪 Testing VEO Authentication Endpoint...")
    print("=" * 50)
    
    success = test_veo_auth_endpoint()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ VEO authentication test completed!")
        print("💡 Check the Cloud Run logs for detailed authentication debugging.")
    else:
        print("❌ VEO authentication test failed.") 