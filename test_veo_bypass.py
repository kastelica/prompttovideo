#!/usr/bin/env python3
"""
Test to trigger VEO authentication by accessing the video generation form
"""

import requests

def test_veo_form_trigger():
    """Test to trigger VEO authentication by accessing the video generation form"""
    
    session = requests.Session()
    
    try:
        print("🎬 Testing VEO trigger by accessing video generation form...")
        
        # Try to access the main page which should have the video generation form
        main_url = "https://slopvids.com/"
        
        print(f"📡 Accessing: {main_url}")
        response = session.get(main_url, timeout=30)
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Successfully accessed main page")
            
            # Check if the response contains video generation form elements
            content = response.text.lower()
            if 'generate' in content or 'video' in content or 'prompt' in content:
                print("✅ Found video generation form elements")
                print("💡 This should have triggered any VEO-related code")
            else:
                print("⚠️  No video generation form elements found")
            
            return True
        else:
            print(f"❌ Failed to access main page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing VEO Form Trigger...")
    print("=" * 40)
    
    success = test_veo_form_trigger()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Test completed successfully!")
        print("💡 Check the Cloud Run logs for VEO authentication debugging.")
    else:
        print("❌ Test failed.") 