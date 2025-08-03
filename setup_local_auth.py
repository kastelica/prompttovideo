#!/usr/bin/env python3
"""
Setup script for local Veo API authentication
"""

import subprocess
import os
import sys

def check_gcloud_auth():
    """Check if gcloud is authenticated"""
    print("🔍 Checking gcloud authentication...")
    
    try:
        result = subprocess.run(['gcloud', 'auth', 'list'], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            if 'ACTIVE' in result.stdout:
                print("✅ gcloud is authenticated")
                return True
            else:
                print("❌ gcloud is not authenticated")
                return False
        else:
            print("❌ Failed to check gcloud auth")
            return False
            
    except FileNotFoundError:
        print("❌ gcloud command not found")
        return False
    except Exception as e:
        print(f"❌ Error checking gcloud auth: {e}")
        return False

def setup_application_default_credentials():
    """Set up application default credentials"""
    print("\n🔧 Setting up application default credentials...")
    
    try:
        result = subprocess.run(['gcloud', 'auth', 'application-default', 'login'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Application default credentials set up successfully")
            return True
        else:
            print(f"❌ Failed to set up application default credentials: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up application default credentials: {e}")
        return False

def check_project_config():
    """Check if project is configured"""
    print("\n🔍 Checking project configuration...")
    
    try:
        result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            project = result.stdout.strip()
            if project:
                print(f"✅ Project configured: {project}")
                return True
            else:
                print("❌ No project configured")
                return False
        else:
            print("❌ Failed to get project configuration")
            return False
            
    except Exception as e:
        print(f"❌ Error checking project configuration: {e}")
        return False

def set_project():
    """Set the project"""
    project_id = "dirly-466300"
    print(f"\n🔧 Setting project to: {project_id}")
    
    try:
        result = subprocess.run(['gcloud', 'config', 'set', 'project', project_id], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ Project set to: {project_id}")
            return True
        else:
            print(f"❌ Failed to set project: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting project: {e}")
        return False

def test_access_token():
    """Test getting an access token"""
    print("\n🧪 Testing access token retrieval...")
    
    try:
        result = subprocess.run([
            'gcloud', 'auth', 'application-default', 'print-access-token',
            '--scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/aiplatform.googleapis.com'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            token = result.stdout.strip()
            if token:
                print("✅ Successfully obtained access token")
                print(f"🔍 Token length: {len(token)}")
                print(f"🔍 Token preview: {token[:20]}...")
                return True
            else:
                print("❌ Got empty access token")
                return False
        else:
            print(f"❌ Failed to get access token: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing access token: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Veo API Local Authentication Setup")
    print("=" * 50)
    
    # Check if gcloud is authenticated
    if not check_gcloud_auth():
        print("\n🔧 Please run: gcloud auth login")
        print("Then run this script again.")
        return False
    
    # Check project configuration
    if not check_project_config():
        if not set_project():
            return False
    
    # Set up application default credentials
    if not setup_application_default_credentials():
        return False
    
    # Test access token
    if not test_access_token():
        return False
    
    print("\n🎉 Local authentication setup complete!")
    print("You can now run: python test_veo_auth.py")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 