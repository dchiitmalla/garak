#!/bin/bash

# Garak Dashboard Deployment Script
# This script handles the complete deployment process to Google Cloud Platform

set -e  # Exit on any error

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
ENVIRONMENT="${ENVIRONMENT:-production}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_warning "Terraform is not installed. Infrastructure deployment will be skipped."
    fi
    
    # Check if project ID is set
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            log_error "PROJECT_ID is not set and no default project found."
            echo "Please set PROJECT_ID environment variable or run 'gcloud config set project YOUR_PROJECT_ID'"
            exit 1
        fi
    fi
    
    log_success "Prerequisites check completed. Project: $PROJECT_ID"
}

# Function to authenticate with Google Cloud
authenticate() {
    log_info "Authenticating with Google Cloud..."
    
    # Check if already authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_info "Not authenticated. Starting authentication process..."
        gcloud auth login
    fi
    
    # Configure Docker for Container Registry
    gcloud auth configure-docker --quiet
    
    log_success "Authentication completed"
}

# Function to deploy infrastructure with Terraform
deploy_infrastructure() {
    if [ "$SKIP_INFRASTRUCTURE" = "true" ]; then
        log_info "Skipping infrastructure deployment (SKIP_INFRASTRUCTURE=true)"
        return
    fi
    
    log_info "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform if needed
    if [ ! -d ".terraform" ]; then
        log_info "Initializing Terraform..."
        terraform init
    fi
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform.tfvars" ]; then
        log_error "terraform.tfvars file not found. Please create it from terraform.tfvars.example"
        exit 1
    fi
    
    # Plan and apply
    log_info "Planning infrastructure changes..."
    terraform plan -var="project_id=$PROJECT_ID" -var="environment=$ENVIRONMENT"
    
    if [ "$AUTO_APPROVE" = "true" ]; then
        log_info "Applying infrastructure changes (auto-approved)..."
        terraform apply -auto-approve -var="project_id=$PROJECT_ID" -var="environment=$ENVIRONMENT"
    else
        log_info "Applying infrastructure changes..."
        terraform apply -var="project_id=$PROJECT_ID" -var="environment=$ENVIRONMENT"
    fi
    
    cd ..
    log_success "Infrastructure deployment completed"
}

# Function to build and push Docker image
build_and_push_image() {
    log_info "Building and pushing Docker image..."
    
    # Build the image
    log_info "Building Docker image..."
    docker build -f dashboard/Dockerfile.cloudrun -t gcr.io/$PROJECT_ID/garak-dashboard:$IMAGE_TAG .
    
    # Push the image
    log_info "Pushing Docker image to Container Registry..."
    docker push gcr.io/$PROJECT_ID/garak-dashboard:$IMAGE_TAG
    
    log_success "Docker image built and pushed successfully"
}

# Function to deploy to Cloud Run
deploy_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    # Determine service name based on environment
    SERVICE_NAME="garak-dashboard-api"
    if [ "$ENVIRONMENT" != "production" ]; then
        SERVICE_NAME="garak-dashboard-$ENVIRONMENT"
    fi
    
    # Set environment-specific configuration
    case $ENVIRONMENT in
        "production")
            MIN_INSTANCES=1
            MAX_INSTANCES=100
            MEMORY="2Gi"
            CPU="2"
            ;;
        "staging")
            MIN_INSTANCES=0
            MAX_INSTANCES=10
            MEMORY="2Gi"
            CPU="2"
            ;;
        "development")
            MIN_INSTANCES=0
            MAX_INSTANCES=5
            MEMORY="1Gi"
            CPU="1"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    # Deploy to Cloud Run
    gcloud run deploy $SERVICE_NAME \
        --image gcr.io/$PROJECT_ID/garak-dashboard:$IMAGE_TAG \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --memory $MEMORY \
        --cpu $CPU \
        --min-instances $MIN_INSTANCES \
        --max-instances $MAX_INSTANCES \
        --set-env-vars "ENVIRONMENT=$ENVIRONMENT,PROJECT_ID=$PROJECT_ID,REGION=$REGION" \
        --vpc-connector garak-vpc-connector \
        --vpc-egress private-ranges-only \
        --service-account garak-dashboard-sa@$PROJECT_ID.iam.gserviceaccount.com \
        --timeout 300 \
        --concurrency 1000 \
        --project $PROJECT_ID
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')
    
    log_success "Cloud Run deployment completed"
    log_info "Service URL: $SERVICE_URL"
}

