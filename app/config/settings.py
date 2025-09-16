from starlette.config import Config
from starlette.datastructures import Secret
try:
   config = Config(".env")
except FileNotFoundError:
   config = Config()
DATABASE_URL = config("DATABASE_URL", cast=Secret)

def get_db_url() -> str:
    # Convert Secret to normal string
    return str(DATABASE_URL)