#!/usr/bin/env python3
"""
Test Google Cloud authentication
"""

import os
from google.oauth2 import service_account
from google.auth.transport import requests

def test_google_auth():
    """Test Google Cloud authentication"""
    print("🔐 Testing Google Cloud authentication...")
    
    try:
        # Check if credentials file exists
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
            return False
        
        if not os.path.exists(creds_path):
            print(f"❌ Credentials file not found: {creds_path}")
            return False
        
        print(f"✅ Credentials file found: {creds_path}")
        
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        print("✅ Service account credentials loaded")
        
        # Test authentication
        auth_req = requests.Request()
        credentials.refresh(auth_req)
        
        if credentials.valid:
            print("✅ Authentication successful!")
            print(f"📋 Project ID: {credentials.project_id}")
            print(f"🔑 Token expires: {credentials.expiry}")
            return True
        else:
            print("❌ Authentication failed - credentials not valid")
            return False
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

if __name__ == '__main__':
    test_google_auth() 