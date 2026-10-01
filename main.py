"""Backend local del localizador (sin AWS).

    python -m uvicorn main:app --reload

Expone la misma API que API Gateway + Lambda, bajo /api, con SQLite en lugar de
DynamoDB y un simulador en lugar de IoT Core. La lógica de negocio es la misma
capa `layers/common/localizador` que usan las Lambdas. Si existe `frontend/dist`,
también sirve la app web en http://127.0.0.1:8000.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "layers" / "common"))

from fastapi import APIRouter, FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from localizador import paginacion, validacion  # noqa: E402
from localizador.errores import ErrorAplicacion  # noqa: E402
from localizador.servicios import (  # noqa: E402
    ServicioBusquedas,
    ServicioCategorias,
    ServicioLocalizacion,
    ServicioMovimientos,
    ServicioObjetos,
    ServicioPlano,
)
from servidor_local.almacen_sqlite import (  # noqa: E402
    BaseLocal,
    PublicadorLedSqlite,
    RepositorioBusquedasSqlite,
    RepositorioCategoriasSqlite,
    RepositorioMovimientosSqlite,
    RepositorioObjetosSqlite,
    SimuladorNodos,
)

logger = logging.getLogger("localizador.local")

RUTA_BD = Path(os.environ.get("LOCALIZADOR_BD") or RAIZ / "datos_local" / "localizador.db")
DIST = RAIZ / "frontend" / "dist"
ORIGENES_CORS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOW_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

base = BaseLocal(RUTA_BD)
repositorio_objetos = RepositorioObjetosSqlite(base)
repositorio_categorias = RepositorioCategoriasSqlite(base)
servicio_objetos = ServicioObjetos(repositorio_objetos, repositorio_categorias)
servicio_categorias = ServicioCategorias(repositorio_categorias, repositorio_objetos)
repositorio_busquedas = RepositorioBusquedasSqlite(base)
servicio_localizacion = ServicioLocalizacion(
    repositorio_objetos, PublicadorLedSqlite(base), repositorio_busquedas
)
servicio_plano = ServicioPlano(repositorio_objetos)
servicio_movimientos = ServicioMovimientos(
    RepositorioMovimientosSqlite(base), repositorio_busquedas
)
servicio_busquedas = ServicioBusquedas(repositorio_busquedas)
simulador = SimuladorNodos(base)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
    base.inicializar()
    logger.info("Base local lista en %s", RUTA_BD)
    if (DIST / "index.html").exists():
        logger.info("App web disponible en http://127.0.0.1:8000")
    else:
        logger.info("Frontend sin compilar: ejecuta 'npm run build' en frontend/ o usa 'npm run dev'.")
    yield


app = FastAPI(
    title="Localizador de objetos — modo local",
    description="Misma API que AWS (API Gateway + Lambda), con SQLite y simulador de nodos ESP32.",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_CORS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(ErrorAplicacion)
async def error_de_aplicacion(_: Request, exc: ErrorAplicacion) -> JSONResponse:
    cuerpo = {"error": exc.codigo, "mensaje": exc.mensaje}
    if exc.detalles:
        cuerpo["detalles"] = exc.detalles
    return JSONResponse(cuerpo, status_code=exc.estado_http)


@app.exception_handler(Exception)
async def error_inesperado(_: Request, exc: Exception) -> JSONResponse:
    logger.error("Error no controlado", exc_info=exc)
    return JSONResponse(
        {"error": "error_interno", "mensaje": "Error interno del servidor."}, status_code=500
    )


async def _evento(request: Request, **ruta: str) -> dict:
    """Traduce la petición al formato de evento de API Gateway.

    Así se reutilizan exactamente las mismas funciones de validación que usan
    las Lambdas, sin reglas duplicadas.
    """
    cuerpo = None
    if request.method in ("POST", "PUT"):
        cuerpo = (await request.body()).decode("utf-8", errors="replace")
    return {
        "queryStringParameters": dict(request.query_params) or None,
        "pathParameters": ruta or None,
        "body": cuerpo,
    }


api = APIRouter(prefix="/api")


@api.get("/objetos")
async def listar_objetos(request: Request):
    e = await _evento(request)
    return servicio_objetos.listar(
        validacion.parametro_query(e, "categoria"),
        validacion.limite_pagina(e),
        paginacion.decodificar_cursor(validacion.parametro_query(e, "cursor")),
        validacion.parametro_query(e, "q"),
    )


@api.get("/objetos/{object_id}")
async def obtener_objeto(request: Request, object_id: str):
    e = await _evento(request, object_id=object_id)
    return servicio_objetos.obtener(validacion.parametro_ruta(e, "object_id"))


@api.post("/objetos", status_code=201)
async def crear_objeto(request: Request):
    e = await _evento(request)
    return servicio_objetos.crear(validacion.cuerpo_json(e))


@api.put("/objetos/{object_id}")
async def actualizar_objeto(request: Request, object_id: str):
    e = await _evento(request, object_id=object_id)
    return servicio_objetos.actualizar(
        validacion.parametro_ruta(e, "object_id"), validacion.cuerpo_json(e)
    )


@api.delete("/objetos/{object_id}")
async def eliminar_objeto(request: Request, object_id: str):
    e = await _evento(request, object_id=object_id)
    return servicio_objetos.eliminar(validacion.parametro_ruta(e, "object_id"))


@api.post("/objetos/{object_id}/localizar", status_code=202)
async def localizar_objeto(request: Request, object_id: str):
    e = await _evento(request, object_id=object_id)
    object_id = validacion.parametro_ruta(e, "object_id")
    duracion = validacion.duracion_localizacion(validacion.cuerpo_json(e, obligatorio=False))
    return servicio_localizacion.localizar(object_id, duracion)


@api.post("/busquedas", status_code=201)
async def registrar_busqueda_control(request: Request):
    """Medicion manual de referencia: cuanto tardaba encontrar el objeto sin el sistema."""
    e = await _evento(request)
    return servicio_busquedas.registrar_control(validacion.cuerpo_json(e))


@api.post("/busquedas/{busqueda_id}/confirmar")
async def confirmar_busqueda(request: Request, busqueda_id: str):
    e = await _evento(request, busqueda_id=busqueda_id)
    return servicio_busquedas.confirmar(validacion.parametro_ruta(e, "busqueda_id"))


@api.get("/metricas/localizacion")
async def metricas_localizacion():
    return servicio_busquedas.resumen()


@api.post("/movimientos", status_code=201)
async def registrar_movimiento(request: Request):
    e = await _evento(request)
    return servicio_movimientos.registrar(validacion.cuerpo_json(e))


@api.get("/movimientos")
async def listar_movimientos(request: Request):
    e = await _evento(request)
    return servicio_movimientos.listar(
        validacion.parametro_query_obligatorio(e, "object_id"),
        validacion.limite_pagina(e),
        paginacion.decodificar_cursor(validacion.parametro_query(e, "cursor")),
    )


@api.get("/almacenes")
async def listar_almacenes():
    return servicio_plano.almacenes()


@api.get("/almacenes/{almacen_id}/plano")
async def obtener_plano(request: Request, almacen_id: str):
    e = await _evento(request, almacen_id=almacen_id)
    return servicio_plano.obtener(validacion.parametro_ruta(e, "almacen_id"))


@api.get("/categorias")
async def listar_categorias(request: Request):
    e = await _evento(request)
    return servicio_categorias.listar(
        validacion.limite_pagina(e),
        paginacion.decodificar_cursor(validacion.parametro_query(e, "cursor")),
    )


@api.post("/categorias", status_code=201)
async def crear_categoria(request: Request):
    e = await _evento(request)
    return servicio_categorias.crear(validacion.cuerpo_json(e))


@api.put("/categorias/{categoria_id}")
async def actualizar_categoria(request: Request, categoria_id: str):
    e = await _evento(request, categoria_id=categoria_id)
    return servicio_categorias.actualizar(
        validacion.parametro_ruta(e, "categoria_id"), validacion.cuerpo_json(e)
    )


@api.delete("/categorias/{categoria_id}")
async def eliminar_categoria(request: Request, categoria_id: str):
    e = await _evento(request, categoria_id=categoria_id)
    return servicio_categorias.eliminar(validacion.parametro_ruta(e, "categoria_id"))


# --- Solo en local: sustituye a los nodos ESP32 físicos -------------------------------


@api.get("/simulador/almacenes")
async def almacenes_simulados():
    return {"elementos": simulador.almacenes()}


@api.get("/simulador/almacenes/{almacen_id}/led")
async def estado_tira(almacen_id: str):
    return simulador.estado(almacen_id)


@api.get("/salud")
async def salud():
    return {"estado": "ok", "modo": "local", "base_de_datos": RUTA_BD.name}


app.include_router(api)

# --- App web compilada (frontend/dist) ------------------------------------------------

app.mount("/assets", StaticFiles(directory=DIST / "assets", check_dir=False), name="assets")


@app.get("/{ruta:path}", include_in_schema=False)
async def app_web(ruta: str):
    if ruta.startswith("api/"):
        return JSONResponse(
            {"error": "no_encontrado", "mensaje": "Ruta de API no encontrada."}, status_code=404
        )
    indice = DIST / "index.html"
    if not indice.exists():
        return JSONResponse(
            {
                "mensaje": "API local funcionando. El frontend aún no está compilado.",
                "compilar": "cd frontend && npm run build",
                "api": "/api/objetos",
                "documentacion": "/docs",
            }
        )
    archivo = (DIST / ruta).resolve()
    if ruta and archivo.is_file() and archivo.is_relative_to(DIST.resolve()):
        return FileResponse(archivo)
    return FileResponse(indice)
