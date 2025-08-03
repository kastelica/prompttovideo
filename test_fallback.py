#!/usr/bin/env python3
"""
Test script to verify the fallback mechanism works without Redis
"""

import requests
import json
import time

def test_video_generation_fallback():
    """Test video generation without Redis (should use direct execution)"""
    
    # Test data
    test_data = {
        "prompt": "A beautiful sunset over mountains",
        "quality": "free"
    }
    
    print("🧪 Testing video generation fallback (without Redis)...")
    print(f"📝 Test prompt: {test_data['prompt']}")
    print(f"📝 Test quality: {test_data['quality']}")
    
    try:
        # Make request to generate video
        print("📤 Sending request to /generate...")
        response = requests.post(
            'http://localhost:5000/generate',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response: {data}")
            
            if 'task_id' in data:
                print("🎯 Celery task queued successfully!")
            else:
                print("🔄 Using direct execution (fallback mode)")
                
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_redis_connection():
    """Test if Redis is available"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is available")
        return True
    except Exception as e:
        print(f"❌ Redis not available: {e}")
        return False

if __name__ == "__main__":
    print("🚀 PromptToVideo Fallback Test")
    print("=" * 40)
    
    # Test Redis availability
    redis_available = test_redis_connection()
    
    if not redis_available:
        print("\n📝 Redis not available - testing fallback mechanism...")
        success = test_video_generation_fallback()
        
        if success:
            print("\n🎉 SUCCESS: Fallback mechanism works!")
            print("📝 The system will use direct execution instead of Celery")
        else:
            print("\n❌ FAILED: Fallback mechanism not working")
    else:
        print("\n✅ Redis is available - testing Celery mode...")
        success = test_video_generation_fallback()
        
        if success:
            print("\n🎉 SUCCESS: Celery mode works!")
        else:
            print("\n❌ FAILED: Celery mode not working")
    
    print("\n" + "=" * 40)
    print("�� Test complete!") 