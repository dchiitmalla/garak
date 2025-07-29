FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for Garak
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    wget \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libmagic1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for base2048 package
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create a non-root user to run the application with proper home directory
RUN groupadd -r garak && useradd -r -g garak -m -d /home/garak garak

# Create and set up home directory for garak user
RUN mkdir -p /home/garak/.config/garak && \
    chown -R garak:garak /home/garak && \
    chmod -R 755 /home/garak

# Create directory structure
RUN mkdir -p /app/dashboard /app/garak /app/reports /app/data

# Copy and install Garak first
COPY garak /app/garak/
COPY pyproject.toml /app/
COPY README.md /app/

# Install Garak package
RUN pip install --no-cache-dir -e /app/

# Install optional dependencies that are commonly needed to prevent import errors
RUN pip install --no-cache-dir google-generativeai

# Pre-download NLTK data to system location (accessible to all users)
RUN python3 -c "import nltk; nltk.download('words', quiet=True, download_dir='/usr/local/share/nltk_data'); nltk.download('punkt', quiet=True, download_dir='/usr/local/share/nltk_data'); nltk.download('stopwords', quiet=True, download_dir='/usr/local/share/nltk_data')"

# Install Flask & dashboard deps, then explicitly install Gunicorn
COPY dashboard/requirements.txt /app/dashboard/
RUN pip install --no-cache-dir -r /app/dashboard/requirements.txt \
    && pip install --no-cache-dir gunicorn


# Copy dashboard application files
COPY dashboard /app/dashboard/

# Test garak installation and basic functionality
RUN python3 -c "import garak; print('Garak imported successfully')"
RUN python3 -m garak --help > /dev/null && echo "Garak CLI working"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=/app/dashboard/app.py
ENV PYTHONPATH=/app:/app/dashboard
ENV DATA_DIR=/app/data
ENV REPORT_DIR=/app/reports
ENV HOME=/home/garak
ENV GARAK_CONFIG_DIR=/home/garak/.config/garak
ENV HF_HOME=/home/garak/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/garak/.cache/huggingface/transformers
ENV NLTK_DATA=/usr/local/share/nltk_data:/home/garak/.nltk_data
ENV TORCH_HOME=/home/garak/.cache/torch

# Create necessary directories and set permissions
RUN mkdir -p /app/reports /app/data && \
    mkdir -p /home/garak/.config/garak && \
    mkdir -p /home/garak/.cache/huggingface/transformers && \
    mkdir -p /home/garak/.nltk_data && \
    mkdir -p /home/garak/.cache/torch && \
    chown -R garak:garak /app/reports /app/data /home/garak && \
    chmod -R 755 /home/garak

EXPOSE 8080

# Switch to non-root user
USER garak

# Test garak functionality as garak user
RUN python3 -c "import garak; print('Garak working as garak user')"
RUN python3 -m garak --help > /dev/null && echo "Garak CLI working as garak user"

# Set working directory to dashboard
WORKDIR /app/dashboard

# Use exec form to make Gunicorn the main process (PID 1)
# The PORT environment variable is automatically set by Cloud Run.
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 0 app:app --log-level info