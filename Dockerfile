FROM python:3.14-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY templates/ ./templates/

# Install wsgy
RUN pip install gunicorn

# Expose port
EXPOSE 5000

# Run the application with gunicorn (WSGI)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]