from jose import jwt, JWTError
from config.settings import get_settings

settings = get_settings()


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_access_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
