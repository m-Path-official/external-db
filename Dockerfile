# syntax=docker/dockerfile:1

# Use a slim Python base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system deps (if any are needed), then Python deps.
# We keep layers efficient by copying only requirements first.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application source
COPY . .

# Default environment values (can be overridden by docker-compose or .env)
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000

# Expose the application port (informational)
EXPOSE 8000

# Start the app. We use python app.py so it respects APP_HOST/APP_PORT and .env
CMD ["python", "app.py"]
