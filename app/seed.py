"""
Script para crear el primer usuario de la aplicación.

Crea (o resetea) una cuenta de secretaria con rol SECRETARIA.
Ejecútalo una sola vez, desde la carpeta del proyecto:

    python -m app.seed

Después inicia sesión con el email y contraseña que imprime, y cambia
la contraseña por una propia. La contraseña se guarda hasheada (bcrypt),
nunca en texto plano.
"""
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Usuario, RolEnum
from app.auth import hash_password

EMAIL_SECRETARIA = "secretaria@sinole.org"
PASSWORD_INICIAL = "cambiar123"
NOMBRE = "Secretaria SINOLE"


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(Usuario).where(Usuario.email == EMAIL_SECRETARIA))

        if existing is not None:
            # Reset seguro: actualiza la contraseña y rol, sin duplicar.
            existing.nombre = NOMBRE
            existing.password_hash = hash_password(PASSWORD_INICIAL)
            existing.rol = RolEnum.SECRETARIA
            existing.activo = True
            print(f"Usuario existente actualizado: {EMAIL_SECRETARIA}")
        else:
            db.add(Usuario(
                nombre=NOMBRE,
                email=EMAIL_SECRETARIA,
                password_hash=hash_password(PASSWORD_INICIAL),
                rol=RolEnum.SECRETARIA,
                activo=True,
            ))
            print(f"Usuario creado: {EMAIL_SECRETARIA}")

        db.commit()
        print(f"Email:      {EMAIL_SECRETARIA}")
        print(f"Contrasena: {PASSWORD_INICIAL}")
        print("Rol:        secretaria")
        print("\nIMPORTANTE: cambia esta contraseña lo antes posible.")
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()