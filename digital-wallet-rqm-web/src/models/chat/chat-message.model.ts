// Mensaje que se dibuja en pantalla.
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}
