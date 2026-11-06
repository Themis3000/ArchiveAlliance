from typing import Annotated
from fastapi import FastAPI, Depends
from db import oauth2_scheme, conn_utils
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


@app.get("/user/{username}")
async def get_user(username: str):
    async with conn_utils.get_conn() as conn:
        user = await queries.get_user(conn, username=username)
    if user is None:
        raise Exception()
    return {"message": f"Their password is {user.password}"}


@app.get("/hello/{name}")
async def say_hello(name: str, token: Annotated[str, Depends(oauth2_scheme)]):
    return {"message": f"Hello {name}"}


# @app.post("/token")
# async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token():
#     pass
