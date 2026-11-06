from datetime import timedelta, datetime, timezone
from typing import Annotated
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel
from . import conn_utils
from .sqlc import queries, models


SECRET_KEY = "eaedf1eca19cd97855d50698724bc88304af49acf1e65ff7d17b982ae34758fe"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    return password_hash.verify(plain_password, hashed_password)


async def authenticate_user(username: str, password: str) -> models.User:
    async with conn_utils.get_conn() as conn:
        user = await queries.get_user(conn, username=username)
    if user is None:
        verify_password(password, DUMMY_HASH)  # to help prevent a timing attack
        raise InvalidUsernamePass()
    if not verify_password(password, user.password.tobytes()):
        raise InvalidUsernamePass()
    return user


class InvalidUsernamePass(Exception):
    pass


def create_access_token(data: dict) -> Token:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return Token(access_token=encoded_jwt, token_type="bearer")


async def get_current_jwt(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    username = payload.get("username")
    if username is None:
        raise InvalidJWTData("No username")
    return payload


class InvalidJWTData(Exception):
    pass


async def add_user(username: str, password: str, is_super_admin=False):
    hashed_password = password_hash.hash(password).encode()
    async with conn_utils.get_conn() as conn:
        await queries.add_user(conn, username=username, password=hashed_password, super_admin=is_super_admin)
