import type { ApiError } from '../models/api/api-error.model'

// URL del backend; se cambia con VITE_API_URL en un archivo .env.
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Lanza un error con el mensaje del backend cuando la respuesta no es 2xx.
export async function ensureOk(response: Response): Promise<Response> {
  if (response.ok) {
    return response
  }
  const body = (await response.json().catch(() => null)) as ApiError | null
  throw new Error(body?.detail ?? body?.error ?? `${response.status} ${response.statusText}`)
}

// Convierte cualquier error capturado en un texto para mostrar.
export function toErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}
