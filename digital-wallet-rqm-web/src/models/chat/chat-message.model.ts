import type { BalanceCardData } from '../../display/balance-card'
import type { PaymentReceiptData } from '../../display/payment-receipt'
import type { QrPaymentCardData } from '../../display/qr-payment-card'

// Mensaje que se dibuja en pantalla. Con "card", "qrPayment" o "receipt", el agente mandó un componente en vez de texto.
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  card?: BalanceCardData
  qrPayment?: QrPaymentCardData
  receipt?: PaymentReceiptData
}
