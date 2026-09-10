"""
Rutas de autenticación: login y logout.

Diseño para la secretaria (una usuaria real, no técnica):
- Login de 1 paso, sin fricción.
- Error humano: "Correo o contraseña incorrectos".
- Cookie firmada httpOnly, expiración 8h (jornada).
- Logout visible con confirmación mínima.
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import (
    COOKIE_NAME,
    SESION_HORAS,
    crear_token_sesion,
    get_current_user,
    hash_password,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models import Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", name="login")
def login_form(request: Request, error: str | None = None):
    """Pantalla de login mínima y clara."""
    return templates.TemplateResponse(
        request, "login.html",
        {"error": error or None},
    )


@router.post("/login")
def login_submit(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Verifica credenciales, crea cookie de sesión y redirige al panel."""
    user = db.query(Usuario).filter(Usuario.email == email).first()

    if user is None or not user.activo or not verify_password(password, user.password_hash):
        # Mismo mensaje genérico: no revela si el email existe o no.
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Correo o contraseña incorrectos"},
            status_code=401,
        )

    # Credenciales OK → firma la cookie con el user_id
    token = crear_token_sesion(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESION_HORAS * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.SECURE_COOKIES,  # False solo si SECURE_COOKIES=false en tu .env local
        path="/",
    )
    return response


@router.get("/logout", name="logout")
def logout():
    """Cierra la sesión borrando la cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response