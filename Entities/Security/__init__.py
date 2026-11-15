from typing import Optional
import uuid, datetime
from fastapi import Header, Query, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from Commons.app_consts import admin_token as legacy_admin_token

SECRET_KEY = "09da5e74afaa9ma2565c818195b7b9563b93xc059f6f0f4cab6cf63b88e8d3e7"
ALGORITHM = "HS256"


class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_device_id_hash(device_id):
    return uuid.uuid5(uuid.NAMESPACE_X500, device_id)


def hash_admin_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_admin_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(weeks=52)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_admin_access_token(admin_data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = {
        "sub": str(admin_data.get("_id", "")),
        "admin_id": str(admin_data.get("_id", "")),
        "username": str(admin_data.get("username", "")),
        "role": str(admin_data.get("role", "admin")),
        "permissions": admin_data.get("permissions", []),
        "is_admin": True,
    }
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        # 30 days admin session
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def extract_token(token):
    try:
        if isinstance(token, str) and token.startswith("Bearer "):
            token = token[7:].strip()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: int = payload.get("phone")
        id: str = payload.get("id")
        device_id: str = payload.get("device_id")
        token_data = {'phone': phone, 'id': id, 'device_id': device_id}
        return token_data
    except Exception:
        return None


async def get_current_admin(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
) -> dict:
    raw_token = None
    if authorization:
        raw_token = authorization[7:].strip() if authorization.startswith("Bearer ") else authorization.strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن اهراز هویت ادمین الزامی است.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Backward compatibility with legacy admin token
    if raw_token == legacy_admin_token:
        return {
            "_id": "legacy_superadmin",
            "username": "root",
            "full_name": "Root Superadmin (Legacy Token)",
            "role": "superadmin",
            "permissions": ["*"],
            "is_active": True,
        }

    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="دسترسی به بخش مدیریت مجاز نمی‌باشد.",
            )

        admin_id = payload.get("admin_id") or payload.get("sub")
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="شناسه ادمین نامعتبر است.",
            )

        from Entities.Database import game_database
        admin_doc = game_database.admin_manager.find_by_id(admin_id)
        if not admin_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="حساب کاربری ادمین در پایگاه داده یافت نشد.",
            )

        if not admin_doc.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="حساب ادمین شما غیرفعال شده است.",
            )

        sanitized = game_database.admin_manager._sanitize_admin(admin_doc)
        return sanitized

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن ادمین منقضی یا نامعتبر است.",
            headers={"WWW-Authenticate": "Bearer"},
        )
