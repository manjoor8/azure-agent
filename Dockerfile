# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=6003

# Set work directory
WORKDIR /app

# Install dependencies and curl for healthchecks
COPY requirements.txt .
RUN apt-get update && apt-get install -y curl && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Expose the port
EXPOSE 6003

# Run the application
CMD ["python", "agent.py"]
