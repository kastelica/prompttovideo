#!/bin/bash

# PromptToVideo.com Deployment Script
# Supports both Google Cloud Run and Railway deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PromptToVideo.com Deployment Script${NC}"

# Check if required environment variables are set
if [ -z "$DEPLOY_TARGET" ]; then
    echo -e "${YELLOW}DEPLOY_TARGET not set. Please set to 'cloudrun' or 'railway'${NC}"
    exit 1
fi

# Function to deploy to Cloud Run
deploy_cloudrun() {
    echo -e "${BLUE}Deploying to Google Cloud Run...${NC}"
    
    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        echo -e "${RED}GOOGLE_CLOUD_PROJECT environment variable is required for Cloud Run deployment${NC}"
        exit 1
    fi
    
    # Build and deploy using Cloud Build
    gcloud builds submit --config cloudbuild.yaml .
    
    echo -e "${GREEN}✅ Successfully deployed to Cloud Run!${NC}"
    echo -e "${BLUE}Your app should be available at: https://prompttovideo-${GOOGLE_CLOUD_PROJECT}.run.app${NC}"
}

# Function to deploy to Railway
deploy_railway() {
    echo -e "${BLUE}Deploying to Railway...${NC}"
    
    # Check if Railway CLI is installed
    if ! command -v railway &> /dev/null; then
        echo -e "${YELLOW}Railway CLI not found. Installing...${NC}"
        npm install -g @railway/cli
    fi
    
    # Deploy to Railway
    railway up
    
    echo -e "${GREEN}✅ Successfully deployed to Railway!${NC}"
    echo -e "${BLUE}Your app should be available at the Railway-provided URL${NC}"
}

# Main deployment logic
case $DEPLOY_TARGET in
    "cloudrun")
        deploy_cloudrun
        ;;
    "railway")
        deploy_railway
        ;;
    *)
        echo -e "${RED}Invalid DEPLOY_TARGET. Use 'cloudrun' or 'railway'${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}" 