# Function to run health checks
health_check() {
    log_info "Running health checks..."
    
    # Determine service URL
    SERVICE_NAME="garak-dashboard-api"
    if [ "$ENVIRONMENT" != "production" ]; then
        SERVICE_NAME="garak-dashboard-$ENVIRONMENT"
    fi
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' 2>/dev/null)
    
    if [ -z "$SERVICE_URL" ]; then
        log_error "Could not get service URL for health check"
        return 1
    fi
    
    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    sleep 10
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    if curl -f -s "$SERVICE_URL/api/v1/health" > /dev/null; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi
    
    # Test info endpoint
    log_info "Testing API info endpoint..."
    if curl -f -s "$SERVICE_URL/api/v1/info" > /dev/null; then
        log_success "API info endpoint working"
    else
        log_error "API info endpoint failed"
        return 1
    fi
    
    log_success "All health checks passed"
    log_info "API is available at: $SERVICE_URL"
}

# Function to bootstrap API (create admin key)
bootstrap_api() {
    if [ "$SKIP_BOOTSTRAP" = "true" ]; then
        log_info "Skipping API bootstrap (SKIP_BOOTSTRAP=true)"
        return
    fi
    
    log_info "Bootstrapping API (creating admin key)..."
    
    # Determine service URL
    SERVICE_NAME="garak-dashboard-api"
    if [ "$ENVIRONMENT" != "production" ]; then
        SERVICE_NAME="garak-dashboard-$ENVIRONMENT"
    fi
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' 2>/dev/null)
    
    if [ -z "$SERVICE_URL" ]; then
        log_error "Could not get service URL for bootstrap"
        return 1
    fi
    
    # Create admin API key
    log_info "Creating admin API key..."
    RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/admin/bootstrap")
    
    if echo "$RESPONSE" | grep -q "api_key"; then
        log_success "Admin API key created successfully"
        log_warning "Please save the API key from the response above - it won't be shown again!"
        echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
    else
        log_info "Admin key may already exist or bootstrap not needed"
        echo "$RESPONSE"
    fi
}

# Function to show deployment summary
show_summary() {
    log_info "Deployment Summary"
    echo "=================================="
    echo "Project ID: $PROJECT_ID"
    echo "Environment: $ENVIRONMENT"
    echo "Region: $REGION"
    echo "Image: gcr.io/$PROJECT_ID/garak-dashboard:$IMAGE_TAG"
    
    # Get service URL
    SERVICE_NAME="garak-dashboard-api"
    if [ "$ENVIRONMENT" != "production" ]; then
        SERVICE_NAME="garak-dashboard-$ENVIRONMENT"
    fi
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' 2>/dev/null)
    
    if [ -n "$SERVICE_URL" ]; then
        echo "Service URL: $SERVICE_URL"
        echo ""
        echo "API Endpoints:"
        echo "  Health: $SERVICE_URL/api/v1/health"
        echo "  Info: $SERVICE_URL/api/v1/info"
        echo "  Docs: $SERVICE_URL/api/docs"
        echo "  Admin: $SERVICE_URL/api/v1/admin/api-keys"
    fi
    
    echo "=================================="
}

# Main deployment function
main() {
    log_info "Starting Garak Dashboard deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Project: $PROJECT_ID"
    
    # Run deployment steps
    check_prerequisites
    authenticate
    deploy_infrastructure
    build_and_push_image
    deploy_cloud_run
    health_check
    bootstrap_api
    show_summary
    
    log_success "Deployment completed successfully!"
}

# Help function
show_help() {
    echo "Garak Dashboard Deployment Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Environment Variables:"
    echo "  PROJECT_ID              GCP Project ID (required)"
    echo "  ENVIRONMENT             Deployment environment (default: production)"
    echo "  REGION                  GCP region (default: us-central1)"
    echo "  IMAGE_TAG              Docker image tag (default: latest)"
    echo "  AUTO_APPROVE           Auto-approve Terraform changes (default: false)"
    echo "  SKIP_INFRASTRUCTURE    Skip infrastructure deployment (default: false)"
    echo "  SKIP_BOOTSTRAP         Skip API bootstrap (default: false)"
    echo ""
    echo "Examples:"
    echo "  PROJECT_ID=my-project $0"
    echo "  ENVIRONMENT=staging PROJECT_ID=my-project $0"
    echo "  AUTO_APPROVE=true PROJECT_ID=my-project $0"
    echo ""
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main
        ;;
esac