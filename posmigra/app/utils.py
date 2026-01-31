import bcrypt
import logging
from pal.services.filters import filter_by_hierarchy
from pal.services.stock import paginate
from pal.services.tra import paginate_tra

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    try:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise

def check_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        return False
