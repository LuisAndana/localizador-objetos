"""Errores de dominio que se traducen a codigos HTTP en la capa de respuesta."""


class ErrorAplicacion(Exception):
    """Error esperado y seguro de mostrar al cliente."""

    estado_http = 500
    codigo = "error_interno"

    def __init__(self, mensaje: str, detalles: dict | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles or {}


class ErrorValidacion(ErrorAplicacion):
    estado_http = 400
    codigo = "peticion_invalida"


class ErrorProhibido(ErrorAplicacion):
    estado_http = 403
    codigo = "prohibido"


class ErrorNoEncontrado(ErrorAplicacion):
    estado_http = 404
    codigo = "no_encontrado"


class ErrorConflicto(ErrorAplicacion):
    estado_http = 409
    codigo = "conflicto"
