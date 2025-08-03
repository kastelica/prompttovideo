# Production Deployment Guide for PromptToVideo

This guide explains how to deploy PromptToVideo to Google Cloud Run with Cloud SQL and Cloud Memorystore.

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud Run     │    │   Cloud Run     │    │  Cloud SQL      │
│  (Flask App)    │    │ (Celery Workers)│    │ (PostgreSQL)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Cloud Memorystore│
                    │    (Redis)      │
                    └─────────────────┘
```

## 📋 **Prerequisites**

1. **Google Cloud Project** with billing enabled
2. **Google Cloud CLI** installed and configured
3. **Docker** installed locally
4. **Terraform** (optional, for infrastructure as code)

## 🚀 **Quick Deployment (Manual)**

### **Step 1: Enable Required APIs**
```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  containerregistry.googleapis.com
```

### **Step 2: Create Cloud SQL Database**
```bash
# Create PostgreSQL instance
gcloud sql instances create prompttovideo-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-type=SSD \
  --storage-size=10GB

# Create database
gcloud sql databases create prompttovideo \
  --instance=prompttovideo-db

# Create user
gcloud sql users create prompttovideo \
  --instance=prompttovideo-db \
  --password=your-secure-password
```

### **Step 3: Create Cloud Memorystore Redis**
```bash
# Create Redis instance
gcloud redis instances create prompttovideo-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_6_x

# Get Redis IP
REDIS_IP=$(gcloud redis instances describe prompttovideo-redis \
  --region=us-central1 \
  --format="value(host)")
```

### **Step 4: Build and Deploy**

#### **Build Docker Images**
```bash
PROJECT_ID=$(gcloud config get-value project)

# Build Flask app
docker build -t gcr.io/$PROJECT_ID/prompttovideo .

# Build Celery worker
docker build -f Dockerfile.celery -t gcr.io/$PROJECT_ID/celery-worker .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/prompttovideo
docker push gcr.io/$PROJECT_ID/celery-worker
```

#### **Deploy Flask App**
```bash
gcloud run deploy prompttovideo \
  --image gcr.io/$PROJECT_ID/prompttovideo \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "REDIS_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_BROKER_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_RESULT_BACKEND=redis://$REDIS_IP:6379/0" \
  --set-env-vars "DATABASE_URL=postgresql://prompttovideo:your-password@/prompttovideo?host=/cloudsql/$PROJECT_ID:us-central1:prompttovideo-db"
```

#### **Deploy Celery Workers**
```bash
gcloud run deploy celery-worker \
  --image gcr.io/$PROJECT_ID/celery-worker \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "REDIS_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_BROKER_URL=redis://$REDIS_IP:6379/0" \
  --set-env-vars "CELERY_RESULT_BACKEND=redis://$REDIS_IP:6379/0" \
  --set-env-vars "DATABASE_URL=postgresql://prompttovideo:your-password@/prompttovideo?host=/cloudsql/$PROJECT_ID:us-central1:prompttovideo-db" \
  --set-env-vars "CELERY_WORKER_CONCURRENCY=4"
```

## 🏗️ **Infrastructure as Code (Terraform)**

### **Step 1: Initialize Terraform**
```bash
cd terraform
terraform init
```

### **Step 2: Create terraform.tfvars**
```hcl
project_id  = "your-project-id"
region      = "us-central1"
db_password = "your-secure-password"
```

### **Step 3: Deploy Infrastructure**
```bash
terraform plan
terraform apply
```

## 🔧 **Environment Variables**

### **Required for Production**
```bash
FLASK_ENV=production
REDIS_URL=redis://10.0.0.3:6379/0
CELERY_BROKER_URL=redis://10.0.0.3:6379/0
CELERY_RESULT_BACKEND=redis://10.0.0.3:6379/0
DATABASE_URL=postgresql://user:pass@/dbname?host=/cloudsql/PROJECT_ID:REGION:INSTANCE
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_CLOUD_PROJECT_ID=your-project-id
```

### **Optional for Production**
```bash
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
```

## 📊 **Monitoring and Scaling**

### **Cloud Run Scaling**
- **Flask App**: Scales to 0 when not in use (cost-effective)
- **Celery Workers**: Set minimum scale to 1 for continuous processing
- **Auto-scaling**: Based on CPU and memory usage

### **Monitoring**
```bash
# View logs
gcloud logs read "resource.type=cloud_run_revision"

# Monitor Celery workers
gcloud run services describe celery-worker --region=us-central1
```

### **Scaling Commands**
```bash
# Scale Celery workers
gcloud run services update celery-worker \
  --region=us-central1 \
  --min-instances=2 \
  --max-instances=10
```

## 🔒 **Security Considerations**

### **Network Security**
- Cloud SQL: Private IP only
- Cloud Memorystore: VPC network
- Cloud Run: HTTPS only

### **IAM Permissions**
```bash
# Grant Cloud Run access to Cloud SQL
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

## 💰 **Cost Optimization**

### **Estimated Monthly Costs**
- **Cloud Run**: $5-20/month (depending on usage)
- **Cloud SQL**: $25/month (db-f1-micro)
- **Cloud Memorystore**: $35/month (1GB)
- **Total**: ~$65-80/month

### **Cost Optimization Tips**
1. Use `db-f1-micro` for development
2. Scale Celery workers to 0 during off-hours
3. Use Cloud Run's auto-scaling to 0
4. Monitor usage with Cloud Monitoring

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Celery Workers Not Processing Tasks**
```bash
# Check worker status
gcloud run services describe celery-worker --region=us-central1

# View worker logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=celery-worker"
```

#### **Redis Connection Issues**
```bash
# Test Redis connectivity
gcloud redis instances describe prompttovideo-redis --region=us-central1

# Check Redis logs
gcloud logging read "resource.type=gce_instance AND resource.labels.instance_name:redis"
```

#### **Database Connection Issues**
```bash
# Test database connectivity
gcloud sql connect prompttovideo-db --user=prompttovideo

# Check database logs
gcloud logging read "resource.type=gce_instance AND resource.labels.instance_name:prompttovideo-db"
```

## 🔄 **CI/CD Pipeline**

### **GitHub Actions Example**
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Google Cloud CLI
        uses: google-github-actions/setup-gcloud@v0
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
      
      - name: Build and Deploy
        run: |
          chmod +x deploy-production.sh
          ./deploy-production.sh
```

## 📈 **Performance Optimization**

### **Celery Configuration**
```python
# app/tasks.py
CELERY_WORKER_CONCURRENCY = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes
```

### **Database Optimization**
```sql
-- Add indexes for better performance
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at);
```

This setup provides a scalable, cost-effective, and production-ready deployment for PromptToVideo on Google Cloud. 