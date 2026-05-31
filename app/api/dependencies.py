from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.patient import Patient
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
auth_service = AuthService()


async def get_current_patient(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Patient:
    try:
        return await auth_service.get_patient_from_token(db, token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc


async def require_super_admin(current_user: Annotated[Patient, Depends(get_current_patient)]):
    # Try to determine a role field on the current_user
    role = getattr(current_user, "role", None)
    is_super = getattr(current_user, "is_super_admin", None)
    if role != "super_admin" and not is_super:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return current_user
