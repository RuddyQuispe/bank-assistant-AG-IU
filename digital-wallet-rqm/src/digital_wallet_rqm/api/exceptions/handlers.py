import logging
import traceback
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InvalidCredentialsError,
    NotFoundError,
    UnauthorizedError,
)

logger = logging.getLogger(__name__)

# Equivalente a los @ExceptionHandler de un @RestControllerAdvice: tipo de error -> status HTTP.
# Una subclase (p. ej. SessionForbiddenError) usa el status de su padre más cercano.
_STATUS_BY_ERROR: dict[type[AppError], int] = {
    BadRequestError: status.HTTP_400_BAD_REQUEST,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
}

# Campo "error" para los errores que lanza FastAPI/Starlette (ruta inexistente, método no permitido...)
_ERROR_BY_STATUS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "Petición inválida",
    status.HTTP_401_UNAUTHORIZED: "No autenticado",
    status.HTTP_403_FORBIDDEN: "Acceso denegado",
    status.HTTP_404_NOT_FOUND: "Recurso no encontrado",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Método no permitido",
    status.HTTP_409_CONFLICT: "Conflicto",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Datos inválidos",
}

INTERNAL_ERROR = "Error interno del servidor"
INTERNAL_ERROR_DETAIL = "Ocurrió un error inesperado; el detalle quedó en el log del servidor"


def error_body(error: str, detail: str) -> dict[str, str]:
    """Cuerpo único de los errores 4XX y 5XX"""
    return {"error": error, "detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    """Registra el manejo global de errores; se llama una vez en create_app()"""
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    # Cualquier otra excepción: 500; el traceback siempre va al log
    app.add_exception_handler(Exception, _handle_unexpected_error)


def _status_for(error: AppError) -> int | None:
    for error_type in type(error).__mro__:
        if error_type in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[error_type]
    return None


async def _handle_app_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, AppError)
    status_code = _status_for(error)
    if status_code is None:
        # AppError sin tipo específico: se trata como error interno para no exponer su mensaje
        return await _handle_unexpected_error(request, error)

    # El reto Bearer solo aplica a rutas protegidas por token; el login fallido no lo lleva
    needs_challenge = isinstance(error, UnauthorizedError) and not isinstance(error, InvalidCredentialsError)
    headers = {"WWW-Authenticate": "Bearer"} if needs_challenge else None
    return JSONResponse(status_code=status_code, content=error_body(error.error, error.detail), headers=headers)


async def _handle_validation_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    # Una línea por campo: "body.question: String should have at least 1 character"
    problems = [
        f"{'.'.join(str(part) for part in problem['loc'])}: {problem['msg']}" for problem in error.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_body(_ERROR_BY_STATUS[status.HTTP_422_UNPROCESSABLE_CONTENT], "; ".join(problems)),
    )


async def _handle_http_exception(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, StarletteHTTPException)
    title = _ERROR_BY_STATUS.get(error.status_code, HTTPStatus(error.status_code).phrase)
    return JSONResponse(
        status_code=error.status_code,
        content=error_body(title, str(error.detail)),
        headers=error.headers,
    )


async def _handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s %s", request.method, request.url.path, exc_info=error)
    # El traceback expone código y datos internos: solo se envía si se habilitó explícitamente (desarrollo)
    if settings.ERROR_TRACEBACK_ENABLED:
        detail = "".join(traceback.format_exception(error))
    else:
        detail = INTERNAL_ERROR_DETAIL
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_body(INTERNAL_ERROR, detail))
