FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    git \
    ca-certificates \
    curl \
    pkg-config \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for all users
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
ENV PATH="/root/.cargo/bin:${PATH}"

# Create non-root user for better security
RUN groupadd -g 1000 garak && \
    useradd -u 1000 -g garak -s /bin/bash -m garak

# Install Rust for garak user too
RUN mkdir -p /home/garak/.cargo/bin && \
    cp -a /root/.cargo/bin/* /home/garak/.cargo/bin/ && \
    echo 'export PATH="/home/garak/.cargo/bin:$PATH"' >> /home/garak/.bashrc && \
    chown -R garak:garak /home/garak/.cargo

# Create directories for data and reports
RUN mkdir -p /app/data /app/reports

# Copy project files
COPY --chown=garak:garak . /app/

# First install base2048 with Rust support
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install -v base2048>=0.1.3 && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir ".[tests,lint,calibration,audio]" && \
    chown -R garak:garak /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/garak \
    PYTHONPATH=/app

# Copy and set permissions for entrypoint script
COPY --chown=garak:garak docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER garak

# Expose port for potential API/web interface
EXPOSE 8000

# Set health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import garak; print('Healthy')" || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
