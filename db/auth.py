from datetime import timedelta, datetime, timezone
import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel
from .sqlc import queries, models
import os


SECRET_KEY = os.environ["SECRET_KEY"]
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ["TOKEN_EXPIRE_MINS"])

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    return password_hash.verify(plain_password, hashed_password)


async def authenticate_user(conn, username: str, password: str) -> models.User:
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
    return Token(access_token=encoded_jwt, token_type="Bearer")


def get_current_jwt(access_token: str) -> dict:
    payload = jwt.decode(access_token, SECRET_KEY, algorithms=["HS256"])
    username = payload.get("username")
    if username is None:
        raise InvalidJWTData("No username")
    return payload


class InvalidJWTData(Exception):
    pass


async def add_user(conn, username: str, password: str, is_super_admin=False):
    hashed_password = password_hash.hash(password).encode()
    await queries.add_user(conn, username=username, password=hashed_password, super_admin=is_super_admin)
