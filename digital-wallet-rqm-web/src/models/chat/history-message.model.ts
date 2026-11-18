// Mensaje guardado en el historial del backend.
export interface HistoryMessage {
  role: 'human' | 'ai'
  content: string
  // Tarjeta del saldo que mostró el agente (content viene vacío); mismos datos que show_account_balance
  card?: Record<string, unknown> | null
}
