import type { ChatSession } from '../models/chat/chat-session.model'
import type { HistoryMessage } from '../models/chat/history-message.model'
import { API_URL, ensureOk } from './config'

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` }
}

// GET /chat/sessions: sesiones del usuario, la más reciente primero.
export async function listSessions(token: string): Promise<ChatSession[]> {
  const response = await fetch(`${API_URL}/chat/sessions`, { headers: authHeaders(token) })
  await ensureOk(response)
  return (await response.json()) as ChatSession[]
}

// POST /chat/sessions: crea una sesión vacía del dueño del token.
export async function createSession(token: string): Promise<ChatSession> {
  const response = await fetch(`${API_URL}/chat/sessions`, { method: 'POST', headers: authHeaders(token) })
  await ensureOk(response)
  return (await response.json()) as ChatSession
}

// GET /chat/sessions/{id}/history: preguntas y respuestas guardadas.
export async function getHistory(token: string, sessionId: string): Promise<HistoryMessage[]> {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}/history`, { headers: authHeaders(token) })
  await ensureOk(response)
  return (await response.json()) as HistoryMessage[]
}

// DELETE /chat/sessions/{id}: borra la sesión y su historial.
export async function deleteSession(token: string, sessionId: string): Promise<void> {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}`, { method: 'DELETE', headers: authHeaders(token) })
  await ensureOk(response)
}
