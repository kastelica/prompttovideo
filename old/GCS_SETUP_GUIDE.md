# 🚀 Google Cloud Storage Setup Guide

## Quick Setup (Automated)

Run the setup script:
```bash
python setup_gcs.py
```

## Manual Setup Steps

### 1. **Google Cloud Console Setup**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Note your **Project ID** (you'll need this)

### 2. **Enable Required APIs**

In Google Cloud Console, enable these APIs:
- **Google Cloud Storage API**
- **Vertex AI API** (for Veo video generation)

### 3. **Create Service Account & Credentials**

1. Go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Name it something like `veo-video-service`
4. Grant these roles:
   - **Storage Admin** (for GCS access)
   - **Vertex AI User** (for Veo API)
5. Click **Create and Continue**
6. Click **Done**

### 4. **Download Credentials**

1. Click on your service account
2. Go to **Keys** tab
3. Click **Add Key** > **Create new key**
4. Choose **JSON** format
5. Download and save as `veo.json` in your project directory

### 5. **Create GCS Bucket**

1. Go to **Cloud Storage** > **Buckets**
2. Click **Create Bucket**
3. Choose a unique name (e.g., `your-project-veo-videos`)
4. Choose location (e.g., `us-central1`)
5. Choose **Standard** storage class
6. Click **Create**

### 6. **Update Environment Variables**

Add these to your `.env` file:
```env
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./veo.json
```

### 7. **Test Setup**

Run the setup script to verify everything works:
```bash
python setup_gcs.py
```

## 📁 Where Videos Are Stored

After successful video generation, your MP4 files will be stored in:

- **GCS Bucket**: `gs://your-bucket-name/videos/`
- **File Structure**: 
  - `videos/{video_id}.mp4` - Original video
  - `videos/{video_id}/watermarked.mp4` - Watermarked version (360p)
  - `thumbnails/{video_id}.jpg` - Video thumbnail

## 🔗 Accessing Videos

- **Signed URLs**: Generated automatically for web access (expires in 1 hour)
- **Public URLs**: If bucket is public (for testing)
- **Dashboard**: Videos appear in your web dashboard

## 🛠️ Troubleshooting

### Common Issues:

1. **"Credentials not found"**
   - Make sure `veo.json` is in your project directory
   - Check `GOOGLE_APPLICATION_CREDENTIALS` environment variable

2. **"Bucket not found"**
   - Verify bucket name in `.env` file
   - Check bucket exists in Google Cloud Console

3. **"Permission denied"**
   - Ensure service account has Storage Admin role
   - Check API is enabled

4. **"Project not found"**
   - Verify project ID in `.env` file
   - Check project exists in Google Cloud Console

### Testing Commands:

```bash
# Test credentials
python -c "from google.cloud import storage; print('Credentials OK')"

# Test bucket access
python -c "from google.cloud import storage; client = storage.Client(); print('GCS OK')"

# List buckets
python -c "from google.cloud import storage; client = storage.Client(); [print(b.name) for b in client.list_buckets()]"
```

## 💰 Cost Considerations

- **Storage**: ~$0.02/GB/month
- **Network**: ~$0.12/GB (outbound)
- **Operations**: ~$0.004/10k operations
- **Typical video**: 10-50MB per 8-second video

## 🔒 Security Best Practices

1. **Don't commit `veo.json` to version control**
2. **Use environment variables for sensitive data**
3. **Limit service account permissions**
4. **Enable Cloud Audit Logs**
5. **Set up bucket lifecycle policies**

## 📞 Support

If you encounter issues:
1. Check Google Cloud Console logs
2. Verify all setup steps completed
3. Test with the setup script
4. Check Flask application logs 