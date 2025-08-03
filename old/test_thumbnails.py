#!/usr/bin/env python3
"""
Test script for video thumbnail generation functionality
Tests various scenarios and provides detailed output
"""

import os
import sys
import requests
from urllib.parse import urljoin

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Video

app = create_app()
app.app_context().push()

print("Checking video thumbnail status...")

# Count videos without thumbnails
videos_without_thumbnails = Video.query.filter(
    Video.gcs_signed_url.isnot(None),
    Video.gcs_signed_url != '',
    (Video.thumbnail_url.is_(None) | (Video.thumbnail_url == ''))
).count()

print(f"Videos without thumbnails: {videos_without_thumbnails}")

# Count videos with thumbnails
videos_with_thumbnails = Video.query.filter(
    Video.thumbnail_url.isnot(None),
    Video.thumbnail_url != ''
).count()

print(f"Videos with thumbnails: {videos_with_thumbnails}")

# Total videos with GCS URLs
total_videos = Video.query.filter(
    Video.gcs_signed_url.isnot(None),
    Video.gcs_signed_url != ''
).count()

print(f"Total videos with GCS URLs: {total_videos}")

# Show some examples
print("\nSample videos without thumbnails:")
videos = Video.query.filter(
    Video.gcs_signed_url.isnot(None),
    Video.gcs_signed_url != '',
    (Video.thumbnail_url.is_(None) | (Video.thumbnail_url == ''))
).limit(5).all()

for video in videos:
    print(f"  ID: {video.id}, Prompt: {video.prompt[:30]}...") 