#!/usr/bin/env python3
"""
Setup PromptToVideo for real Veo API mode
"""

import os

def setup_real_mode():
    """Set up environment for real Veo API mode"""
    print("🚀 Setting up PromptToVideo for real Veo API mode...")
    
    # Create .env file with real mode settings
    env_content = """FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production
DATABASE_URL=sqlite:///app.db
VEO_MOCK_MODE=false
GCS_BUCKET_NAME=your-gcs-bucket-name
DAILY_FREE_CREDITS=3
CREDIT_COST_360P=1
CREDIT_COST_1080P=3
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("📝 Updated .env file with real mode settings")
    print("✅ VEO_MOCK_MODE=false")
    print()
    print("🔑 Next steps to enable real video generation:")
    print("1. Set up Google Cloud credentials:")
    print("   - Go to: https://console.cloud.google.com/")
    print("   - Create a service account and download the JSON key")
    print("   - Set environment variable: GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
    print()
    print("2. Set your Google Cloud project ID:")
    print("   - Set environment variable: GOOGLE_CLOUD_PROJECT_ID=your-project-id")
    print()
    print("3. Enable Veo API in your Google Cloud project:")
    print("   - Go to: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com")
    print("   - Enable the Vertex AI API")
    print()
    print("4. Set up a GCS bucket for video storage:")
    print("   - Create a bucket in Google Cloud Storage")
    print("   - Update GCS_BUCKET_NAME in .env file")
    print()
    print("⚠️  Note: Real mode will make actual API calls and may incur charges!")
    print("💡 For testing without charges, keep VEO_MOCK_MODE=true")

if __name__ == '__main__':
    setup_real_mode() 