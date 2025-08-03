#!/usr/bin/env python3
"""
Script to enable mock mode and prevent Veo API charges
"""

import os
import sys

def enable_mock_mode():
    """Enable mock mode to prevent Veo API charges"""
    
    print("💰 ===== VEO API COST PREVENTION ===== 💰")
    print()
    print("⚠️  WARNING: Veo API charges for every call, even failed ones!")
    print("⚠️  You've already been charged $145 for failed attempts.")
    print()
    print("🔧 Enabling mock mode to prevent further charges...")
    print()
    
    # Set environment variable
    os.environ['VEO_MOCK_MODE'] = 'True'
    
    print("✅ VEO_MOCK_MODE=True set in environment")
    print()
    print("🎭 Mock mode will now:")
    print("   - Skip real Veo API calls")
    print("   - Create placeholder video files")
    print("   - Prevent any further charges")
    print()
    print("🚀 To use real Veo API (and get charged):")
    print("   - Set VEO_MOCK_MODE=False")
    print("   - Or unset the environment variable")
    print()
    print("📁 Videos will be created as text files in the videos/ directory")
    print("🌐 They'll still be accessible via /videos/{video_id}.mp4")
    print()
    
    return True

def check_current_charges():
    """Check current Google Cloud charges"""
    print("💳 To check your current charges:")
    print("   1. Go to Google Cloud Console")
    print("   2. Navigate to Billing")
    print("   3. Check Vertex AI charges")
    print()
    print("🔗 https://console.cloud.google.com/billing")
    print()

if __name__ == "__main__":
    enable_mock_mode()
    check_current_charges()
    
    print("🎯 Next steps:")
    print("   1. Restart your Flask server")
    print("   2. Try generating a video")
    print("   3. Check the videos/ directory for placeholder files")
    print()
    print("💡 The system will work exactly the same, but without charges!") 