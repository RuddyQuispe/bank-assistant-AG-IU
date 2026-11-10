import type { ChatSession } from '../models/chat/chat-session.model'

interface SessionListProps {
  sessions: ChatSession[]
  activeId: string | null
  onSelect: (sessionId: string) => void
  onCreate: () => void
  onDelete: (sessionId: string) => void
}

// Presentacional: barra lateral con las conversaciones del usuario.
export function SessionList({ sessions, activeId, onSelect, onCreate, onDelete }: SessionListProps) {
  return (
    <div className="d-flex flex-column h-100">
      <div className="p-3 border-bottom">
        <button type="button" className="btn btn-primary w-100" onClick={onCreate}>
          + New chat
        </button>
      </div>
      <div className="list-group list-group-flush overflow-auto flex-grow-1">
        {sessions.length === 0 && <p className="small text-body-secondary text-center my-4">No conversations yet.</p>}
        {sessions.map((session) => (
          <div
            key={session.session_id}
            className={`list-group-item list-group-item-action d-flex align-items-center gap-2 ${
              session.session_id === activeId ? 'active' : ''
            }`}
            role="button"
            onClick={() => onSelect(session.session_id)}
          >
            <span className="text-truncate flex-grow-1 small">{session.title ?? 'New conversation'}</span>
            <button
              type="button"
              className={`btn btn-sm py-0 px-1 ${session.session_id === activeId ? 'btn-light' : 'btn-outline-danger'}`}
              aria-label="Delete conversation"
              onClick={(event) => {
                event.stopPropagation()
                onDelete(session.session_id)
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
