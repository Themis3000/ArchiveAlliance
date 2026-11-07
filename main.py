from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from db import auth, connection_utils
from db.sqlc import queries
from contextlib import asynccontextmanager
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

conn_utils = connection_utils.Connector()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await conn_utils.connect()
    yield
    await conn_utils.disconnect()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates/")


@app.get("/test")
async def root():
    return {"message": "Hello World"}


@app.get("/user/myjwt")
async def get_user_jwt(jwt: Annotated[str, Depends(auth.get_current_jwt)]):
    return jwt


@app.post("/user/add")
async def add_user(username: str, password: str):
    async with conn_utils.get_conn() as conn:
        await auth.add_user(conn, username, password)
    return {"success": True}


@app.post("/login")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    try:
        async with conn_utils.get_conn() as conn:
            user = await auth.authenticate_user(conn, form_data.username, form_data.password)
    except auth.InvalidUsernamePass:
        raise HTTPException(status_code=401, detail="Invalid username/password")
    jwt_data = {"user_id": user.id_, "username": user.username, "super_admin": user.super_admin}
    token = auth.create_access_token(jwt_data)
    return RedirectResponse("/modify_directives", status_code=302,
                            headers={"Set-Cookie": f"access_token={token.access_token}; Secure"})


@app.get("/modify_directives")
async def modify_directives_page(request: Request, jwt: Annotated[str, Depends(auth.get_current_jwt)]):
    async with conn_utils.get_conn() as conn:
        directives = await queries.list_directives(conn)

    return templates.TemplateResponse(
        request,
        "modify_directives.jinja",
        context={"request": request, "directives": directives}
    )


# This should stay after all other endpoints
app.mount("/", StaticFiles(directory="static", html=True), name="static")
