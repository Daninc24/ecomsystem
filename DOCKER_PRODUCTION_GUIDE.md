# 🐳 Docker Production Deployment Guide

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Clone and setup
git clone <your-repo> markethub-pro
cd markethub-pro

# 2. Configure environment
cp .env.example .env
# Edit .env with your production values

# 3. Deploy with Docker
./docker-deploy.sh

# 4. Access your store
open https://localhost
```

## 📋 Prerequisites

### System Requirements
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: Minimum 10GB free space
- **OS**: Linux, macOS, or Windows with WSL2

### Domain & SSL
- Domain name pointed to your server
- SSL certificate (Let's Encrypt recommended)
- DNS A record configured

## 🔧 Configuration

### 1. Environment Variables

Copy and customize the environment file:
```bash
cp .env.example .env
```

**Critical Variables** (Must Change):
```bash
# Security
SECRET_KEY=your-super-secure-secret-key-min-32-chars
MONGO_ROOT_PASSWORD=strong-mongodb-password-change-this
REDIS_PASSWORD=strong-redis-password-change-this

# Domain
DOMAIN_NAME=yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
```

**Payment Gateways** (Configure as needed):
```bash
# Stripe (https://stripe.com)
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key

# PayPal (https://developer.paypal.com)
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_MODE=live

# M-Pesa (Safaricom Kenya)
MPESA_CONSUMER_KEY=your_mpesa_consumer_key
MPESA_CONSUMER_SECRET=your_mpesa_consumer_secret
MPESA_SHORTCODE=your_mpesa_shortcode
MPESA_PASSKEY=your_mpesa_passkey
MPESA_ENVIRONMENT=production
```

### 2. SSL Certificates

**Option A: Let's Encrypt (Recommended)**
```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*.pem
```

**Option B: Self-Signed (Development/Testing)**
```bash
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
```

## 🚀 Deployment

### Automated Deployment
```bash
./docker-deploy.sh
```

### Manual Deployment
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Initialize database
docker-compose exec web python init_mongo_data.py

# Check status
docker-compose ps
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │     Redis       │
│  (Load Balancer)│    │   (Sessions)    │
│   Port 80/443   │    │   Port 6379     │
└─────────────────┘    └─────────────────┘
         │                       │
         ▼                       │
┌─────────────────┐              │
│   Flask App     │◄─────────────┘
│  (MarketHub)    │
│   Port 5000     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│    MongoDB      │
│  (Database)     │
│   Port 27017    │
└─────────────────┘
```

### Services
- **nginx**: Reverse proxy, SSL termination, static files
- **web**: Flask application (MarketHub Pro)
- **mongo**: MongoDB database
- **redis**: Session storage and caching

## 🔍 Monitoring & Maintenance

### Health Checks
```bash
# Application health
curl https://yourdomain.com/health

# Service status
docker-compose ps

# View logs
docker-compose logs -f web
```

### Database Management
```bash
# MongoDB shell
docker-compose exec mongo mongosh -u admin -p

# Database backup
docker-compose exec mongo mongodump --uri="mongodb://admin:password@localhost:27017/ecommerce" --out=/backup

# Restore backup
docker-compose exec mongo mongorestore --uri="mongodb://admin:password@localhost:27017/ecommerce" /backup/ecommerce
```

### Log Management
```bash
# View application logs
docker-compose logs -f web

# View nginx logs
docker-compose logs -f nginx

# View all logs
docker-compose logs -f

# Log rotation (add to crontab)
0 2 * * * docker system prune -f
```

## 🔒 Security Configuration

### Firewall Setup (Ubuntu/Debian)
```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Check status
sudo ufw status
```

### SSL Security Test
```bash
# Test SSL configuration
curl -I https://yourdomain.com

# Check SSL rating
# Visit: https://www.ssllabs.com/ssltest/
```

### Security Headers Verification
```bash
curl -I https://yourdomain.com | grep -E "(X-|Strict|Content-Security)"
```

## 📊 Performance Optimization

