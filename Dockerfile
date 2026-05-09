FROM python:3.12-slim

# Install build dependencies for native packages (numpy, scikit-learn, bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory (Railway volume mounts here)
RUN mkdir -p /data

# Railway uses $PORT env var (not always 8000)
ENV PORT=8000
EXPOSE ${PORT}

# Use shell form so $PORT gets expanded at runtime
CMD uvicorn api_server:app --host 0.0.0.0 --port $PORT
