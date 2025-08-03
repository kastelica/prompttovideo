#!/usr/bin/env python3
"""
Create Rename Script for GCS Videos
==================================

This script creates a mapping and rename script for GCS video files.
"""

import os
import sys
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"

def connect_to_database():
    """Connect to the production database"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return engine, Session()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None, None

def get_videos_with_gcs_urls(session):
    """Get videos that have GCS URLs"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                gcs_url,
                status
            FROM videos 
            WHERE status = 'completed' AND gcs_url IS NOT NULL
            ORDER BY id
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return []

def generate_descriptive_filename(video):
    """Generate a descriptive filename from video title"""
    if not video.title or video.title == 'None':
        return f"video_{video.id}.mp4"
    
    # Clean the title for filename
    filename = video.title.lower()
    # Remove special characters except spaces and hyphens
    filename = re.sub(r'[^a-z0-9\s-]', '', filename)
    # Replace spaces with hyphens
    filename = re.sub(r'\s+', '-', filename)
    # Remove multiple hyphens
    filename = re.sub(r'-+', '-', filename)
    # Remove leading/trailing hyphens
    filename = filename.strip('-')
    
    # Add video ID for uniqueness
    filename = f"{filename}-{video.id}.mp4"
    
    return filename

def create_rename_mapping(videos):
    """Create mapping of current GCS paths to new descriptive names"""
    mappings = []
    
    for video in videos:
        if video.gcs_url:
            # Extract current path from GCS URL
            current_path = video.gcs_url.replace('gs://prompt-veo-videos/', '')
            
            # Handle signed URLs
            if current_path.startswith('https://'):
                # Extract just the path part from signed URL
                path_match = re.search(r'/archive/videos/(\d+\.mp4)', current_path)
                if path_match:
                    current_path = f"archive/videos/{path_match.group(1)}"
                else:
                    continue  # Skip if we can't parse the signed URL
            
            # Generate new descriptive name
            new_filename = generate_descriptive_filename(video)
            
            # Create new path (keep archive structure)
            path_parts = current_path.split('/')
            if len(path_parts) >= 3:
                # archive/20250803_050844/videos/[job_id]/sample_0.mp4
                new_path = f"{path_parts[0]}/{path_parts[1]}/videos/{new_filename}"
            else:
                # Fallback
                new_path = f"archive/videos/{new_filename}"
            
            mappings.append({
                'video': video,
                'current_path': current_path,
                'new_path': new_path,
                'new_filename': new_filename
            })
    
    return mappings

def create_rename_script(mappings):
    """Create a Python script to perform the renames"""
    script_content = """#!/usr/bin/env python3
\"\"\"
Rename GCS Video Files
=====================

This script renames video files in GCS to use descriptive names.
Generated automatically by create_rename_script.py
\"\"\"

from google.cloud import storage
import os

def rename_gcs_files():
    \"\"\"Rename GCS video files to descriptive names\"\"\"
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket("prompt-veo-videos")
    
    # Rename operations
    rename_operations = [
"""
    
    for mapping in mappings:
        current = mapping['current_path']
        new = mapping['new_path']
        video = mapping['video']
        
        script_content += f"""        # Video {video.id}: '{video.title}'
        ("{current}", "{new}"),
"""
    
    script_content += """    ]
    
    print("Starting rename operations...")
    print(f"Total files to rename: {len(rename_operations)}")
    print()
    
    success_count = 0
    error_count = 0
    
    for current_path, new_path in rename_operations:
        try:
            # Get the blob
            blob = bucket.blob(current_path)
            
            if not blob.exists():
                print(f"File not found: {current_path}")
                error_count += 1
                continue
            
            # Copy to new location
            new_blob = bucket.blob(new_path)
            bucket.copy_blob(blob, bucket, new_path)
            
            # Delete old file
            blob.delete()
            
            print(f"Renamed: {current_path} -> {new_path}")
            success_count += 1
            
        except Exception as e:
            print(f"Error renaming {current_path}: {e}")
            error_count += 1
    
    print()
    print(f"RENAME SUMMARY:")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(rename_operations)}")

if __name__ == "__main__":
    rename_gcs_files()
"""
    
    # Write the script
    script_filename = "perform_gcs_renames.py"
    with open(script_filename, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"Rename script created: {script_filename}")
    return script_filename

def create_csv_mapping(mappings):
    """Create a CSV file with the mapping for reference"""
    csv_content = "Video ID,Title,Current Path,New Path,New Filename\n"
    
    for mapping in mappings:
        video = mapping['video']
        csv_content += f"{video.id},\"{video.title}\",{mapping['current_path']},{mapping['new_path']},{mapping['new_filename']}\n"
    
    csv_filename = "video_rename_mapping.csv"
    with open(csv_filename, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    print(f"CSV mapping created: {csv_filename}")
    return csv_filename

def main():
    """Main process"""
    print("CREATE RENAME SCRIPT FOR GCS VIDEOS")
    print("=" * 50)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get videos
        print("Fetching videos from database...")
        videos = get_videos_with_gcs_urls(session)
        if not videos:
            print("No videos found with GCS URLs")
            return
        
        print(f"Found {len(videos)} videos with GCS URLs")
        
        # Create rename mapping
        mappings = create_rename_mapping(videos)
        
        if not mappings:
            print("No mappings created")
            return
        
        # Show preview
        print(f"\nRENAME PREVIEW:")
        print("-" * 40)
        for i, mapping in enumerate(mappings[:5], 1):
            video = mapping['video']
            current = mapping['current_path']
            new = mapping['new_path']
            
            print(f"{i}. Video {video.id}: '{video.title}'")
            print(f"   FROM: {current}")
            print(f"   TO:   {new}")
            print()
        
        if len(mappings) > 5:
            print(f"... and {len(mappings) - 5} more")
        
        # Create files
        script_filename = create_rename_script(mappings)
        csv_filename = create_csv_mapping(mappings)
        
        print(f"\nReady to rename {len(mappings)} files!")
        print(f"Review the mapping in: {csv_filename}")
        print(f"Run the rename script: python {script_filename}")
        print(f"\nWARNING: This will permanently rename files in GCS!")
        print(f"Make sure to backup or test on a small subset first.")
        
    except Exception as e:
        print(f"Error during process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 