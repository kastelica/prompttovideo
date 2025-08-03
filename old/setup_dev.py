#!/usr/bin/env python3
"""
Development Setup Script for PromptToVideo

This script helps set up the development environment without requiring
Google Cloud credentials. It enables mock mode for the Veo API.
"""

import os
import sys

def setup_development_env():
    """Set up development environment variables"""
    
    print("🚀 Setting up PromptToVideo development environment...")
    
    # Check if .env file exists
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"✅ Found existing {env_file} file")
    else:
        print(f"📝 Creating {env_file} file...")
    
    # Development environment variables
    env_vars = {
        'FLASK_ENV': 'development',
        'SECRET_KEY': 'dev-secret-key-change-in-production',
        'JWT_SECRET_KEY': 'dev-jwt-secret-key-change-in-production',
        'DATABASE_URL': 'sqlite:///app.db',
        'VEO_MOCK_MODE': 'true',  # Enable mock mode for development
        'GCS_BUCKET_NAME': 'mock-bucket',
        'DAILY_FREE_CREDITS': '3',
        'CREDIT_COST_360P': '1',
        'CREDIT_COST_1080P': '3',
    }
    
    # Write to .env file
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print("✅ Development environment configured!")
    print("\n📋 Configuration:")
    for key, value in env_vars.items():
        print(f"   {key}={value}")
    
    print("\n🎯 Next steps:")
    print("1. Run: python app.py")
    print("2. Open: http://localhost:5000")
    print("3. Create an account and try generating a video!")
    print("\n💡 Note: Veo API is in mock mode for development")
    print("   Videos will be simulated without requiring Google Cloud credentials")

if __name__ == '__main__':
    setup_development_env() 