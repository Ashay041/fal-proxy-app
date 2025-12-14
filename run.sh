#!/bin/bash

# Run docker-compose
echo "Starting services with docker-compose..."
docker-compose up --build

# TODO: remove this after docker-compose is ready
# Rebuild and run:
# docker-compose down
# docker-compose up --build
