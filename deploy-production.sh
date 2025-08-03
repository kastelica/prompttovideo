#!/bin/bash

# Deploy to Cloud Run with Stripe configuration
gcloud run deploy prompttovideo \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key,STRIPE_SECRET_KEY=sk_test_your_secret_key,STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=dirly-466300" \
  --set-env-vars="GCS_BUCKET_NAME=prompt-veo-videos" \
  --set-env-vars="DATABASE_URL=your_database_url" \
  --set-env-vars="REDIS_URL=your_redis_url" 