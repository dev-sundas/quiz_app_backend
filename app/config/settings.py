from starlette.config import Config
from starlette.datastructures import Secret
import os

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

# Load both URLs (may not both exist locally)
DATABASE_URL = config("DATABASE_URL", cast=Secret, default=None)
DATABASE_PUBLIC_URL = config("DATABASE_PUBLIC_URL", cast=Secret, default=None)

def get_db_url() -> str:
    """
    Pick the correct DB URL:
    - Inside Railway: use DATABASE_URL (internal)
    - Locally: use DATABASE_PUBLIC_URL (external), fall back to DATABASE_URL if not set
    """
    if os.getenv("RAILWAY_ENVIRONMENT") == "production":
        return str(DATABASE_URL)
    return str(DATABASE_PUBLIC_URL or DATABASE_URL)
