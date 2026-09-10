"""
Configuración central de la app.
Lee las variables desde el archivo .env (que tú creas a partir de .env.example).
Así nunca hay contraseñas escritas directamente en el código.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    # Si la cookie de sesión debe llevar el atributo Secure (solo HTTPS).
    # Fail-secure: si falta esta variable (ej. deploy mal configurado),
    # el default es True. Solo se desactiva explícitamente en tu .env local
    # (SECURE_COOKIES=false) cuando corres la app sin HTTPS.
    SECURE_COOKIES: bool = True

    # Reglas de negocio configurables sin tocar código
    DIAS_HABILES_LIMITE: int = 5      # a partir de aquí un documento está "Vencido"
    DIAS_HABILES_ALERTA: int = 4      # a partir de aquí entra en "Por Vencer"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
