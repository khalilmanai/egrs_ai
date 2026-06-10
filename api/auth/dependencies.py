from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from api.auth.jwt import verify_token
from config.settings import get_settings

security = HTTPBearer(auto_error=False)
settings = get_settings()

ALLOWED_ROLES = {"ADMINISTRATEUR", "MANAGER"}


def _check_api_key(request: Request) -> bool:
    api_key = request.headers.get("X-API-Key")
    return api_key == settings.ai_internal_api_key


async def get_current_user(
    request: Request,
    credentials=Depends(security),
) -> dict:
    if _check_api_key(request):
        return {"source": "internal", "role": "ADMINISTRATEUR"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
        )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
    return payload


def require_roles(*roles: str):
    async def _check(payload: dict = Depends(get_current_user)):
        if payload.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé — rôle insuffisant",
            )
        return payload
    return _check
