#!/usr/bin/env python3
"""
Make Bucket Public
=================

This script makes the GCS bucket or specific folders publicly accessible
so thumbnails can be accessed without authentication.
"""

import os
import sys
from google.cloud import storage
from google.cloud.storage import Bucket

def make_bucket_public():
    """Make the bucket or specific folders publicly accessible"""
    
    # Initialize GCS client
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket("prompt-veo-videos")
    except Exception as e:
        print(f"Failed to connect to GCS: {e}")
        return
    
    try:
        print("Making bucket publicly accessible...")
        
        # Make the entire bucket publicly readable
        # This will allow public access to all objects in the bucket
        bucket.make_public()
        
        print("✅ Bucket is now publicly accessible!")
        print("All objects in the bucket can now be accessed without authentication.")
        print()
        print("You can now access thumbnails using direct URLs like:")
        print("https://storage.googleapis.com/prompt-veo-videos/archive/20250803_050844/thumbnails/1.jpg")
        print()
        print("The thumbnails should now be visible on your website.")
        
    except Exception as e:
        print(f"❌ Error making bucket public: {e}")
        print()
        print("Alternative solutions:")
        print("1. Use signed URLs with 7-day expiration (maximum allowed)")
        print("2. Set up a Cloud CDN for public access")
        print("3. Use Firebase Hosting for static assets")
        print("4. Configure bucket IAM policies manually in Google Cloud Console")

if __name__ == "__main__":
    print("MAKE BUCKET PUBLIC")
    print("=" * 50)
    make_bucket_public() 