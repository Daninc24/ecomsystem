# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Setup Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Initialize Database
```bash
# Initialize database with sample data
python init_data.py
```

### Step 3: Run Application
```bash
# Start the development server
python app.py

# Open browser to: http://localhost:5000
```

## 🔑 Default Login Credentials

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**User Account:**
- Username: `user`
- Password: `user123`

## 📱 Test the Application

1. **Browse Products**: Visit http://localhost:5000
2. **User Features**: Register/Login, add to cart, checkout
3. **Admin Features**: Login as admin, manage products and orders

## 🛠️ Development Commands

```bash
# Activate virtual environment (always run first)
source venv/bin/activate

# Start development server
python app.py

# Reset database (if needed)
rm ecommerce.db
python init_data.py

# Add new sample products
python init_data.py
```

## 📁 Project Structure

```
ecommerce-flask/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── init_data.py        # Database initialization
├── requirements.txt    # Python dependencies
├── ecommerce.db       # SQLite database
├── static/            # CSS, JS, images
├── templates/         # HTML templates
└── venv/             # Virtual environment
```

## 🔧 Troubleshooting

**Database Issues:**
```bash
# Delete and recreate database
rm ecommerce.db
python init_data.py
```

**Port Already in Use:**
```bash
# Change port in app.py (last line)
app.run(debug=True, port=5001)
```

**Module Not Found:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

## 🌟 Features to Test

- ✅ User registration and login
- ✅ Product browsing and search
- ✅ Shopping cart functionality
- ✅ Order placement and tracking
- ✅ Admin product management
- ✅ Admin order management
- ✅ Responsive design (mobile/desktop)

## 📚 Next Steps

1. **Customize**: Edit templates and CSS to match your brand
2. **Deploy**: Follow DEPLOYMENT.md for production setup
3. **Extend**: Add new features like reviews, wishlist, etc.

---

**Need Help?** Check README.md for detailed documentation or TESTING_CHECKLIST.md for comprehensive testing guide.