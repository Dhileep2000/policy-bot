import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==================== API & LLM Configuration ====================
    GEMINI_API_KEY: str = ""  # CRITICAL: Google Gemini API key - MUST be in .env, never commit
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_FALLBACK_MODEL: str = "gemini-2.5-flash"

    # ==================== Supabase / PostgreSQL Configuration ====================
    SUPABASE_URL: str = ""
    # Server-only key. Never expose this value to the browser.
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_JWKS_URL: str = ""

    # ==================== Local document processing ====================
    DOCUMENTS_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")

    # ==================== Text Processing Configuration ====================
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RELEVANCE_THRESHOLD: float = 0.28

    # ==================== Server Configuration ====================
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    ENVIRONMENT: str = "development"  # development, staging, production

    # ==================== CORS & Security Configuration ====================
    # Comma-separated list of allowed origins for CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "Content-Type,Authorization"

    # ==================== Government & Compliance Configuration ====================
    # Enable audit logging for government compliance (SOC 2, ISO 27001, etc.)
    ENABLE_AUDIT_LOGGING: bool = True
    # Organization name for document tagging and compliance
    ORGANIZATION_NAME: str = "Corporate"
    # Data classification level (UNCLASSIFIED, INTERNAL, CONFIDENTIAL, SECRET)
    DATA_CLASSIFICATION: str = "CONFIDENTIAL"
    # Enable sensitive data masking in logs
    ENABLE_SENSITIVE_DATA_MASKING: bool = True
    # Require HTTPS in production
    REQUIRE_HTTPS: bool = False  # Set to True in production

    # ==================== Performance & Timeout Configuration ====================
    REQUEST_TIMEOUT: int = 60  # seconds
    UPLOAD_MAX_SIZE_MB: int = 100
    MAX_DOCUMENTS: int = 1000

    # ==================== Logging Configuration ====================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    ENABLE_REQUEST_LOGGING: bool = True

    # ==================== API Rate Limiting ====================
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Resolve relative document paths from the backend directory, not from whichever
# directory happened to be used to start Uvicorn.
if not os.path.isabs(settings.DOCUMENTS_DIR):
    settings.DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), settings.DOCUMENTS_DIR)


def is_placeholder(value: str) -> bool:
    """Return whether a sample configuration value was used instead of a secret."""
    normalized = value.strip().lower()
    return not normalized or "your_" in normalized or "your-project" in normalized



def gemini_is_configured() -> bool:
    return not is_placeholder(settings.GEMINI_API_KEY)


def supabase_is_configured() -> bool:
    return not is_placeholder(settings.SUPABASE_URL) and not is_placeholder(settings.SUPABASE_SECRET_KEY)


# Ensure folders exist
os.makedirs(settings.DOCUMENTS_DIR, exist_ok=True)

# Validate critical configuration
if not gemini_is_configured():
    import warnings
    warnings.warn(
        "GEMINI_API_KEY is not set in .env file. "
        "Please set GEMINI_API_KEY before running the application in production.",
        category=RuntimeWarning
    )

if not supabase_is_configured():
    import warnings
    warnings.warn(
        "SUPABASE_URL and SUPABASE_SECRET_KEY must be set in .env before running the application.",
        category=RuntimeWarning,
    )






