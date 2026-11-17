import { useEffect, useState } from 'react'
import { toErrorMessage } from '../api/config'
import { createSession, deleteSession, listSessions } from '../api/sessions'
import { getDailyUsage } from '../api/usage'
import type { ChatSession } from '../models/chat/chat-session.model'
import type { UsageReport } from '../models/usage/usage-report.model'
import { Conversation } from './Conversation'
import { SessionList } from './SessionList'
import { UsageBadge } from './UsageBadge'
import { UsageModal } from './UsageModal'

interface ChatScreenProps {
  nickname: string
  token: string
  onLogout: () => void
}

// El consumo es informativo: si falla, se oculta el indicador sin mostrar error.
async function loadUsage(token: string, setUsage: (report: UsageReport | null) => void) {
  try {
    setUsage(await getDailyUsage(token))
  } catch {
    setUsage(null)
  }
}

// Contenedor: maneja la lista de sesiones y cuál está abierta.
export function ChatScreen({ nickname, token, onLogout }: ChatScreenProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Consumo de tokens del usuario; null mientras carga o si falló (no bloquea el chat)
  const [usage, setUsage] = useState<UsageReport | null>(null)
  const [showUsage, setShowUsage] = useState(false)

  // 1. Al entrar: trae la lista y abre la sesión más reciente.
  useEffect(() => {
    async function loadSessions() {
      try {
        const list = await listSessions(token)
        setSessions(list)
        setActiveId(list[0]?.session_id ?? null)
      } catch (err) {
        setError(toErrorMessage(err))
      }
    }
    loadSessions()
    loadUsage(token, setUsage)
  }, [token])

  // 2. Después de cada respuesta: recarga la lista (el backend pone el título) y el consumo del día.
  async function refreshAfterRun() {
    loadUsage(token, setUsage)
    try {
      setSessions(await listSessions(token))
    } catch (err) {
      setError(toErrorMessage(err))
    }
  }

  // 3. Nueva conversación: se crea en el backend y se abre.
  async function handleCreate() {
    try {
      const session = await createSession(token)
      setSessions((current) => [session, ...current])
      setActiveId(session.session_id)
    } catch (err) {
      setError(toErrorMessage(err))
    }
  }

  // 4. Borrar: si era la abierta, se abre la siguiente.
  async function handleDelete(sessionId: string) {
    try {
      await deleteSession(token, sessionId)
      const remaining = sessions.filter((s) => s.session_id !== sessionId)
      setSessions(remaining)
      if (sessionId === activeId) setActiveId(remaining[0]?.session_id ?? null)
    } catch (err) {
      setError(toErrorMessage(err))
    }
  }

  return (
    <div className="card shadow-lg border-0 overflow-hidden" style={{ maxWidth: 1000, width: '100%', height: '80vh' }}>
      <div className="card-header bg-body d-flex justify-content-between align-items-center py-3">
        <div>
          <div className="fw-bold">Digital Wallet</div>
          <div className="small text-body-secondary">Signed in as {nickname}</div>
        </div>
        <div className="d-flex align-items-center gap-2">
          <UsageBadge report={usage} onOpen={() => setShowUsage(true)} />
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </div>
      {error && <div className="alert alert-danger rounded-0 py-2 small mb-0">{error}</div>}
      <div className="d-flex flex-grow-1" style={{ minHeight: 0 }}>
        <aside className="border-end bg-body" style={{ width: 260, flexShrink: 0 }}>
          <SessionList
            sessions={sessions}
            activeId={activeId}
            onSelect={setActiveId}
            onCreate={handleCreate}
            onDelete={handleDelete}
          />
        </aside>
        <section className="d-flex flex-column flex-grow-1" style={{ minWidth: 0 }}>
          {activeId ? (
            <Conversation key={activeId} token={token} sessionId={activeId} onRunFinished={refreshAfterRun} />
          ) : (
            <div className="flex-grow-1 d-flex align-items-center justify-content-center text-body-secondary">
              Start a new chat to talk with your assistant.
            </div>
          )}
        </section>
      </div>
      {showUsage && usage && <UsageModal report={usage} onClose={() => setShowUsage(false)} />}
    </div>
  )
}
