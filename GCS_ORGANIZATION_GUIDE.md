# GCS Bucket Organization Guide

## Overview

This guide explains the new organized file structure for the `prompt-veo-videos` GCS bucket and how to migrate from the current messy structure.

## Current Issues

### Problems with Current Structure:
1. **Inconsistent bucket names**: Some files use `prompttovideo-videos`, others use `prompt-veo-videos`
2. **Simple naming**: Just `videos/{id}.mp4` and `thumbnails/{id}.jpg`
3. **No organization**: All files in flat structure
4. **No quality differentiation**: Can't distinguish between free/premium videos
5. **No chronological organization**: Hard to find files by date
6. **Missing thumbnails**: Many videos lack proper thumbnails

## New Organized Structure

### File Naming Convention

#### Videos:
```
videos/{year}/{month}/{quality}/{video_id}_{prompt_hash}_{timestamp}.mp4
```

#### Thumbnails:
```
thumbnails/{year}/{month}/{quality}/{video_id}_{prompt_hash}_{timestamp}.jpg
```

### Examples:

#### Video Files:
- `videos/2024/12/free/123_a1b2c3d4_20241215_143022.mp4`
- `videos/2024/12/premium/124_e5f6g7h8_20241215_143045.mp4`
- `videos/2024/12/1080p/125_i9j0k1l2_20241215_143108.mp4`

#### Thumbnail Files:
- `thumbnails/2024/12/free/123_a1b2c3d4_20241215_143022.jpg`
- `thumbnails/2024/12/premium/124_e5f6g7h8_20241215_143045.jpg`
- `thumbnails/2024/12/1080p/125_i9j0k1l2_20241215_143108.jpg`

### Structure Benefits:

1. **Chronological Organization**: Easy to find files by year/month
2. **Quality Separation**: Different quality levels in separate folders
3. **Uniqueness**: Prompt hash and timestamp prevent conflicts
4. **Scalability**: Structure supports large volumes of files
5. **Cost Management**: Easy to implement lifecycle policies by quality
6. **Backup/Recovery**: Organized structure simplifies backup strategies

## Implementation

### New Functions Added:

#### `app/gcs_utils.py`:
- `generate_video_filename()`: Creates organized video filenames
- `generate_thumbnail_filename()`: Creates organized thumbnail filenames
- `parse_gcs_filename()`: Parses GCS URLs to extract components
- `get_storage_stats()`: Provides storage statistics
- `list_gcs_files()`: Lists files with metadata

#### `app/tasks.py`:
- `generate_video_thumbnail_from_gcs()`: Generates thumbnails from GCS videos
- `download_video_from_gcs()`: Downloads videos for processing

### Updated Functions:
- Video generation now uses organized naming
- Thumbnail generation uses organized naming
- All new uploads follow the organized structure

## Migration Strategy

### Phase 1: New Uploads (✅ Complete)
- All new video uploads use organized naming
- All new thumbnail generation uses organized naming
- Backward compatibility maintained for existing files

### Phase 2: Generate Missing Thumbnails (🔄 Ready)
- Generate thumbnails for existing videos without them
- Use organized naming for new thumbnails
- Update database records

### Phase 3: Migrate Existing Files (🔄 Ready)
- Move existing files to organized structure
- Update database records
- Clean up orphaned files

## Usage

### Analysis Scripts:

#### 1. Analyze Current Structure:
```bash
python analyze_gcs_structure.py
```
This script provides:
- Storage statistics
- File pattern analysis
- Database vs GCS comparison
- Recommendations

#### 2. Migration Script:
```bash
python migrate_gcs_structure.py
```
This script provides:
- Preview of what will be migrated
- Video file migration
- Thumbnail generation
- Orphaned file cleanup

### Manual Usage:

#### Generate Organized Filename:
```python
from app.gcs_utils import generate_video_filename

gcs_path, filename, gcs_url = generate_video_filename(
    video_id=123,
    quality='premium',
    prompt='A beautiful sunset over mountains',
    user_id=456
)
# Returns: ('videos/2024/12/premium/123_a1b2c3d4_20241215_143022.mp4', 
#           '123_a1b2c3d4_20241215_143022.mp4',
#           'gs://prompt-veo-videos/videos/2024/12/premium/123_a1b2c3d4_20241215_143022.mp4')
```

