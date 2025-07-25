# Docker Deployment Guide

This guide covers building and deploying the Garak Dashboard using Docker for both local development and Google Cloud Platform (GCP) production environments.

## Quick Start

### Local Development with Docker Compose

```bash
# 1. Ensure you have the environment variables set
cp .env.example .env
# Edit .env with your Firebase configuration

# 2. Build and run with docker-compose
docker-compose up --build

# 3. Access the dashboard at http://localhost:8080
```

### Production Deployment to GCP Cloud Run

```bash
# 1. Build and deploy in one command
./build-and-deploy.sh

# 2. Or step by step:
./build-and-deploy.sh --create-secrets  # Create GCP secrets
./build-and-deploy.sh --build-only      # Build Docker image
./build-and-deploy.sh --deploy-only     # Deploy to Cloud Run
```

## File Overview

### Core Files

- **`Dockerfile.production`** - Multi-stage production Docker build
- **`entrypoint.sh`** - Handles environment setup and GCP Secret Manager integration
- **`docker-compose.yml`** - Local development environment
- **`build-and-deploy.sh`** - Automated build and deployment script
- **`.dockerignore`** - Optimizes Docker build context

### Environment Management

- **`.env`** - Local environment variables
- **GCP Secret Manager** - Production secrets (Firebase service account, app secret key)
- **Cloud Run Environment Variables** - Non-sensitive configuration

## Architecture

### Multi-Stage Docker Build

The production Dockerfile uses a multi-stage build:

1. **Builder Stage**: Compiles dependencies, installs Rust, builds packages
2. **Production Stage**: Minimal runtime image with only necessary components

Benefits:
- Smaller final image size (~200MB vs ~1GB)
- Improved security (no build tools in production)
- Faster deployment and startup times

### Secret Management

**Local Development:**
- Environment variables from `.env` file
- Firebase service account from local `firebase-sa.json`

**Production (GCP):**
- GCP Secret Manager for sensitive data
- Cloud Run environment variables for configuration
- Automatic secret injection via `entrypoint.sh`

## Environment Variables

### Required Firebase Configuration

```bash
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789012
FIREBASE_APP_ID=1:123456789012:web:abcdef1234567890
```

### Application Settings

```bash
# Authentication
DISABLE_AUTH=false                    # Set to true for development only

# Application
SECRET_KEY=your-secret-key           # Flask secret key
DEBUG=false                          # Debug mode (development only)
PORT=8080                           # Server port

# Directories
DATA_DIR=/app/data                  # Job data directory
REPORT_DIR=/app/reports             # Reports directory

# GCP Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GCP_PROJECT_ID=your-project-id
```

## GCP Secret Manager Setup

### 1. Create Required Secrets

```bash
# Create Firebase service account secret
gcloud secrets create garak-firebase-service-account \
    --data-file=firebase-sa.json \
    --project=your-project-id

# Create app secret key
openssl rand -base64 32 | gcloud secrets create garak-app-secret-key \
    --data-file=- \
    --project=your-project-id
```

### 2. Grant Cloud Run Access

```bash
# Get the Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe garak-dashboard \
    --region=us-central1 \
    --project=your-project-id \
    --format="value(spec.template.spec.serviceAccountName)")

# Grant secret access
gcloud secrets add-iam-policy-binding garak-firebase-service-account \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=your-project-id

gcloud secrets add-iam-policy-binding garak-app-secret-key \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=your-project-id
```

## Build and Deployment Scripts

### build-and-deploy.sh Usage

```bash
# Show help
./build-and-deploy.sh --help

# Build and deploy with defaults
./build-and-deploy.sh

# Build for specific project and region
./build-and-deploy.sh --project my-project --region us-west1

# Create GCP secrets
./build-and-deploy.sh --create-secrets

# Local testing
./build-and-deploy.sh --local-test

# Build only (no deployment)
./build-and-deploy.sh --build-only

# Deploy only (skip building)
./build-and-deploy.sh --deploy-only
```

### Manual Build Process

