import { useState } from 'react'
import { login } from './api/auth'
import { toErrorMessage } from './api/config'
import { LoginForm } from './components/LoginForm'
import { ChatScreen } from './components/ChatScreen'

// Contenedor raíz: sin token muestra el login; con token, el chat.
function App() {
  const [nickname, setNickname] = useState('')
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Guarda el token; las sesiones las maneja ChatScreen.
  async function handleLogin(name: string) {
    setLoading(true)
    setError(null)
    try {
      const accessToken = await login(name)
      setNickname(name)
      setToken(accessToken)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  function handleLogout() {
    setToken(null)
  }

  return (
    <main className="min-vh-100 d-flex align-items-center justify-content-center p-3">
      {token ? (
        <ChatScreen nickname={nickname} token={token} onLogout={handleLogout} />
      ) : (
        <LoginForm loading={loading} error={error} onSubmit={handleLogin} />
      )}
    </main>
  )
}

export default App
