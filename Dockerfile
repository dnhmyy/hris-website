# Dockerfile (Production Ready)
FROM python:3.10-slim-bookworm

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

# Workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

COPY . .

# Create a non-root user and change ownership
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the Flask port
EXPOSE 5000

# Start command: Use Gunicorn for production
# Note: We run from the root, so the module name is backend.app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "backend.app:app"]
