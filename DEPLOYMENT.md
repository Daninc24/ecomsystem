# Deployment Guide

This guide covers deploying the E-commerce Flask application to various platforms.

## Local Development

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd ecommerce-flask

# Run automated setup
python setup.py

# Start the application
python app.py
```

### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_data.py

# Start development server
python app.py
```

## Production Deployment

### 1. Heroku Deployment

#### Prerequisites
- Heroku CLI installed
- Git repository

#### Steps
1. **Create Heroku app**:
   ```bash
   heroku create your-ecommerce-app
   ```

2. **Add PostgreSQL addon**:
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set FLASK_CONFIG=production
   heroku config:set SECRET_KEY=your-super-secret-key-here
   ```

4. **Create Procfile**:
   ```
   web: gunicorn app:app
   release: python init_data.py
   ```

5. **Update requirements.txt**:
   ```
   Flask==2.3.3
   Flask-SQLAlchemy==3.0.5
   Werkzeug==2.3.7
   gunicorn==21.2.0
   psycopg2-binary==2.9.7
   ```

6. **Deploy**:
   ```bash
   git add .
   git commit -m "Deploy to Heroku"
   git push heroku main
   ```

### 2. DigitalOcean Droplet

#### Prerequisites
- Ubuntu 20.04+ server
- Domain name (optional)

#### Steps
1. **Update system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python and dependencies**:
   ```bash
   sudo apt install python3 python3-pip python3-venv nginx postgresql postgresql-contrib -y
   ```

3. **Create application user**:
   ```bash
   sudo adduser ecommerce
   sudo usermod -aG sudo ecommerce
   su - ecommerce
   ```

4. **Clone and setup application**:
   ```bash
   git clone <repository-url> ecommerce-app
   cd ecommerce-app
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn psycopg2-binary
   ```

5. **Setup PostgreSQL**:
   ```bash
   sudo -u postgres createuser --interactive
   sudo -u postgres createdb ecommerce
   ```

6. **Configure environment**:
   ```bash
   export FLASK_CONFIG=production
   export SECRET_KEY=your-super-secret-key
   export DATABASE_URL=postgresql://username:password@localhost/ecommerce
   ```

7. **Initialize database**:
   ```bash
   python init_data.py
   ```

8. **Create systemd service** (`/etc/systemd/system/ecommerce.service`):
   ```ini
   [Unit]
   Description=Gunicorn instance to serve E-commerce app
   After=network.target

   [Service]
   User=ecommerce
   Group=www-data
   WorkingDirectory=/home/ecommerce/ecommerce-app
   Environment="PATH=/home/ecommerce/ecommerce-app/venv/bin"
   Environment="FLASK_CONFIG=production"
   Environment="SECRET_KEY=your-super-secret-key"
   Environment="DATABASE_URL=postgresql://username:password@localhost/ecommerce"
   ExecStart=/home/ecommerce/ecommerce-app/venv/bin/gunicorn --workers 3 --bind unix:ecommerce.sock -m 007 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

9. **Configure Nginx** (`/etc/nginx/sites-available/ecommerce`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com www.your-domain.com;

       location / {
           include proxy_params;
           proxy_pass http://unix:/home/ecommerce/ecommerce-app/ecommerce.sock;
       }

       location /static {
           alias /home/ecommerce/ecommerce-app/static;
       }
   }
   ```

10. **Enable and start services**:
    ```bash
    sudo systemctl start ecommerce
    sudo systemctl enable ecommerce
    sudo ln -s /etc/nginx/sites-available/ecommerce /etc/nginx/sites-enabled
    sudo systemctl restart nginx
    ```

### 3. AWS EC2 Deployment

Similar to DigitalOcean but with AWS-specific configurations:

1. **Launch EC2 instance** (Ubuntu 20.04)
2. **Configure security groups** (HTTP, HTTPS, SSH)
3. **Follow DigitalOcean steps** for application setup
4. **Optional**: Use RDS for PostgreSQL database
5. **Optional**: Use S3 for static file storage

### 4. Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

#### docker-compose.yml
```yaml
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
```

#### Deploy with Docker
```bash
# Build and run
docker-compose up -d

# Initialize database
docker-compose exec web python init_data.py
```

## Environment Variables

### Required for Production
- `FLASK_CONFIG=production`
- `SECRET_KEY=your-super-secret-key`
- `DATABASE_URL=postgresql://user:pass@host:port/dbname`

### Optional
- `MAIL_SERVER=smtp.gmail.com`
- `MAIL_PORT=587`
- `MAIL_USERNAME=your-email@gmail.com`
- `MAIL_PASSWORD=your-app-password`

## SSL/HTTPS Setup

### Using Let's Encrypt (Certbot)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Database Migration

### From SQLite to PostgreSQL
```bash
# Export SQLite data
sqlite3 ecommerce.db .dump > backup.sql

# Import to PostgreSQL (after editing SQL file)
psql -U username -d ecommerce -f backup.sql
```

## Monitoring and Maintenance

### Log Files
- Application logs: `/var/log/ecommerce/`
- Nginx logs: `/var/log/nginx/`
- System logs: `journalctl -u ecommerce`

### Backup Strategy
```bash
# Database backup
pg_dump ecommerce > backup_$(date +%Y%m%d).sql

# File backup
tar -czf static_backup_$(date +%Y%m%d).tar.gz static/
```

### Performance Monitoring
- Use tools like New Relic, DataDog, or Prometheus
- Monitor database performance
- Set up alerts for downtime

## Security Checklist

- [ ] Use HTTPS in production
- [ ] Set secure session cookies
- [ ] Use strong SECRET_KEY
- [ ] Keep dependencies updated
- [ ] Use environment variables for secrets
- [ ] Configure firewall properly
- [ ] Regular security updates
- [ ] Database access restrictions
- [ ] Input validation and sanitization
- [ ] Rate limiting (consider using Flask-Limiter)

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Check DATABASE_URL format
   - Verify database server is running
   - Check firewall settings

2. **Static files not loading**:
   - Verify Nginx configuration
   - Check file permissions
   - Ensure static directory exists

3. **Application won't start**:
   - Check systemd service logs
   - Verify Python virtual environment
   - Check for missing dependencies

4. **Performance issues**:
   - Monitor database queries
   - Check server resources
   - Consider adding caching (Redis)

### Useful Commands
```bash
# Check service status
sudo systemctl status ecommerce

# View logs
sudo journalctl -u ecommerce -f

# Restart services
sudo systemctl restart ecommerce nginx

# Test configuration
nginx -t
```

## Scaling Considerations

### Horizontal Scaling
- Use load balancer (nginx, HAProxy)
- Multiple application instances
- Shared database and session storage

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Add caching layer (Redis/Memcached)

### Database Scaling
- Read replicas
- Connection pooling
- Query optimization

---

For specific deployment questions or issues, refer to the platform-specific documentation or create an issue in the repository.