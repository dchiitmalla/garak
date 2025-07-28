# Garak Dashboard Public API - Deployment Guide

This guide provides step-by-step instructions for deploying the Garak Dashboard API to Google Cloud Platform as a public, scalable endpoint.

## Overview

The deployment creates a production-ready API service with:
- **Cloud Run** for serverless container hosting
- **Cloud SQL PostgreSQL** for API key storage
- **Memorystore Redis** for rate limiting
- **Cloud Storage** for job data and reports
- **VPC networking** for security
- **Comprehensive monitoring** and logging

## Prerequisites

### Required Tools
1. **Google Cloud SDK** (gcloud CLI)
2. **Docker** for container building
3. **Terraform** for infrastructure provisioning
4. **curl** for API testing

### GCP Requirements
1. **GCP Project** with billing enabled
2. **Project Owner** or equivalent permissions
3. **APIs enabled** (handled automatically by Terraform)

## Quick Start

### 1. Clone and Setup

```bash
# Navigate to the dashboard directory
cd garak/dashboard

# Copy and configure Terraform variables
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
vim terraform/terraform.tfvars  # Edit with your values
```

### 2. Configure Environment

```bash
# Set your GCP project
export PROJECT_ID="your-gcp-project-id"
export ENVIRONMENT="production"  # or "staging", "development"

# Authenticate with Google Cloud
gcloud auth login
gcloud config set project $PROJECT_ID
```

### 3. Deploy Everything

```bash
# Run the automated deployment script
PROJECT_ID=$PROJECT_ID ./scripts/deploy.sh
```

This single script will:
- Deploy all infrastructure with Terraform
- Build and push the Docker image
- Deploy to Cloud Run
- Run health checks
- Bootstrap the admin API key

## Manual Deployment Steps

If you prefer manual control or need to troubleshoot:

### Step 1: Infrastructure Deployment

```bash
cd terraform

# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan -var="project_id=$PROJECT_ID"

# Deploy infrastructure
terraform apply -var="project_id=$PROJECT_ID"
```

### Step 2: Build and Deploy Application

```bash
# Build the Docker image
docker build -f dashboard/Dockerfile.cloudrun -t gcr.io/$PROJECT_ID/garak-dashboard:latest .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/garak-dashboard:latest

# Deploy to Cloud Run
gcloud run deploy garak-dashboard-api \
  --image gcr.io/$PROJECT_ID/garak-dashboard:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 100 \
  --vpc-connector garak-vpc-connector \
  --service-account garak-dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Step 3: Test Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe garak-dashboard-api --region us-central1 --format 'value(status.url)')

# Test health endpoint
curl "$SERVICE_URL/api/v1/health"

# Test info endpoint
curl "$SERVICE_URL/api/v1/info"
```

### Step 4: Bootstrap API

```bash
# Create the initial admin API key
curl -X POST "$SERVICE_URL/api/v1/admin/bootstrap"
```

**Important:** Save the returned API key securely - it won't be shown again!

## Configuration

### Environment Variables

The following environment variables configure the deployment:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PROJECT_ID` | GCP Project ID | - | Yes |
| `ENVIRONMENT` | Environment name | `production` | No |
| `REGION` | GCP region | `us-central1` | No |
| `DATABASE_URL` | Database connection URL | Auto-configured | No |
| `REDIS_URL` | Redis connection URL | Auto-configured | No |
| `SECRET_KEY` | Flask secret key | From Secret Manager | No |

### Terraform Variables

Key variables in `terraform/terraform.tfvars`:

```hcl
# Required
project_id    = "your-gcp-project-id"
db_password   = "secure-database-password"
app_secret_key = "32-character-secret-key"

# Optional
environment   = "production"
region        = "us-central1"
db_tier       = "db-f1-micro"
redis_tier    = "STANDARD_HA"
```

## Environment Management

### Development Environment

```bash
# Deploy with minimal resources for development
ENVIRONMENT=development AUTO_APPROVE=true ./scripts/deploy.sh
```

Development configuration:
- SQLite database (local)
- No Redis rate limiting
- Local file storage
- Minimal Cloud Run resources

### Staging Environment

```bash
# Deploy staging environment
ENVIRONMENT=staging ./scripts/deploy.sh
```

Staging configuration:
- Cloud SQL PostgreSQL
- Redis rate limiting
- Cloud Storage
- Moderate Cloud Run resources

### Production Environment

```bash
# Deploy production environment
ENVIRONMENT=production ./scripts/deploy.sh
```

Production configuration:
- Cloud SQL with high availability
- Redis with high availability
- Cloud Storage with lifecycle policies
- Full Cloud Run resources and monitoring

## API Usage

### 1. Create API Keys

After deployment, create API keys for users:

```bash
# Use the admin key from bootstrap
curl -X POST "$SERVICE_URL/api/v1/admin/api-keys" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User API Key",
    "description": "For security scans",
    "permissions": ["read", "write"],
    "rate_limit": 100,
    "expires_days": 365
  }'
```

### 2. Run Security Scans

```bash
# Create a security scan
curl -X POST "$SERVICE_URL/api/v1/scans" \
  -H "X-API-Key: $USER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "generator": "openai",
    "model_name": "gpt-3.5-turbo",
    "probe_categories": ["dan", "security"],
    "api_keys": {
      "openai_api_key": "sk-your-openai-key"
    },
    "name": "GPT-3.5 Security Test"
  }'
