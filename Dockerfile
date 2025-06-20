# Dockerfile for Project Scribe and Ex-Work Agents

# Use official Python image as a base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports if needed (e.g., for APIs or services)
EXPOSE 8000
EXPOSE 5000

# Dynamic entrypoint
ENTRYPOINT ["/entrypoint.sh"]
