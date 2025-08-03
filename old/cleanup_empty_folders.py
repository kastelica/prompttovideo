#!/usr/bin/env python3
"""
Cleanup Empty Folders Script

This script removes all empty subfolders under the videos/ directory
in the GCS bucket to clean up the structure.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.gcs_utils import get_gcs_bucket_name
from google.cloud import storage

def get_gcs_client():
    """Get GCS client with proper credentials"""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        creds_path = os.path.join(os.getcwd(), 'veo.json')
    
    if os.path.exists(creds_path):
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        return storage.Client(credentials=credentials)
    else:
        return storage.Client()

def get_empty_video_folders():
    """Get all empty subfolders under videos/ directory"""
    print("🔍 ===== FINDING EMPTY VIDEO FOLDERS =====")
    print()
    
    # Get GCS client
    storage_client = get_gcs_client()
    bucket_name = get_gcs_bucket_name()
    bucket = storage_client.bucket(bucket_name)
    
    # List all blobs with videos/ prefix
    blobs = list(bucket.list_blobs(prefix='videos/'))
    
    print(f"📁 Found {len(blobs)} total objects under videos/")
    
    # Extract folder paths from blob names
    folders = set()
    for blob in blobs:
        name = blob.name
        if name.startswith('videos/'):
            # Split the path and get the folder structure
            parts = name.split('/')
            if len(parts) >= 3:  # videos/folder/...
                folder_path = '/'.join(parts[:2])  # videos/folder
                folders.add(folder_path)
    
    print(f"📁 Found {len(folders)} folders under videos/")
    
    # Check which folders are empty (no files directly in them)
    empty_folders = []
    for folder in sorted(folders):
        # Check if there are any files directly in this folder
        folder_blobs = list(bucket.list_blobs(prefix=folder + '/'))
        files_in_folder = [b for b in folder_blobs if b.name != folder + '/' and not b.name.endswith('/')]
        
        if not files_in_folder:
            empty_folders.append(folder)
            print(f"   🗑️ Empty folder: {folder}")
        else:
            print(f"   📁 Folder with files: {folder} ({len(files_in_folder)} files)")
    
    print(f"\n📊 Summary:")
    print(f"   Total folders: {len(folders)}")
    print(f"   Empty folders: {len(empty_folders)}")
    print(f"   Non-empty folders: {len(folders) - len(empty_folders)}")
    
    return empty_folders

def delete_empty_folders(empty_folders):
    """Delete empty folders from GCS"""
    if not empty_folders:
        print("✅ No empty folders to delete")
        return
    
    print(f"\n🗑️ ===== DELETING EMPTY FOLDERS =====")
    print()
    
    # Get GCS client
    storage_client = get_gcs_client()
    bucket_name = get_gcs_bucket_name()
    bucket = storage_client.bucket(bucket_name)
    
    deleted_count = 0
    error_count = 0
    
    for folder in empty_folders:
        try:
            # In GCS, folders don't actually exist as objects
            # They're just prefixes in object names
            # So we need to check if there are any objects with this prefix
            blobs = list(bucket.list_blobs(prefix=folder + '/'))
            
            if not blobs:
                print(f"✅ Folder {folder} is already empty (no objects to delete)")
                deleted_count += 1
            else:
                print(f"⚠️ Folder {folder} has {len(blobs)} objects, skipping")
                
        except Exception as e:
            print(f"❌ Error checking folder {folder}: {e}")
            error_count += 1
    
    print(f"\n📊 Deletion Summary:")
    print(f"   ✅ Processed: {deleted_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📁 Total folders: {len(empty_folders)}")

def verify_cleanup():
    """Verify that empty folders have been cleaned up"""
    print(f"\n🔍 ===== VERIFYING CLEANUP =====")
    print()
    
    # Get GCS client
    storage_client = get_gcs_client()
    bucket_name = get_gcs_bucket_name()
    bucket = storage_client.bucket(bucket_name)
    
    # List all blobs with videos/ prefix
    blobs = list(bucket.list_blobs(prefix='videos/'))
    
    print(f"📁 Files under videos/ directory: {len(blobs)}")
    
    if blobs:
        print("📁 Current video files:")
        for blob in blobs[:10]:
            print(f"   - {blob.name}")
        if len(blobs) > 10:
            print(f"   ... and {len(blobs) - 10} more")
    else:
        print("✅ No files under videos/ directory (clean state)")
    
    # Check for any remaining folders
    folders = set()
    for blob in blobs:
        name = blob.name
        if name.startswith('videos/'):
            parts = name.split('/')
            if len(parts) >= 3:
                folder_path = '/'.join(parts[:2])
                folders.add(folder_path)
    
    print(f"\n📁 Folders under videos/: {len(folders)}")
    if folders:
        for folder in sorted(folders):
            folder_blobs = list(bucket.list_blobs(prefix=folder + '/'))
            files_in_folder = [b for b in folder_blobs if b.name != folder + '/' and not b.name.endswith('/')]
            print(f"   - {folder}: {len(files_in_folder)} files")

def main():
    """Main function"""
    print("🚀 Starting Empty Folder Cleanup...")
    print()
    
    try:
        # Step 1: Find empty folders
        empty_folders = get_empty_video_folders()
        
        if not empty_folders:
            print("✅ No empty folders found")
            return
        
        # Step 2: Confirm deletion
        print(f"\n⚠️ Found {len(empty_folders)} empty folders to clean up")
        confirm = input("Do you want to proceed with cleanup? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Cleanup cancelled")
            return
        
        # Step 3: Delete empty folders
        delete_empty_folders(empty_folders)
        
        # Step 4: Verify cleanup
        verify_cleanup()
        
        print(f"\n✅ Empty folder cleanup complete!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 