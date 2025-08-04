#!/usr/bin/env python3
"""
Simple test to trigger VEO authentication by accessing the video generation form
"""

import requests

def test_veo_trigger():
    """Test to trigger VEO authentication by accessing the video generation form"""
    
    session = requests.Session()
    
    try:
        print("🎬 Testing VEO trigger by accessing video generation form...")
        
        # Try to access the dashboard which should trigger any VEO-related code
        dashboard_url = "https://slopvids.com/dashboard"
        
        print(f"📡 Accessing: {dashboard_url}")
        response = session.get(dashboard_url, timeout=30)
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Successfully accessed dashboard")
            print("💡 This should have triggered any VEO-related code")
            return True
        else:
            print(f"❌ Failed to access dashboard: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing VEO Trigger...")
    print("=" * 40)
    
    success = test_veo_trigger()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Test completed successfully!")
        print("💡 Check the Cloud Run logs for VEO authentication debugging.")
    else:
        print("❌ Test failed.") 