#### Parse GCS URL:
```python
from app.gcs_utils import parse_gcs_filename

parsed = parse_gcs_filename('gs://prompt-veo-videos/videos/2024/12/premium/123_a1b2c3d4_20241215_143022.mp4')
# Returns: {
#     'bucket_name': 'prompt-veo-videos',
#     'file_type': 'videos',
#     'year': '2024',
#     'month': '12',
#     'quality': 'premium',
#     'is_organized': True,
#     'filename': '123_a1b2c3d4_20241215_143022.mp4',
#     'extension': 'mp4'
# }
```

#### Get Storage Statistics:
```python
from app.gcs_utils import get_storage_stats

stats = get_storage_stats()
# Returns comprehensive storage statistics including:
# - Total files and size
# - Files by quality, year, month
# - Organized vs legacy file counts
```

## Configuration

### Environment Variables:
```bash
# Set the correct bucket name
export GCS_BUCKET_NAME=prompt-veo-videos
```

### Config File:
The `config.py` has been updated to use `prompt-veo-videos` as the default bucket name.

## Monitoring and Maintenance

### Regular Tasks:
1. **Storage Monitoring**: Use `get_storage_stats()` to monitor usage
2. **Orphaned File Cleanup**: Regular cleanup of files without database records
3. **Thumbnail Generation**: Ensure all videos have thumbnails
4. **Lifecycle Policies**: Implement GCS lifecycle policies for cost optimization

### Lifecycle Policy Example:
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 365,
          "matchesPrefix": ["videos/*/free/"]
        }
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 730,
          "matchesPrefix": ["videos/*/premium/"]
        }
      }
    ]
  }
}
```

## Troubleshooting

### Common Issues:

#### 1. Bucket Name Mismatch:
- **Problem**: Files in different buckets
- **Solution**: Update environment variables and config
- **Check**: Use `get_gcs_bucket_name()` function

#### 2. Missing Thumbnails:
- **Problem**: Videos without thumbnails
- **Solution**: Run thumbnail generation script
- **Check**: Use database query for videos without thumbnails

#### 3. Orphaned Files:
- **Problem**: Files without database records
- **Solution**: Run cleanup script
- **Check**: Compare GCS files with database records

#### 4. Permission Issues:
- **Problem**: Cannot access GCS bucket
- **Solution**: Check service account credentials
- **Check**: Verify `GOOGLE_APPLICATION_CREDENTIALS` path

### Debug Commands:
```python
# Check bucket access
from app.gcs_utils import list_gcs_files
files = list_gcs_files(prefix='videos/', max_results=10)

# Check file info
from app.gcs_utils import get_file_info_from_gcs
info = get_file_info_from_gcs('gs://prompt-veo-videos/videos/123.mp4')

# Parse filename
from app.gcs_utils import parse_gcs_filename
parsed = parse_gcs_filename('gs://prompt-veo-videos/videos/123.mp4')
```

## Future Enhancements

### Planned Improvements:
1. **File Metadata**: Add custom metadata to GCS objects
2. **Compression**: Implement video compression for cost savings
3. **CDN Integration**: Use Cloud CDN for better performance
4. **Analytics**: Track file access patterns
5. **Automated Cleanup**: Scheduled cleanup of old files

### Metadata Example:
```python
metadata = {
    'user_id': str(video.user_id),
    'prompt': video.prompt[:100],  # Truncated for GCS limits
    'quality': video.quality,
    'created_at': video.created_at.isoformat(),
    'duration': str(video.duration) if video.duration else '',
    'status': video.status
}
```

## Support

For issues or questions about the GCS organization system:
1. Check this guide first
2. Run the analysis scripts to understand current state
3. Use the migration scripts for automated fixes
4. Review the code in `app/gcs_utils.py` for implementation details 