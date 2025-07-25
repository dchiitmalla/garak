# Environment Variables for Garak Dashboard

This document describes the environment variables required for the Garak Dashboard application.

## Firebase Authentication Variables

The following environment variables are required for Firebase authentication:

| Variable | Description | Example |
|----------|-------------|---------|
| `FIREBASE_API_KEY` | Firebase API key | `AIzaSyXXXXXXXXXXXXXXXXXXXXX` |
| `FIREBASE_AUTH_DOMAIN` | Firebase authentication domain | `your-project-id.firebaseapp.com` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | `your-project-id` |
| `FIREBASE_STORAGE_BUCKET` | Firebase storage bucket | `your-project-id.appspot.com` |
| `FIREBASE_MESSAGING_SENDER_ID` | Firebase messaging sender ID | `123456789012` |
| `FIREBASE_APP_ID` | Firebase application ID | `1:123456789012:web:abcdef1234567890` |

## Authentication Control

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DISABLE_AUTH` | Disable authentication | `false` | `true` or `false` |
| `HOST` | Host domain (overrides Firebase auth domain if set) | `null` | `dashboard.example.com` |
| `FIREBASE_CREDENTIALS` | Path to Firebase service account JSON file | `/app/firebase-sa.json` | `/path/to/firebase-sa.json` |

## Data and Report Directories

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATA_DIR` | Directory for storing job data | `/app/data` | `/path/to/data` |
| `REPORT_DIR` | Directory for storing reports | `/app/reports` | `/path/to/reports` |

## Docker Deployment

When deploying with Docker, ensure these environment variables are passed to the container using the `-e` flag or an environment file:

```bash
docker run -p 8080:8080 \
  -e FIREBASE_API_KEY=your-api-key \
  -e FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com \
  -e FIREBASE_PROJECT_ID=your-project-id \
  -e FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com \
  -e FIREBASE_MESSAGING_SENDER_ID=123456789012 \
  -e FIREBASE_APP_ID=1:123456789012:web:abcdef1234567890 \
  -v "/path/to/data:/app/data" \
  -v "/path/to/reports:/app/reports" \
  -v "/path/to/config:/home/garak/.local/share/garak" \
  -v "/path/to/cache:/home/garak/.cache/garak" \
  -v "/path/to/tmp:/tmp" \
  garak-dashboard
```

Or using an environment file:

```bash
docker run -p 8080:8080 \
  --env-file .env \
  -v "/path/to/data:/app/data" \
  -v "/path/to/reports:/app/reports" \
  -v "/path/to/config:/home/garak/.local/share/garak" \
  -v "/path/to/cache:/home/garak/.cache/garak" \
  -v "/path/to/tmp:/tmp" \
  garak-dashboard
```

## Local Development

For local development, you can create a `.env` file in the dashboard directory:

```
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789012
FIREBASE_APP_ID=1:123456789012:web:abcdef1234567890
DISABLE_AUTH=false
DATA_DIR=./data
REPORT_DIR=./reports
```
