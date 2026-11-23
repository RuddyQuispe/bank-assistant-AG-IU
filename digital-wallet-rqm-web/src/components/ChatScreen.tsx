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
import './ChatScreen.css'

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
  // Solo en móvil: panel lateral de conversaciones abierto o cerrado
  const [showSessions, setShowSessions] = useState(false)

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
      setShowSessions(false)
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
    <div className="chat-screen card shadow-lg border-0 overflow-hidden">
      <div className="chat-header card-header bg-body d-flex justify-content-between align-items-center gap-2 py-3">
        <div className="d-flex align-items-center gap-2" style={{ minWidth: 0 }}>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm d-md-none"
            aria-label={showSessions ? 'Hide conversations' : 'Show conversations'}
            aria-expanded={showSessions}
            onClick={() => setShowSessions((open) => !open)}
          >
            {showSessions ? '✕' : '☰'}
          </button>
          <div style={{ minWidth: 0 }}>
            <div className="fw-bold text-nowrap">Digital Wallet</div>
            <div className="small text-body-secondary text-truncate d-none d-md-block">Signed in as {nickname}</div>
            {/* Móvil: el consumo va como subtítulo para no competir con los botones */}
            <div className="d-md-none lh-1">
              <UsageBadge report={usage} compact onOpen={() => setShowUsage(true)} />
            </div>
          </div>
        </div>
        <div className="d-flex align-items-center gap-2">
          <div className="d-none d-md-block">
            <UsageBadge report={usage} onOpen={() => setShowUsage(true)} />
          </div>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm text-nowrap"
            aria-label="Sign out"
            title="Sign out"
            onClick={onLogout}
          >
            {/* Ícono "salir" (box-arrow-right de Bootstrap Icons) */}
            <svg className="d-md-none" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M10 12.5a.5.5 0 0 1-.5.5h-8a.5.5 0 0 1-.5-.5v-9a.5.5 0 0 1 .5-.5h8a.5.5 0 0 1 .5.5v2a.5.5 0 0 0 1 0v-2A1.5 1.5 0 0 0 9.5 2h-8A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h8a1.5 1.5 0 0 0 1.5-1.5v-2a.5.5 0 0 0-1 0z"
              />
              <path
                fillRule="evenodd"
                d="M15.854 8.354a.5.5 0 0 0 0-.708l-3-3a.5.5 0 0 0-.708.708L14.293 7.5H5.5a.5.5 0 0 0 0 1h8.793l-2.147 2.146a.5.5 0 0 0 .708.708z"
              />
            </svg>
            <span className="d-none d-md-inline">Sign out</span>
          </button>
        </div>
      </div>
      {error && <div className="alert alert-danger rounded-0 py-2 small mb-0">{error}</div>}
      <div className="chat-body d-flex flex-grow-1">
        {showSessions && <div className="chat-backdrop d-md-none" onClick={() => setShowSessions(false)} />}
        <aside className={`chat-sessions border-end bg-body ${showSessions ? 'open' : ''}`}>
          <SessionList
            sessions={sessions}
            activeId={activeId}
            onSelect={(sessionId) => {
              setActiveId(sessionId)
              setShowSessions(false)
            }}
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
