from datetime import datetime, timedelta, timezone
import os

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext


# ===========================================================
# Load environment variables
# ===========================================================

load_dotenv()


# ===========================================================
# Password hashing configuration
# ===========================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ===========================================================
# JWT configuration
# ===========================================================

SECRET_KEY = os.getenv("JWT_SECRET")

ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60",
    )
)


# ===========================================================
# Validate JWT configuration
# ===========================================================

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET is not configured in the environment."
    )


# ===========================================================
# Password hashing
# ===========================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ===========================================================
# Create Access Token
# ===========================================================

def create_access_token(data: dict) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


# ===========================================================
# Decode Access Token
# ===========================================================

def decode_access_token(token: str) -> dict:

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except JWTError:

        return {}