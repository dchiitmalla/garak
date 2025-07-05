FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for Garak
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for base2048 package
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create directory structure
RUN mkdir -p /app/dashboard /app/garak /app/reports /app/data

# Copy and install Garak first
COPY garak /app/garak/
COPY pyproject.toml /app/
COPY README.md /app/

# Install Garak package
RUN pip install --no-cache-dir -e /app/

# Install Flask and dashboard dependencies
COPY dashboard/requirements.txt /app/dashboard/
RUN pip install --no-cache-dir -r /app/dashboard/requirements.txt

# Copy dashboard application files
COPY dashboard /app/dashboard/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=/app/dashboard/app.py
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/reports /app/data

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "dashboard.app:app"]
