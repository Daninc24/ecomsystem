#!/bin/bash

echo "🚀 Starting Enhanced E-Commerce Application..."
echo "=============================================="

# Activate virtual environment
source venv/bin/activate

# Check if database exists, if not create it
if [ ! -f "ecommerce.db" ]; then
    echo "📦 Database not found. Creating database..."
    python create_db.py
    python init_data.py
fi

echo "🌐 Starting Flask application..."
echo "Access the application at: http://localhost:5000"
echo ""
echo "🔑 Login Credentials:"
echo "Admin: admin/admin123"
echo "User: user/user123"
echo "Vendors: techstore/vendor123, homestyle/vendor123, fitnessgear/vendor123"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=============================================="

python app.py