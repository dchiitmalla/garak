#!/bin/bash
# Script to run Garak Dashboard with Firebase authentication in Docker

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker and try again."
  exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t garak-dashboard -f dashboard/Dockerfile .

# Create directories for volume mounts if they don't exist
mkdir -p dashboard/data
mkdir -p dashboard/reports
mkdir -p dashboard/garak_config
mkdir -p dashboard/garak_cache
mkdir -p dashboard/garak_tmp

# Run the Docker container with Firebase authentication
echo "Running Docker container with Firebase authentication..."
docker run -p 8080:8080 -e PORT=8080 \
  -v "$(pwd)/dashboard/data:/app/data" \
  -v "$(pwd)/dashboard/reports:/app/reports" \
  -v "$(pwd)/dashboard/garak_config:/home/garak/.local/share/garak" \
  -v "$(pwd)/dashboard/garak_cache:/home/garak/.cache/garak" \
  -v "$(pwd)/dashboard/garak_tmp:/tmp" \
  -v "$(pwd)/firebase-sa.json:/app/firebase-sa.json" \
  -e FIREBASE_CREDENTIALS=/app/firebase-sa.json \
  -e FIREBASE_API_KEY=AIzaSyA5PORYtPK1BNZPlh7daqipXtSAqGPJ_Og \
  -e FIREBASE_PROJECT_ID=garak-da264 \
  -e DISABLE_AUTH=false \
  --name garak-dashboard-container \
  garak-dashboard \
  gunicorn --workers 2 --bind 0.0.0.0:8080 dashboard.app:app --log-level info

echo "Garak Dashboard is running at http://localhost:8080"
