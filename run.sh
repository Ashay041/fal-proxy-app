#!/bin/bash

# # Check if .env file exists
# if [ ! -f .env ]; then
#     echo "Error: .env file not found!"
#     echo "Please create a .env file with:"
#     echo ""
#     echo "FAL_KEY=your_key_here"
#     echo ""
#     exit 1
# fi

# Run docker-compose
echo "Starting services with docker-compose..."
docker-compose up --build

# TODO: remove comment
# dev commands for docker compose
# Run in background (detached mode)
# docker-compose up -d

# # Stop everything
# docker-compose down

# # Rebuild and start (if you changed code)
# docker-compose up --build

# # View logs
# docker-compose logs -f

# # Stop without removing containers
# docker-compose stop

# # Start stopped containers
# docker-compose start