```

### 3. Monitor Scans

```bash
# Get scan status
curl -H "X-API-Key: $USER_API_KEY" "$SERVICE_URL/api/v1/scans/$SCAN_ID/status"

# Get scan results when complete
curl -H "X-API-Key: $USER_API_KEY" "$SERVICE_URL/api/v1/scans/$SCAN_ID"
```

## Monitoring and Operations

### Health Monitoring

The API provides comprehensive health checks:

```bash
# System health
curl "$SERVICE_URL/api/v1/health"

# API capabilities
curl "$SERVICE_URL/api/v1/info"
```

### Log Monitoring

```bash
# View Cloud Run logs
gcloud run services logs read garak-dashboard-api --region us-central1

# View recent logs
gcloud run services logs tail garak-dashboard-api --region us-central1
```

### Metrics and Alerts

Access monitoring dashboards:
- **Cloud Monitoring**: [Console Link](https://console.cloud.google.com/monitoring)
- **Cloud Logging**: [Logs Explorer](https://console.cloud.google.com/logs)
- **Error Reporting**: [Error Console](https://console.cloud.google.com/errors)

### Performance Tuning

#### Cloud Run Optimization

```bash
# Scale up for high traffic
gcloud run services update garak-dashboard-api \
  --region us-central1 \
  --min-instances 5 \
  --max-instances 200 \
  --memory 4Gi \
  --cpu 4
```

#### Database Optimization

```bash
# Upgrade database tier for production
# Update terraform.tfvars:
db_tier = "db-custom-4-15360"  # 4 vCPU, 15GB RAM

# Apply changes
terraform apply -var="project_id=$PROJECT_ID"
```

## Security

### API Key Management

```bash
# List all API keys (admin only)
curl -H "X-API-Key: $ADMIN_API_KEY" "$SERVICE_URL/api/v1/admin/api-keys"

# Revoke a compromised key
curl -X POST -H "X-API-Key: $ADMIN_API_KEY" "$SERVICE_URL/api/v1/admin/api-keys/$KEY_ID/revoke"

# Delete an old key
curl -X DELETE -H "X-API-Key: $ADMIN_API_KEY" "$SERVICE_URL/api/v1/admin/api-keys/$KEY_ID"
```

### Rate Limiting

Monitor rate limiting status:

```bash
# Check rate limit status for a key
curl -H "X-API-Key: $ADMIN_API_KEY" "$SERVICE_URL/api/v1/admin/api-keys/$KEY_ID/rate-limit"
```

### Security Headers

The API includes security headers:
- `X-RateLimit-*` headers for rate limiting info
- CORS headers for web client support
- Security headers for XSS protection

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```bash
# Check Cloud SQL status
gcloud sql instances describe garak-dashboard-db

# Check VPC connector
gcloud compute networks vpc-access connectors describe garak-vpc-connector --region us-central1
```

#### 2. Redis Connection Issues

```bash
# Check Redis instance
gcloud redis instances describe garak-redis --region us-central1

# Test Redis connectivity from Cloud Shell
redis-cli -h REDIS_IP ping
```

#### 3. API Key Bootstrap Issues

```bash
# Check if admin keys already exist
curl -X POST "$SERVICE_URL/api/v1/admin/bootstrap"

# If you get "admin_exists" error, admin key already created
# Check Cloud Logging for the original key or create new ones using existing admin key
```

#### 4. Container Build Issues

```bash
# Check build logs
gcloud builds list --limit 5

# Get detailed build log
gcloud builds log BUILD_ID
```

### Debug Commands

```bash
# Check Cloud Run service status
gcloud run services describe garak-dashboard-api --region us-central1

# Check container logs
gcloud run services logs read garak-dashboard-api --region us-central1

# Test local container
docker run -p 8080:8080 gcr.io/$PROJECT_ID/garak-dashboard:latest
```

## Cost Optimization

### Development/Testing

- Use `db-f1-micro` for database
- Set `min-instances=0` for Cloud Run
- Use `BASIC` Redis tier
- Enable Cloud Storage lifecycle policies

### Production

- Monitor actual usage and scale appropriately
- Use committed use discounts for predictable workloads
- Enable Cloud CDN for static content
- Set up alerting for unusual cost spikes

## Backup and Recovery

### Database Backups

Automated backups are configured by Terraform:
- Daily backups with 30-day retention
- Point-in-time recovery enabled
- Regional backup storage

### Disaster Recovery

```bash
# Export API keys (for backup)
curl -H "X-API-Key: $ADMIN_API_KEY" "$SERVICE_URL/api/v1/admin/api-keys" > api_keys_backup.json

# Export job data (handled automatically by Cloud Storage)
# Reports are stored in Cloud Storage with lifecycle management
```

## Support and Maintenance

### Updates

To update the API:

1. Update code and commit changes
2. Run deployment script:
   ```bash
   IMAGE_TAG=$(date +%Y%m%d-%H%M%S) ./scripts/deploy.sh
   ```

### Scaling

The system auto-scales based on traffic, but you can adjust limits:

```bash
# Update scaling configuration
gcloud run services update garak-dashboard-api \
  --region us-central1 \
  --min-instances 2 \
  --max-instances 500
```

### Monitoring Alerts

Set up monitoring alerts for:
- High error rates (>5%)
- High response times (>2s)
- Database connection issues
- API key usage spikes

For support with deployment issues, check:
1. Cloud Logging for detailed error messages
2. Cloud Monitoring for performance metrics
3. Terraform documentation for infrastructure issues
4. This deployment guide for common solutions