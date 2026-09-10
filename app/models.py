"""
Modelos = las tablas de la base de datos.
Cada clase de aquí se convierte en una tabla en PostgreSQL cuando
corres la migración de Alembic.
"""
import enum
import datetime

from sqlalchemy import String, Date, Boolean, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EntidadEnum(str, enum.Enum):
    SINOLE = "SINOLE"
    FEDUNPE = "FEDUNPE"


class RolEnum(str, enum.Enum):
    SECRETARIA = "secretaria"       # puede crear/editar/cerrar documentos
    CONSULTA = "consulta"           # solo puede ver el panel (dirigentes)
    ADMIN = "admin"                 # gestiona usuarios


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[RolEnum] = mapped_column(Enum(RolEnum), default=RolEnum.CONSULTA)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Documento(Base):
    """
    Una fila = un documento ENVIADO (equivalente a una fila del Excel
    'Documentos Enviados 2025'). La respuesta, si llega, se guarda en
    los mismos campos (fecha_recepcion, n_documento_respuesta, etc.)
    en vez de crear una tabla aparte, igual que en el Excel actual.
    """
    __tablename__ = "documentos"
    __table_args__ = (
        UniqueConstraint("n_documento", name="uq_documentos_n_documento"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- Datos del documento enviado ---
    entidad: Mapped[EntidadEnum] = mapped_column(Enum(EntidadEnum), index=True)
    fecha_envio: Mapped[datetime.date] = mapped_column(Date)
    n_documento: Mapped[str] = mapped_column(String(50))
    asunto: Mapped[str] = mapped_column(Text)
    destinatario: Mapped[str] = mapped_column(String(200))
    cc: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requiere_respuesta: Mapped[bool] = mapped_column(Boolean, default=False)
    carta_reiterativa_enviada: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Datos de la respuesta (se llenan al vincular, o quedan vacíos) ---
    fecha_recepcion: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    n_documento_respuesta: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asunto_respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    responde: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Trazabilidad de quién lo registró ---
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creado_por: Mapped["Usuario"] = relationship()

    @property
    def esta_cerrado(self) -> bool:
        """Un documento se considera cerrado cuando ya tiene respuesta vinculada."""
        return self.fecha_recepcion is not None
