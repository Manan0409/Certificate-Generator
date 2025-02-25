FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for image processing and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    fontconfig \
    fonts-liberation \
    fonts-dejavu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p uploads/fonts certificates \
    && chmod -R 777 uploads certificates

# Create error template files if they don't exist
RUN mkdir -p templates \
    && echo "<h1>Page Not Found</h1><p>The requested page was not found.</p><a href='/'>Go Home</a>" > templates/404.html \
    && echo "<h1>Server Error</h1><p>An internal server error occurred.</p><a href='/'>Go Home</a>" > templates/500.html

# Expose port (Render will use PORT env var)
ENV PORT=10000
EXPOSE $PORT

# Run the application with gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT app:app
