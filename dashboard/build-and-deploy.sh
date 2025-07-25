#!/bin/bash
set -e

# Configuration
DEFAULT_PROJECT_ID="garak-da264"  # Replace with your GCP project ID
DEFAULT_REGION="us-central1"
DEFAULT_SERVICE_NAME="garak-dashboard"
DEFAULT_REGISTRY="gcr.io"

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

# Help function
show_help() {
    cat << EOF
Garak Dashboard - Build and Deploy to GCP Cloud Run

Usage: $0 [OPTIONS]

Options:
    -p, --project       GCP Project ID (default: $DEFAULT_PROJECT_ID)
    -r, --region        GCP Region (default: $DEFAULT_REGION)
    -s, --service       Cloud Run service name (default: $DEFAULT_SERVICE_NAME)
    -t, --tag           Docker image tag (default: latest)
    --registry          Container registry (default: $DEFAULT_REGISTRY)
    
    --build-only        Only build the Docker image, don't deploy
    --deploy-only       Only deploy (skip building), requires existing image
    --local-test        Build and run locally with docker-compose
    
    --set-env           Set environment variables interactively
    --create-secrets    Create required GCP secrets
    
    -h, --help          Show this help message

Environment Variables:
    FIREBASE_API_KEY              Firebase API key
    FIREBASE_AUTH_DOMAIN          Firebase auth domain
    FIREBASE_PROJECT_ID           Firebase project ID
    FIREBASE_STORAGE_BUCKET       Firebase storage bucket
    FIREBASE_MESSAGING_SENDER_ID  Firebase messaging sender ID
    FIREBASE_APP_ID               Firebase app ID
    
Examples:
    # Build and deploy with defaults
    $0
    
    # Build only
    $0 --build-only
    
    # Deploy to specific project and region
    $0 -p my-project -r us-west1
    
    # Create secrets first
    $0 --create-secrets
    
    # Local testing
    $0 --local-test

EOF
}

# Parse command line arguments
PROJECT_ID="$DEFAULT_PROJECT_ID"
REGION="$DEFAULT_REGION"
SERVICE_NAME="$DEFAULT_SERVICE_NAME"
IMAGE_TAG="latest"
REGISTRY="$DEFAULT_REGISTRY"
BUILD_ONLY=false
DEPLOY_ONLY=false
LOCAL_TEST=false
SET_ENV=false
CREATE_SECRETS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --deploy-only)
            DEPLOY_ONLY=true
            shift
            ;;
        --local-test)
            LOCAL_TEST=true
            shift
            ;;
        --set-env)
            SET_ENV=true
            shift
            ;;
        --create-secrets)
            CREATE_SECRETS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required commands exist
    local required_commands=("docker" "gcloud")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is required but not installed"
            exit 1
        fi
    done
    
    # Check if we're in the right directory
    if [[ ! -f "Dockerfile.production" ]]; then
        log_error "Dockerfile.production not found. Run this script from the dashboard directory."
        exit 1
    fi
    
    # Check Docker buildx
    if ! docker buildx version &> /dev/null; then
        log_error "Docker buildx is required for multi-platform builds"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create GCP secrets
create_gcp_secrets() {
    log_info "Creating GCP secrets..."
    
    # Check if firebase-sa.json exists
    if [[ ! -f "firebase-sa.json" ]]; then
        log_error "firebase-sa.json not found. Please ensure the Firebase service account file is present."
        exit 1
    fi
    
    # Create Firebase service account secret
    log_info "Creating Firebase service account secret..."
    if gcloud secrets describe garak-firebase-service-account --project="$PROJECT_ID" &> /dev/null; then
        log_warning "Secret garak-firebase-service-account already exists"
        read -p "Update existing secret? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            gcloud secrets versions add garak-firebase-service-account --data-file=firebase-sa.json --project="$PROJECT_ID"
        fi
    else
        gcloud secrets create garak-firebase-service-account --data-file=firebase-sa.json --project="$PROJECT_ID"
    fi
    
    # Create app secret key
    log_info "Creating app secret key..."
    if gcloud secrets describe garak-app-secret-key --project="$PROJECT_ID" &> /dev/null; then
        log_warning "Secret garak-app-secret-key already exists"
    else
        # Generate a random secret key
        SECRET_KEY=$(openssl rand -base64 32)
        echo -n "$SECRET_KEY" | gcloud secrets create garak-app-secret-key --data-file=- --project="$PROJECT_ID"
    fi
    
    log_success "GCP secrets created successfully"
}

# Build Docker image
build_image() {
    log_info "Building Docker image for AMD64 architecture..."
    
    local image_name="${REGISTRY}/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"
    
    # Build multi-platform image
    docker buildx build \
        --platform linux/amd64 \
        --file Dockerfile.production \
        --tag "$image_name" \
        --load \
        ..
    
    log_success "Docker image built: $image_name"
    echo "$image_name"
}

