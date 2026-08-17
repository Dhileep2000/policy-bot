# Security & Configuration Guide

## Overview

This document explains how sensitive information and configuration is managed in the Lexis AI Policy Intelligence application to ensure security compliance, government standards, and best practices.

## ⚠️ Critical Security Information

### Never Commit Secrets to Version Control

**CRITICAL RULE**: Never commit `.env` files, API keys, database credentials, or any sensitive information to Git. The repository has `.gitignore` configured to prevent this, but always verify:

```bash
# Check what would be committed
git status

# Ensure .env files are in .gitignore
cat .gitignore | grep -E "\.env|secrets"
```

### Secrets Already Committed?

If you accidentally commit sensitive information:

```bash
# Remove file from Git history
git filter-branch --tree-filter 'rm -f .env backend/.env frontend/.env' HEAD

# Or use git-filter-repo (recommended)
git filter-repo --invert-paths --path .env
```

## Environment Variables Configuration

### Backend Configuration

All backend configuration is loaded from `backend/.env` file via `config.py`:

**Location**: `backend/.env`  
**Template**: `backend/.env.example`

Create `backend/.env` by copying the template:

```bash
cd backend
cp .env.example .env
# Then edit .env and add your actual values
```

**Key Secrets to Configure**:

```bash
# CRITICAL: Get from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_api_key_here

# Optional: Override server host/port for production
SERVER_HOST=0.0.0.0          # For production deployment
SERVER_PORT=8000

# Optional: Update CORS origins for your domain
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Optional: Enable government compliance features
ENABLE_AUDIT_LOGGING=True
ORGANIZATION_NAME=YourOrganization
DATA_CLASSIFICATION=CONFIDENTIAL
REQUIRE_HTTPS=True            # Set to True in production
```

### Frontend Configuration

Frontend configuration is optional and loaded via `frontend/.env`:

**Location**: `frontend/.env`  
**Template**: `frontend/.env.example`

```bash
cd frontend
cp .env.example .env
```

**Common Settings**:

```bash
# For production deployment
VITE_API_BASE_URL=https://api.yourdomain.com

# Application metadata
VITE_APP_TITLE=Lexis AI Policy Intelligence
```

## Configuration Security Best Practices

### 1. API Keys & Secrets

- ✅ **DO** store in `.env` files with restricted permissions
- ✅ **DO** rotate API keys regularly (especially in production)
- ✅ **DO** use different keys for dev/staging/production
- ❌ **DON'T** commit `.env` files to version control
- ❌ **DON'T** hardcode secrets in source code
- ❌ **DON'T** share secrets in Slack, email, or unencrypted channels

### 2. Database Credentials

```bash
# Current: SQLite (local development)
DATABASE_PATH=./policy_assistant.db

# For production: consider using managed services
# - PostgreSQL with AWS RDS
# - Cloud SQL on Google Cloud
# - Azure Database for PostgreSQL
```

### 3. CORS Configuration

**Development** (current):
```bash
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

**Staging/Production**:
```bash
# Restrict to your actual domain
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

❌ **Never use**: `CORS_ORIGINS=*` in production  
❌ **Never allow**: `http://` in production (use `https://`)

### 4. HTTPS & TLS

**Development**: `REQUIRE_HTTPS=False`

**Production**:
```bash
REQUIRE_HTTPS=True
# Ensure your deployment:
# - Uses TLS certificates (Let's Encrypt, AWS ACM, etc.)
# - Redirects HTTP to HTTPS
# - Has HSTS headers enabled
```

## Government & Compliance Features

### Audit Logging

For government compliance (FedRAMP, SOC 2, ISO 27001):

```bash
ENABLE_AUDIT_LOGGING=True
```

This enables:
- Request/response logging (sanitized)
- Authentication events
- Document access tracking
- API usage analytics

### Data Classification

For handling government/confidential documents:

```bash
# Allowed values: UNCLASSIFIED, INTERNAL, CONFIDENTIAL, SECRET
DATA_CLASSIFICATION=CONFIDENTIAL
```

