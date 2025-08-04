#!/usr/bin/env python3
"""
Test script for AI suggestion endpoints
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_PROMPT = "A beautiful sunset over the ocean"

def test_ai_suggest():
    """Test the improve prompt endpoint"""
    print("🧪 Testing /api/ai-suggest (improve prompt)...")
    
    url = f"{BASE_URL}/api/ai-suggest"
    data = {"prompt": TEST_PROMPT}
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"📝 Original prompt: {result.get('original_prompt')}")
            print(f"💡 Suggestions: {len(result.get('suggestions', []))}")
            for i, suggestion in enumerate(result.get('suggestions', []), 1):
                print(f"   {i}. {suggestion}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_ai_suggest_random():
    """Test the random suggestions endpoint"""
    print("\n🧪 Testing /api/ai-suggest-random (random ideas)...")
    
    url = f"{BASE_URL}/api/ai-suggest-random"
    
    try:
        response = requests.post(url, timeout=30)
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"💡 Random suggestions: {len(result.get('suggestions', []))}")
            for i, suggestion in enumerate(result.get('suggestions', []), 1):
                print(f"   {i}. {suggestion}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("🚀 Testing AI Suggestion Endpoints")
    print("=" * 50)
    
    test_ai_suggest()
    test_ai_suggest_random()
    
    print("\n✅ Testing complete!") 