# E-Commerce Flask Application

A complete, responsive E-commerce multitask website built with Python Flask, HTML, CSS, and Vanilla JavaScript.

## Features

### 🛍️ Core E-commerce Features
- **Product Catalog**: Browse products with search, filter, and sort functionality
- **Shopping Cart**: Add/remove items, update quantities with real-time calculations
- **Checkout System**: Complete order placement with form validation
- **Order Management**: Track order history and status
- **User Authentication**: Secure registration and login system

### 👨‍💼 Admin Dashboard
- **Product Management**: Add, edit, delete products
- **Order Management**: View and update order status
- **User Management**: View registered users
- **Dashboard Analytics**: Overview of store statistics

### 🎨 User Experience
- **Responsive Design**: Mobile-first approach, works on all devices
- **Real-time Updates**: Dynamic cart updates without page refresh
- **Form Validation**: Client-side and server-side validation
- **Loading States**: Visual feedback for user actions
- **Notifications**: Success/error messages for user actions

## Technology Stack

- **Backend**: Python Flask with SQLAlchemy ORM
- **Database**: SQLite (easily configurable to PostgreSQL)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Authentication**: Session-based with bcrypt password hashing
- **Security**: CSRF protection, input validation, SQL injection prevention

## Project Structure

```
ecommerce-flask/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── init_data.py          # Database initialization script
├── setup.py              # Automated setup script
├── README.md             # This file
├── ecommerce.db          # SQLite database (created after setup)
├── static/
│   ├── css/
│   │   └── style.css     # Main stylesheet
│   ├── js/
│   │   └── main.js       # JavaScript functionality
│   └── images/           # Static images
└── templates/
    ├── base.html         # Base template
    ├── index.html        # Homepage
    ├── login.html        # Login page
    ├── register.html     # Registration page
    ├── products.html     # Product catalog
    ├── product_detail.html # Product details
    ├── cart.html         # Shopping cart
    ├── checkout.html     # Checkout page
    ├── orders.html       # Order history
    ├── profile.html      # User profile
    ├── contact.html      # Contact page
    └── admin/
        ├── dashboard.html    # Admin dashboard
        ├── products.html     # Product management
        ├── add_product.html  # Add product form
        ├── edit_product.html # Edit product form
        └── orders.html       # Order management
```

## Database Schema

### Users Table
- `id` (Primary Key)
- `username` (Unique)
- `email` (Unique)
- `password` (Hashed)
- `role` (admin/user)
- `created_at`

### Products Table
- `id` (Primary Key)
- `name`
- `description`
- `price`
- `stock`
- `category`
- `image_url`

### Cart Table
- `id` (Primary Key)
- `user_id` (Foreign Key)
- `product_id` (Foreign Key)
- `quantity`

### Orders Table
- `id` (Primary Key)
- `user_id` (Foreign Key)
- `total_price`
- `order_status`
- `created_at`

### OrderItems Table
- `id` (Primary Key)
- `order_id` (Foreign Key)
- `product_id` (Foreign Key)
- `quantity`
- `price`

## Quick Start

### Option 1: Automated Setup (Recommended)

1. **Clone or download the project files**

2. **Run the setup script**:
   ```bash
   python setup.py
   ```
   
3. **Start the application**:
   ```bash
   python app.py
   ```

4. **Open your browser** to `http://localhost:5000`

### Option 2: Manual Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the database**:
   ```bash
   python init_data.py
   ```

3. **Start the application**:
   ```bash
   python app.py
   ```

## Default Login Credentials

After setup, you can use these accounts:

**Admin Account**:
- Username: `admin`
- Password: `admin123`
- Access: Full admin dashboard and user features

**Regular User Account**:
- Username: `user`
- Password: `user123`
- Access: Shopping and user features only

## Usage Guide

### For Customers

1. **Browse Products**: Visit the Products page to see all available items
2. **Search & Filter**: Use the search bar and category filters to find specific products
3. **Product Details**: Click on any product to see detailed information
4. **Add to Cart**: Click "Add to Cart" on product pages (requires login)
5. **Manage Cart**: View and modify your cart items
6. **Checkout**: Complete your purchase with the checkout form
7. **Track Orders**: View your order history in the Orders section

### For Administrators

1. **Access Admin Panel**: Login with admin credentials and click "Admin" in navigation
2. **Manage Products**: Add, edit, or delete products from the catalog
3. **Process Orders**: View all orders and update their status
4. **Monitor Analytics**: View store statistics on the dashboard

## API Endpoints

### Authentication
- `GET/POST /register` - User registration
- `GET/POST /login` - User login
- `GET /logout` - User logout

### Products
- `GET /` - Homepage with featured products
- `GET /products` - Product catalog with search/filter
- `GET /product/<id>` - Product details

### Cart & Orders
- `POST /add_to_cart` - Add item to cart (JSON)
- `GET /cart` - View shopping cart
- `POST /update_cart` - Update cart item quantity (JSON)
- `POST /remove_from_cart` - Remove item from cart (JSON)
- `GET /checkout` - Checkout page
- `POST /place_order` - Place order (JSON)
- `GET /orders` - User order history

### Admin (Admin access required)
- `GET /admin` - Admin dashboard
- `GET /admin/products` - Product management
- `GET/POST /admin/add_product` - Add new product
- `GET/POST /admin/edit_product/<id>` - Edit product
- `GET /admin/delete_product/<id>` - Delete product
- `GET /admin/orders` - Order management
- `POST /admin/update_order_status` - Update order status (JSON)

## Security Features

- **Password Hashing**: Uses Werkzeug's bcrypt for secure password storage
- **Session Management**: Secure session-based authentication
- **Input Validation**: Both client-side and server-side validation
- **SQL Injection Prevention**: SQLAlchemy ORM prevents SQL injection
- **Role-based Access**: Admin and user roles with appropriate permissions

## Customization

### Adding New Product Categories
1. Add products with new category names through the admin panel
2. Categories are automatically populated in the filter dropdown

### Modifying Styles
- Edit `static/css/style.css` to customize the appearance
- The CSS uses CSS Grid and Flexbox for responsive layouts
- Color scheme and spacing can be easily modified

### Adding New Features
- Follow the existing Flask blueprint pattern
- Add new routes in `app.py`
- Create corresponding HTML templates
- Add JavaScript functionality in `static/js/main.js`

## Troubleshooting

### Common Issues

1. **Database errors**: Delete `ecommerce.db` and run `python init_data.py` again
2. **Port already in use**: Change the port in `app.py`: `app.run(debug=True, port=5001)`
3. **Permission errors**: Make sure you have write permissions in the project directory
4. **Module not found**: Ensure all dependencies are installed: `pip install -r requirements.txt`

### Development Mode

The application runs in debug mode by default. For production:

1. Set `debug=False` in `app.py`
2. Change the secret key to a secure random value
3. Use a production database (PostgreSQL recommended)
4. Set up proper web server (nginx + gunicorn)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the code comments for implementation details
3. Create an issue with detailed error information

---

**Enjoy building your E-commerce store!** 🚀