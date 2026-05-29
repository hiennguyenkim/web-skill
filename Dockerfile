# Start from the official Playwright Jammy container image
# This comes preinstalled with python, node, and browser execution dependencies
FROM mcr.microsoft.com/playwright:v1.44.0-noble

# Set working directory
WORKDIR /usr/src/app

# Install Python 3 and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application source code
COPY core/ ./core/
COPY skills/ ./skills/
COPY apps/ ./apps/
COPY cli.py ./

# Expose port for FastAPI server
EXPOSE 8000

# Default entry point command is to run the FastAPI HTTP server
CMD ["python3", "cli.py", "serve", "--port", "8000", "--host", "0.0.0.0"]
