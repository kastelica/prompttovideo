# Terraform configuration for PromptToVideo on Google Cloud

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "main" {
  name             = "prompttovideo-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    
    backup_configuration {
      enabled = true
    }
    
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0"
      }
    }
  }

  deletion_protection = false
}

# Cloud SQL database
resource "google_sql_database" "database" {
  name     = "prompttovideo"
  instance = google_sql_database_instance.main.name
}

# Cloud SQL user
resource "google_sql_user" "users" {
  name     = "prompttovideo"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# Cloud Memorystore Redis instance
resource "google_redis_instance" "cache" {
  name           = "prompttovideo-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  redis_version  = "REDIS_6_X"
  
  authorized_network = "default"
}

# Cloud Run service for Flask app
resource "google_cloud_run_service" "flask_app" {
  name     = "prompttovideo"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/prompttovideo"
        
        env {
          name  = "FLASK_ENV"
          value = "production"
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
        }
        
        env {
          name  = "CELERY_BROKER_URL"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
        }
        
        env {
          name  = "CELERY_RESULT_BACKEND"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.users.name}:${var.db_password}@${google_sql_database_instance.main.private_ip_address}/${google_sql_database.database.name}"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Cloud Run service for Celery workers
resource "google_cloud_run_service" "celery_worker" {
  name     = "celery-worker"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/celery-worker"
        
        env {
          name  = "FLASK_ENV"
          value = "production"
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
        }
        
        env {
          name  = "CELERY_BROKER_URL"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
        }
        
        env {
          name  = "CELERY_RESULT_BACKEND"
          value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.users.name}:${var.db_password}@${google_sql_database_instance.main.private_ip_address}/${google_sql_database.database.name}"
        }
        
        env {
          name  = "CELERY_WORKER_CONCURRENCY"
          value = "4"
        }
      }
    }
  }
}

# IAM policy for Cloud Run
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "flask_app" {
  location = google_cloud_run_service.flask_app.location
  project  = google_cloud_run_service.flask_app.project
  service  = google_cloud_run_service.flask_app.name

  policy_data = data.google_iam_policy.noauth.policy_data
} 