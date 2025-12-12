# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .
COPY requirements-dev.txt .

# Install Python dependencies
RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["./run.sh"]