import logging

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import crud, web, auth_routes
from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.schemas import DocumentoCreate, DocumentoOut, DocumentoVincularRespuesta
from app.business_logic import calcular_estado

# Logging estructurado a stdout/stderr — Uvicorn lo captura en su consola.
# Formato: fecha/hora, nivel, módulo de origen, mensaje.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="SGD-SINOLE", version="0.1.0")

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
    user=Depends(get_current_user),
):
    doc = crud.crear_documento(db, data, usuario_id=user.id)
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
    user=Depends(get_current_user),
):
    doc = crud.vincular_respuesta(db, doc_id, data)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _a_documento_out(doc)


@app.post("/documentos/{doc_id}/carta-reiterativa", response_model=DocumentoOut)
def generar_carta_reiterativa(
    doc_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    doc = crud.marcar_carta_reiterativa(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _a_documento_out(doc)