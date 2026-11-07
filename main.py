import datetime
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Request, Form, Cookie, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from jwt import InvalidTokenError
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


async def get_active_jwt(request: Request, access_token: Annotated[str, Cookie()]) -> dict:
    try:
        jwt_data = auth.get_current_jwt(access_token)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="JWT token is invalid")
    async with conn_utils.get_conn() as conn:
        valid = await queries.check_user_enabled(conn, id_=jwt_data["user_id"])
    if not valid:
        raise HTTPException(status_code=403, detail="JWT token belongs to an inactive account")
    request.state.jwt = jwt_data
    return jwt_data


@app.middleware("http")
async def refresh_jwt(request: Request, call_next):
    response = await call_next(request)

    if "jwt" not in request.state:
        return response

    jwt_exp = datetime.datetime.fromtimestamp(request.state.jwt["exp"])
    issued_time = jwt_exp - datetime.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    if issued_time + datetime.timedelta(minutes=10) < datetime.datetime.now():
        token = auth.create_access_token(request.state.jwt)
        response.headers["Set-Cookie"] = f"access_token={token.access_token}; Secure"
    return response


@app.post("/user/add")
async def add_user(username: str, password: str, jwt: Annotated[dict, Depends(get_active_jwt)]):
    if not jwt.get("super_admin"):
        raise HTTPException(status_code=403, detail="You must be a super admin to add a new account")
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
    return RedirectResponse("/directives", status_code=302,
                            headers={"Set-Cookie": f"access_token={token.access_token}; Secure"})


@app.get("/directives")
async def directives_page(request: Request, jwt: Annotated[dict, Depends(get_active_jwt)]):
    async with conn_utils.get_conn() as conn:
        directives = await queries.list_directives(conn)

    return templates.TemplateResponse(
        request,
        "directives.jinja",
        context={"request": request, "directives": directives}
    )


@app.post("/add_directive")
async def add_directive(jwt: Annotated[dict, Depends(get_active_jwt)],
                        directive_type: Annotated[str, Form()],
                        selector_type: Annotated[str, Form()],
                        selector: Annotated[str, Form()],
                        change_note: Annotated[str, Form()],
                        directive_data: Annotated[str | None, Form()] = None,
                        origin: Annotated[str, Form()] = "*"):
    async with conn_utils.get_conn() as conn:
        await queries.add_directive_with_audit(conn,
                                               selector_type=selector_type,
                                               selector=selector,
                                               directive_type=directive_type,
                                               directive_data=directive_data,
                                               applies_to=origin,
                                               note=change_note,
                                               user_id=int(jwt["user_id"]))
    return RedirectResponse("/directives", status_code=302)


@app.post("/set_directive_status")
async def set_directive_status(jwt: Annotated[dict, Depends(get_active_jwt)],
                               directive_id: Annotated[int, Form()],
                               note: Annotated[str, Form()],
                               enabled: Annotated[bool, Form()] = False):
    action = "enabled" if enabled else "disabled"
    async with conn_utils.get_conn() as conn:
        async with conn.transaction():
            await queries.set_directive_status(conn, id_=directive_id, active=enabled)
            await queries.add_audit(conn, user_id=int(jwt["user_id"]), note=note, directive=directive_id, action=action)
    return RedirectResponse(f"/directives/{directive_id}", status_code=302)


@app.post("/add_audit_note")
async def add_note_to_directive(jwt: Annotated[dict, Depends(get_active_jwt)],
                                directive_id: Annotated[int, Form()],
                                note: Annotated[str, Form()]):
    async with conn_utils.get_conn() as conn:
        await queries.add_audit(conn, user_id=int(jwt["user_id"]), note=note, directive=directive_id, action="note")
    return RedirectResponse(f"/directives/{directive_id}", status_code=302)


@app.get("/directives/{directive_id}")
async def get_directive_page(request: Request,
                             jwt: Annotated[dict, Depends(get_active_jwt)],
                             directive_id: int):
    async with conn_utils.get_conn() as conn:
        directive = await queries.get_directive(conn, id_=directive_id)
        audit_log = await queries.get_directive_audits(conn, directive=directive_id)
    if audit_log is None:
        raise HTTPException(status_code=404, detail="Could not find that directive")
    return templates.TemplateResponse(
        request,
        "directive_page.jinja",
        context={"directive": directive, "audit_log": audit_log}
    )


@app.get("/api/check_work_status")
async def check_work_status(work_id: int, authors: Annotated[list[str], Query()], site: str):
    async with conn_utils.get_conn() as conn:
        directives = await queries.get_work_directives(conn, work_id=str(work_id), authors=authors, origin=site)

    permission = True
    for directive in directives:
        if directive.directive_type in ["removed_notice", "removed_notice_note", "do_not_serve"]:
            permission = False
            continue
        if directive.directive_type == "no_restrictions":
            permission = True
            break

    return {"permission": permission, "directives": directives}


# This should stay after all other endpoints
app.mount("/", StaticFiles(directory="static", html=True), name="static")