```bash
# 1. Build multi-platform image
docker buildx build \
    --platform linux/amd64 \
    --file Dockerfile.production \
    --tag gcr.io/your-project/garak-dashboard:latest \
    --load \
    .

# 2. Push to Google Container Registry
gcloud auth configure-docker
docker push gcr.io/your-project/garak-dashboard:latest

# 3. Deploy to Cloud Run
gcloud run deploy garak-dashboard \
    --image gcr.io/your-project/garak-dashboard:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --port 8080 \
    --set-env-vars="FIREBASE_API_KEY=your-key,FIREBASE_PROJECT_ID=your-project"
```

## Health Checks and Monitoring

### Health Check Endpoints

- **`/health`** - Basic health check with system status
- **`/ready`** - Readiness probe for Kubernetes/Cloud Run

### Example Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "1.0.0",
  "environment": "production",
  "auth_enabled": true,
  "firebase_initialized": true,
  "data_dir_exists": true,
  "report_dir_exists": true
}
```

## Troubleshooting

### Common Issues

**Build Failures:**
```bash
# Clean Docker build cache
docker builder prune

# Rebuild from scratch
docker buildx build --no-cache ...
```

**Authentication Issues:**
```bash
# Check GCP authentication
gcloud auth list

# Check secrets exist
gcloud secrets list --project=your-project-id

# Test secret access
gcloud secrets versions access latest --secret=garak-firebase-service-account
```

**Deployment Issues:**
```bash
# Check Cloud Run logs
gcloud logs read --project=your-project-id --service=garak-dashboard

# Check service status
gcloud run services describe garak-dashboard --region=us-central1
```

### Debugging

**Local Development:**
```bash
# Run with debug output
DOCKER_BUILDKIT=1 docker-compose up --build

# Check container logs
docker-compose logs -f garak-dashboard

# Access running container
docker-compose exec garak-dashboard /bin/bash
```

**Production:**
```bash
# View Cloud Run logs
gcloud logs tail --project=your-project-id --service=garak-dashboard

# Check environment variables
gcloud run services describe garak-dashboard --format="export" --region=us-central1
```

## Security Considerations

### Production Security

1. **Never embed secrets in Docker images**
2. **Use GCP Secret Manager for sensitive data**
3. **Run containers as non-root user** (automatically handled)
4. **Enable Cloud Run authentication** for production environments
5. **Use HTTPS-only** (automatically provided by Cloud Run)

### Network Security

```bash
# Restrict Cloud Run to authenticated users only
gcloud run services remove-iam-policy-binding garak-dashboard \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --region=us-central1
```

## Performance Optimization

### Container Optimization

- **Multi-stage builds** reduce image size
- **Layer caching** speeds up builds
- **Non-root user** improves security
- **Health checks** enable proper load balancing

### Cloud Run Settings

```bash
# Optimized Cloud Run configuration
gcloud run deploy garak-dashboard \
    --memory=2Gi \
    --cpu=2 \
    --concurrency=100 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300
```

## Monitoring and Logging

### Cloud Logging

All application logs are automatically sent to Google Cloud Logging. View them with:

```bash
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=garak-dashboard" --project=your-project-id
```

### Monitoring

Set up monitoring with:

```bash
# Enable Cloud Monitoring API
gcloud services enable monitoring.googleapis.com --project=your-project-id

# Create uptime check
gcloud alpha monitoring uptime create \
    --display-name="Garak Dashboard Health Check" \
    --http-check-path="/health" \
    --http-check-port=443 \
    --resource-type=url \
    --resource-url="https://your-service-url.com"
```

## Cost Optimization

### Cloud Run Pricing

- **CPU allocation**: Only charged when processing requests
- **Memory allocation**: Only charged during request processing
- **Request count**: $0.40 per million requests
- **Free tier**: 2 million requests per month

### Optimization Tips

1. **Use minimum required memory/CPU**
2. **Set appropriate min/max instances**
3. **Implement efficient request handling**
4. **Use Cloud CDN for static assets** (if applicable)

For detailed pricing, see: https://cloud.google.com/run/pricing