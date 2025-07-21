# Garak Dashboard

The Garak Dashboard is a web interface for managing and viewing security evaluations performed with the [Garak security testing framework](https://github.com/NVIDIA/garak).

## Running Locally

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Garak framework installed

### Installation

1. Clone the Garak repository (if you haven't already):
   ```bash
   git clone https://github.com/NVIDIA/garak.git
   cd garak
   ```

2. Install Garak in development mode:
   ```bash
   pip install -e .
   ```

3. Install dashboard dependencies:
   ```bash
   cd dashboard
   pip install -r requirements.txt
   ```

### Running the Dashboard

#### Method 1: Using Flask Development Server

For development purposes, you can run the dashboard using Flask's built-in development server:

```bash
cd /path/to/garak/dashboard
export FLASK_APP=app.py
export PYTHONPATH=/path/to/garak
flask run --port 8080
```

#### Method 2: Using Gunicorn (Recommended for Production-like Environment)

For a more production-like setup, use Gunicorn:

```bash
cd /path/to/garak
gunicorn --workers 2 --bind 0.0.0.0:8080 dashboard.app:app
```

### Accessing the Dashboard

Once the server is running, you can access the dashboard at:

```
http://localhost:8080
```

## Directory Structure

The dashboard uses two important directories for storing data:

- `dashboard/data/`: Stores job configuration and status files
- `dashboard/reports/`: Stores evaluation reports and results

These directories are created automatically if they don't exist.

## Running with Docker

For containerized deployment, see the Docker instructions below.

### Building the Docker Image

```bash
cd /path/to/garak
docker build -t garak-dashboard -f dashboard/Dockerfile .
```

### Running the Docker Container

```bash
docker run -p 8080:8080 -e PORT=8080 \
  -v /path/to/garak/dashboard/data:/app/data \
  -v /path/to/garak/dashboard/reports:/app/reports \
  --name garak-dashboard-container garak-dashboard \
  gunicorn --workers 2 --bind 0.0.0.0:8080 dashboard.app:app --log-level info
```

For example, if your garak repository is at `/Users/username/garak`:

```bash
docker run -p 8080:8080 -e PORT=8080 \
  -v /Users/username/garak/dashboard/data:/app/data \
  -v /Users/username/garak/dashboard/reports:/app/reports \
  --name garak-dashboard-container garak-dashboard \
  gunicorn --workers 2 --bind 0.0.0.0:8080 dashboard.app:app --log-level info
```

### Stopping and Removing the Container

```bash
docker stop garak-dashboard-container && docker rm garak-dashboard-container
```

## Deploying to Google Cloud Platform (GCP)

The Garak Dashboard can be deployed to Google Cloud Platform using Google Container Registry (GCR) and Cloud Run for a serverless deployment.

### Prerequisites

- Google Cloud Platform account
- Google Cloud SDK installed and configured
- Docker installed locally

### Building and Pushing Docker Images to GCP

#### 1. Authenticate with Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Configure Docker to use gcloud as a credential helper
gcloud auth configure-docker
```

#### 2. Build the Docker Image for AMD64 Architecture

For Cloud Run deployment, build the image specifically for AMD64 architecture using Docker Buildx:

```bash
# Build the image with AMD64 platform specification and load it into Docker
docker buildx build --platform linux/amd64 -t garak-dashboard:latest -f dashboard/Dockerfile . --load
```

#### 3. Tag the Image for Google Container Registry

Replace `[PROJECT_ID]` with your Google Cloud project ID:

```bash
docker tag garak-dashboard:latest gcr.io/[PROJECT_ID]/garak-dashboard:latest
```

#### 4. Push the Image to Google Container Registry

```bash
docker push gcr.io/[PROJECT_ID]/garak-dashboard:latest
```

#### 5. Deploy to Cloud Run

```bash
gcloud run deploy garak-dashboard \
  --image gcr.io/[PROJECT_ID]/garak-dashboard:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8080 \
  --set-env-vars="DISABLE_AUTH=false"
```

### Important Considerations for GCP Deployment

1. **Data Persistence**: Cloud Run containers are ephemeral. For persistent storage:
   - Mount a Cloud Storage bucket using the Cloud Storage FUSE adapter
   - Use a separate database service for job and report data

2. **Environment Variables**: Set these in the Cloud Run deployment:
   - `DISABLE_AUTH`: Set to `false` to enable authentication
   - `FIREBASE_PROJECT_ID`: Your Firebase project ID for authentication
   - `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account credentials

3. **Resource Allocation**: Adjust memory and CPU based on your workload requirements

## Parsing Reports for BigQuery Analysis

The dashboard includes a Python script, `html_report_parser.py`, designed to parse the generated HTML reports, extract key findings, and upload them to Google BigQuery for advanced analysis and long-term storage.

### Overview

- **Source**: The script reads all `.report.html` files from a Google Cloud Storage (GCS) bucket.
- **Processing**: It parses the HTML to extract structured data for each probe and detector result.
- **Destination**: The extracted data is uploaded to a specified BigQuery table.

### Extracted Data Fields

The following fields are extracted from each report and uploaded to BigQuery:

- `run_uuid`: The unique identifier for the Garak scan.
- `model_name`: The name of the model that was evaluated.
- `start_time`: The timestamp when the scan was initiated.
- `garak_version`: The version of Garak used for the scan.
- `probe_group`: The category of the probe (e.g., `promptinject`).
- `probe_name`: The specific name of the probe (e.g., `promptinject.Hijack`)
- `detector_name`: The detector used to evaluate the probe's output.
- `pass_rate`: The percentage of tests that passed.
- `z_score`: The statistical z-score of the results.
- `final_defcon`: The final DEFCON level indicating the severity of the finding.
- `load_timestamp`: The timestamp when the data was uploaded to BigQuery.

### Configuration and How to Run

The script is pre-configured to work with a specific GCP environment. To run it, follow these steps:

1.  **Place Service Account Credentials**:
    Ensure you have a GCP service account key file named `gcp-creds.json` in the root directory of the `garak` project. This service account must have permissions for Google Cloud Storage (read) and BigQuery (write).

2.  **Install Required Libraries**:
    The script requires additional Python libraries. Install them using pip:
    ```bash
    pip install google-cloud-storage google-cloud-bigquery beautifulsoup4 lxml
    ```

3.  **Execute the Script**:
    Run the script from the root of the `garak` repository:
    ```bash
    python dashboard/html_report_parser.py
    ```

The script will automatically connect to the configured GCS bucket, process all reports, and upload the results to the BigQuery table.

## Troubleshooting

### Common Issues

#### Job Not Found Errors

If you see "Job not found" errors for jobs that should exist:

1. Ensure the data and reports directories are correctly configured
2. Check that the job files exist in your data directory
3. Restart the dashboard server to reload jobs from disk

#### Permission Issues

If running with Docker, ensure that volume mounts have appropriate permissions.

#### Environment Variables

The dashboard uses several environment variables that can be configured:

- `DATA_DIR`: Path to the directory where job data is stored (default: `dashboard/data`)
- `REPORT_DIR`: Path to the directory where reports are stored (default: `dashboard/reports`)
- `DOCKER_ENV`: Set to `true` when running in Docker to adjust paths accordingly

## Creating a New Evaluation

1. Navigate to the dashboard homepage
2. Click "New Evaluation"
3. Configure your evaluation parameters:
   - Select a model to test
   - Choose probes to run
   - Set any additional parameters
4. Click "Start Evaluation"
5. Monitor the job status on the dashboard
