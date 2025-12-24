#!/bin/bash

# MarketHub Pro - Production Deployment Script
# This script helps deploy the application to production

set -e  # Exit on any error

echo "🚀 MarketHub Pro - Production Deployment"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your production settings!"
    echo "   - Set FLASK_CONFIG=production"
    echo "   - Set a strong SECRET_KEY"
    echo "   - Configure email settings"
    echo "   - Set admin credentials"
fi

# Initialize database
echo "🗄️  Initializing database..."
python init_sqlite_db.py

# Create logs directory
echo "📋 Creating logs directory..."
mkdir -p logs

# Set proper permissions
echo "🔒 Setting file permissions..."
chmod +x run.py
chmod +x deploy_production.sh

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "📦 Installing Gunicorn for production..."
    pip install gunicorn
fi

echo ""
echo "✅ Deployment preparation complete!"
echo ""
echo "🚀 To start the production server:"
echo "   gunicorn -w 4 -b 0.0.0.0:5000 'app_sqlite:create_app(\"production\")'"
echo ""
echo "🔧 Or start in development mode:"
echo "   python run.py"
echo ""
echo "🌐 Access points:"
echo "   • Main site: http://localhost:5000"
echo "   • Admin dashboard: http://localhost:5000/admin"
echo "   • API health: http://localhost:5000/api/admin/health"
echo ""
echo "🔑 Default admin credentials:"
echo "   • Email: admin@markethubpro.com"
echo "   • Password: admin123"
echo "   ⚠️  CHANGE THESE IN PRODUCTION!"
echo ""
echo "📖 For detailed deployment guide, see PRODUCTION_READINESS_REPORT.md"