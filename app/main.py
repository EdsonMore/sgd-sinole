import logging

from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from slowapi.errors import RateLimitExceeded

from app import crud, web, auth_routes
from app.auth import get_current_user, get_current_editor
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.schemas import DocumentoCreate, DocumentoOut, DocumentoVincularRespuesta
from app.business_logic import calcular_estado

# Logging estructurado a stdout/stderr — Uvicorn lo captura en su consola.
# Formato: fecha/hora, nivel, módulo de origen, mensaje.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="SGD-SINOLE", version="0.1.0")

# Rate limiting por IP (en memoria, suficiente para esta escala).
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Se excedió el límite de intentos en /login: mismo formulario, mensaje claro."""
    return auth_routes.templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Demasiados intentos. Espere un momento e intente de nuevo."},
        status_code=429,
    )

# Middleware de sesión (usa itsdangerous + SECRET_KEY del .env)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Rutas de autenticación (login/logout) — SIN protección
app.include_router(auth_routes.router)

# Rutas del panel (protegidas por sesión en web.py)
app.include_router(web.router)


def _a_documento_out(doc) -> DocumentoOut:
    """Convierte un Documento de la base de datos en la respuesta de la API,
    calculando su estado (semáforo) al vuelo — el estado nunca se guarda
    directamente en la tabla, así siempre está actualizado a 'hoy'."""
    estado = calcular_estado(
        requiere_respuesta=doc.requiere_respuesta,
        fecha_envio=doc.fecha_envio,
        fecha_recepcion=doc.fecha_recepcion,
    )
    return DocumentoOut.model_validate({**doc.__dict__, "estado": estado})


@app.get("/health")
def health():
    """Endpoint simple para confirmar que la API y la conexión a la BD están vivas."""
    return {"status": "ok"}


# --- API protegida (requiere sesión válida) ---

@app.post("/documentos", response_model=DocumentoOut)
def registrar_documento(
    data: DocumentoCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_editor),
):
    try:
        doc = crud.crear_documento(db, data, usuario_id=user.id)
    except crud.DocumentoDuplicado:
        raise HTTPException(status_code=409, detail="Ya existe un documento con ese número")
    return _a_documento_out(doc)


@app.get("/documentos", response_model=list[DocumentoOut])
def listar_documentos(
    entidad: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    docs = crud.listar_documentos(db, entidad)
    return [_a_documento_out(d) for d in docs]


@app.get("/documentos/{doc_id}", response_model=DocumentoOut)
def obtener_documento(
    doc_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    doc = crud.obtener_documento(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _a_documento_out(doc)


@app.post("/documentos/{doc_id}/vincular-respuesta", response_model=DocumentoOut)
def vincular_respuesta(
    doc_id: int,
    data: DocumentoVincularRespuesta,
    db: Session = Depends(get_db),
    user=Depends(get_current_editor),
):
    try:
        doc = crud.vincular_respuesta(db, doc_id, data)
    except crud.DocumentoNoRequiereRespuesta:
        raise HTTPException(status_code=409, detail="Este documento no requiere respuesta")
    except crud.FechaRecepcionInvalida:
        raise HTTPException(status_code=422, detail="La fecha de recepción no puede ser anterior a la fecha de envío")
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _a_documento_out(doc)


@app.post("/documentos/{doc_id}/carta-reiterativa", response_model=DocumentoOut)
def generar_carta_reiterativa(
    doc_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_editor),
):
    doc = crud.marcar_carta_reiterativa(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _a_documento_out(doc)