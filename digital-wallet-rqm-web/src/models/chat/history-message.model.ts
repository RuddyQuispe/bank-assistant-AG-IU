// Mensaje guardado en el historial del backend.
export interface HistoryMessage {
  role: 'human' | 'ai'
  content: string
  // Tarjeta del saldo que mostró el agente (content viene vacío); mismos datos que show_account_balance
  card?: Record<string, unknown> | null
  // Cobro QR que mostró el agente; mismos datos que show_qr_payment
  qr_payment?: Record<string, unknown> | null
  // Comprobante de un pago con QR; mismos datos que show_payment_receipt
  receipt?: Record<string, unknown> | null
}
