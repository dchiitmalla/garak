#!/bin/bash

# Configuration
PROJECT_ID="garak-464900"
REGION="us-central1"  # Use a specific region for the function
FUNCTION_NAME="garak-ingest-http-function"
RUNTIME="python311"

echo "Deploying HTTP-triggered Cloud Function..."
gcloud functions deploy ${FUNCTION_NAME} \
  --gen2 \
  --runtime=${RUNTIME} \
  --region=${REGION} \
  --source=. \
  --entry-point=process_bucket_files \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --timeout=540s