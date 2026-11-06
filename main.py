from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from db import conn_utils, auth
from db.sqlc import queries
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_: FastAPI):
    await conn_utils.connect()
    yield
    await conn_utils.disconnect()

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/user/myjwt")
async def get_user_jwt(jwt: Annotated[str, Depends(auth.get_current_jwt)]):
    return jwt


@app.post("/user/add")
async def add_user(username: str, password: str):
    await auth.add_user(username, password)
    return {"success": True}


@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> auth.Token:
    try:
        user = await auth.authenticate_user(form_data.username, form_data.password)
    except auth.InvalidUsernamePass:
        raise HTTPException(status_code=401, detail="Invalid username/password")
    jwt_data = {"user_id": user.id_, "username": user.username, "super_admin": user.super_admin}
    token = auth.create_access_token(jwt_data)
    return token
