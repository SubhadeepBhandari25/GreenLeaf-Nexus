import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# Serverless / Vercel compatibility
if os.environ.get("VERCEL"):
    import shutil
    TMP_DIR = Path("/tmp")
    (TMP_DIR / "instance").mkdir(parents=True, exist_ok=True)
    (TMP_DIR / "exports").mkdir(parents=True, exist_ok=True)
    (TMP_DIR / "static" / "uploads").mkdir(parents=True, exist_ok=True)

    TMP_DB = TMP_DIR / "instance" / "greenleaf.db"
    SEED_DB = BASE_DIR / "instance" / "greenleaf.db"
    if not TMP_DB.exists() and SEED_DB.exists():
        shutil.copy2(SEED_DB, TMP_DB)

    DEFAULT_DATABASE_URI = f"sqlite:///{TMP_DB}"
    UPLOAD_FOLDER_DEFAULT = TMP_DIR / "static" / "uploads"
    EXPORTS_FOLDER_DEFAULT = TMP_DIR / "exports"
else:
    DEFAULT_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'greenleaf.db'}"
    UPLOAD_FOLDER_DEFAULT = BASE_DIR / "static" / "uploads"
    EXPORTS_FOLDER_DEFAULT = BASE_DIR / "exports"


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "greenleaf-nexus-super-secret-key-2026")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Store parameters
    STORE_NAME = os.environ.get("STORE_NAME", "GreenLeaf Grocers")
    STORE_TAGLINE = os.environ.get("STORE_TAGLINE", "Fresh Stock. Smart Decisions.")
    STORE_ADDRESS = os.environ.get(
        "STORE_ADDRESS", "124 Eco Valley Road, Green Park, Bengaluru - 560034"
    )
    STORE_PHONE = os.environ.get("STORE_PHONE", "+91 80 2345 6789")
    STORE_EMAIL = os.environ.get("STORE_EMAIL", "support@greenleafgrocers.com")
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "₹")
    
    # Tax & Discount Configuration
    TAX_RATE = float(os.environ.get("TAX_RATE", 0.05))  # 5% default VAT/GST
    MAX_DISCOUNT_PERCENT = float(os.environ.get("MAX_DISCOUNT_PERCENT", 30.0))  # Max 30% discount
    
    # Inventory Rules
    LOW_STOCK_THRESHOLD_DEFAULT = 10
    EXPIRY_WARNING_DAYS = 15
    
    # Uploads & Exports
    UPLOAD_FOLDER = UPLOAD_FOLDER_DEFAULT
    EXPORTS_FOLDER = EXPORTS_FOLDER_DEFAULT
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", DEFAULT_DATABASE_URI
    )


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False  # Allows streamlined form testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    PRESERVE_CONTEXT_ON_EXCEPTION = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", DEFAULT_DATABASE_URI
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
