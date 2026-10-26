class AppError(Exception):
    """Base de los errores de la aplicación.

    El dominio y los servicios lanzan estas excepciones sin conocer HTTP; el adaptador HTTP
    (infrastructure/http/exception_handlers.py) decide el status, como un @RestControllerAdvice de Spring.
    La respuesta es {"error": error, "detail": detail}.
    """

    # Mensaje corto del tipo de error (campo "error" de la respuesta)
    error = "Error de la aplicación"
    # Explicación por defecto (campo "detail"); cada excepción puede dar una propia
    default_detail = "Ocurrió un error en la aplicación"

    def __init__(self, detail: str | None = None) -> None:
        # "detail" lo ve el cliente: no poner datos internos
        self.detail = detail or self.default_detail
        super().__init__(self.detail)
