#!/usr/bin/env python3
"""
Test script to check VEO access requirements and availability
"""

import os
import requests
import json

# Set up environment
os.environ['GOOGLE_CLOUD_PROJECT'] = 'dirly-466300'

try:
    import google.auth
    from google.auth.transport.requests import Request
    print("✅ Google Cloud libraries imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Google Cloud libraries: {e}")
    exit(1)

def get_auth_token():
    """Get authentication token using Application Default Credentials"""
    try:
        print("🔑 Getting authentication token...")
        credentials, project = google.auth.default(
            scopes=[
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/aiplatform.googleapis.com'
            ]
        )
        
        # Refresh the token
        credentials.refresh(Request())
        
        if credentials.valid and credentials.token:
            print("✅ Successfully obtained authentication token")
            return credentials.token
        else:
            print("❌ Authentication token is not valid")
            return None
            
    except Exception as e:
        print(f"❌ Failed to get authentication token: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def test_veo_regions():
    """Test VEO availability in different regions"""
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test different regions where VEO might be available
    regions = [
        'us-central1',
        'us-west4', 
        'us-east1',
        'europe-west4',
        'asia-northeast1'
    ]
    
    for region in regions:
        print(f"\n🌍 Testing region: {region}")
        
        # Test 1: Check if we can access the region
        url = f"https://{region}-aiplatform.googleapis.com/v1/projects/dirly-466300/locations/{region}/publishers/google/models/veo-2.0-generate-001"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            print(f"   Model access: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ VEO model accessible in {region}")
                return region
            elif response.status_code == 404:
                print(f"   ⚠️  VEO model not found in {region}")
            elif response.status_code == 403:
                print(f"   ❌ Access denied in {region}")
            else:
                print(f"   ❌ Error {response.status_code} in {region}")
                
        except Exception as e:
            print(f"   ❌ Exception in {region}: {e}")
    
    return None

def test_veo_quota():
    """Test if there are quota or access issues"""
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test with a minimal request to see if we get quota errors
    url = "https://us-central1-aiplatform.googleapis.com/v1/projects/dirly-466300/locations/us-central1/publishers/google/models/veo-2.0-generate-001:predictLongRunning"
    
    request_data = {
        "instances": [{"prompt": "A simple test"}],
        "parameters": {
            "durationSeconds": 5,
            "aspectRatio": "16:9",
            "enhancePrompt": False,
            "sampleCount": 1,
            "personGeneration": "dont_allow",
            "storageUri": "gs://prompt-veo-videos/videos/"
        }
    }
    
    try:
        print("\n🧪 Testing VEO quota and access...")
        response = requests.post(url, headers=headers, json=request_data, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            operation_name = result.get('name')
            if operation_name:
                print(f"✅ VEO access granted! Operation: {operation_name}")
                return True
            else:
                print(f"❌ No operation name in response: {result}")
                return False
        elif response.status_code == 403:
            print(f"❌ Access denied (403): {response.text}")
            return False
        elif response.status_code == 429:
            print(f"❌ Quota exceeded (429): {response.text}")
            return False
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def check_veo_requirements():
    """Check VEO-specific requirements"""
    print("\n📋 Checking VEO Requirements:")
    print("1. Project ID: dirly-466300")
    print("2. Vertex AI API: Enabled")
    print("3. ML API: Enabled")
    print("4. Service Account: prompttovideo-runner@dirly-466300.iam.gserviceaccount.com")
    print("5. Permissions:")
    print("   - roles/aiplatform.user")
    print("   - roles/aiplatform.serviceAgent")
    print("   - roles/compute.serviceAgent")
    print("   - roles/storage.admin")
    
    print("\n🔍 VEO Access Requirements:")
    print("- VEO requires explicit access approval from Google")
    print("- Available in specific regions (us-central1, us-west4, etc.)")
    print("- May require quota allocation")
    print("- May require project-level approval")

if __name__ == "__main__":
    print("🧪 Testing VEO Access and Requirements...")
    print("=" * 60)
    
    # Check requirements
    check_veo_requirements()
    
    # Test different regions
    print("\n🌍 Testing VEO Regional Availability:")
    working_region = test_veo_regions()
    
    # Test quota and access
    print("\n🧪 Testing VEO Quota and Access:")
    access_granted = test_veo_quota()
    
    print("\n" + "=" * 60)
    if working_region and access_granted:
        print("✅ VEO is fully accessible!")
        print(f"🌍 Working region: {working_region}")
    elif working_region:
        print("⚠️  VEO model accessible but generation failed")
        print(f"🌍 Working region: {working_region}")
    else:
        print("❌ VEO access issues detected")
        print("💡 Possible solutions:")
        print("   1. Request VEO access from Google")
        print("   2. Check project-level permissions")
        print("   3. Verify regional availability")
        print("   4. Check quota allocation") 