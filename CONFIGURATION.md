# Payment Tracking Dashboard - Configuration Guide

## Environment Variables (.env)

Copy `.env.example` to `.env` and customize:

```bash
# Backend
cd backend
cp .env.example .env
```

Edit `backend/.env`:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=payment_tracking

# Application Settings
DEBUG=True
LOG_LEVEL=INFO

# File Upload
MAX_UPLOAD_SIZE=52428800  # 50MB in bytes
ALLOWED_EXTENSIONS=xlsx,xls

# Payment Matching (Customize based on your needs)
FUZZY_MATCH_THRESHOLD=80          # 0-100: Higher = stricter matching
DATE_PROXIMITY_DAYS=7             # Days window for date matching
AMOUNT_TOLERANCE_PERCENT=0.5      # % tolerance for amount matching

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# Optional: Logging
LOG_FILE=app.log
```

### Production Configuration

For production, modify these settings:

```env
# Production Database (e.g., MongoDB Atlas)
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/payment_tracking?retryWrites=true&w=majority

# Security
DEBUG=False
LOG_LEVEL=WARNING

# CORS - Restrict to your domain
CORS_ORIGINS=["https://yourdomain.com"]

# Matching - Tighten based on your requirements
FUZZY_MATCH_THRESHOLD=85          # Stricter matching
DATE_PROXIMITY_DAYS=3             # Tighter date window
AMOUNT_TOLERANCE_PERCENT=0.1      # Tighter amount tolerance
```

---

## Matching Algorithm Tuning

### FUZZY_MATCH_THRESHOLD
- **80** (default): Good for real-world data with typos
- **85-90**: Strict matching, fewer false positives
- **70-75**: Loose matching, more matches but some incorrect

Example:
```
"ABC Company" vs "ABC Co" at 80% → Match ✓
"ABC Company" vs "ABC Co" at 90% → No Match ✗
```

### DATE_PROXIMITY_DAYS
- **7** (default): Payment within 1 week of invoice
- **3**: Tight window (strict same-day/next-day)
- **14**: Loose window (2-week payment terms)
- **0**: Exact date match only

Example:
```
Invoice: 2024-01-15
Payment: 2024-01-20 → Match ✓ (5 days)
Payment: 2024-01-23 → No Match ✗ (8 days)
```

### AMOUNT_TOLERANCE_PERCENT
- **0.5** (default): ±0.5% tolerance (₹1000 ±₹5)
- **0.1**: Very strict tolerance
- **1.0**: 1% tolerance
- **0**: Exact amount only

Example:
```
Invoice: ₹10,000
Payment: ₹10,025 → Match ✓ (0.25%)
Payment: ₹10,100 → No Match ✗ (1%)
```

---

## Frontend Configuration

### Vite Proxy Setup (`vite.config.js`)

The frontend is configured to proxy API requests:
```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

This means:
- Frontend runs on: `http://localhost:3000`
- API runs on: `http://localhost:8000`
- Requests to `/api/*` are forwarded to backend

### Tailwind CSS Theme (`tailwind.config.cjs`)

Customize colors:
```javascript
colors: {
  primary: '#2563eb',    // Blue
  secondary: '#10b981',  // Green
  danger: '#ef4444',     // Red
  warning: '#f59e0b'     // Amber
}
```

### API Client Configuration (`src/services/api.js`)

The API base URL is automatically set:
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
```

---

## Database Configuration

### MongoDB Connection String

**Local Development:**
```
mongodb://localhost:27017
```

**MongoDB Atlas (Cloud):**
```
mongodb+srv://username:password@cluster-name.mongodb.net/database-name?retryWrites=true&w=majority
```

### Database Indexes

Indexes are automatically created on startup:
- `bills`: invoice_no, party_name, invoice_date, status
- `payments`: payment_id, party_name, payment_date
- `parties`: party_name (unique)

---

## Logging Configuration

### Log Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General information (default)
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors

### View Logs

**Backend Logs:**
```bash
# Check log file
tail -f backend/app.log

# Or in console (when running with --reload)
python -m uvicorn app.main:app --reload --log-level debug
```

**Frontend Logs:**
```javascript
// Browser console (F12)
console.log('Message')
console.error('Error')
```

---

## File Upload Configuration

### Max File Size

Default: **50MB**

Change in `.env`:
```env
MAX_UPLOAD_SIZE=104857600  # 100MB in bytes
```

### Allowed File Types

Default: `.xlsx, .xls`

Files must be:
- Excel format (.xlsx or .xls)
- Less than MAX_UPLOAD_SIZE
- Not empty

---

## Docker Configuration

### Environment File for Docker

Create `docker/.env` for Docker Compose:
```env
MONGODB_VERSION=7.0
PYTHON_VERSION=3.11
NODE_VERSION=18

API_PORT=8000
FRONTEND_PORT=3000

MONGODB_ROOT_USERNAME=root
MONGODB_ROOT_PASSWORD=password123
MONGODB_DB_NAME=payment_tracking

DEBUG=False
LOG_LEVEL=INFO
```

---

## SSL/HTTPS Configuration (Production)

### With Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Performance Tuning

### Database Connection Pool

Adjust in `app/core/database.py`:
```python
client = AsyncMotorClient(
    MONGODB_URL,
    maxPoolSize=50,      # Increase for more concurrent connections
    minPoolSize=10       # Minimum connections
)
```

### Matching Algorithm Performance

For large datasets, consider:
```env
# Batch processing
BATCH_SIZE=1000

# Caching
ENABLE_CACHE=True
CACHE_TTL=3600
```

---

## Monitoring Configuration

### Application Health Check

The system includes a health check endpoint:
```bash
curl http://localhost:8000/api/health
# Returns: {"status": "healthy"}
```

### Error Tracking

Enable error logging in `.env`:
```env
LOG_LEVEL=DEBUG
LOG_FILE=error.log
```

---

## Backup & Recovery

### MongoDB Backup

```bash
# Backup
mongodump --uri "mongodb://localhost:27017" --out ./backup

# Restore
mongorestore --uri "mongodb://localhost:27017" ./backup
```

### Database Export

```bash
# Export bills collection to CSV
mongoexport --uri "mongodb://localhost:27017" \
  --collection bills \
  --out bills.csv \
  --csv
```

---

## Security Checklist

- [ ] Change default credentials
- [ ] Enable HTTPS/SSL
- [ ] Restrict CORS origins
- [ ] Set DEBUG=False in production
- [ ] Use strong MongoDB password
- [ ] Enable database backups
- [ ] Set up monitoring
- [ ] Configure firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable logging and auditing

---

## Quick Reference

| Setting | Development | Production |
|---------|-----------|-----------|
| DEBUG | True | False |
| LOG_LEVEL | DEBUG | WARNING |
| FUZZY_MATCH_THRESHOLD | 80 | 85-90 |
| DATE_PROXIMITY_DAYS | 7 | 3-7 |
| AMOUNT_TOLERANCE_PERCENT | 0.5 | 0.1-0.5 |
| MongoDB | Local | Atlas/Managed |
| CORS_ORIGINS | "*" | Specific domains |

---

For more details, see:
- **README.md** - Full documentation
- **DOCKER_DEPLOYMENT.md** - Docker setup
- **DEVELOPMENT.md** - Development guide
