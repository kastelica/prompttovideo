#!/usr/bin/env python3
"""
Google Cloud Storage Setup Script for PromptToVideo
This script helps you set up GCS for storing generated videos.
"""

import os
import sys
from google.cloud import storage
from google.oauth2 import service_account

def check_credentials():
    """Check if Google Cloud credentials are available"""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        creds_path = os.path.join(os.getcwd(), 'veo.json')
    
    if os.path.exists(creds_path):
        print(f"✅ Found credentials at: {creds_path}")
        return creds_path
    else:
        print(f"❌ No credentials found at: {creds_path}")
        return None

def create_bucket(bucket_name, project_id):
    """Create a GCS bucket"""
    try:
        # Initialize storage client
        creds_path = check_credentials()
        if creds_path:
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials, project=project_id)
        else:
            storage_client = storage.Client(project=project_id)
        
        # Check if bucket already exists
        bucket = storage_client.bucket(bucket_name)
        if bucket.exists():
            print(f"✅ Bucket '{bucket_name}' already exists")
            return True
        
        # Create the bucket
        bucket = storage_client.create_bucket(bucket_name)
        print(f"✅ Created bucket: {bucket_name}")
        
        # Make bucket publicly readable (optional, for easier testing)
        bucket.make_public()
        print(f"✅ Made bucket publicly readable")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating bucket: {e}")
        return False

def update_env_file(bucket_name, project_id):
    """Update .env file with GCS settings"""
    env_file = '.env'
    env_content = []
    
    # Read existing .env file
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.readlines()
    
    # Update or add GCS settings
    gcs_bucket_setting = f"GCS_BUCKET_NAME={bucket_name}\n"
    gcs_project_setting = f"GOOGLE_CLOUD_PROJECT_ID={project_id}\n"
    
    # Check if settings already exist
    bucket_exists = any(line.startswith('GCS_BUCKET_NAME=') for line in env_content)
    project_exists = any(line.startswith('GOOGLE_CLOUD_PROJECT_ID=') for line in env_content)
    
    if not bucket_exists:
        env_content.append(gcs_bucket_setting)
    if not project_exists:
        env_content.append(gcs_project_setting)
    
    # Write back to .env file
    with open(env_file, 'w') as f:
        f.writelines(env_content)
    
    print(f"✅ Updated {env_file} with GCS settings")

def main():
    print("🚀 Google Cloud Storage Setup for PromptToVideo")
    print("=" * 50)
    
    # Check credentials
    creds_path = check_credentials()
    if not creds_path:
        print("\n❌ Please set up Google Cloud credentials first:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Navigate to IAM & Admin > Service Accounts")
        print("3. Create a new service account or select existing")
        print("4. Create a new key (JSON format)")
        print("5. Download and save as 'veo.json' in this directory")
        print("6. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        return
    
    # Get project ID from credentials
    try:
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        project_id = credentials.project_id
        print(f"✅ Using project: {project_id}")
    except Exception as e:
        print(f"❌ Error reading project ID: {e}")
        project_id = input("Enter your Google Cloud Project ID: ").strip()
    
    # Get bucket name
    bucket_name = input(f"Enter GCS bucket name (default: {project_id}-veo-videos): ").strip()
    if not bucket_name:
        bucket_name = f"{project_id}-veo-videos"
    
    # Create bucket
    print(f"\n📦 Creating bucket: {bucket_name}")
    if create_bucket(bucket_name, project_id):
        # Update .env file
        update_env_file(bucket_name, project_id)
        
        print("\n🎉 GCS Setup Complete!")
        print(f"📁 Bucket: {bucket_name}")
        print(f"🔑 Project: {project_id}")
        print(f"📄 Credentials: {creds_path}")
        
        print("\n📋 Next steps:")
        print("1. Restart your Flask application")
        print("2. Try generating a video")
        print("3. Check the bucket for uploaded videos")
    else:
        print("\n❌ GCS setup failed. Please check your credentials and try again.")

if __name__ == "__main__":
    main() 