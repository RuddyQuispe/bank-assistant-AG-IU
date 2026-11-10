import type { TokenResponse } from '../models/auth/token-response.model'
import { API_URL, ensureOk } from './config'

// POST /auth/token: cambia un nickname por un JWT.
export async function login(nickname: string): Promise<string> {
  const response = await fetch(`${API_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname }),
  })
  await ensureOk(response)
  const body = (await response.json()) as TokenResponse
  return body.access_token
}
