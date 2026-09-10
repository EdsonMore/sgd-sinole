import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Documento
from app.schemas import DocumentoCreate, DocumentoVincularRespuesta


def crear_documento(db: Session, data: DocumentoCreate, usuario_id: int | None = None) -> Documento:
    doc = Documento(**data.model_dump(), creado_por_id=usuario_id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def listar_documentos(db: Session, entidad: str | None = None) -> list[Documento]:
    stmt = select(Documento).order_by(Documento.fecha_envio.desc())
    if entidad:
        stmt = stmt.where(Documento.entidad == entidad)
    return list(db.scalars(stmt))


def obtener_documento(db: Session, doc_id: int) -> Documento | None:
    return db.get(Documento, doc_id)


def vincular_respuesta(db: Session, doc_id: int, data: DocumentoVincularRespuesta) -> Documento | None:
    doc = db.get(Documento, doc_id)
    if doc is None:
        return None
    for campo, valor in data.model_dump().items():
        setattr(doc, campo, valor)
    db.commit()
    db.refresh(doc)
    return doc


def marcar_carta_reiterativa(db: Session, doc_id: int) -> Documento | None:
    doc = db.get(Documento, doc_id)
    if doc is None:
        return None
    doc.carta_reiterativa_enviada = True
    db.commit()
    db.refresh(doc)
    return doc
