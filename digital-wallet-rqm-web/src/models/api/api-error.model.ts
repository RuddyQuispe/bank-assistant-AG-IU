// Cuerpo de error que devuelve el backend (ver error_schema.py).
export interface ApiError {
  error: string
  detail?: string
}
