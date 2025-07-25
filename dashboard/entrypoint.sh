#!/bin/bash
set -e

echo "Starting Garak Dashboard entrypoint..."

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to fetch secret from GCP Secret Manager
fetch_secret() {
    local secret_name=$1
    local project_id=${GOOGLE_CLOUD_PROJECT:-$GCP_PROJECT_ID}
    
    if [ -z "$project_id" ]; then
        log "WARNING: No GCP project ID found. Skipping secret fetch for $secret_name"
        return 1
    fi
    
    log "Fetching secret: $secret_name from project: $project_id"
    
    # Try to fetch the secret
    if command -v gcloud >/dev/null 2>&1; then
        # Use gcloud if available
        gcloud secrets versions access latest --secret="$secret_name" --project="$project_id" 2>/dev/null
    else
        # Use Python with google-cloud-secret-manager
        python3 -c "
from google.cloud import secretmanager
import os
import sys

try:
    client = secretmanager.SecretManagerServiceClient()
    project_id = '$project_id'
    secret_name = '$secret_name'
    name = f'projects/{project_id}/secrets/{secret_name}/versions/latest'
    response = client.access_secret_version(request={'name': name})
    print(response.payload.data.decode('UTF-8'), end='')
except Exception as e:
    print(f'Error fetching secret {secret_name}: {e}', file=sys.stderr)
    sys.exit(1)
"
    fi
}

# Set default values
export PORT=${PORT:-8080}
export FLASK_ENV=${FLASK_ENV:-production}
export PYTHONPATH=${PYTHONPATH:-/app}

log "Port: $PORT"
log "Flask Environment: $FLASK_ENV"
log "Python Path: $PYTHONPATH"

# Handle Firebase service account from GCP Secret Manager
if [ "$DISABLE_AUTH" != "true" ]; then
    log "Authentication enabled - setting up Firebase credentials"
    
    # Try to fetch Firebase service account from Secret Manager
    SECRET_NAME=${FIREBASE_SECRET_NAME:-"garak-firebase-service-account"}
    
    if [ -n "$GOOGLE_CLOUD_PROJECT" ] || [ -n "$GCP_PROJECT_ID" ]; then
        log "Attempting to fetch Firebase service account from Secret Manager..."
        
        if SERVICE_ACCOUNT_JSON=$(fetch_secret "$SECRET_NAME"); then
            log "Successfully fetched Firebase service account from Secret Manager"
            echo "$SERVICE_ACCOUNT_JSON" > /tmp/firebase-sa.json
            export FIREBASE_CREDENTIALS="/tmp/firebase-sa.json"
            chmod 600 /tmp/firebase-sa.json
        else
            log "WARNING: Failed to fetch Firebase service account from Secret Manager"
            log "Falling back to environment variables or mounted files"
        fi
    else
        log "No GCP project configured - skipping Secret Manager"
    fi
    
    # Validate Firebase configuration
    if [ -z "$FIREBASE_API_KEY" ] || [ -z "$FIREBASE_PROJECT_ID" ]; then
        log "ERROR: Missing required Firebase configuration"
        log "Required environment variables:"
        log "  - FIREBASE_API_KEY"
        log "  - FIREBASE_PROJECT_ID" 
        log "  - FIREBASE_AUTH_DOMAIN"
        log "  - FIREBASE_STORAGE_BUCKET"
        log "  - FIREBASE_MESSAGING_SENDER_ID"
        log "  - FIREBASE_APP_ID"
        log "Alternatively, set DISABLE_AUTH=true to bypass authentication"
        exit 1
    fi
    
    log "Firebase configuration validated"
else
    log "Authentication disabled via DISABLE_AUTH=true"
fi

# Ensure data directories exist
mkdir -p "$DATA_DIR" "$REPORT_DIR"
log "Data directories created: $DATA_DIR, $REPORT_DIR"

# Set Flask app secret key from Secret Manager or environment
if [ -n "$GOOGLE_CLOUD_PROJECT" ] || [ -n "$GCP_PROJECT_ID" ]; then
    SECRET_KEY_NAME=${SECRET_KEY_SECRET_NAME:-"garak-app-secret-key"}
    
    if SECRET_KEY_VALUE=$(fetch_secret "$SECRET_KEY_NAME" 2>/dev/null); then
        export SECRET_KEY="$SECRET_KEY_VALUE"
        log "Flask secret key loaded from Secret Manager"
    elif [ -z "$SECRET_KEY" ]; then
        log "WARNING: No secret key found in Secret Manager or environment"
        log "Using default secret key (not recommended for production)"
        export SECRET_KEY="garak-dashboard-default-secret-change-me"
    fi
else
    if [ -z "$SECRET_KEY" ]; then
        log "WARNING: No secret key configured"
        export SECRET_KEY="garak-dashboard-default-secret-change-me"
    fi
fi

# Log configuration (without sensitive values)
log "Configuration summary:"
log "  - Authentication: $([ "$DISABLE_AUTH" = "true" ] && echo "Disabled" || echo "Enabled")"
log "  - Firebase Project: ${FIREBASE_PROJECT_ID:-"Not set"}"
log "  - Data Directory: $DATA_DIR"
log "  - Reports Directory: $REPORT_DIR"
log "  - Secret Key: $([ -n "$SECRET_KEY" ] && echo "Set" || echo "Not set")"

# Validate the Python app can start
log "Validating application configuration..."
if ! python3 -c "
import sys
sys.path.insert(0, '/app')
try:
    from dashboard import auth
    print('Import test successful')
except Exception as e:
    print(f'Import test failed: {e}')
    sys.exit(1)
"; then
    log "ERROR: Application validation failed"
    exit 1
fi

log "Application validation successful"

# Execute the main command
log "Starting application with command: $*"
exec "$@"