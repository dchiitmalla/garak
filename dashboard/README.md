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
