FROM python:3.14-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY templates/ ./templates/

# Set the entrypoint to run the main application
CMD ["python", "main.py"]