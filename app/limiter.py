"""
Limiter único de rate limiting (slowapi), compartido por toda la app.
Se importa desde main.py (para registrarlo en app.state) y desde los
routers que necesiten aplicar límites a sus endpoints (ej. login).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
