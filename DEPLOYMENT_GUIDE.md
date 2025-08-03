# 🚀 PromptToVideo Google Cloud Deployment Guide

## Prerequisites
- Google Cloud Account with billing enabled
- Google Cloud CLI installed
- All API keys ready (Veo, Stripe, Gemini)

## Step 1: Google Cloud Setup

### 1.1 Create Project
1. Go to https://console.cloud.google.com
2. Create new project or select existing
3. Note your Project ID (e.g., `my-prompttovideo-project`)

### 1.2 Enable Billing
- Go to Billing in Google Cloud Console
- Link billing account to your project

### 1.3 Install and Configure gcloud CLI
```bash
# After installation, initialize
gcloud init

# Select your project
gcloud config set project YOUR_PROJECT_ID

# Login
gcloud auth login
```

## Step 2: Enable APIs and Setup Services

### 2.1 Enable Required APIs
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable storage.googleapis.com
```

### 2.2 Create GCS Bucket
```bash
gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-prompttovideo-videos
```

## Step 3: Environment Variables

### 3.1 Set Cloud Run Environment Variables
```bash
gcloud run services update prompttovideo \
  --region us-central1 \
  --set-env-vars \
    FLASK_ENV=production,\
    SECRET_KEY=your-super-secret-key,\
    VEO_API_KEY=your-veo-api-key,\
    STRIPE_SECRET_KEY=your-stripe-secret-key,\
    STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key,\
    GEMINI_API_KEY=your-gemini-api-key,\
    GCS_BUCKET_NAME=YOUR_PROJECT_ID-prompttovideo-videos
```

### 3.2 Required Environment Variables
- `SECRET_KEY`: Flask secret key
- `VEO_API_KEY`: Your Veo API key
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_PUBLISHABLE_KEY`: Stripe publishable key
- `GEMINI_API_KEY`: Google Gemini API key
- `GCS_BUCKET_NAME`: Your GCS bucket name

## Step 4: Deploy

### 4.1 Using Cloud Build (Recommended)
```bash
gcloud builds submit --config cloudbuild.yaml
```

### 4.2 Using Direct Deploy
```bash
gcloud run deploy prompttovideo \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --max-instances 10
```

## Step 5: Post-Deployment

### 5.1 Get Your URL
```bash
gcloud run services describe prompttovideo \
  --region us-central1 \
  --format 'value(status.url)'
```

### 5.2 Test Your Application
- Visit your Cloud Run URL
- Test video generation
- Test AI suggestions
- Test payment flow

## Step 6: Database Setup

### 6.1 Option A: Cloud SQL (Recommended for Production)
```bash
# Create Cloud SQL instance
gcloud sql instances create prompttovideo-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create prompttovideo \
  --instance=prompttovideo-db

# Create user
gcloud sql users create prompttovideo-user \
  --instance=prompttovideo-db \
  --password=your-secure-password
```

### 6.2 Option B: SQLite (Simple, not recommended for production)
- SQLite database will be created automatically
- Data persists in Cloud Run container (may be lost on updates)

## Troubleshooting

### Common Issues
1. **FFmpeg not found**: Already fixed in Dockerfile
2. **Environment variables not set**: Use gcloud run services update
3. **Permission errors**: Check IAM roles
4. **Database connection**: Verify DATABASE_URL

### Useful Commands
```bash
# View logs
gcloud logs tail --service=prompttovideo

# Update service
gcloud run services update prompttovideo --region us-central1

# Delete service
gcloud run services delete prompttovideo --region us-central1
```

## Cost Optimization
- Cloud Run scales to zero when not in use
- GCS storage is very cheap
- Monitor usage in Google Cloud Console
- Set budget alerts

## Security Notes
- All API keys are stored as environment variables
- HTTPS is enabled by default
- No authentication required (public service)
- Consider adding authentication for production 