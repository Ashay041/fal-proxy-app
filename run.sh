#!/bin/bash

# Stop existing containers gracefully (keeps volumes)
echo "Stopping existing containers..."
docker-compose down
# Start services with rebuild
echo "Starting services with docker-compose..."
docker-compose up --build