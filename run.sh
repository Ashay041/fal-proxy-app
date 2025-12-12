#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file with your FAL_KEY:"
    exit 1
fi

# Build and run with Docker
echo "Building Docker image..."
docker build -t fal-proxy .

echo "Starting fal-proxy..."
docker run -p 8000:8000 --env-file .env fal-proxy