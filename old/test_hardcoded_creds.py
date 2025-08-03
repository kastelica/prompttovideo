#!/usr/bin/env python3
"""
Test hardcoded credentials in VeoClient
"""

from app import create_app
from app.veo_client import VeoClient

def test_hardcoded_creds():
    """Test hardcoded credentials"""
    app = create_app()
    
    with app.app_context():
        print("🔐 Testing hardcoded credentials...")
        
        try:
            veo_client = VeoClient()
            print("✅ VeoClient initialized successfully")
            
            # Test getting auth token
            token = veo_client._get_auth_token()
            print(f"✅ Auth token obtained: {token[:20]}..." if len(token) > 20 else f"✅ Auth token: {token}")
            
            # Test video generation
            print("\n🎬 Testing video generation...")
            result = veo_client.generate_video("A beautiful sunset over the ocean", "360p", 8)
            print(f"✅ Video generation result: {result}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_hardcoded_creds() 