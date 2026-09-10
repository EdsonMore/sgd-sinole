# SGD-SINOLE

Sistema de Gestión Documental y de Alertas para SINOLE / FEDUNPE.
Backend en FastAPI + PostgreSQL, pensado para crecer de "una PC" a
"varios usuarios/PCs" sin rehacer la base.

## Estructura del proyecto

```
sgd-sinole/
├── app/
│   ├── main.py            # Endpoints de la API (FastAPI)
│   ├── models.py          # Tablas: Documento, Usuario
│   ├── schemas.py         # Validación de entrada/salida
│   ├── crud.py            # Funciones que hablan con la base de datos
│   ├── business_logic.py  # Cálculo de días hábiles y semáforo (Vencido/Por vencer/En plazo)
│   ├── database.py        # Conexión a PostgreSQL
│   └── config.py          # Lee las variables del .env
├── alembic/                # Migraciones (historial versionado de la BD)
├── requirements.txt
└── .env.example
```

## Paso 1 — Crear la base de datos en pgAdmin

1. Abre pgAdmin, conéctate a tu servidor local (el que ya tienes).
2. Click derecho en **Databases** → **Create** → **Database**.
3. Nombre: `sgd_sinole` → Save.

(No hace falta crear tablas a mano: eso lo hace Alembic en el paso 4).

## Paso 2 — Preparar el entorno de Python

Desde la carpeta del proyecto:

```bash
python -m venv venv
venv\Scripts\activate        # en Windows
# source venv/bin/activate   # en Mac/Linux

pip install -r requirements.txt
```

## Paso 3 — Configurar la conexión

```bash
copy .env.example .env       # en Windows
# cp .env.example .env       # en Mac/Linux
```

Abre `.env` y coloca el usuario/contraseña/puerto que usas en pgAdmin
para conectarte a tu servidor local. Si en pgAdmin tu conexión es la de
por defecto (usuario `postgres`, puerto `5432`), solo cambia
`TU_PASSWORD` por tu contraseña real y `sgd_sinole` ya coincide con el
nombre que creaste en el Paso 1.

## Paso 4 — Crear las tablas (migración)

```bash
alembic upgrade head
```

Esto crea las tablas `usuarios` y `documentos` en tu base `sgd_sinole`.
Puedes verificarlo refrescando el árbol de la base en pgAdmin
(Schemas → public → Tables).

## Paso 5 — Levantar el servidor

```bash
uvicorn app.main:app --reload
```

Abre en el navegador: **http://127.0.0.1:8000/docs**
Ahí verás la documentación interactiva (Swagger) con todos los
endpoints, y puedes probarlos directo desde el navegador sin escribir
nada de frontend todavía.

## Endpoints ya funcionando

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/documentos` | Registrar un documento enviado |
| GET | `/documentos` | Listar todos (con su estado ya calculado) |
| GET | `/documentos?entidad=SINOLE` | Filtrar por entidad |
| GET | `/documentos/{id}` | Ver un documento puntual |
| POST | `/documentos/{id}/vincular-respuesta` | Módulo de "1 clic" para cerrar expediente |
| POST | `/documentos/{id}/carta-reiterativa` | Marcar que se generó la carta reiterativa |

## Cómo se calcula el semáforo

Vive en `app/business_logic.py`, separado de todo lo demás a propósito:
- **En Plazo**: menos de 4 días hábiles transcurridos.
- **Por Vencer**: 4 o 5 días hábiles transcurridos.
- **Vencido**: más de 5 días hábiles transcurridos.
- **Cerrado**: ya tiene una respuesta vinculada.

El estado **nunca se guarda en la base de datos** — se recalcula cada
vez que se pide un documento, así siempre está actualizado a la fecha
de hoy sin necesidad de un proceso aparte que lo actualice.

## Próximos pasos sugeridos (en orden)

1. **Probar el flujo completo desde `/docs`**: crear un documento,
   listarlo, vincular una respuesta.
2. **Migrar el Excel histórico 2025** con un script (`pandas` +
   `crud.crear_documento`) — te lo puedo armar cuando llegues aquí.
3. **Autenticación** (login con `passlib` + JWT) — ya está el modelo
   `Usuario` con roles (`secretaria`, `consulta`, `admin`) listo para
   conectarlo.
4. **Frontend** (panel semáforo visual con Jinja2 + Bootstrap, o React
   más adelante).
5. **Notificaciones de escritorio** (`plyer`/`win10toast` + tarea
   programada de Windows que consulte `/documentos` cada cierto tiempo).
6. **Tests con pytest** para `business_logic.py` — es la lógica más
   crítica y la más fácil de testear sin depender de la base de datos.

## Notas de mantenimiento

- Cualquier cambio a `app/models.py` requiere generar una nueva
  migración: `alembic revision --autogenerate -m "descripcion"` y
  luego `alembic upgrade head`.
- El archivo `.env` **nunca** se sube a git (ya está en `.gitignore`).
  Solo se comparte `.env.example` como plantilla.