### Resource Limits
Edit `docker-compose.yml` to add resource limits:
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Database Optimization
```bash
# MongoDB performance tuning
docker-compose exec mongo mongosh --eval "
db.adminCommand('setParameter', {
  'wiredTigerConcurrentReadTransactions': 128,
  'wiredTigerConcurrentWriteTransactions': 128
})
"
```

### Nginx Optimization
The included `nginx.conf` already includes:
- Gzip compression
- Static file caching
- Rate limiting
- Security headers

## 🔄 Updates & Maintenance

### Application Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose build web
docker-compose up -d web

# Check health
curl https://yourdomain.com/health
```

### Database Migrations
```bash
# Run database migrations
docker-compose exec web python -c "
from app_mongo import app, mongo
with app.app_context():
    # Add migration code here
    pass
"
```

### Backup Strategy
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T mongo mongodump --uri="mongodb://admin:${MONGO_ROOT_PASSWORD}@localhost:27017/ecommerce" --archive | gzip > backups/mongo_${DATE}.gz
docker run --rm -v $(pwd)/static:/data alpine tar czf /data/../backups/static_${DATE}.tar.gz -C /data .
EOF

chmod +x backup.sh

# Add to crontab for daily backups
echo "0 2 * * * /path/to/your/app/backup.sh" | crontab -
```

## 🚨 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check logs
docker-compose logs

# Check disk space
df -h

# Check memory
free -h
```

**Database connection errors:**
```bash
# Check MongoDB status
docker-compose exec mongo mongosh --eval "db.adminCommand('ping')"

# Reset MongoDB
docker-compose restart mongo
```

**SSL certificate issues:**
```bash
# Check certificate validity
openssl x509 -in ssl/cert.pem -text -noout

# Renew Let's Encrypt certificate
sudo certbot renew
```

**Performance issues:**
```bash
# Check resource usage
docker stats

# Check database performance
docker-compose exec mongo mongosh --eval "db.stats()"
```

### Emergency Procedures

**Complete restart:**
```bash
docker-compose down
docker-compose up -d
```

**Reset database (⚠️ Data Loss):**
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec web python init_mongo_data.py
```

**Rollback deployment:**
```bash
git checkout previous-commit
docker-compose build
docker-compose up -d
```

## 📈 Scaling

### Horizontal Scaling
```yaml
# docker-compose.yml
services:
  web:
    deploy:
      replicas: 3
    
  nginx:
    depends_on:
      - web
```

### Load Balancer Configuration
```nginx
# nginx.conf
upstream app {
    server web_1:5000;
    server web_2:5000;
    server web_3:5000;
}
```

### Database Scaling
- Use MongoDB Atlas for managed scaling
- Implement read replicas
- Consider sharding for large datasets

## 🎯 Production Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Domain DNS configured
- [ ] Firewall rules set
- [ ] Backup strategy implemented

### Post-Deployment
- [ ] Health check passes
- [ ] SSL test passes (A+ rating)
- [ ] Security headers verified
- [ ] Performance test completed
- [ ] Monitoring configured

### Ongoing Maintenance
- [ ] Daily backup verification
- [ ] Weekly security updates
- [ ] Monthly performance review
- [ ] Quarterly security audit

## 📞 Support

### Useful Commands
```bash
# Quick status check
docker-compose ps && curl -s https://yourdomain.com/health | jq

# Resource usage
docker stats --no-stream

# Disk usage
docker system df

# Clean up
docker system prune -f
```

### Log Locations
- Application logs: `docker-compose logs web`
- Nginx logs: `docker-compose logs nginx`
- MongoDB logs: `docker-compose logs mongo`
- System logs: `/var/log/syslog`

---

## 🎉 Success!

Your MarketHub Pro e-commerce platform is now running in production with:

✅ **High Performance**: Nginx + Gunicorn + MongoDB  
✅ **Security**: SSL, Security Headers, Rate Limiting  
✅ **Scalability**: Docker containers, horizontal scaling ready  
✅ **Monitoring**: Health checks, comprehensive logging  
✅ **Backup**: Automated backup strategy  

**Admin Access**: https://yourdomain.com/admin/dashboard  
**Default Credentials**: admin / admin123 (⚠️ Change immediately!)

Happy selling! 🛒💰