from digital_wallet_rqm.exceptions.base import AppError

# Errores genéricos: cada uno corresponde a un status HTTP (ver api/exceptions/handlers.py)


class BadRequestError(AppError):
    """La petición es inválida para la lógica de negocio"""

    error = "Petición inválida"
    default_detail = "La petición no cumple las reglas del negocio"


class UnauthorizedError(AppError):
    """Falta identificar al usuario o su credencial no sirve"""

    error = "No autenticado"
    default_detail = "Se requiere un token válido"


class ForbiddenError(AppError):
    """El usuario está identificado pero no puede usar el recurso"""

    error = "Acceso denegado"
    default_detail = "No tiene permiso para usar este recurso"


class NotFoundError(AppError):
    """El recurso pedido no existe"""

    error = "Recurso no encontrado"
    default_detail = "El recurso pedido no existe"


class ConflictError(AppError):
    """La operación choca con el estado actual del recurso"""

    error = "Conflicto"
    default_detail = "La operación choca con el estado actual del recurso"


# Errores de negocio: heredan del genérico y así reciben su status y su "error" sin registrar nada más


class SessionForbiddenError(ForbiddenError):
    """La sesión existe pero pertenece a otro usuario"""

    # No se revela de quién es la sesión
    default_detail = "La sesión pertenece a otro usuario"


class SessionNotFoundError(NotFoundError):
    """El id de sesión no existe: las sesiones nuevas se crean sin id y el servidor lo asigna"""

    default_detail = "La sesión no existe"


class InvalidCredentialsError(UnauthorizedError):
    """El login falló: el usuario no existe"""

    default_detail = "Usuario desconocido"


class InvalidTokenError(UnauthorizedError):
    """El token no es válido: mal firmado, vencido, de otro emisor o mal formado"""

    default_detail = "Token inválido"

    def __init__(self, reason: str) -> None:
        # El motivo real queda para logs y tests; el cliente solo ve el detalle genérico
        super().__init__()
        self.reason = reason
