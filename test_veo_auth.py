#!/usr/bin/env python3
"""
Test script to diagnose VEO authentication issues
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_environment():
    """Test environment variables and authentication"""
    print("🔍 TESTING VEO AUTHENTICATION")
    print("=" * 50)
    
    # Check environment variables
    print("\n📋 ENVIRONMENT VARIABLES:")
    gac = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if gac:
        print(f"   GOOGLE_APPLICATION_CREDENTIALS: {gac}")
        if os.path.exists(gac):
            print(f"   ✅ File exists: {gac}")
        else:
            print(f"   ❌ File does NOT exist: {gac}")
            print("   🔄 Removing environment variable...")
            if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            print("   ✅ Environment variable removed")
    else:
        print("   ✅ GOOGLE_APPLICATION_CREDENTIALS not set")
    
    print(f"   GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
    print(f"   FLASK_ENV: {os.environ.get('FLASK_ENV', 'NOT SET')}")
    
    # Test Google Cloud authentication
    print("\n🔑 TESTING GOOGLE CLOUD AUTHENTICATION:")
    try:
        import google.auth
        from google.auth.transport.requests import Request
        print("   ✅ Google Cloud libraries available")
        
        # Try to get default credentials
        print("   🔄 Getting default credentials...")
        credentials, project = google.auth.default(
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/aiplatform.googleapis.com'
            ]
        )
        
        # Refresh the token
        print("   🔄 Refreshing token...")
        credentials.refresh(Request())
        
        if credentials.valid and credentials.token:
            print("   ✅ Authentication successful!")
            print(f"   📝 Project: {project}")
            print(f"   🔑 Token preview: {str(credentials.token)[:20]}...")
            return True
        else:
            print("   ❌ Credentials are not valid")
            return False
            
    except ImportError as e:
        print(f"   ❌ Google Cloud libraries not available: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return False

def test_veo_client():
    """Test the VEO client directly"""
    print("\n🎬 TESTING VEO CLIENT:")
    print("=" * 50)
    
    try:
        # Add the app directory to the Python path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        
        from app.veo_client import VeoClient
        
        print("   ✅ VEO client imported successfully")
        
        # Create client instance
        client = VeoClient()
        print(f"   📝 Project ID: {client.project_id}")
        print(f"   📝 Location: {client.location}")
        print(f"   📝 Model ID: {client.model_id}")
        
        # Test authentication
        print("   🔄 Testing authentication...")
        token = client._get_auth_token()
        
        if token:
            print("   ✅ VEO client authentication successful!")
            return True
        else:
            print("   ❌ VEO client authentication failed!")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing VEO client: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main test function"""
    print("🧪 VEO AUTHENTICATION DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Test 1: Environment
    env_ok = test_environment()
    
    # Test 2: VEO Client
    veo_ok = test_veo_client()
    
    # Summary
    print("\n📊 TEST SUMMARY:")
    print("=" * 50)
    print(f"   Environment: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"   VEO Client: {'✅ PASS' if veo_ok else '❌ FAIL'}")
    
    if env_ok and veo_ok:
        print("\n🎉 All tests passed! VEO authentication should work.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        
        if not env_ok:
            print("\n🔧 RECOMMENDATIONS:")
            print("   • Ensure you're running on Cloud Run with proper service account")
            print("   • Check that GOOGLE_CLOUD_PROJECT is set correctly")
            print("   • Verify the service account has necessary permissions")

if __name__ == '__main__':
    main() 