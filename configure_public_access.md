# Configure Public Access for GCS Bucket

Since the bucket has uniform bucket-level access enabled, we need to configure IAM policies to allow public read access. Here are the steps:

## Option 1: Make Entire Bucket Public (Recommended)

1. **Go to Google Cloud Console**
   - Navigate to: https://console.cloud.google.com/storage/browser/prompt-veo-videos

2. **Configure Bucket Permissions**
   - Click on the bucket name: `prompt-veo-videos`
   - Go to the "Permissions" tab
   - Click "Add" to add a new principal

3. **Add Public Access**
   - **New principals**: `allUsers`
   - **Role**: `Storage Object Viewer`
   - Click "Save"

4. **Confirm the Change**
   - You'll see a warning about making the bucket public
   - Click "Allow public" to confirm

## Option 2: Make Only Thumbnail Folder Public

If you prefer to keep the bucket private and only make thumbnails public:

1. **Create a Public Folder**
   - Create a new folder: `public-thumbnails/`
   - Copy thumbnail files to this folder

2. **Set Folder Permissions**
   - Right-click on the `public-thumbnails/` folder
   - Select "Edit permissions"
   - Add `allUsers` with `Storage Object Viewer` role

## Option 3: Use Cloud CDN (Advanced)

1. **Set up Cloud CDN**
   - Create a load balancer
   - Configure Cloud CDN with the GCS bucket as backend
   - This provides public access with caching

## After Configuration

Once public access is configured, update the thumbnail URLs in the database to use direct URLs:

```sql
UPDATE videos 
SET thumbnail_url = CONCAT('https://storage.googleapis.com/prompt-veo-videos/', 
                          REPLACE(thumbnail_url, 'https://storage.googleapis.com/prompt-veo-videos/', ''))
WHERE status = 'completed' AND thumbnail_url IS NOT NULL;
```

## Security Considerations

- **Option 1** makes ALL files in the bucket publicly readable
- **Option 2** only makes thumbnails public (more secure)
- **Option 3** provides caching and better performance

## Quick Test

After configuration, test a thumbnail URL:
```
https://storage.googleapis.com/prompt-veo-videos/archive/20250803_050844/thumbnails/1.jpg
```

This should display the thumbnail image directly in your browser.

## Next Steps

1. Choose an option above and configure it
2. Run the database update script to use direct URLs
3. Test the thumbnails on your website
4. Consider setting up a Cloud CDN for better performance 