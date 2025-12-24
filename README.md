# MarketHub Pro - E-commerce Platform with Dynamic Admin System

A comprehensive e-commerce platform built with Flask and SQLite, featuring a powerful dynamic admin system that allows real-time configuration management without server restarts.

## 🚀 Features

### Core E-commerce Features
- **Product Management**: Complete product catalog with categories, variants, and inventory tracking
- **User Management**: Customer accounts, vendor management, and role-based access control
- **Order Processing**: Full order lifecycle from cart to delivery
- **Payment Integration**: Support for Stripe, PayPal, and other payment gateways
- **Responsive Design**: Mobile-first design that works on all devices

### Dynamic Admin System
- **Real-time Configuration**: Change site settings without server restarts
- **Content Management**: Inline editing with version control and rollback
- **Theme Customization**: Live theme editor with CSS generation
- **User & Permission Management**: Comprehensive RBAC system
- **Analytics Dashboard**: Real-time metrics and custom reporting
- **Mobile Admin Interface**: Full admin functionality on mobile devices
- **Security Features**: Advanced session management, audit logging, and threat detection

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Authentication**: Flask-Login with session management
- **Security**: CSRF protection, input validation, audit logging
- **Admin System**: Custom-built dynamic admin interface

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ecommercesys
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python init_sqlite_db.py
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the application**
   - Main site: http://localhost:5000
   - Admin dashboard: http://localhost:5000/admin
   - Default admin login: admin@markethubpro.com / admin123

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Flask Configuration
FLASK_CONFIG=development
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///ecommerce.db
ADMIN_DATABASE_URL=sqlite:///admin.db

# Admin Configuration
ADMIN_EMAIL=admin@markethubpro.com
ADMIN_PASSWORD=admin123

# Email Configuration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Payment Configuration (optional)
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
```

### Configuration Modes

- **Development**: `FLASK_CONFIG=development` (default)
- **Testing**: `FLASK_CONFIG=testing`
- **Production**: `FLASK_CONFIG=production`

## 📊 Database Schema

The application uses SQLite with the following main tables:

- **users**: User accounts and authentication
- **roles**: Role-based access control
- **products**: Product catalog
- **categories**: Product categories
- **orders**: Order management
- **admin_settings**: Dynamic configuration
- **activity_logs**: Audit trail

## 🎨 Admin System Features

### Configuration Management
- Real-time site settings updates
- Category-based configuration organization
- Input validation and error handling
- Change broadcasting to all components

### Content Management
- Inline content editing
- Version history and rollback
- Media asset management
- Real-time publishing

### Theme Customization
- Live theme preview
- Dynamic CSS generation
- Asset management (logos, favicons)
- Mobile responsiveness validation

### User Management
- Comprehensive user CRUD operations
- Role and permission management
- Vendor application processing
- Activity audit logging

### Analytics & Reporting
- Real-time system metrics
- Custom report generation
- Data export (CSV, PDF, API)
- Performance monitoring

## � Mobitle Admin Interface

The admin system includes a fully responsive mobile interface with:

- Touch-optimized navigation
- Gesture support (swipe, long-press)
- Mobile-specific UI components
- Offline capability
- Push notifications

## 🔒 Security Features

- **Input Validation**: Comprehensive sanitization and validation
- **Session Security**: Advanced session management with anomaly detection
- **Access Control**: Granular role-based permissions
- **Audit Logging**: Complete activity tracking
- **Threat Detection**: Real-time security monitoring
- **CSRF Protection**: Cross-site request forgery prevention

## 🚀 Deployment

### Development
```bash
python run.py
```

### Production
1. Set environment variables for production
2. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 "app_sqlite:create_app('production')"
   ```

## 📁 Project Structure

```
ecommercesys/
├── admin/                  # Dynamic admin system
│   ├── api/               # Admin API endpoints
│   ├── database/          # Database configuration
│   ├── models/            # Admin data models
│   └── services/          # Admin business logic
├── static/                # Static assets
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript files
│   └── images/           # Images and icons
├── templates/             # HTML templates
│   ├── admin/            # Admin templates
│   └── ...               # Public templates
├── app_sqlite.py         # Main Flask application
├── models_sqlite.py      # SQLite database models
├── config_sqlite.py      # Configuration settings
├── run.py               # Application entry point
└── requirements.txt     # Python dependencies
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation in the `/docs` folder
- Review the admin system guide in the admin dashboard

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Advanced SEO features
- [ ] Marketplace functionality
- [ ] Mobile app API
- [ ] Advanced analytics
- [ ] Third-party integrations

---

**MarketHub Pro** - Your complete e-commerce solution with dynamic administration.