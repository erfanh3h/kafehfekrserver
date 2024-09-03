from typing import Optional
import uuid, datetime
from fastapi import Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from Entities.Network_Exeptions import HttpExceptions

SECRET_KEY = "09da5e74afaa9ma2565c818195b7b9563b93xc059f6f0f4cab6cf63b88e8d3e7"
ALGORITHM = "HS256"


# ACCESS_TOKEN_EXPIRE_DAY = 30

class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
exceptions_object = HttpExceptions()


def get_device_id_hash(device_id):
    return uuid.uuid5(uuid.NAMESPACE_X500, device_id)


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(weeks=52)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def extract_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: int = payload.get("phone")
        id: str = payload.get("id")
        device_id: str = payload.get("device_id")
        token_data = {'phone': phone, 'id': id , 'device_id': device_id}
    except JWTError:
        raise exceptions_object.raise401()
    except:
        raise exceptions_object.raise401()
    return token_data


async def get_current_user(authorization: str = Header(...)):
    try:
        payload = jwt.decode(authorization, SECRET_KEY, algorithms=[ALGORITHM])
        phone: int = payload.get("phone")
        id: str = payload.get("id")
        token_data = {'phone': phone, 'id': id}
    except JWTError:
        raise exceptions_object.raise401()
    except:
        raise exceptions_object.raise401()
    from Entities.Database import game_database
    user = game_database.users_manager.read_user(id=token_data['id'])
    if user is None:
        raise exceptions_object.raise401()
    return user


async def get_current_user_optional(authorization: str = Header(None)):
    try:
        payload = jwt.decode(authorization, SECRET_KEY, algorithms=[ALGORITHM])
        phone: int = payload.get("phone")
        id: str = payload.get("id")
        token_data = {'phone': phone, 'id': id}
    except:
        return None
    from Entities.Database import game_database
    user = game_database.users_manager.read_user(id=token_data['id'])
    return user
