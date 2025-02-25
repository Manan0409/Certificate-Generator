FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libjpeg-dev \
    fontconfig \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories if they don't exist
RUN mkdir -p uploads/fonts certificates

# Expose port (Render will actually use PORT env var)
ENV PORT=10000
EXPOSE $PORT

# Run the application with gunicorn, binding to PORT env var
CMD gunicorn --bind 0.0.0.0:$PORT app:app