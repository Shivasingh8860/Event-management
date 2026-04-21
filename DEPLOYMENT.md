# Production Deployment Guide

This guide helps you deploy the College Event Management System to a production environment.

## Pre-Deployment Checklist

- [ ] Change default admin credentials
- [ ] Configure SMTP for email notifications
- [ ] Set up SSL/HTTPS certificate
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Set DEBUG=False in production
- [ ] Generate a strong SECRET_KEY
- [ ] Review and configure firewall rules
- [ ] Set up regular database backups
- [ ] Configure logging and monitoring

## Deployment Options

### Option 1: Using Gunicorn (Recommended)

1. **Install Gunicorn**:
   ```bash
   pip install gunicorn
   ```

2. **Create a WSGI entry point** (`wsgi.py`):
   ```python
   from app import app
   
   if __name__ == "__main__":
       app.run()
   ```

3. **Run with Gunicorn**:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```

### Option 2: Using uWSGI

1. **Install uWSGI**:
   ```bash
   pip install uwsgi
   ```

2. **Create uWSGI config** (`uwsgi.ini`):
   ```ini
   [uwsgi]
   module = wsgi:app
   master = true
   processes = 4
   socket = /tmp/events.sock
   chmod-socket = 660
   vacuum = true
   die-on-term = true
   ```

3. **Run uWSGI**:
   ```bash
   uwsgi --ini uwsgi.ini
   ```

## Nginx Configuration

Create `/etc/nginx/sites-available/college-events`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /path/to/your/app/static;
        expires 30d;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/college-events /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/HTTPS Setup with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## PostgreSQL Database Setup

1. **Install PostgreSQL**:
   ```bash
   sudo apt install postgresql postgresql-contrib
   ```

2. **Create database and user**:
   ```sql
   sudo -u postgres psql
   CREATE DATABASE college_events;
   CREATE USER events_user WITH PASSWORD 'strong_password';
   GRANT ALL PRIVILEGES ON DATABASE college_events TO events_user;
   ```

3. **Update app.py**:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://events_user:strong_password@localhost/college_events'
   ```

4. **Install psycopg2**:
   ```bash
   pip install psycopg2-binary
   ```

## Environment Variables

Create `/etc/environment` or use `.env` file:

```bash
export SECRET_KEY='your-generated-secret-key'
export DATABASE_URL='postgresql://user:pass@localhost/dbname'
export MAIL_USERNAME='your-email@domain.com'
export MAIL_PASSWORD='your-app-password'
export FLASK_ENV='production'
```

## Systemd Service Configuration

Create `/etc/systemd/system/college-events.service`:

```ini
[Unit]
Description=College Event Management System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
Environment="PATH=/path/to/your/venv/bin"
ExecStart=/path/to/your/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable college-events
sudo systemctl start college-events
sudo systemctl status college-events
```

## Security Hardening

### 1. Update app.py for Production

```python
import os

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'fallback-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler
    
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('College Events startup')
```

### 2. Firewall Configuration

```bash
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable
```

### 3. Rate Limiting

Install Flask-Limiter:
```bash
pip install Flask-Limiter
```

Add to app.py:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

## Database Backups

Create backup script (`backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/college-events"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
pg_dump college_events > $BACKUP_DIR/db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

## Monitoring

### 1. Application Monitoring

Install and configure:
- **Sentry** for error tracking
- **New Relic** or **Datadog** for APM
- **Prometheus + Grafana** for metrics

### 2. Server Monitoring

```bash
# Install monitoring tools
sudo apt install htop nethogs iotop

# Check logs
sudo journalctl -u college-events -f
tail -f logs/app.log
```

## Performance Optimization

### 1. Database Optimization

```python
# Add indexes in app.py
class Event(db.Model):
    __table_args__ = (
        db.Index('idx_event_date', 'date'),
    )

class Registration(db.Model):
    __table_args__ = (
        db.Index('idx_reg_event', 'event_id'),
        db.Index('idx_reg_student', 'student_id'),
    )
```

### 2. Caching

Install Flask-Caching:
```bash
pip install Flask-Caching
```

Configure:
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/events')
@cache.cached(timeout=300)
def events():
    # ... route logic
```

### 3. Static File Serving

Use CDN for Bootstrap, Font Awesome, and static assets.

## Maintenance

### Regular Tasks

1. **Daily**:
   - Check application logs
   - Monitor server resources
   - Review error reports

2. **Weekly**:
   - Review database backups
   - Check security updates
   - Analyze user activity

3. **Monthly**:
   - Update dependencies
   - Review performance metrics
   - Clean old data if necessary

### Update Procedure

1. Backup database
2. Pull latest code
3. Install dependencies
4. Run database migrations (if any)
5. Restart service
6. Verify functionality

```bash
# Update process
cd /path/to/app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart college-events
```

## Troubleshooting

### Common Issues

**Application won't start**:
```bash
sudo systemctl status college-events
sudo journalctl -u college-events -n 50
```

**Database connection errors**:
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials in environment variables
- Check firewall rules

**Email not sending**:
- Verify SMTP credentials
- Check firewall allows outbound port 587
- Review email provider settings

**High memory usage**:
- Reduce Gunicorn workers
- Implement caching
- Optimize database queries

## Scaling

### Horizontal Scaling

1. **Load Balancer**: Use Nginx or HAProxy
2. **Multiple App Servers**: Run multiple Gunicorn instances
3. **Shared Database**: All instances connect to same PostgreSQL
4. **Session Storage**: Use Redis for shared sessions

### Vertical Scaling

- Upgrade server resources (CPU, RAM)
- Optimize database queries
- Implement caching strategies

## Support

For production issues:
1. Check application logs
2. Review server logs
3. Consult deployment documentation
4. Contact system administrator

---

**Remember**: Always test changes in a staging environment before deploying to production!
