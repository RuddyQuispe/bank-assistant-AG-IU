// Comprobante de un pago con QR. Llega en los args de show_payment_receipt, que arma el backend
// después de pagar; igual se valida antes de dibujarlo.
export interface PaymentReceiptData {
  receiptNumber: string
  recipientName: string
  bank: string
  destinationAccount: string
  fromAccount: string
  amount: number
  currency: string
  balanceAfter: number
  // Fecha y hora ISO del pago
  paidAt: string
}

const DECIMAL = /^\d+(\.\d+)?$/

function isText(value: unknown): value is string {
  return typeof value === 'string' && value.trim() !== ''
}

// Devuelve el comprobante, o null si los args no tienen la forma esperada.
export function parsePaymentReceipt(args: unknown): PaymentReceiptData | null {
  if (typeof args !== 'object' || args === null) return null
  const data = args as Record<string, unknown>
  const texts = [
    data.receipt_number,
    data.recipient_name,
    data.bank,
    data.destination_account,
    data.from_account,
    data.currency,
    data.paid_at,
  ]
  if (!texts.every(isText)) return null
  // Montos como texto ("350.00") para no perder decimales en el JSON
  if (typeof data.amount !== 'string' || !DECIMAL.test(data.amount)) return null
  if (typeof data.balance_after !== 'string' || !DECIMAL.test(data.balance_after)) return null
  if (Number.isNaN(Date.parse(data.paid_at as string))) return null
  return {
    receiptNumber: data.receipt_number as string,
    recipientName: data.recipient_name as string,
    bank: data.bank as string,
    destinationAccount: data.destination_account as string,
    fromAccount: data.from_account as string,
    amount: Number(data.amount),
    currency: data.currency as string,
    balanceAfter: Number(data.balance_after),
    paidAt: data.paid_at as string,
  }
}

// Hora del pago en Bolivia, como el resto de la banca (el día del consumo también usa La Paz)
export function formatPaidAt(isoDateTime: string): string {
  return new Date(isoDateTime).toLocaleString('en-US', {
    timeZone: 'America/La_Paz',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}
