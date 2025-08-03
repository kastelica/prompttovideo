#!/bin/bash

# Production Deployment Script for PromptToVideo
# Project: dirly-466300

set -e

PROJECT_ID="dirly-466300"
REGION="us-central1"
SERVICE_NAME="prompttovideo"
WORKER_SERVICE_NAME="celery-worker"

echo "🚀 Deploying PromptToVideo to Google Cloud..."
echo "📋 Project ID: $PROJECT_ID"
echo "🌍 Region: $REGION"

# 1. Enable required APIs (if not already enabled)
echo "🔧 Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  containerregistry.googleapis.com \
  --project=$PROJECT_ID

# 2. Create Cloud Memorystore Redis (if not exists)
echo "🔴 Setting up Cloud Memorystore Redis..."
if ! gcloud redis instances describe prompttovideo-redis --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "Creating Redis instance..."
    gcloud redis instances create prompttovideo-redis \
      --size=1 \
      --region=$REGION \
      --redis-version=redis_6_x \
      --project=$PROJECT_ID
else
    echo "Redis instance already exists"
fi

# Get Redis IP
REDIS_IP=$(gcloud redis instances describe prompttovideo-redis \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(host)")

echo "✅ Redis IP: $REDIS_IP"

# 3. Build and push Docker images
echo "📦 Building Docker images..."

# Build Flask app
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

# Build Celery worker
docker build -f Dockerfile.celery -t gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME:latest .

echo "📤 Pushing images to Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest
docker push gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME:latest

# 4. Deploy Flask app to Cloud Run
echo "🌐 Deploying Flask app to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --max-instances 5 \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "REDIS_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_BROKER_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_RESULT_BACKEND=redis://$REDIS_IP:6379/0" \
  --set-env-vars "DATABASE_URL=postgresql://prompttovideo:PromptToVideo2024!@/prompttovideo?host=/cloudsql/$PROJECT_ID:$REGION:prompttovideo-db" \
  --set-env-vars "GCS_BUCKET_NAME=prompt-veo-videos" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID" \
  --set-env-vars "GEMINI_API_KEY=your_gemini_api_key" \
  --set-env-vars "DAILY_FREE_CREDITS=3" \
  --set-env-vars "CREDIT_COST_FREE=1" \
  --set-env-vars "CREDIT_COST_PREMIUM=3" \
  --set-env-vars "STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key" \
  --set-env-vars "STRIPE_SECRET_KEY=your_stripe_secret_key" \
  --add-cloudsql-instances "$PROJECT_ID:$REGION:prompttovideo-db" \
  --service-account "1032601070049-compute@developer.gserviceaccount.com"

# 5. Deploy Celery workers to Cloud Run
echo "🔧 Deploying Celery workers to Cloud Run..."
gcloud run deploy $WORKER_SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME:latest \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --no-allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 1 \
  --max-instances 10 \
  --min-instances 1 \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "REDIS_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_BROKER_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_RESULT_BACKEND=redis://$REDIS_IP:6379/0" \
  --set-env-vars "DATABASE_URL=postgresql://prompttovideo:PromptToVideo2024!@/prompttovideo?host=/cloudsql/$PROJECT_ID:$REGION:prompttovideo-db" \
  --set-env-vars "GCS_BUCKET_NAME=prompt-veo-videos" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID" \
  --set-env-vars "GEMINI_API_KEY=your_gemini_api_key" \
  --set-env-vars "DAILY_FREE_CREDITS=3" \
  --set-env-vars "CREDIT_COST_FREE=1" \
  --set-env-vars "CREDIT_COST_PREMIUM=3" \
  --set-env-vars "STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key" \
  --set-env-vars "STRIPE_SECRET_KEY=your_stripe_secret_key" \
  --set-env-vars "CELERY_WORKER_CONCURRENCY=4" \
  --add-cloudsql-instances "$PROJECT_ID:$REGION:prompttovideo-db" \
  --service-account "1032601070049-compute@developer.gserviceaccount.com"

echo "✅ Deployment complete!"
echo ""
echo "🌐 Flask App URL: https://$SERVICE_NAME-$REGION-$PROJECT_ID.a.run.app"
echo "🔧 Celery Workers: https://$WORKER_SERVICE_NAME-$REGION-$PROJECT_ID.a.run.app"
echo ""
echo "📊 Monitor your deployment:"
echo "   - Cloud Run Console: https://console.cloud.google.com/run?project=$PROJECT_ID"
echo "   - Cloud Build Console: https://console.cloud.google.com/cloud-build?project=$PROJECT_ID"
echo "   - Cloud SQL Console: https://console.cloud.google.com/sql?project=$PROJECT_ID"
echo "   - Cloud Memorystore Console: https://console.cloud.google.com/memorystore/redis?project=$PROJECT_ID" 