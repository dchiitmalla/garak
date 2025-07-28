# Garak Dashboard Terraform Infrastructure

This directory contains Terraform configurations for deploying the Garak Dashboard API to Google Cloud Platform.

## Prerequisites

1. **Google Cloud Platform Account** with billing enabled
2. **Terraform** installed (>= 1.0)
3. **Google Cloud SDK** installed and configured
4. **Project Owner** or equivalent permissions in GCP

## Quick Start

### 1. Set up GCP Authentication

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 2. Prepare Terraform Variables

```bash
# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
```

### 3. Initialize and Deploy

```bash
# Initialize Terraform
terraform init

# Review the execution plan
terraform plan

# Apply the configuration
terraform apply
```

## Configuration

### Required Variables

- `project_id`: Your GCP project ID
- `db_password`: Secure password for the PostgreSQL database
- `app_secret_key`: Secret key for Flask application (minimum 32 characters)

### Optional Variables

See `variables.tf` for all available configuration options.

## Architecture

The Terraform configuration creates:

### Core Infrastructure
- **VPC Network** with private subnet
- **VPC Connector** for Cloud Run private access
- **Cloud SQL PostgreSQL** instance with private IP
- **Memorystore Redis** for rate limiting
- **Cloud Storage** buckets for reports and job data
- **Cloud Run** service for the API

### Security
- **Service Account** with minimal required permissions
- **Secret Manager** for sensitive configuration
- **Private networking** for database and Redis
- **IAM bindings** following principle of least privilege

### Monitoring
- **Cloud Monitoring** with alert policies
- **Cloud Logging** for centralized logs
- **Health checks** for service monitoring

## Post-Deployment

After successful deployment:

1. **Get the Cloud Run URL**:
   ```bash
   terraform output cloud_run_url
   ```

2. **Test the API**:
   ```bash
   curl "$(terraform output -raw cloud_run_url)/api/v1/health"
   ```

3. **Bootstrap the API**:
   ```bash
   curl -X POST "$(terraform output -raw cloud_run_url)/api/v1/admin/bootstrap"
   ```

## Environment Management

### Development Environment

```bash
# Use smaller resources for development
terraform apply -var="environment=dev" \
                -var="db_tier=db-f1-micro" \
                -var="redis_tier=BASIC" \
                -var="min_instances=0"
```

### Production Environment

```bash
# Use production-ready resources
terraform apply -var="environment=production" \
                -var="db_tier=db-custom-2-7680" \
                -var="redis_tier=STANDARD_HA" \
                -var="min_instances=2"
```

## Maintenance

### Backup and Recovery

- **Database backups**: Automatically configured with 30-day retention
- **Storage lifecycle**: Reports archived after 30 days, deleted after 90 days
- **Point-in-time recovery**: Enabled for the database

### Updates

```bash
# Update the infrastructure
terraform plan
terraform apply

# Update the application
# (Requires rebuilding and pushing the Docker image)
```

### Monitoring

Access monitoring dashboards:
- **Cloud Monitoring**: [Google Cloud Console](https://console.cloud.google.com/monitoring)
- **Cloud Logging**: [Logs Explorer](https://console.cloud.google.com/logs)
- **Error Reporting**: [Error Reporting](https://console.cloud.google.com/errors)

## Troubleshooting

### Common Issues

1. **API not enabled**: Ensure all required APIs are enabled in your project
2. **Insufficient permissions**: Service account needs proper IAM roles
3. **VPC Connector failures**: Check subnet CIDR doesn't conflict
4. **Database connection issues**: Verify private network configuration

### Debug Commands

```bash
# Check Cloud Run logs
gcloud run services logs read garak-dashboard-api --region=us-central1

# Check Cloud SQL status
gcloud sql instances describe garak-dashboard-db

# Check Redis status
gcloud redis instances describe garak-redis --region=us-central1
```

## Cost Optimization

### Development
- Use `db-f1-micro` for database
- Use `BASIC` Redis tier
- Set `min_instances=0` for Cloud Run

### Production
- Use appropriate database tiers based on load
- Enable Cloud CDN for static content
- Set up auto-scaling based on metrics

## Security Best Practices

1. **Secrets Management**: All sensitive data in Secret Manager
2. **Network Security**: Private IPs for databases
3. **IAM**: Minimal permissions for service accounts
4. **SSL/TLS**: Enforced for all connections
5. **Audit Logging**: Enabled for all services

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will permanently delete all data. Ensure you have backups if needed.

## Support

For issues with this Terraform configuration:
1. Check the [Terraform documentation](https://registry.terraform.io/providers/hashicorp/google)
2. Review [Google Cloud documentation](https://cloud.google.com/docs)
3. Check the logs in Google Cloud Console