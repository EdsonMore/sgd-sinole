"""
Rutas del frontend (server-rendered con Jinja2).

Protegidas por sesión: si no hay usuario, redirige a /login.
La UI se adapta al rol: secretaria ve CRUD; consulta solo lectura.
"""
import datetime
import logging

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import crud
from app.auth import get_current_user_optional, es_rol
from app.database import get_db
from app.business_logic import calcular_estado, EstadoDocumento

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

logger = logging.getLogger(__name__)


# Mapa estado -> etiqueta legible para la secretaria
LABEL_ESTADO = {
    EstadoDocumento.EN_PLAZO: "En plazo",
    EstadoDocumento.POR_VENCER: "Por vencer",
    EstadoDocumento.VENCIDO: "Vencido",
    EstadoDocumento.CERRADO: "Cerrado",
    EstadoDocumento.NO_APLICA: "Sin respuesta",
}


def _decorar(doc):
    """Agrega a un documento su estado y etiqueta legible."""
    estado = calcular_estado(
        requiere_respuesta=doc.requiere_respuesta,
        fecha_envio=doc.fecha_envio,
        fecha_recepcion=doc.fecha_recepcion,
    )
    doc.estado = estado
    doc.estado_label = LABEL_ESTADO[estado]
    return doc


def _require_user(request: Request, user) -> RedirectResponse | None:
    """Si no hay usuario, redirige a login con mensaje claro."""
    if user is None:
        return RedirectResponse(url="/login?next=/", status_code=303)
    return None


@router.get("/", name="panel")
def panel(
    request: Request,
    entidad: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    # Protección: sin sesión -> login
    redirect = _require_user(request, user)
    if redirect:
        return redirect

    docs = crud.listar_documentos(db, entidad)
    docs = [_decorar(d) for d in docs]

    conteo = {
        "en_plazo": 0,
        "por_vencer": 0,
        "vencido": 0,
        "cerrado": 0,
        "no_aplica": 0,
    }
    for d in docs:
        clave = {
            EstadoDocumento.EN_PLAZO: "en_plazo",
            EstadoDocumento.POR_VENCER: "por_vencer",
            EstadoDocumento.VENCIDO: "vencido",
            EstadoDocumento.CERRADO: "cerrado",
            EstadoDocumento.NO_APLICA: "no_aplica",
        }[d.estado]
        conteo[clave] += 1

    return templates.TemplateResponse(
        request, "panel.html",
        {
            "documentos": docs,
            "conteo": conteo,
            "entidad": entidad or "",
            "user": user,
            "puede_crear": es_rol(user, "secretaria", "admin"),
        },
    )


@router.get("/registrar", name="formulario_registro")
def formulario_registro(
    request: Request,
    user=Depends(get_current_user_optional),
):
    redirect = _require_user(request, user)
    if redirect:
        return redirect
    # Solo secretaria/admin pueden ver este formulario
    if not es_rol(user, "secretaria", "admin"):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request, "registro.html",
        {"hoy": datetime.date.today().isoformat(), "user": user},
    )


@router.post("/registrar")
def registrar_documento_form(
    request: Request,
    entidad: str = Form(...),
    fecha_envio: str = Form(...),
    n_documento: str = Form(...),
    asunto: str = Form(...),
    destinatario: str = Form(...),
    cc: str | None = Form(None),
    requiere_respuesta: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    redirect = _require_user(request, user)
    if redirect:
        return redirect
    if not es_rol(user, "secretaria", "admin"):
        return RedirectResponse(url="/", status_code=303)

    try:
        from app.schemas import DocumentoCreate
        from app.models import EntidadEnum

        data = DocumentoCreate(
            entidad=EntidadEnum(entidad),
            fecha_envio=datetime.date.fromisoformat(fecha_envio),
            n_documento=n_documento,
            asunto=asunto,
            destinatario=destinatario,
            cc=cc or None,
            requiere_respuesta=requiere_respuesta == "true",
        )
        crud.crear_documento(db, data, usuario_id=user.id)
    except ValidationError as exc:
        mensaje = exc.errors()[0]["msg"].removeprefix("Value error, ")
        return templates.TemplateResponse(
            request, "registro.html",
            {"hoy": fecha_envio, "error": mensaje, "user": user},
            status_code=400,
        )
    except crud.DocumentoDuplicado:
        return templates.TemplateResponse(
            request, "registro.html",
            {"hoy": fecha_envio, "error": "Ya existe un documento con ese número", "user": user},
            status_code=400,
        )
    except Exception:
        logger.exception(
            "Error al registrar documento (usuario_id=%s, entidad=%s, n_documento=%s)",
            user.id, entidad, n_documento,
        )
        return templates.TemplateResponse(
            request, "registro.html",
            {"hoy": fecha_envio, "error": "Error al guardar. Intente nuevamente o contacte al administrador.", "user": user},
            status_code=400,
        )
    return RedirectResponse(url="/", status_code=303)


@router.get("/documentos/{doc_id}/vincular", name="formulario_vincular")
def formulario_vincular(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    redirect = _require_user(request, user)
    if redirect:
        return redirect
    if not es_rol(user, "secretaria", "admin"):
        return RedirectResponse(url="/", status_code=303)

    doc = crud.obtener_documento(db, doc_id)
    if doc is None:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request, "vincular.html",
        {"doc": doc, "hoy": datetime.date.today().isoformat(), "user": user},
    )


@router.post("/documentos/{doc_id}/vincular")
def vincular_respuesta_form(
    request: Request,
    doc_id: int,
    fecha_recepcion: str = Form(...),
    n_documento_respuesta: str = Form(...),
    asunto_respuesta: str = Form(...),
    responde: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    redirect = _require_user(request, user)
    if redirect:
        return redirect
    if not es_rol(user, "secretaria", "admin"):
        return RedirectResponse(url="/", status_code=303)

    doc = crud.obtener_documento(db, doc_id)
    if doc is None:
        return RedirectResponse(url="/", status_code=303)
    try:
        from app.schemas import DocumentoVincularRespuesta

        data = DocumentoVincularRespuesta(
            fecha_recepcion=datetime.date.fromisoformat(fecha_recepcion),
            n_documento_respuesta=n_documento_respuesta,
            asunto_respuesta=asunto_respuesta,
            responde=responde,
        )
        crud.vincular_respuesta(db, doc_id, data)
    except crud.FechaRecepcionInvalida:
        return templates.TemplateResponse(
            request, "vincular.html",
            {"doc": doc, "hoy": fecha_recepcion, "error": "La fecha de recepción no puede ser anterior a la fecha de envío", "user": user},
            status_code=422,
        )
    except Exception:
        logger.exception(
            "Error al vincular respuesta (usuario_id=%s, doc_id=%s)",
            user.id, doc_id,
        )
        return templates.TemplateResponse(
            request, "vincular.html",
            {"doc": doc, "hoy": fecha_recepcion, "error": "Error al guardar. Intente nuevamente o contacte al administrador.", "user": user},
            status_code=400,
        )
    return RedirectResponse(url="/", status_code=303)