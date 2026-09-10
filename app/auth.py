"""
Autenticación y sesión.

Diseño para la secretaria real (usuaria no técnica, sobrecargada):
- Login de 1 paso.
- Sesión persistente en cookie firmada (itsdangerous), httpOnly.
- Expiración fija de 8 horas (una jornada laboral): entra al empezar
  el día y no se le vuelve a preguntar hasta mañana.
"""
import datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.hash import bcrypt

from app.config import settings
from app.database import get_db
from app.models import Usuario

# Nombre de la cookie y duración de la sesión.
COOKIE_NAME = "sgd_sesion"
SESION_HORAS = 8  # jornada laboral de la secretaria

# Firmante de la cookie: cifra y vence el identificador del usuario.
_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="sgd-sesion")


def hash_password(plain: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash almacenado."""
    try:
        return bcrypt.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


def crear_token_sesion(user_id: int) -> str:
    """Firma el id del usuario con expiración de SESION_HORAS horas."""
    return _serializer.dumps({"user_id": user_id})


def leer_token_sesion(token: str) -> int | None:
    """
    Devuelve el id del usuario si la cookie es válida y no venció,
    o None en caso contrario (firma inválida o expirada).
    """
    try:
        data = _serializer.loads(token, max_age=SESION_HORAS * 3600)
        return int(data["user_id"])
    except (BadSignature, SignatureExpired, KeyError, ValueError):
        return None


def obtener_usuario_actual(request: Request, db: Session) -> Usuario | None:
    """Lee la cookie de sesión del request y devuelve el Usuario si existe y está activo."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = leer_token_sesion(token)
    if user_id is None:
        return None
    user = db.get(Usuario, user_id)
    if user is None or not user.activo:
        return None
    return user


# --- Dependencias inyectables en las rutas ---

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Obligatoria: devuelve el usuario logueado o lanza 401 si no hay sesión válida."""
    user = obtener_usuario_actual(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Usuario | None:
    """Opcional: devuelve el usuario logueado o None (para vistas que adaptan UI al rol)."""
    return obtener_usuario_actual(request, db)


def es_rol(usuario: Usuario | None, *roles: str) -> bool:
    """True si el usuario tiene alguno de los roles indicados."""
    if usuario is None:
        return False
    return usuario.rol.value in roles