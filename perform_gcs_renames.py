#!/usr/bin/env python3
"""
Rename GCS Video Files
=====================

This script renames video files in GCS to use descriptive names.
Generated automatically by create_rename_script.py
"""

from google.cloud import storage
import os

def rename_gcs_files():
    """Rename GCS video files to descriptive names"""
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket("prompt-veo-videos")
    
    # Rename operations
    rename_operations = [
        # Video 1: 'Monkey in tree'
        ("archive/videos/10875715537089896394/sample_0.mp4", "archive/videos/videos/monkey-in-tree-1.mp4"),
        # Video 2: 'Monkey in space'
        ("archive/videos/11011262595541970115/sample_0.mp4", "archive/videos/videos/monkey-in-space-2.mp4"),
        # Video 3: 'Ladybugs playing tennis'
        ("archive/videos/12252732177473975870/sample_0.mp4", "archive/videos/videos/ladybugs-playing-tennis-3.mp4"),
        # Video 4: 'Bblyrics in Recycle bin'
        ("archive/videos/1422573394135096443/sample_0.mp4", "archive/videos/videos/bblyrics-in-recycle-bin-4.mp4"),
        # Video 5: 'Hockey player flying'
        ("archive/videos/14398545529728304036/sample_0.mp4", "archive/videos/videos/hockey-player-flying-5.mp4"),
        # Video 11: 'Colorful Balloons'
        ("archive/videos/11.mp4", "archive/videos/videos/colorful-balloons-11.mp4"),
        # Video 13: 'None'
        ("archive/videos/13.mp4", "archive/videos/videos/video_13.mp4"),
        # Video 14: 'None'
        ("archive/videos/14.mp4", "archive/videos/videos/video_14.mp4"),
        # Video 15: 'None'
        ("archive/videos/15.mp4", "archive/videos/videos/video_15.mp4"),
        # Video 16: 'None'
        ("archive/videos/16.mp4", "archive/videos/videos/video_16.mp4"),
        # Video 61: 'Ocean Waves Crashing'
        ("archive/videos/61.mp4", "archive/videos/videos/ocean-waves-crashing-61.mp4"),
        # Video 1166575668786923349: 'Horse on skates'
        ("archive/videos/1166575668786923349/sample_0.mp4", "archive/videos/videos/horse-on-skates-1166575668786923349.mp4"),
        # Video 1422573394135096443: 'Waterfall in Jungle'
        ("archive/videos/1422573394135096443/sample_0.mp4", "archive/videos/videos/waterfall-in-jungle-1422573394135096443.mp4"),
        # Video 2418485289036200076: 'Aurora Borealis'
        ("archive/videos/2418485289036200076/sample_0.mp4", "archive/videos/videos/aurora-borealis-2418485289036200076.mp4"),
        # Video 3408840530871288378: 'Volcano Eruption'
        ("archive/videos/3408840530871288378/sample_0.mp4", "archive/videos/videos/volcano-eruption-3408840530871288378.mp4"),
        # Video 4333248414357645713: 'Underwater Coral Reef'
        ("archive/videos/4333248414357645713/sample_0.mp4", "archive/videos/videos/underwater-coral-reef-4333248414357645713.mp4"),
        # Video 6085687816516152312: 'Space Galaxy'
        ("archive/videos/6085687816516152312/sample_0.mp4", "archive/videos/videos/space-galaxy-6085687816516152312.mp4"),
        # Video 6385391778595382911: 'Rainbow Over Mountains'
        ("archive/videos/6385391778595382911/sample_0.mp4", "archive/videos/videos/rainbow-over-mountains-6385391778595382911.mp4"),
        # Video 8781296985594815621: 'Northern Lights'
        ("archive/videos/8781296985594815621/sample_0.mp4", "archive/videos/videos/northern-lights-8781296985594815621.mp4"),
    ]
    
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
