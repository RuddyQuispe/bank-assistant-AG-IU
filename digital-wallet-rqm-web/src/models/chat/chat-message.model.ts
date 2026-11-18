import type { BalanceCardData } from '../../display/balance-card'

// Mensaje que se dibuja en pantalla. Con "card", el agente mandó un componente en vez de texto.
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  card?: BalanceCardData
}
