import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import EntidadEnum
from app.business_logic import EstadoDocumento


class DocumentoCreate(BaseModel):
    """Lo que se envía al REGISTRAR un documento nuevo (paso 'Registro de Salida')."""
    entidad: EntidadEnum
    fecha_envio: datetime.date
    n_documento: str
    asunto: str
    destinatario: str
    cc: str | None = None
    requiere_respuesta: bool = False

    @field_validator("fecha_envio")
    @classmethod
    def fecha_envio_no_futura(cls, valor: datetime.date) -> datetime.date:
        if valor > datetime.date.today():
            raise ValueError("La fecha de envío no puede ser futura")
        return valor


class DocumentoVincularRespuesta(BaseModel):
    """Lo que se envía al usar el módulo de '1 clic' para cerrar un expediente."""
    fecha_recepcion: datetime.date
    n_documento_respuesta: str
    asunto_respuesta: str
    responde: str


class DocumentoOut(BaseModel):
    """Lo que la API devuelve: los datos del documento + su estado calculado."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    entidad: EntidadEnum
    fecha_envio: datetime.date
    n_documento: str
    asunto: str
    destinatario: str
    cc: str | None
    requiere_respuesta: bool
    carta_reiterativa_enviada: bool
    fecha_recepcion: datetime.date | None
    n_documento_respuesta: str | None
    asunto_respuesta: str | None
    responde: str | None
    estado: EstadoDocumento


class DocumentoAlerta(BaseModel):
    """Resumen mínimo de un documento VENCIDO/POR_VENCER, para las notificaciones de escritorio."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    n_documento: str
    entidad: EntidadEnum
    estado: EstadoDocumento
