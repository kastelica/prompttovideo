#!/usr/bin/env python3
"""
Test script for the profile system
"""

import requests
import json
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Adjust if your server runs on different port
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

def test_profile_system():
    """Test the profile system end-to-end"""
    
    print("🧪 Testing Profile System")
    print("=" * 50)
    
    # Step 1: Register a test user
    print("\n1. Registering test user...")
    register_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "confirm_password": TEST_PASSWORD
    }
    
    register_response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    
    if register_response.status_code == 200:
        print("✅ User registered successfully")
    elif register_response.status_code == 400 and "already exists" in register_response.text:
        print("ℹ️ User already exists, proceeding with login")
    else:
        print(f"❌ Registration failed: {register_response.status_code}")
        return
    
    # Step 2: Login
    print("\n2. Logging in...")
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    auth_token = login_response.json().get('access_token')
    if not auth_token:
        print("❌ No auth token received")
        return
    
    print("✅ Login successful")
    
    # Step 3: Get current user info
    print("\n3. Getting current user info...")
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    
    if me_response.status_code != 200:
        print(f"❌ Failed to get user info: {me_response.status_code}")
        return
    
    user_info = me_response.json()
    user_id = user_info.get('id')
    print(f"✅ User ID: {user_id}")
    
    # Step 4: Test profile API
    print("\n4. Testing profile API...")
    profile_response = requests.get(f"{BASE_URL}/api/v1/profile/{user_id}", headers=headers)
    
    if profile_response.status_code != 200:
        print(f"❌ Profile API failed: {profile_response.status_code}")
        print(f"Response: {profile_response.text}")
        return
    
    profile_data = profile_response.json()
    print("✅ Profile data retrieved successfully")
    print(f"   Display Name: {profile_data.get('display_name')}")
    print(f"   Total Videos: {profile_data.get('total_videos')}")
    print(f"   Total Views: {profile_data.get('total_views')}")
    print(f"   Followers: {profile_data.get('follower_count')}")
    print(f"   Following: {profile_data.get('following_count')}")
    
    # Step 5: Test profile page
    print("\n5. Testing profile page...")
    profile_page_response = requests.get(f"{BASE_URL}/profile/{user_id}")
    
    if profile_page_response.status_code == 200:
        print("✅ Profile page loads successfully")
        if "profileContainer" in profile_page_response.text:
            print("✅ Profile container found in HTML")
        else:
            print("⚠️ Profile container not found in HTML")
    else:
        print(f"❌ Profile page failed: {profile_page_response.status_code}")
    
    # Step 6: Test follow functionality
    print("\n6. Testing follow functionality...")
    follow_response = requests.post(f"{BASE_URL}/api/v1/follow/{user_id}", headers=headers)
    
    if follow_response.status_code == 200:
        follow_data = follow_response.json()
        print(f"✅ Follow action: {follow_data.get('action')}")
    else:
        print(f"❌ Follow failed: {follow_response.status_code}")
    
    # Step 7: Test profile update
    print("\n7. Testing profile update...")
    update_data = {
        "display_name": f"Test User {datetime.now().strftime('%H:%M:%S')}",
        "bio": "This is a test bio for the updated profile system.",
        "location": "Test City, Test Country"
    }
    
    update_response = requests.put(f"{BASE_URL}/api/v1/profile", json=update_data, headers=headers)
    
    if update_response.status_code == 200:
        print("✅ Profile updated successfully")
    else:
        print(f"❌ Profile update failed: {update_response.status_code}")
    
    # Step 8: Verify updated profile
    print("\n8. Verifying updated profile...")
    updated_profile_response = requests.get(f"{BASE_URL}/api/v1/profile/{user_id}", headers=headers)
    
    if updated_profile_response.status_code == 200:
        updated_profile = updated_profile_response.json()
        print(f"✅ Updated display name: {updated_profile.get('display_name')}")
        print(f"✅ Updated bio: {updated_profile.get('bio')}")
        print(f"✅ Updated location: {updated_profile.get('location')}")
    else:
        print(f"❌ Failed to get updated profile: {updated_profile_response.status_code}")
    
    print("\n" + "=" * 50)
    print("🎉 Profile system test completed!")
    print(f"📝 Test results saved to: test_profile_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    # Save test results
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "profile_data": profile_data,
        "updated_profile": updated_profile_response.json() if updated_profile_response.status_code == 200 else None,
        "follow_action": follow_response.json() if follow_response.status_code == 200 else None
    }
    
    with open(f"test_profile_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(test_results, f, indent=2)

if __name__ == "__main__":
    test_profile_system() 