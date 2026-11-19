import { API_URL, ensureOk } from './config'

// GET /qr/demo: tokens de los QR de prueba (solo tokens; los datos del cobro se ven al escanear).
export async function getDemoQrs(token: string): Promise<string[]> {
  const response = await fetch(`${API_URL}/qr/demo`, { headers: { Authorization: `Bearer ${token}` } })
  await ensureOk(response)
  const body = (await response.json()) as { codes: string[] }
  return body.codes
}
