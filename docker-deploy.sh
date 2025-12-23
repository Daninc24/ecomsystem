#!/bin/bash

# 🐳 Docker Production Deployment Script
# MarketHub Pro E-Commerce Platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo "🐳 MarketHub Pro - Docker Production Deployment"
echo "=============================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are installed"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_info "Please edit .env file with your production values before continuing."
    echo ""
    echo "Required environment variables:"
    echo "- SECRET_KEY (generate a strong secret key)"
    echo "- MONGO_ROOT_PASSWORD (MongoDB root password)"
    echo "- REDIS_PASSWORD (Redis password)"
    echo "- Payment gateway credentials (Stripe, PayPal, M-Pesa)"
    echo ""
    read -p "Have you updated the .env file with production values? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        print_error "Please update .env file first, then run this script again."
        exit 1
    fi
fi

print_status ".env file found"

# Create SSL directory if it doesn't exist
if [ ! -d "ssl" ]; then
    mkdir -p ssl
    print_info "SSL directory created. Please add your SSL certificates:"
    echo "  - ssl/cert.pem (SSL certificate)"
    echo "  - ssl/key.pem (SSL private key)"
    echo ""
    echo "For development/testing, you can generate self-signed certificates:"
    echo "  openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes"
    echo ""
    read -p "Do you have SSL certificates in place? (y/N): " ssl_confirm
    if [[ $ssl_confirm != [yY] ]]; then
        print_warning "Generating self-signed certificates for testing..."
        openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        print_status "Self-signed certificates generated"
    fi
fi

# Create logs directory
mkdir -p logs
print_status "Logs directory created"

# Build and start services
print_info "Building Docker images..."
docker-compose build

print_info "Starting services..."
docker-compose up -d

# Wait for services to be ready
print_info "Waiting for services to start..."
sleep 30

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    print_status "Services are running"
else
    print_error "Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Initialize database with sample data
print_info "Initializing database..."
docker-compose exec -T web python init_mongo_data.py

# Run health check
print_info "Running health check..."
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    print_status "Health check passed"
else
    print_warning "Health check failed. The application might still be starting up."
fi

echo ""
print_status "🚀 Deployment completed successfully!"
echo ""
print_info "Your MarketHub Pro e-commerce platform is now running:"
echo "  🌐 HTTP:  http://localhost"
echo "  🔒 HTTPS: https://localhost"
echo "  📊 Admin: https://localhost/admin/dashboard"
echo ""
print_info "Default admin credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
print_warning "IMPORTANT: Change the admin password immediately!"
echo ""
print_info "Useful commands:"
echo "  📋 View logs:     docker-compose logs -f"
echo "  🔄 Restart:       docker-compose restart"
echo "  🛑 Stop:          docker-compose down"
echo "  🗑️  Clean up:      docker-compose down -v"
echo ""
print_info "For production deployment, ensure you:"
echo "  1. Use real SSL certificates"
echo "  2. Set strong passwords in .env"
echo "  3. Configure your domain name"
echo "  4. Set up monitoring and backups"
echo ""
print_status "Happy selling! 🛒"