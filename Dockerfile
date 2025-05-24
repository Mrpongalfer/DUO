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
    pip install -r requirements.txt

# Expose ports if needed (e.g., for APIs or services)
EXPOSE 8000

# Default command
CMD ["python3", "scribe0.py"]
