#!/usr/bin/env python3
"""
Test script to trigger VEO API call in production and see detailed authentication debugging
"""

import requests
import json

def test_veo_production():
    """Test VEO API call in production to trigger authentication debugging"""
    
    # Production URL
    url = "https://slopvids.com/api/v1/generate"
    
    # Test data
    data = {
        "prompt": "A beautiful sunset over the ocean",
        "quality": "free"
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print("🎬 Testing VEO API call in production...")
        print(f"📡 URL: {url}")
        print(f"📋 Data: {json.dumps(data, indent=2)}")
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
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
    print("🧪 Testing VEO Production API...")
    print("=" * 50)
    
    success = test_veo_production()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ VEO API call completed successfully!")
    else:
        print("❌ VEO API call failed.")
        print("💡 Check the Cloud Run logs for detailed authentication debugging.") 