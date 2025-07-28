# Outputs for Garak Dashboard Infrastructure

output "cloud_run_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.garak_dashboard.uri
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.garak_db.connection_name
}

output "database_private_ip" {
  description = "Private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.garak_db.private_ip_address
}

output "redis_host" {
  description = "Redis instance host"
  value       = google_redis_instance.garak_redis.host
}

output "redis_port" {
  description = "Redis instance port"
  value       = google_redis_instance.garak_redis.port
}

output "reports_bucket_name" {
  description = "Name of the Cloud Storage bucket for reports"
  value       = google_storage_bucket.garak_reports.name
}

output "job_data_bucket_name" {
  description = "Name of the Cloud Storage bucket for job data"
  value       = google_storage_bucket.garak_job_data.name
}

output "service_account_email" {
  description = "Email of the service account for Cloud Run"
  value       = google_service_account.garak_dashboard_sa.email
}

output "vpc_connector_name" {
  description = "Name of the VPC connector"
  value       = google_vpc_access_connector.garak_connector.name
}

output "load_balancer_ip" {
  description = "External IP address of the load balancer (if enabled)"
  value       = var.enable_custom_domain ? google_compute_global_address.garak_lb_ip[0].address : null
}

output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "environment" {
  description = "The environment name"
  value       = var.environment
}