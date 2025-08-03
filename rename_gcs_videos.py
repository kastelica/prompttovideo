#!/usr/bin/env python3
"""
Rename GCS Videos to Descriptive Names
=====================================

This script renames video files in GCS to use descriptive names based on their titles.
It will create a mapping of current names to new descriptive names.
"""

import os
import sys
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from google.cloud import storage

# Database connection
DATABASE_URL = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"

def connect_to_database():
    """Connect to the production database"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return engine, Session()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None, None

def get_videos_with_mappings(session):
    """Get videos that have been successfully mapped to GCS files"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                prompt,
                slug,
                gcs_url,
                veo_job_id,
                status,
                public
            FROM videos 
            WHERE status = 'completed' AND gcs_url IS NOT NULL
            ORDER BY id
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return []

def generate_descriptive_filename(video):
    """Generate a descriptive filename from video title"""
    if not video.title:
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
    print(f"\n📝 CREATING RENAME MAPPING")
    print("=" * 60)
    
    mappings = []
    
    for video in videos:
        # Extract current path from GCS URL
        if video.gcs_url:
            # Convert gs://bucket/path to just path
            current_path = video.gcs_url.replace('gs://prompt-veo-videos/', '')
            
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
            
            print(f"📹 Video {video.id}: '{video.title}'")
            print(f"   Current: {current_path}")
            print(f"   New: {new_path}")
            print()
    
    return mappings

def preview_rename_operations(mappings):
    """Preview what rename operations would look like"""
    print(f"\n🔍 RENAME PREVIEW")
    print("=" * 60)
    
    print("The following rename operations would be performed:")
    print()
    
    for i, mapping in enumerate(mappings, 1):
        video = mapping['video']
        current = mapping['current_path']
        new = mapping['new_path']
        
        print(f"{i:2d}. Video {video.id}: '{video.title}'")
        print(f"    FROM: {current}")
        print(f"    TO:   {new}")
        print()

def create_rename_script(mappings, bucket_name="prompt-veo-videos"):
    """Create a Python script to perform the renames"""
    script_content = f"""#!/usr/bin/env python3
\"\"\"
Rename GCS Video Files
=====================

This script renames video files in GCS to use descriptive names.
Generated automatically by rename_gcs_videos.py
\"\"\"

from google.cloud import storage
import os

def rename_gcs_files():
    \"\"\"Rename GCS video files to descriptive names\"\"\"
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket("{bucket_name}")
    
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
    
    print("🔄 Starting rename operations...")
    print(f"Total files to rename: {len(rename_operations)}")
    print()
    
    success_count = 0
    error_count = 0
    
    for current_path, new_path in rename_operations:
        try:
            # Get the blob
            blob = bucket.blob(current_path)
            
            if not blob.exists():
                print(f"❌ File not found: {current_path}")
                error_count += 1
                continue
            
            # Copy to new location
            new_blob = bucket.blob(new_path)
            bucket.copy_blob(blob, bucket, new_path)
            
            # Delete old file
            blob.delete()
            
            print(f"✅ Renamed: {current_path} → {new_path}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error renaming {current_path}: {e}")
            error_count += 1
    
    print()
    print(f"📊 RENAME SUMMARY:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📁 Total: {len(rename_operations)}")

if __name__ == "__main__":
    rename_gcs_files()
"""
    
    # Write the script
    script_filename = "perform_gcs_renames.py"
    with open(script_filename, 'w') as f:
        f.write(script_content)
    
    print(f"📄 Rename script created: {script_filename}")
    print(f"   Run: python {script_filename}")
    print(f"   This will rename {len(mappings)} files")
    
    return script_filename

def create_csv_mapping(mappings):
    """Create a CSV file with the mapping for reference"""
    csv_content = "Video ID,Title,Current Path,New Path,New Filename\n"
    
    for mapping in mappings:
        video = mapping['video']
        csv_content += f"{video.id},\"{video.title}\",{mapping['current_path']},{mapping['new_path']},{mapping['new_filename']}\n"
    
    csv_filename = "video_rename_mapping.csv"
    with open(csv_filename, 'w') as f:
        f.write(csv_content)
    
    print(f"📊 CSV mapping created: {csv_filename}")
    return csv_filename

def main():
    """Main rename process"""
    print("🔄 RENAME GCS VIDEOS TO DESCRIPTIVE NAMES")
    print("=" * 60)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get videos
        print("📊 Fetching videos from database...")
        videos = get_videos_with_mappings(session)
        if not videos:
            print("❌ No videos found with GCS URLs")
            return
        
        print(f"✅ Found {len(videos)} videos with GCS URLs")
        
        # Create rename mapping
        mappings = create_rename_mapping(videos)
        
        if not mappings:
            print("❌ No mappings created")
            return
        
        # Preview operations
        preview_rename_operations(mappings)
        
        # Ask user if they want to proceed
        response = input(f"\nDo you want to create the rename script for {len(mappings)} files? (y/n): ")
        
        if response.lower() == 'y':
            # Create rename script
            script_filename = create_rename_script(mappings)
            
            # Create CSV mapping
            csv_filename = create_csv_mapping(mappings)
            
            print(f"\n✅ Ready to rename {len(mappings)} files!")
            print(f"📄 Review the mapping in: {csv_filename}")
            print(f"🚀 Run the rename script: python {script_filename}")
            print(f"\n⚠️  WARNING: This will permanently rename files in GCS!")
            print(f"   Make sure to backup or test on a small subset first.")
        else:
            print("❌ Rename script creation cancelled")
        
    except Exception as e:
        print(f"❌ Error during rename process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 