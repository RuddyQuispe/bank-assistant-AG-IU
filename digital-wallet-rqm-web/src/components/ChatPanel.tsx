import { useState, type FormEvent } from 'react'
import type { ChatMessage } from '../models/chat/chat-message.model'

interface ChatPanelProps {
  messages: ChatMessage[]
  running: boolean
  step: string | null
  error: string | null
  onSend: (question: string) => void
}

// Presentacional: dibuja los mensajes y la caja de pregunta.
export function ChatPanel({ messages, running, step, error, onSend }: ChatPanelProps) {
  const [question, setQuestion] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSend(question.trim())
    setQuestion('')
  }

  return (
    <>
      <div className="flex-grow-1 overflow-auto p-3 bg-body-tertiary">
        {messages.length === 0 && (
          <p className="text-body-secondary text-center my-5">Ask anything about your wallet.</p>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`d-flex mb-2 ${message.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
          >
            <div
              className={`px-3 py-2 rounded-3 ${message.role === 'user' ? 'bg-primary text-white' : 'bg-white border'}`}
              style={{ maxWidth: '80%', whiteSpace: 'pre-wrap' }}
            >
              {message.content || <span className="spinner-grow spinner-grow-sm" aria-label="Typing" />}
            </div>
          </div>
        ))}
        {step && (
          <div className="d-flex align-items-center gap-2 text-body-secondary small mb-2">
            <span className="spinner-border spinner-border-sm" aria-hidden="true" />
            <span role="status">{step}</span>
          </div>
        )}
        {error && (
          <div className="alert alert-danger py-2 small mt-2" role="alert">
            {error}
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="d-flex gap-2 p-3 border-top">
        <input
          className="form-control"
          placeholder="Type your question…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={running}
          autoFocus
        />
        <button type="submit" className="btn btn-primary" disabled={running || !question.trim()}>
          {running ? <span className="spinner-border spinner-border-sm" aria-label="Sending" /> : 'Send'}
        </button>
      </form>
    </>
  )
}
