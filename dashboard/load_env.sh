#!/bin/bash
# Load environment variables for Garak Dashboard

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your Firebase settings."
    exit 1
fi

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

echo "Environment variables loaded from .env file"
echo "Firebase Project ID: $FIREBASE_PROJECT_ID"
echo "Firebase Auth Domain: $FIREBASE_AUTH_DOMAIN"
echo "Firebase Credentials: $FIREBASE_CREDENTIALS"
echo "Authentication Enabled: $([ "$DISABLE_AUTH" = "true" ] && echo "No" || echo "Yes")"

# Verify Firebase service account file exists
if [ "$DISABLE_AUTH" != "true" ] && [ ! -f "$FIREBASE_CREDENTIALS" ]; then
    echo "Warning: Firebase service account file not found at: $FIREBASE_CREDENTIALS"
    echo "Please ensure the file exists or set DISABLE_AUTH=true for development"
fi