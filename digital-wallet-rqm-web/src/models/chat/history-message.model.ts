// Mensaje guardado en el historial del backend.
export interface HistoryMessage {
  role: 'human' | 'ai'
  content: string
}