# Push image to registry
push_image() {
    local image_name="$1"
    
    log_info "Pushing image to registry..."
    
    # Configure Docker to use gcloud as credential helper
    gcloud auth configure-docker --quiet
    
    # Push the image
    docker push "$image_name"
    
    log_success "Image pushed successfully: $image_name"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    local image_name="$1"
    
    log_info "Deploying to Cloud Run..."
    
    # Prepare environment variables
    local env_vars=(
        "FLASK_ENV=production"
        "DEBUG=false"
        "DOCKER_ENV=true"
    )
    
    # Add Firebase configuration from environment if available
    if [[ -n "$FIREBASE_API_KEY" ]]; then
        env_vars+=("FIREBASE_API_KEY=$FIREBASE_API_KEY")
    fi
    if [[ -n "$FIREBASE_AUTH_DOMAIN" ]]; then
        env_vars+=("FIREBASE_AUTH_DOMAIN=$FIREBASE_AUTH_DOMAIN")
    fi
    if [[ -n "$FIREBASE_PROJECT_ID" ]]; then
        env_vars+=("FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID")
    fi
    if [[ -n "$FIREBASE_STORAGE_BUCKET" ]]; then
        env_vars+=("FIREBASE_STORAGE_BUCKET=$FIREBASE_STORAGE_BUCKET")
    fi
    if [[ -n "$FIREBASE_MESSAGING_SENDER_ID" ]]; then
        env_vars+=("FIREBASE_MESSAGING_SENDER_ID=$FIREBASE_MESSAGING_SENDER_ID")
    fi
    if [[ -n "$FIREBASE_APP_ID" ]]; then
        env_vars+=("FIREBASE_APP_ID=$FIREBASE_APP_ID")
    fi
    
    # Build environment variables string
    local env_vars_string=""
    for var in "${env_vars[@]}"; do
        env_vars_string="$env_vars_string--set-env-vars=$var "
    done
    
    # Deploy to Cloud Run
    gcloud run deploy "$SERVICE_NAME" \
        --image="$image_name" \
        --platform=managed \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --allow-unauthenticated \
        --memory=2Gi \
        --cpu=2 \
        --port=8080 \
        --timeout=300 \
        --concurrency=100 \
        --min-instances=0 \
        --max-instances=10 \
        $env_vars_string
    
    log_success "Deployment completed successfully"
    
    # Get service URL
    local service_url=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)")
    log_info "Service URL: $service_url"
}

# Local testing with docker-compose
local_test() {
    log_info "Starting local test with docker-compose..."
    
    # Check if .env file exists
    if [[ ! -f ".env" ]]; then
        log_warning ".env file not found. Creating from environment variables..."
        create_env_file
    fi
    
    # Build and run with docker-compose
    docker-compose up --build
}

# Create .env file from environment variables
create_env_file() {
    log_info "Creating .env file..."
    
    cat > .env << EOF
# Firebase Configuration
FIREBASE_API_KEY=${FIREBASE_API_KEY:-}
FIREBASE_AUTH_DOMAIN=${FIREBASE_AUTH_DOMAIN:-}
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-}
FIREBASE_STORAGE_BUCKET=${FIREBASE_STORAGE_BUCKET:-}
FIREBASE_MESSAGING_SENDER_ID=${FIREBASE_MESSAGING_SENDER_ID:-}
FIREBASE_APP_ID=${FIREBASE_APP_ID:-}

# Application Settings
SECRET_KEY=${SECRET_KEY:-garak-dashboard-secret-key-local}
DISABLE_AUTH=${DISABLE_AUTH:-false}
DEBUG=${DEBUG:-true}
PORT=${PORT:-8080}

# GCP Settings
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GCP_PROJECT_ID=${PROJECT_ID}
EOF
    
    log_success ".env file created"
}

# Interactive environment variable setup
set_environment_variables() {
    log_info "Setting up environment variables interactively..."
    
    echo "Please provide the following Firebase configuration values:"
    
    read -p "Firebase API Key: " FIREBASE_API_KEY
    read -p "Firebase Auth Domain: " FIREBASE_AUTH_DOMAIN
    read -p "Firebase Project ID: " FIREBASE_PROJECT_ID
    read -p "Firebase Storage Bucket: " FIREBASE_STORAGE_BUCKET
    read -p "Firebase Messaging Sender ID: " FIREBASE_MESSAGING_SENDER_ID
    read -p "Firebase App ID: " FIREBASE_APP_ID
    
    # Export variables
    export FIREBASE_API_KEY FIREBASE_AUTH_DOMAIN FIREBASE_PROJECT_ID
    export FIREBASE_STORAGE_BUCKET FIREBASE_MESSAGING_SENDER_ID FIREBASE_APP_ID
    
    log_success "Environment variables set"
}

# Main execution
main() {
    log_info "Starting Garak Dashboard deployment process"
    log_info "Project: $PROJECT_ID, Region: $REGION, Service: $SERVICE_NAME"
    
    # Check prerequisites
    check_prerequisites
    
    # Handle special modes
    if $CREATE_SECRETS; then
        create_gcp_secrets
        exit 0
    fi
    
    if $SET_ENV; then
        set_environment_variables
        create_env_file
        exit 0
    fi
    
    if $LOCAL_TEST; then
        local_test
        exit 0
    fi
    
    # Build and/or deploy
    if ! $DEPLOY_ONLY; then
        image_name=$(build_image)
        push_image "$image_name"
    else
        image_name="${REGISTRY}/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"
        log_info "Using existing image: $image_name"
    fi
    
    if ! $BUILD_ONLY; then
        deploy_to_cloud_run "$image_name"
    fi
    
    log_success "Process completed successfully!"
}

# Run main function
main "$@"