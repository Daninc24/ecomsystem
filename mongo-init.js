// MongoDB initialization script for Docker
db = db.getSiblingDB('ecommerce');

// Create application user
db.createUser({
  user: 'ecommerce_user',
  pwd: 'ecommerce_password_change_in_production',
  roles: [
    {
      role: 'readWrite',
      db: 'ecommerce'
    }
  ]
});

// Create indexes for better performance
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.products.createIndex({ "basic_info.name": "text", "basic_info.description": "text" });
db.products.createIndex({ "basic_info.category": 1 });
db.products.createIndex({ "pricing.price": 1 });
db.products.createIndex({ "status": 1 });
db.orders.createIndex({ "user_id": 1 });
db.orders.createIndex({ "created_at": -1 });
db.cart.createIndex({ "user_id": 1 });
db.reviews.createIndex({ "product_id": 1 });

print('MongoDB initialization completed successfully!');