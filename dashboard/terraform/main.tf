# Garak Dashboard Infrastructure Configuration
# This Terraform configuration sets up all required GCP resources for the Garak Dashboard API

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "storage.googleapis.com",
    "cloudbuild.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "errorreporting.googleapis.com"
  ])

  service = each.value
  project = var.project_id

  disable_dependent_services = false
  disable_on_destroy        = false
}

# VPC Network
resource "google_compute_network" "garak_vpc" {
  name                    = "garak-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id

  depends_on = [google_project_service.apis]
}

# Subnet for the region
resource "google_compute_subnetwork" "garak_subnet" {
  name          = "garak-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.garak_vpc.id
  project       = var.project_id

  # Enable private Google access
  private_ip_google_access = true
}

# VPC Connector for Cloud Run to access private resources
resource "google_vpc_access_connector" "garak_connector" {
  provider = google-beta
  name     = "garak-vpc-connector"
  region   = var.region
  project  = var.project_id

  subnet {
    name = google_compute_subnetwork.garak_subnet.name
  }

  # Minimum instances for faster cold starts
  min_instances = 2
  max_instances = 10

  depends_on = [google_project_service.apis]
}

# Service Account for Cloud Run
resource "google_service_account" "garak_dashboard_sa" {
  account_id   = "garak-dashboard-sa"
  display_name = "Garak Dashboard Service Account"
  description  = "Service account for Garak Dashboard Cloud Run service"
  project      = var.project_id
}

# IAM bindings for the service account
resource "google_project_iam_member" "garak_dashboard_permissions" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/redis.editor",
    "roles/secretmanager.secretAccessor",
    "roles/monitoring.writer",
    "roles/logging.writer",
    "roles/cloudtrace.agent",
    "roles/errorreporting.writer"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.garak_dashboard_sa.email}"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "garak_db" {
  name             = "garak-dashboard-db"
  database_version = "POSTGRES_15"
  region           = var.region
  project          = var.project_id

  deletion_protection = var.environment == "production" ? true : false

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.garak_vpc.id
      require_ssl     = true
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    maintenance_window {
      day  = 7
      hour = 3
    }
  }

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.apis
  ]
}

# Database
resource "google_sql_database" "garak_database" {
  name     = "garak_dashboard"
  instance = google_sql_database_instance.garak_db.name
  project  = var.project_id
}

# Database User
resource "google_sql_user" "garak_db_user" {
  name     = "garak_user"
  instance = google_sql_database_instance.garak_db.name
  password = var.db_password
  project  = var.project_id
}

# Private service connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.garak_vpc.id
  project       = var.project_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.garak_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Redis Instance
resource "google_redis_instance" "garak_redis" {
  name           = "garak-redis"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size
  region         = var.region
  project        = var.project_id

  authorized_network = google_compute_network.garak_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version = "REDIS_7_0"

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Cloud Storage Bucket for Reports
resource "google_storage_bucket" "garak_reports" {
  name     = "${var.project_id}-garak-reports"
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age                = 30
      matches_storage_class = ["STANDARD"]
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# Cloud Storage Bucket for Job Data
resource "google_storage_bucket" "garak_job_data" {
  name     = "${var.project_id}-garak-job-data"
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Secret for database password
resource "google_secret_manager_secret" "db_password" {
  secret_id = "garak-db-password"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

# Secret for application secret key
resource "google_secret_manager_secret" "app_secret_key" {
  secret_id = "garak-app-secret-key"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "app_secret_key" {
  secret      = google_secret_manager_secret.app_secret_key.id
  secret_data = var.app_secret_key
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "garak_dashboard" {
  name     = "garak-dashboard-api"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.garak_dashboard_sa.email
    
    vpc_access {
      connector = google_vpc_access_connector.garak_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = "gcr.io/${var.project_id}/garak-dashboard:latest"
      
      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
        cpu_idle = true
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql://${google_sql_user.garak_db_user.name}:${var.db_password}@/${google_sql_database.garak_database.name}?host=/cloudsql/${google_sql_database_instance.garak_db.connection_name}"
      }

      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.garak_redis.host}:${google_redis_instance.garak_redis.port}"
      }

      env {
        name  = "GCS_REPORTS_BUCKET"
        value = google_storage_bucket.garak_reports.name
      }

      env {
        name  = "GCS_JOB_DATA_BUCKET"
        value = google_storage_bucket.garak_job_data.name
      }

      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app_secret_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/api/v1/health"
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/api/v1/health"
        }
        initial_delay_seconds = 30
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.apis,
    google_vpc_access_connector.garak_connector
  ]
}

# Cloud Run IAM for public access
resource "google_cloud_run_service_iam_binding" "garak_dashboard_public" {
  location = google_cloud_run_v2_service.garak_dashboard.location
  project  = google_cloud_run_v2_service.garak_dashboard.project
  service  = google_cloud_run_v2_service.garak_dashboard.name
  role     = "roles/run.invoker"

  members = [
    "allUsers",
  ]
}

# Load Balancer for custom domain (optional)
resource "google_compute_global_address" "garak_lb_ip" {
  count   = var.enable_custom_domain ? 1 : 0
  name    = "garak-lb-ip"
  project = var.project_id
}

# Monitoring Alert Policy for high error rate
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "Garak Dashboard High Error Rate"
  project      = var.project_id
  
  conditions {
    display_name = "Error rate > 5%"
    
    condition_threshold {
      filter         = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"garak-dashboard-api\""
      comparison     = "COMPARISON_GT"
      threshold_value = 0.05
      duration       = "300s"
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  combiner = "OR"

  notification_channels = []
  
  alert_strategy {
    auto_close = "1800s"
  }

  depends_on = [google_project_service.apis]
}