# Multi-stage build for optimized Docker image
FROM python:3.14-slim as builder

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# Stage 2: Final image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

# Copy application code
COPY . .

# Create WSGI entry point
RUN echo '#!/usr/bin/env python3\n\nfrom main import app\n\nif __name__ == "__main__":\n    app.run()' > wsgi.py

# Expose port
EXPOSE 5000

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]