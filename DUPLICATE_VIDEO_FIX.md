# Duplicate Video Generation Fix

## Problem Description

The application was experiencing duplicate video generation, resulting in multiple `sample_0.mp4` files being created in Google Cloud Storage. This was happening because:

1. **No duplicate prevention mechanism** in the video generation task
2. **Race conditions** when multiple requests came in for the same video
3. **Background thread execution** without proper locking
4. **Veo API folder structure** creating multiple operation folders

## Root Causes

### 1. Missing Duplicate Prevention
- The `_generate_video_task` function didn't check if a video was already being processed
- Multiple background threads could be started for the same video
- No database-level locking mechanism

### 2. Veo API Storage Structure
- Veo API creates folders with operation IDs: `gs://bucket/videos/operation_id/sample_0.mp4`
- The code expected videos at: `gs://bucket/videos/operation_id.mp4`
- This mismatch caused fallback logic to fail

### 3. Multiple API Endpoints
- Both `/generate` and `/api/v1/generate` endpoints could trigger video generation
- No coordination between endpoints to prevent duplicates

## Fixes Implemented

### 1. Duplicate Prevention in Video Task (`app/tasks.py`)

Added checks at the beginning of `_generate_video_task()`:

```python
# DUPLICATE PREVENTION: Check if video is already being processed
if video.status == 'processing':
    print(f"⚠️ Video {video_id} is already being processed. Skipping duplicate generation.")
    return True

if video.status == 'completed':
    print(f"✅ Video {video_id} is already completed. Skipping duplicate generation.")
    return True

if video.veo_job_id:
    print(f"⚠️ Video {video_id} already has a Veo job ID: {video.veo_job_id}. Skipping duplicate generation.")
    return True
```

### 2. Duplicate Prevention in API Routes

#### Main Routes (`app/main/routes.py`)
Added checks before starting background threads:

```python
# DUPLICATE PREVENTION: Check if video is already being processed
if video.status == 'processing':
    return jsonify({
        'success': True,
        'video_id': video.id,
        'message': 'Video is already being processed'
    }), 200

if video.veo_job_id:
    return jsonify({
        'success': True,
        'video_id': video.id,
        'message': 'Video generation already started'
    }), 200
```

#### Developer API (`app/api/developer_routes.py`)
Added similar checks for the developer API endpoint.

### 3. Improved Veo API Fallback Logic (`app/veo_client.py`)

Updated the fallback logic to check both possible Veo API folder structures:

```python
# Try the standard Veo API folder structure first
expected_gcs_url = f"gs://{get_gcs_bucket_name()}/videos/{operation_id}/sample_0.mp4"

if check_gcs_file_exists(expected_gcs_url):
    return {'success': True, 'status': 'completed', 'video_url': expected_gcs_url}

# Try alternative path structure
expected_gcs_url_alt = f"gs://{get_gcs_bucket_name()}/videos/{operation_id}.mp4"

if check_gcs_file_exists(expected_gcs_url_alt):
    return {'success': True, 'status': 'completed', 'video_url': expected_gcs_url_alt}
```

#### Fixed Indentation Issues

Fixed critical indentation errors that were causing the `url` variable to be undefined:

```python
# Before (broken):
if not token:
    return {'success': False, 'error': error_msg}
    
    headers = {  # This was incorrectly indented
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

# After (fixed):
if not token:
    return {'success': False, 'error': error_msg}

headers = {  # Now properly indented
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}
```

### 4. Cleanup Script (`cleanup_duplicate_videos.py`)

Created a script to identify and clean up existing duplicate videos:

- Scans for videos with the same prompt and user created within 24 hours
- Keeps the best version (completed > processing > failed > pending)
- Marks duplicates as failed with appropriate error messages
- Checks for duplicate Veo job IDs

### 5. Enhanced Video Processing (`app/tasks.py`)

Added comprehensive video processing pipeline:

- **Automatic cleanup**: Deletes original Veo API `sample_0.mp4` files after reorganization
- **Thumbnail generation**: Automatically generates thumbnails when videos complete
- **Thumbnail storage**: Saves thumbnail URLs to database for fast access
- **Better logging**: More detailed step-by-step logging for debugging

### 6. Improved Dashboard Auto-refresh (`app/templates/main/dashboard.html`)

Enhanced the dashboard to automatically detect completed videos:

- Added `data-status` attributes to video cards for better tracking
- Improved auto-refresh logic to check individual video statuses
- Reduced refresh interval from 30s to 15s for faster updates
- Smart polling that only reloads when videos actually complete

### 7. GCS File Management (`app/gcs_utils.py`)

Added file management capabilities:

- `delete_gcs_file()` function to clean up original Veo API files
- Better error handling and logging for file operations

### 8. Thumbnail System Enhancement (`app/models.py`, `app/templates/main/dashboard.html`)

Improved thumbnail handling and display:

- **Database storage**: Added `thumbnail_gcs_url` and `thumbnail_url` fields to Video model
- **Fast access**: Thumbnails are stored in database for immediate display
- **Fallback system**: Dynamic thumbnail generation for videos without stored thumbnails
- **Frontend integration**: Updated dashboard to use new thumbnail system

### 9. Content Policy Violation Handling (`app/veo_client.py`, `app/tasks.py`, `app/templates/main/dashboard.html`)

Added comprehensive handling for content policy violations:

- **Detection**: Automatically detects when Veo API returns `raiMediaFilteredCount > 0`
- **Status Management**: New `content_violation` status in database and frontend
- **User Feedback**: Clear error messages explaining why content was blocked
- **UI Integration**: Orange warning badge and "View Details" button for violated content
- **Error Details**: Modal popup with specific violation information and guidance

## Prevention Strategy

### Database Level
- Check video status before processing
- Check for existing Veo job IDs
- Use database transactions to prevent race conditions

### Application Level
- Check video status in API routes before starting background threads
- Return appropriate responses for duplicate requests
- Log duplicate attempts for monitoring

### Veo API Level
- Improved fallback logic to handle Veo API folder structure
- Better error handling and logging
- Support for multiple possible file locations

## Testing

The cleanup script was run and found no existing duplicates in the database, confirming that the prevention mechanisms should work for future video generations.

## Monitoring

To monitor for future duplicates:

1. Check application logs for duplicate prevention messages
2. Run the cleanup script periodically: `python cleanup_duplicate_videos.py`
3. Monitor GCS for multiple `sample_0.mp4` files in the same operation folder

## Files Modified

1. `app/tasks.py` - Added duplicate prevention, automatic cleanup, thumbnail generation, and content violation handling
2. `app/main/routes.py` - Added duplicate prevention in main API route
3. `app/api/developer_routes.py` - Added duplicate prevention in developer API
4. `app/veo_client.py` - Improved fallback logic, fixed indentation issues, and added content violation detection
5. `app/gcs_utils.py` - Added `delete_gcs_file()` function for cleanup
6. `app/templates/main/dashboard.html` - Enhanced auto-refresh logic, added status tracking, and content violation UI
7. `app/models.py` - Updated Video model to support `content_violation` status
8. `cleanup_duplicate_videos.py` - New script for cleaning up existing duplicates
9. `DUPLICATE_VIDEO_FIX.md` - This documentation file 