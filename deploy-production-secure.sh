#!/bin/bash

# Secure deployment script using Secret Manager for Stripe keys
PROJECT_ID="dirly-466300"
REGION="us-central1"
SERVICE_NAME="prompttovideo"

echo "🚀 Deploying PromptToVideo to Cloud Run with secure Stripe configuration..."

# Deploy to Cloud Run with secrets from Secret Manager
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-secrets="STRIPE_PUBLISHABLE_KEY=stripe-publishable-key:latest" \
  --set-secrets="STRIPE_SECRET_KEY=stripe-secret-key:latest" \
  --set-secrets="STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --set-env-vars="GCS_BUCKET_NAME=prompt-veo-videos" \
  --set-env-vars="DATABASE_URL=your_database_url" \
  --set-env-vars="REDIS_URL=your_redis_url" \
  --project=$PROJECT_ID

echo "✅ Deployment complete!"
echo "🌐 Service URL: https://$SERVICE_NAME-$REGION-$PROJECT_ID.a.run.app" 