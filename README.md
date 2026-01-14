# SpendLens UI

A web application for visualizing and managing spending data.

## Features

- Interactive spending charts and analytics
- Category-based filtering
- Admin interface for record management
- Responsive design for all devices

## Architecture Support

This application builds and runs on:
- AMD64 (x86_64) architecture
- ARM64 (ARM) architecture

## Getting Started

### Prerequisites

- Docker
- PostgreSQL database with required tables
- Environment variables configured

### Running the Application

```bash
# Build and run using Docker
docker build -t spendlens-ui .
docker run -p 5000:5000 spendlens-ui
```

## Development

The application is built with Python Flask and uses:
- PostgreSQL for data storage
- Environment variables for configuration
- Responsive web templates

## Docker Builds

The Docker image is automatically built for both AMD64 and ARM64 architectures using GitHub Actions.

## License

This project is licensed under the MIT License.