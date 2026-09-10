"""
Configuración central de la app.
Lee las variables desde el archivo .env (que tú creas a partir de .env.example).
Así nunca hay contraseñas escritas directamente en el código.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "dev-secret-key-cambiar"

    # Reglas de negocio configurables sin tocar código
    DIAS_HABILES_LIMITE: int = 5      # a partir de aquí un documento está "Vencido"
    DIAS_HABILES_ALERTA: int = 4      # a partir de aquí entra en "Por Vencer"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
