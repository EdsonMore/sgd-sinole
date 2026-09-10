"""
Aquí vive la regla de negocio más importante del sistema: el semáforo
de plazos (En Plazo / Por Vencer / Vencido). Está separada del resto
del código a propósito, para poder testearla sola sin necesitar un
servidor ni una base de datos corriendo.
"""
import datetime
import enum

from app.config import settings


class EstadoDocumento(str, enum.Enum):
    EN_PLAZO = "EN_PLAZO"
    POR_VENCER = "POR_VENCER"
    VENCIDO = "VENCIDO"
    CERRADO = "CERRADO"          # ya tiene respuesta vinculada
    NO_APLICA = "NO_APLICA"      # requiere_respuesta = False


def contar_dias_habiles(fecha_inicio: datetime.date, fecha_fin: datetime.date) -> int:
    """
    Cuenta días hábiles (lunes a viernes) entre dos fechas, sin contar
    el día de inicio. Ej: si se envió un lunes y hoy es martes, es 1 día hábil.

    Nota: esta versión no descuenta feriados peruanos. Si eso se vuelve
    necesario, se puede sumar una tabla `feriados` y filtrar aquí mismo
    sin tocar el resto del sistema.
    """
    if fecha_fin <= fecha_inicio:
        return 0

    dias = 0
    cursor = fecha_inicio
    while cursor < fecha_fin:
        cursor += datetime.timedelta(days=1)
        if cursor.weekday() < 5:  # 0=lunes ... 4=viernes
            dias += 1
    return dias


def calcular_estado(
    requiere_respuesta: bool,
    fecha_envio: datetime.date,
    fecha_recepcion: datetime.date | None,
    hoy: datetime.date | None = None,
) -> EstadoDocumento:
    """
    Determina en qué color del semáforo cae un documento.
    """
    if not requiere_respuesta:
        return EstadoDocumento.NO_APLICA

    if fecha_recepcion is not None:
        return EstadoDocumento.CERRADO

    hoy = hoy or datetime.date.today()
    dias_transcurridos = contar_dias_habiles(fecha_envio, hoy)

    if dias_transcurridos > settings.DIAS_HABILES_LIMITE:
        return EstadoDocumento.VENCIDO
    if dias_transcurridos >= settings.DIAS_HABILES_ALERTA:
        return EstadoDocumento.POR_VENCER
    return EstadoDocumento.EN_PLAZO
