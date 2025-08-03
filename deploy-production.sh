#!/bin/bash

# Production Deployment Script for PromptToVideo
# Deploys to Google Cloud Run with Cloud SQL and Cloud Memorystore

set -e

PROJECT_ID="your-project-id"
REGION="us-central1"
SERVICE_NAME="prompttovideo"
WORKER_SERVICE_NAME="celery-worker"

echo "🚀 Deploying PromptToVideo to Google Cloud..."

# 1. Build and push Docker images
echo "📦 Building Docker images..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .
docker build -f Dockerfile.celery -t gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME .

echo "📤 Pushing images to Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME
docker push gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME

# 2. Deploy Flask app to Cloud Run
echo "🌐 Deploying Flask app to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "REDIS_URL=redis://10.0.0.3:6379/0" \
  --set-env-vars "CELERY_BROKER_URL=redis://10.0.0.3:6379/0" \
  --set-env-vars "CELERY_RESULT_BACKEND=redis://10.0.0.3:6379/0" \
  --set-env-vars "DATABASE_URL=postgresql://user:pass@/dbname?host=/cloudsql/$PROJECT_ID:$REGION:prompttovideo-db"

# 3. Deploy Celery workers to Cloud Run
echo "🔧 Deploying Celery workers to Cloud Run..."
gcloud run deploy $WORKER_SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$WORKER_SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "REDIS_URL=redis://10.0.0.3:6379/0" \
  --set-env-vars "CELERY_BROKER_URL=redis://10.0.0.3:6379/0" \
  --set-env-vars "CELERY_RESULT_BACKEND=redis://10.0.0.3:6379/0" \
  --set-env-vars "DATABASE_URL=postgresql://user:pass@/dbname?host=/cloudsql/$PROJECT_ID:$REGION:prompttovideo-db" \
  --set-env-vars "CELERY_WORKER_CONCURRENCY=4"

echo "✅ Deployment complete!"
echo "🌐 Flask App URL: https://$SERVICE_NAME-$REGION-$PROJECT_ID.a.run.app"
echo "🔧 Celery Workers: https://$WORKER_SERVICE_NAME-$REGION-$PROJECT_ID.a.run.app" 