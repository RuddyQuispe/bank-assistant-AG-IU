import { useState, type FormEvent } from 'react'

interface LoginFormProps {
  loading: boolean
  error: string | null
  onSubmit: (nickname: string) => void
}

// Presentacional: solo pide el nickname y se lo pasa al padre.
export function LoginForm({ loading, error, onSubmit }: LoginFormProps) {
  const [nickname, setNickname] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit(nickname.trim())
  }

  return (
    <div className="card shadow-lg border-0" style={{ maxWidth: 400, width: '100%' }}>
      <div className="card-body p-4 p-md-5">
        <h1 className="h3 fw-bold text-center mb-1">Digital Wallet</h1>
        <p className="text-body-secondary text-center mb-4">Sign in to talk with your assistant</p>
        <form onSubmit={handleSubmit}>
          <div className="form-floating mb-3">
            <input
              id="nickname"
              className="form-control"
              placeholder="Nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              disabled={loading}
              autoFocus
              required
            />
            <label htmlFor="nickname">Nickname</label>
          </div>
          {error && (
            <div className="alert alert-danger py-2 small" role="alert">
              {error}
            </div>
          )}
          <button type="submit" className="btn btn-primary btn-lg w-100" disabled={loading || !nickname.trim()}>
            {loading && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
