# Configuration Guide for Different Environments

## Quick Start

### Development

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload

# Frontend (in new terminal)
cd frontend
npm install
npm run dev
```

Access the app at: **http://localhost:3000**

### Staging Deployment

Create `backend/.env` for staging:

```bash
GEMINI_API_KEY=your_staging_key
ENVIRONMENT=staging
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Use your staging domain
CORS_ORIGINS=https://staging.yourdomain.com,https://api-staging.yourdomain.com

REQUIRE_HTTPS=True
ENABLE_AUDIT_LOGGING=True
```

Deploy:

```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt
npm install

# Run with gunicorn for production-like behavior
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### Production Deployment

#### Option 1: Cloud Run (Google Cloud)

```bash
# Create .env.cloud (not in Git)
GEMINI_API_KEY=<secure-value>
ENVIRONMENT=production
SERVER_HOST=0.0.0.0
CORS_ORIGINS=https://yourdomain.com
REQUIRE_HTTPS=True
ENABLE_AUDIT_LOGGING=True
DATA_CLASSIFICATION=CONFIDENTIAL

# Create Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Build and push
docker build -t policy-api:latest .
docker tag policy-api:latest gcr.io/YOUR_PROJECT/policy-api:latest
docker push gcr.io/YOUR_PROJECT/policy-api:latest

# Deploy to Cloud Run
gcloud run deploy policy-api \
  --image gcr.io/YOUR_PROJECT/policy-api:latest \
  --set-env-vars GEMINI_API_KEY=your-key \
  --allow-unauthenticated
```

#### Option 2: AWS ECS

```bash
# Create ECS task definition with secrets from AWS Secrets Manager
{
  "name": "policy-api",
  "image": "YOUR_REGISTRY/policy-api:latest",
  "portMappings": [{"containerPort": 8000}],
  "secrets": [
    {
      "name": "GEMINI_API_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:policy-api-key"
    }
  ],
  "environment": [
    {"name": "ENVIRONMENT", "value": "production"},
    {"name": "REQUIRE_HTTPS", "value": "True"},
    {"name": "ENABLE_AUDIT_LOGGING", "value": "True"}
  ]
}
```

#### Option 3: Docker Compose (Self-Hosted)

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      ENVIRONMENT: production
      SERVER_HOST: 0.0.0.0
      CORS_ORIGINS: https://yourdomain.com
      REQUIRE_HTTPS: True
    volumes:
      - ./backend/documents:/app/documents
      - ./backend/policy_assistant.db:/app/policy_assistant.db
    restart: always

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      VITE_API_BASE_URL: https://api.yourdomain.com
    depends_on:
      - backend
    restart: always

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - frontend
      - backend
```

## Environment Variable Reference

| Variable | Development | Staging | Production | Notes |
|----------|-------------|---------|------------|-------|
| `GEMINI_API_KEY` | Dev key | Staging key | Prod key (from Secrets Manager) | **CRITICAL - NEVER COMMIT** |
| `ENVIRONMENT` | `development` | `staging` | `production` | Controls feature flags |
| `SERVER_HOST` | `127.0.0.1` | `0.0.0.0` | `0.0.0.0` | Bind address |
| `SERVER_PORT` | `8000` | `8000` | `8000` | Can use reverse proxy |
| `REQUIRE_HTTPS` | `False` | `True` | `True` | Enable TLS redirect |
| `CORS_ORIGINS` | `localhost:*` | `staging.domain` | `yourdomain.com` | Restrict in production |
| `ENABLE_AUDIT_LOGGING` | `False` | `True` | `True` | For compliance |
| `DATA_CLASSIFICATION` | `INTERNAL` | `CONFIDENTIAL` | `CONFIDENTIAL` | Document marking |
| `ENABLE_RATE_LIMITING` | `False` | `True` | `True` | Protect API |

## Database Considerations

### Development
```bash
DATABASE_PATH=./policy_assistant.db  # Local SQLite
```

### Production (Recommended)
Replace SQLite with PostgreSQL:

```bash
# In requirements.txt
psycopg2-binary==2.9.9
SQLAlchemy==2.0.23

# In config.py
DATABASE_URL=postgresql://user:password@host:5432/policy_db
```

## Monitoring & Logging

### Enable Structured Logging
```bash
LOG_FORMAT=json
LOG_LEVEL=INFO
ENABLE_REQUEST_LOGGING=True
```

Parse logs with:
```bash
# CloudWatch (AWS)
aws logs tail /aws/ecs/policy-api --follow

# Google Cloud Logging
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=policy-api" --limit=100

# Datadog
datadog agent config set logs.enabled true
```

### Application Performance Monitoring

```bash
# Add to requirements.txt
# opentelemetry-api
# opentelemetry-sdk
# opentelemetry-exporter-jaeger

# Or use SaaS APM
# - New Relic
# - DataDog
# - Elastic APM
```

## Backup & Disaster Recovery

### Database Backups
```bash
# SQLite (development)
cp policy_assistant.db policy_assistant.db.backup.$(date +%Y%m%d)

# PostgreSQL (production)
pg_dump -h db-host -U postgres policy_db > backup.sql
aws s3 cp backup.sql s3://your-backup-bucket/
```

### Document Backups
```bash
# Backup documents directory
tar -czf documents.tar.gz documents/
aws s3 cp documents.tar.gz s3://your-backup-bucket/

# Or use S3 sync
aws s3 sync documents/ s3://your-doc-bucket/
```

## Security Hardening Checklist

- [ ] API key rotated monthly
- [ ] HTTPS enforced in production
- [ ] Rate limiting enabled
- [ ] CORS restricted to your domain
- [ ] Audit logging enabled
- [ ] Database encrypted at rest
- [ ] Backups encrypted and tested
- [ ] Security headers configured
- [ ] Dependencies updated (npm audit, pip audit)
- [ ] Secrets stored in managed service (Secrets Manager, Vault, etc.)

---

For more details, see [SECURITY.md](./SECURITY.md)
