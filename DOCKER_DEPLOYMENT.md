# Docker Deployment Guide

## 🐳 Quick Docker Deployment

### Prerequisites
- Docker Desktop installed and running
- Docker Compose installed

### Option 1: Using Docker Compose (Recommended)

```bash
# Navigate to project root
cd "C:\Users\kevin\OneDrive\Desktop\JJE PAYMENT"

# Build and start all services
docker-compose up --build

# In another terminal, verify services are running
docker-compose ps
```

**Services will be available at:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MongoDB: localhost:27017 (admin / password123)

### Option 2: Build and Run Individual Containers

#### Backend
```bash
# Build backend image
docker build -t payment-backend:latest ./backend

# Run backend container
docker run -d \
  --name payment_backend \
  -p 8000:8000 \
  -e MONGODB_URL=mongodb://localhost:27017 \
  -e DEBUG=False \
  payment-backend:latest
```

#### Frontend
```bash
# Build frontend image
docker build -t payment-frontend:latest ./frontend

# Run frontend container
docker run -d \
  --name payment_frontend \
  -p 3000:3000 \
  payment-frontend:latest
```

#### MongoDB
```bash
# Run MongoDB container
docker run -d \
  --name payment_mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password123 \
  mongo:7.0
```

### Common Docker Commands

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose stop

# Start services
docker-compose start

# Remove services and volumes
docker-compose down -v

# Rebuild without cache
docker-compose build --no-cache

# Run command in container
docker-compose exec backend python -m uvicorn app.main:app

# Connect to MongoDB
docker-compose exec mongodb mongosh
```

## 🚀 Production Deployment

### Environment Setup

Update `docker-compose.yml` for production:

```yaml
backend:
  environment:
    DEBUG: "False"
    MONGODB_URL: mongodb+srv://user:pass@cluster.mongodb.net
    LOG_LEVEL: WARNING
```

### Using Docker Registry

```bash
# Tag image
docker tag payment-backend:latest your-registry/payment-backend:1.0.0

# Push to registry
docker push your-registry/payment-backend:1.0.0

# Pull in production
docker pull your-registry/payment-backend:1.0.0
```

### Kubernetes Deployment

Create `k8s-backend.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: payment-backend
  template:
    metadata:
      labels:
        app: payment-backend
    spec:
      containers:
      - name: backend
        image: your-registry/payment-backend:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: mongodb-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: payment-backend-service
spec:
  selector:
    app: payment-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f k8s-backend.yaml
```

## 🔒 Security Considerations

### Update Credentials
```yaml
# In docker-compose.yml, change default credentials
mongodb:
  environment:
    MONGO_INITDB_ROOT_USERNAME: secure_user
    MONGO_INITDB_ROOT_PASSWORD: ${DB_PASSWORD}  # Use environment variables
```

### Network Security
```yaml
# Restrict network access
networks:
  payment_network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: br_payment
      com.docker.driver.mtu: 1500
```

### Volume Encryption
```yaml
volumes:
  mongodb_data:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=256m
```

## 📊 Monitoring and Logging

### View Real-time Logs
```bash
docker-compose logs -f
docker-compose logs -f backend --tail=100
```

### Health Checks
Services include health checks defined in Dockerfiles:

```bash
# Check container health
docker inspect payment_backend | grep -A 5 "Health"
```

### CPU/Memory Usage
```bash
# Monitor resource usage
docker stats payment_backend payment_frontend payment_mongodb
```

## 🛠️ Development

### Mount Local Code
```yaml
backend:
  volumes:
    - ./backend:/app
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Rebuild on Code Changes
```bash
docker-compose up --build
```

### Access Container Shell
```bash
# Backend shell
docker-compose exec backend /bin/bash

# MongoDB shell
docker-compose exec mongodb mongosh

# Frontend shell
docker-compose exec frontend /bin/sh
```

## 🧹 Cleanup

```bash
# Stop and remove all containers
docker-compose down

# Remove images
docker-compose down --rmi all

# Remove volumes
docker-compose down -v

# Clean up unused Docker resources
docker system prune -a -v
```

## 📈 Scaling

### Horizontal Scaling with Docker Compose

```bash
# Scale backend to 3 instances
docker-compose up -d --scale backend=3

# Note: Frontend typically runs single instance
# Use load balancer for multiple backend instances
```

### Load Balancer Configuration

Add nginx to `docker-compose.yml`:

```yaml
nginx:
  image: nginx:alpine
  container_name: payment_nginx
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - backend
  networks:
    - payment_network
```

Create `nginx.conf`:

```
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🆘 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs backend

# Check image
docker images

# Rebuild image
docker-compose build --no-cache backend
```

### Port Already in Use
```bash
# Find process using port
# Windows: netstat -ano | findstr :8000
# Linux: lsof -i :8000

# Change port in docker-compose.yml
# ports:
#   - "8001:8000"  # Use different external port
```

### Database Connection Issues
```bash
# Check MongoDB
docker-compose exec mongodb mongosh

# Verify network
docker network ls
docker network inspect payment_network
```

### Permission Issues
```bash
# Fix volume permissions
docker-compose exec backend chown -R appuser:appuser /app
```

---

**For more information, see main README.md**
