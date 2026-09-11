import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Documento
from app.schemas import DocumentoCreate, DocumentoVincularRespuesta
from app.business_logic import (
    validar_carta_reiterativa,
    MSG_NO_REQUIERE_RESPUESTA,
    MSG_YA_CERRADO,
    MSG_NO_VENCIDO,
    MSG_CARTA_YA_ENVIADA,
)

DOCUMENTO_N_DOCUMENTO_CONSTRAINT = "uq_documentos_n_documento"


class DocumentoDuplicado(Exception):
    """Ya existe un documento con ese número (n_documento)."""


class FechaRecepcionInvalida(Exception):
    """La fecha de recepción es anterior a la fecha de envío del documento."""


class DocumentoNoRequiereRespuesta(Exception):
    """El documento fue registrado con requiere_respuesta=False."""


class DocumentoYaCerrado(Exception):
    """El documento ya tiene una respuesta vinculada."""


class DocumentoNoVencido(Exception):
    """El documento no está en estado VENCIDO; no aplica carta reiterativa."""


class CartaReiterativaYaEnviada(Exception):
    """Ya se envió una carta reiterativa a este documento."""


_CARTA_REITERATIVA_EXCEPCIONES = {
    MSG_NO_REQUIERE_RESPUESTA: DocumentoNoRequiereRespuesta,
    MSG_YA_CERRADO: DocumentoYaCerrado,
    MSG_NO_VENCIDO: DocumentoNoVencido,
    MSG_CARTA_YA_ENVIADA: CartaReiterativaYaEnviada,
}


def crear_documento(db: Session, data: DocumentoCreate, usuario_id: int | None = None) -> Documento:
    doc = Documento(**data.model_dump(), creado_por_id=usuario_id)
    db.add(doc)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == DOCUMENTO_N_DOCUMENTO_CONSTRAINT:
            raise DocumentoDuplicado(data.n_documento) from None
        raise
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
    if not doc.requiere_respuesta:
        raise DocumentoNoRequiereRespuesta(doc_id)
    if doc.esta_cerrado:
        raise DocumentoYaCerrado(doc_id)
    if data.fecha_recepcion < doc.fecha_envio:
        raise FechaRecepcionInvalida(data.fecha_recepcion)
    for campo, valor in data.model_dump().items():
        setattr(doc, campo, valor)
    db.commit()
    db.refresh(doc)
    return doc


def marcar_carta_reiterativa(db: Session, doc_id: int) -> Documento | None:
    doc = db.get(Documento, doc_id)
    if doc is None:
        return None
    try:
        validar_carta_reiterativa(
            requiere_respuesta=doc.requiere_respuesta,
            fecha_envio=doc.fecha_envio,
            fecha_recepcion=doc.fecha_recepcion,
            carta_reiterativa_enviada=doc.carta_reiterativa_enviada,
        )
    except ValueError as exc:
        excepcion = _CARTA_REITERATIVA_EXCEPCIONES.get(str(exc))
        if excepcion is None:
            raise
        raise excepcion(doc_id) from None
    doc.carta_reiterativa_enviada = True
    db.commit()
    db.refresh(doc)
    return doc
