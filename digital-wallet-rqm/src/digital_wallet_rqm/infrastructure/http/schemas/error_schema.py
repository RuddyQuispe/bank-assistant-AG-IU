from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Cuerpo de todos los errores 4XX y 5XX (ver infrastructure/http/exception_handlers.py)"""

    error: str
    detail: str


# Respuesta 422 para la documentación: reemplaza el HTTPValidationError por defecto de FastAPI,
# porque el handler global responde validaciones con el mismo cuerpo {error, detail}
VALIDATION_ERROR_RESPONSE: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse, "description": "El cuerpo o los parámetros no cumplen el formato esperado"},
}

# Respuesta 401 para la documentación: FastAPI no la publica sola porque la lanza el filtro de auth
UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Falta el token, es inválido o el usuario no existe"},
}

# Respuesta 404 para la documentación: el id de sesión no existe (las sesiones nuevas se crean sin id)
NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "La sesión no existe"},
}

# Respuesta 403 para la documentación: la responde el handler global de ForbiddenError (exception_handlers.py)
FORBIDDEN_RESPONSE: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorResponse, "description": "La sesión pertenece a otro usuario"},
}
