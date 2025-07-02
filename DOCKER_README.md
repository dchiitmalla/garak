# Running Garak in Docker

This document provides instructions for running the Garak LLM vulnerability scanner in Docker, making it easy to deploy in cloud environments.

## Prerequisites

- Docker installed on your system or cloud environment
- Docker Compose (optional, but recommended)

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/NVIDIA/garak.git
   cd garak
   ```

2. Set your API keys as environment variables (if needed):
   ```
   export OPENAI_API_KEY=your_openai_key
   export HF_TOKEN=your_huggingface_token
   export COHERE_API_KEY=your_cohere_key
   ```

3. Build and start the container:
   ```
   docker-compose up -d
   ```

4. Run Garak commands:
   ```
   docker-compose exec garak garak scan --generator openai --model gpt-3.5-turbo
   ```

### Using Docker Directly

1. Build the Docker image:
   ```
   docker build -t garak .
   ```

2. Run a container:
   ```
   docker run -it --rm \
     -e OPENAI_API_KEY=your_openai_key \
     -e HF_TOKEN=your_huggingface_token \
     garak scan --generator openai --model gpt-3.5-turbo
   ```

## Cloud Deployment Options

### AWS

1. Push your Docker image to Amazon ECR:
   ```
   aws ecr create-repository --repository-name garak
   aws ecr get-login-password | docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.<region>.amazonaws.com
   docker tag garak:latest <your-aws-account-id>.dkr.ecr.<region>.amazonaws.com/garak:latest
   docker push <your-aws-account-id>.dkr.ecr.<region>.amazonaws.com/garak:latest
   ```

2. Deploy using AWS ECS or Fargate

### Google Cloud Platform

1. Push your Docker image to Google Container Registry:
   ```
   gcloud auth configure-docker
   docker tag garak:latest gcr.io/<your-project-id>/garak:latest
   docker push gcr.io/<your-project-id>/garak:latest
   ```

2. Deploy using Google Cloud Run or GKE

### Azure

1. Push your Docker image to Azure Container Registry:
   ```
   az acr login --name <your-acr-name>
   docker tag garak:latest <your-acr-name>.azurecr.io/garak:latest
   docker push <your-acr-name>.azurecr.io/garak:latest
   ```

2. Deploy using Azure Container Instances or AKS

## Volume Mounts

The Docker Compose configuration includes two volume mounts:
- `garak_data`: For persistent data
- `garak_reports`: For storing Garak reports

## Environment Variables

The following environment variables can be set:
- `OPENAI_API_KEY`: Your OpenAI API key
- `HF_TOKEN`: Your Hugging Face token
- `COHERE_API_KEY`: Your Cohere API key

Add any additional environment variables as needed in the `docker-compose.yml` file.

## Customizing the Docker Image

If you need to customize the Docker image, modify the `Dockerfile` to include additional dependencies or configurations.
