// Sesión de chat tal como la devuelve el backend.
export interface ChatSession {
  session_id: string
  title: string | null
  created_at: string
  updated_at: string
}
