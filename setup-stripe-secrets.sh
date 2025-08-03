#!/bin/bash

# Setup Stripe secrets in Google Cloud Secret Manager
PROJECT_ID="dirly-466300"

echo "🔐 Setting up Stripe secrets in Secret Manager..."

# Create secrets
echo "📝 Creating Stripe publishable key secret..."
echo "pk_test_your_publishable_key" | gcloud secrets create stripe-publishable-key \
  --data-file=- \
  --replication-policy="automatic" \
  --project=$PROJECT_ID

echo "📝 Creating Stripe secret key secret..."
echo "sk_test_your_secret_key" | gcloud secrets create stripe-secret-key \
  --data-file=- \
  --replication-policy="automatic" \
  --project=$PROJECT_ID

echo "📝 Creating Stripe webhook secret..."
echo "whsec_your_webhook_secret" | gcloud secrets create stripe-webhook-secret \
  --data-file=- \
  --replication-policy="automatic" \
  --project=$PROJECT_ID

echo "✅ Stripe secrets created successfully!"
echo ""
echo "🔧 To use these secrets in Cloud Run, update your deployment with:"
echo "--set-secrets=STRIPE_PUBLISHABLE_KEY=stripe-publishable-key:latest"
echo "--set-secrets=STRIPE_SECRET_KEY=stripe-secret-key:latest"
echo "--set-secrets=STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest" 