### Sensitive Data Masking

Automatically masks PII, API keys, and credentials in logs:

```bash
ENABLE_SENSITIVE_DATA_MASKING=True
```

This prevents:
- API keys appearing in logs
- Personal information exposure
- Database credentials in error messages

### Organization Name

For document metadata and tagging:

```bash
ORGANIZATION_NAME=MyOrganization
```

## Deployment Security Checklist

### Pre-Deployment

- [ ] API key rotated and stored securely
- [ ] `.env` files in `.gitignore`
- [ ] No secrets in environment logs
- [ ] CORS origins configured for your domain
- [ ] HTTPS enabled with valid certificate
- [ ] Database backups configured
- [ ] Rate limiting enabled
- [ ] Audit logging enabled

### Production Environment Setup

**AWS/Google Cloud/Azure**:

Use managed services for secrets:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret --name policy-api-key --secret-string "your-key"

# Azure Key Vault
az keyvault secret set --vault-name mykeyvault --name GEMINI-API-KEY --value "your-key"

# Google Secret Manager
gcloud secrets create gemini-api-key --replication-policy="automatic" --data-file=-
```

**Environment Setup**:

```bash
# Load from AWS Secrets Manager
export GEMINI_API_KEY=$(aws secretsmanager get-secret-value --secret-id policy-api-key --query SecretString --output text)

# Or use IAM roles for automatic credential injection
```

### Container Deployment (Docker/Kubernetes)

```dockerfile
# Dockerfile - NEVER commit secrets
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Secrets passed at runtime
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# kubernetes-secrets.yaml - Apply separately, not in Git
apiVersion: v1
kind: Secret
metadata:
  name: policy-secrets
type: Opaque
stringData:
  GEMINI_API_KEY: "your-secret-key"
  DATABASE_PASSWORD: "your-db-password"
```

## Verification

### Verify No Secrets in Git

```bash
# Search for common secret patterns
git log -p | grep -E "api_key|password|secret|token|AQ\.Ab"

# Or use dedicated tools
npm install -g detect-secrets
detect-secrets scan --baseline .secrets.baseline
```

### Verify Configuration Loading

```bash
# Backend: Check configuration is loaded from .env
cd backend
python -c "from config import settings; print(f'API Key Set: {bool(settings.GEMINI_API_KEY)}'); print(f'Environment: {settings.ENVIRONMENT}')"

# Should show: API Key Set: True, Environment: development (or configured value)
```

### Verify CORS Configuration

```bash
# Test CORS headers
curl -i -X OPTIONS http://localhost:3000/api/documents \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"

# Should return 200 and appropriate CORS headers
```

## Troubleshooting

### "GEMINI_API_KEY is not set" Warning

**Solution**: Create `backend/.env` with your API key:

```bash
cd backend
echo "GEMINI_API_KEY=your_key_here" > .env
```

### CORS Errors in Frontend

**Problem**: "Access to XMLHttpRequest blocked by CORS"

**Solution**: Update `CORS_ORIGINS` in `backend/.env`:

```bash
# If running frontend on different port:
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Database Not Found

**Problem**: "Unable to open database file"

**Solution**: Ensure `DOCUMENTS_DIR` exists:

```bash
cd backend
mkdir -p documents
# Or in .env, set full path:
DOCUMENTS_DIR=/var/lib/policy_documents
```

## References

- [OWASP: Environment Variables](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12 Factor App: Store Config in Environment](https://12factor.net/config)
- [Google API Key Security](https://cloud.google.com/docs/authentication/api-keys#keeping_credentials_secure)
- [FedRAMP: Security Controls](https://www.fedramp.gov/documents/)
- [SOC 2: Trust Service Criteria](https://www.aicpa.org/resources/landing/system-and-organization-controls-soc-suite)

---

**Last Updated**: 2024  
**Version**: 1.0  
**Maintainer**: DevOps/Security Team
