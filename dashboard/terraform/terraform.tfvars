# Terraform variables for Garak Dashboard deployment
# Generated for garak-shield project

# Required variables
project_id    = "garak-shield"
db_password   = "D9aD7AJD-0BqwEWfP9q25rfTejcOZNUQ"
app_secret_key = "45P5WYsbBMXqbDM6prLMemVYFEsEi94WyXlUF2d5XC4"

# Optional variables with sensible defaults
region        = "us-central1"
zone          = "us-central1-a"
environment   = "production"

# Database configuration
db_tier       = "db-f1-micro"  # Start with small tier
db_disk_size  = 20             # GB

# Redis configuration
redis_tier        = "STANDARD_HA"  # High availability
redis_memory_size = 1               # GB

# Cloud Run configuration
cloud_run_cpu    = "2"     # CPU cores
cloud_run_memory = "2Gi"   # Memory
min_instances    = 1       # Minimum instances
max_instances    = 100     # Maximum instances

# Domain configuration (disabled for now)
enable_custom_domain = false
domain_name         = ""

# Monitoring configuration
enable_monitoring   = true
notification_email  = "divya@getgarak.com"