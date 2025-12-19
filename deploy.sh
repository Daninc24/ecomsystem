#!/bin/bash

# 🚀 E-Commerce Multi-Vendor Platform - Production Deployment Script
# This script helps deploy your application to production

set -e  # Exit on any error

echo "🚀 E-Commerce Multi-Vendor Platform - Production Deployment"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Please run 'python setup.py' first."
    exit 1
fi

print_status "Virtual environment found"

# Activate virtual environment
source venv/bin/activate
print_status "Virtual environment activated"

# Check if database exists
if [ ! -f "instance/ecommerce.db" ]; then
    print_warning "Database not found. Initializing..."
    python init_data.py
    print_status "Database initialized with sample data"
else
    print_status "Database found"
fi

# Test application startup
print_info "Testing application startup..."
timeout 10s python -c "
from app import app, db, User
with app.app_context():
    db.session.execute(db.text('SELECT 1'))
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print('✅ Admin user exists')
    else:
        print('❌ Admin user not found')
" || {
    print_error "Application startup test failed"
    exit 1
}

print_status "Application startup test passed"

# Display deployment options
echo ""
echo "🚀 DEPLOYMENT OPTIONS:"
echo "====================="
echo ""
echo "1. 🌐 HEROKU (Recommended for beginners)"
echo "   - Fastest deployment"
echo "   - Automatic scaling"
echo "   - Built-in PostgreSQL"
echo ""
echo "2. 🖥️  DIGITALOCEAN DROPLET"
echo "   - More control"
echo "   - Cost-effective"
echo "   - Custom configuration"
echo ""
echo "3. ☁️  AWS EC2"
echo "   - Enterprise-grade"
echo "   - Highly scalable"
echo "   - Advanced features"
echo ""
echo "4. 🐳 DOCKER"
echo "   - Containerized deployment"
echo "   - Consistent environments"
echo "   - Easy scaling"
echo ""

# Ask user for deployment choice
echo "Which deployment option would you like to use?"
echo "1) Heroku"
echo "2) DigitalOcean"
echo "3) AWS EC2"
echo "4) Docker"
echo "5) Local Production Test"
echo "6) Exit"
echo ""
read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo ""
        print_info "HEROKU DEPLOYMENT GUIDE"
        echo "========================"
        echo ""
        echo "1. Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli"
        echo "2. Login to Heroku: heroku login"
        echo "3. Create app: heroku create your-ecommerce-app"
        echo "4. Add PostgreSQL: heroku addons:create heroku-postgresql:hobby-dev"
        echo "5. Set environment variables:"
        echo "   heroku config:set FLASK_CONFIG=production"
        echo "   heroku config:set SECRET_KEY=your-super-secret-key-here"
        echo "   heroku config:set STRIPE_SECRET_KEY=sk_live_your_stripe_key"
        echo "   heroku config:set PAYPAL_CLIENT_ID=your_paypal_client_id"
        echo "6. Deploy: git push heroku main"
        echo ""
        print_warning "Don't forget to set your payment gateway API keys!"
        ;;
    2)
        echo ""
        print_info "DIGITALOCEAN DEPLOYMENT GUIDE"
        echo "=============================="
        echo ""
        echo "1. Create Ubuntu 20.04+ droplet"
        echo "2. SSH into your server"
        echo "3. Clone your repository"
        echo "4. Follow the detailed guide in DEPLOYMENT.md"
        echo ""
        print_info "See DEPLOYMENT.md for complete DigitalOcean setup instructions"
        ;;
    3)
        echo ""
        print_info "AWS EC2 DEPLOYMENT GUIDE"
        echo "========================"
        echo ""
        echo "1. Launch EC2 instance (Ubuntu 20.04)"
        echo "2. Configure security groups (HTTP, HTTPS, SSH)"
        echo "3. SSH into your instance"
        echo "4. Follow DigitalOcean steps in DEPLOYMENT.md"
        echo "5. Optional: Use RDS for PostgreSQL"
        echo ""
        print_info "See DEPLOYMENT.md for complete AWS setup instructions"
        ;;
    4)
        echo ""
        print_info "DOCKER DEPLOYMENT"
        echo "=================="
        echo ""
        echo "Building Docker image..."
        
        # Create Dockerfile if it doesn't exist
        if [ ! -f "Dockerfile" ]; then
            cat > Dockerfile << EOF
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
EOF
            print_status "Dockerfile created"
        fi
        
        # Create docker-compose.yml if it doesn't exist
        if [ ! -f "docker-compose.yml" ]; then
            cat > docker-compose.yml << EOF
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_CONFIG=production
      - SECRET_KEY=your-super-secret-key
      - DATABASE_URL=postgresql://postgres:password@db:5432/ecommerce
    depends_on:
      - db
    volumes:
      - ./static:/app/static

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=ecommerce
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
EOF
            print_status "docker-compose.yml created"
        fi
        
        echo ""
        echo "To deploy with Docker:"
        echo "1. docker-compose up -d"
        echo "2. docker-compose exec web python init_data.py"
        echo "3. Visit http://localhost:5000"
        ;;
    5)
        echo ""
        print_info "STARTING LOCAL PRODUCTION TEST"
        echo "==============================="
        echo ""
        print_warning "Setting FLASK_CONFIG=production for this test"
        
        # Install gunicorn if not present
        pip install gunicorn
        
        echo ""
        print_status "Starting production server on http://localhost:8000"
        print_info "Press Ctrl+C to stop the server"
        echo ""
        
        # Set production environment
        export FLASK_CONFIG=production
        export SECRET_KEY=test-production-secret-key-change-in-real-production
        
        # Start with gunicorn
        gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
        ;;
    6)
        print_info "Deployment cancelled"
        exit 0
        ;;
    *)
        print_error "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
print_status "Deployment guide completed!"
print_info "For detailed instructions, see DEPLOYMENT.md"
print_info "For production readiness assessment, see PRODUCTION_READINESS_ASSESSMENT.md"
echo ""
print_warning "IMPORTANT: Remember to set your production SECRET_KEY and payment API keys!"
echo ""