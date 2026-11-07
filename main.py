from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Request, Form
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
async def modify_directives_page(request: Request, jwt: Annotated[dict, Depends(auth.get_current_jwt)]):
    async with conn_utils.get_conn() as conn:
        directives = await queries.list_directives(conn)

    return templates.TemplateResponse(
        request,
        "modify_directives.jinja",
        context={"request": request, "directives": directives}
    )


@app.post("/add_directive")
async def add_directive(jwt: Annotated[dict, Depends(auth.get_current_jwt)],
                        directive_type: Annotated[str, Form()],
                        selector_type: Annotated[str, Form()],
                        selector: Annotated[str, Form()],
                        change_note: Annotated[str, Form()],
                        directive_data: Annotated[str | None, Form()] = None,
                        ):
    async with conn_utils.get_conn() as conn:
        await queries.add_directive_with_audit(conn,
                                               selector_type=selector_type,
                                               selector=selector,
                                               directive_type=directive_type,
                                               directive_data=directive_data,
                                               applies_to="*",
                                               note=change_note,
                                               user_id=int(jwt["user_id"]))
    return RedirectResponse("/modify_directives", status_code=302)


@app.post("/set_directive_status")
async def set_directive_status(jwt: Annotated[dict, Depends(auth.get_current_jwt)],
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
async def add_note_to_directive(jwt: Annotated[dict, Depends(auth.get_current_jwt)],
                                directive_id: Annotated[int, Form()],
                                note: Annotated[str, Form()]):
    async with conn_utils.get_conn() as conn:
        await queries.add_audit(conn, user_id=int(jwt["user_id"]), note=note, directive=directive_id, action="note")
    return RedirectResponse(f"/directives/{directive_id}", status_code=302)


@app.get("/directives/{directive_id}")
async def get_directive_page(request: Request,
                             jwt: Annotated[dict, Depends(auth.get_current_jwt)],
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


# This should stay after all other endpoints
app.mount("/", StaticFiles(directory="static", html=True), name="static")
