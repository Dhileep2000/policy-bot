# Quick Start: Environment & Configuration

## 📚 Documentation Files

- **[CONFIGURATION_SUMMARY.md](./CONFIGURATION_SUMMARY.md)** - Complete overview of all security changes
- **[SECURITY.md](./SECURITY.md)** - Security best practices and compliance guide
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Environment-specific deployment instructions

## 🚀 Quick Start

### Setup (First Time)

```bash
# Backend
cd backend
cp .env.example .env
# EDIT .env and add your GEMINI_API_KEY from https://makersuite.google.com/app/apikey

# Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run backend
python -m uvicorn main:app --reload
# Access at: http://127.0.0.1:8000/docs

# Frontend (in new terminal)
cd frontend
npm install
npm run dev
# Access at: http://localhost:3000
```

### Everyday Development

```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate
python -m uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

## 🔐 Key Security Rules

❌ **NEVER DO**:
- Commit `.env` files
- Hardcode API keys in code
- Share credentials in Slack/email
- Push secrets to Git

✅ **ALWAYS DO**:
- Use `.env` files for secrets
- Add `.env` to `.gitignore` (already done)
- Use `.env.example` for documentation
- Rotate API keys monthly
- Use secrets manager in production

## 📝 Configuration Files

### Backend: `backend/.env`

```bash
# CRITICAL: Your API key (get from https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_key_here

# Optional: For production deployment
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
ENVIRONMENT=development

# Optional: For different frontend URL
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend: `frontend/.env` (optional)

```bash
# For production deployment to different backend
VITE_API_BASE_URL=https://api.yourdomain.com
```

## 🐛 Troubleshooting

### "GEMINI_API_KEY is not set" warning

**Fix**: Create `backend/.env` with your API key:
```bash
cd backend
echo "GEMINI_API_KEY=your_key_here" > .env
```

### CORS errors on frontend

**Fix**: Update `CORS_ORIGINS` in `backend/.env`:
```bash
# If running on different ports:
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Backend won't start

**Fix**: Check configuration is valid:
```bash
cd backend
python -c "from config import settings; print(f'Config OK: {settings.ENVIRONMENT}')"
```

### Frontend build errors

**Fix**: Install dependencies:
```bash
cd frontend
npm install
npm run build
```

## 🔄 Updating Configuration

### Change API Key
```bash
# Edit backend/.env
GEMINI_API_KEY=new_key_here

# Restart backend
# Ctrl+C in backend terminal, run again
```

### Change Server Port
```bash
# Edit backend/.env
SERVER_PORT=9000

# Restart backend
# Frontend will still work via Vite proxy
```

### Change Frontend API URL (Production)
```bash
# Edit frontend/.env
VITE_API_BASE_URL=https://api.yourdomain.com

# Rebuild frontend
npm run build
```

## 📊 Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `ENVIRONMENT` | development | Dev/staging/production |
| `SERVER_HOST` | 127.0.0.1 | Server binding address |
| `SERVER_PORT` | 8000 | Server port |
| `CORS_ORIGINS` | localhost:* | Allowed frontend domains |
| `ENABLE_AUDIT_LOGGING` | True | Compliance logging |
| `DATA_CLASSIFICATION` | CONFIDENTIAL | Document classification |
| `REQUIRE_HTTPS` | False | Enforce HTTPS (set to True in production) |

## 🧪 Testing Configuration

### Verify Backend Config
```bash
cd backend
python -c "from config import settings; print(settings.model_dump())"
```

### Test API
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/docs  # Swagger UI
```

### Test CORS
```bash
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://127.0.0.1:8000/api/documents
```

## 📖 For More Information

- Security best practices: [SECURITY.md](./SECURITY.md)
- Production deployment: [DEPLOYMENT.md](./DEPLOYMENT.md)
- Full configuration summary: [CONFIGURATION_SUMMARY.md](./CONFIGURATION_SUMMARY.md)
- Pydantic Settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- FastAPI CORS docs: https://fastapi.tiangolo.com/tutorial/cors/
- Vite Environment docs: https://vitejs.dev/guide/env-and-mode.html

---

Need help? Check the documentation files above! 🚀
