import { currencyLabel, parseBalanceCard, type BalanceCardData } from './balance-card'

// Datos de la tarjeta del cobro QR. Llegan en los args de show_qr_payment, que arma el backend con el QR
// escaneado y las cuentas del cliente; igual se validan antes de dibujarlos.
export interface QrPaymentCardData {
  // Token del QR: lo necesita el pago (F5)
  code: string
  recipientName: string
  bank: string
  accountNumber: string
  documentId: string
  // 0: el pagador asigna el monto
  amount: number
  currency: string
  usage: 'single' | 'multiple'
  // Fecha ISO (AAAA-MM-DD)
  expiresOn: string
  note: string
  expired: boolean
  alreadyPaid: boolean
  // Cuentas del cliente para pagar
  accounts: BalanceCardData[]
}

const DECIMAL = /^\d+(\.\d+)?$/
const PAYER_AMOUNT = /^\d+(\.\d{1,2})?$/
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

function isText(value: unknown): value is string {
  return typeof value === 'string' && value.trim() !== ''
}

// Devuelve los datos del cobro, o null si los args no tienen la forma esperada.
export function parseQrPaymentCard(args: unknown): QrPaymentCardData | null {
  if (typeof args !== 'object' || args === null) return null
  const data = args as Record<string, unknown>
  const texts = [data.code, data.recipient_name, data.bank, data.account_number, data.document_id, data.currency]
  if (!texts.every(isText) || typeof data.note !== 'string') return null
  // Montos como texto ("350.00") para no perder decimales en el JSON
  if (typeof data.amount !== 'string' || !DECIMAL.test(data.amount)) return null
  if (data.usage !== 'single' && data.usage !== 'multiple') return null
  if (typeof data.expires_on !== 'string' || !ISO_DATE.test(data.expires_on)) return null
  if (typeof data.expired !== 'boolean' || typeof data.already_paid !== 'boolean') return null
  if (!Array.isArray(data.accounts)) return null
  const accounts = data.accounts.map(parseBalanceCard)
  if (accounts.some((account) => account === null)) return null
  return {
    code: data.code as string,
    recipientName: data.recipient_name as string,
    bank: data.bank as string,
    accountNumber: data.account_number as string,
    documentId: data.document_id as string,
    amount: Number(data.amount),
    currency: data.currency as string,
    usage: data.usage,
    expiresOn: data.expires_on,
    note: data.note,
    expired: data.expired,
    alreadyPaid: data.already_paid,
    accounts: accounts as BalanceCardData[],
  }
}

// Monto que escribe el pagador: positivo y con 2 decimales como máximo; null si no sirve.
export function parseAmountInput(text: string): number | null {
  const value = text.trim()
  if (!PAYER_AMOUNT.test(value)) return null
  const amount = Number(value)
  return amount > 0 ? amount : null
}

// Por qué todavía no se puede pagar, o null si se puede. El backend vuelve a validar todo al pagar.
export function paymentProblem(
  card: QrPaymentCardData,
  account: BalanceCardData | undefined,
  amountText: string,
): string | null {
  if (card.expired) return 'This QR has expired.'
  if (card.alreadyPaid) return 'This QR was already paid.'
  if (!account) return 'Choose the account to pay from.'
  if (account.currency !== card.currency) {
    return `This account is in ${currencyLabel(account.currency)} and the QR charges in ${currencyLabel(card.currency)}.`
  }
  const amount = card.amount === 0 ? parseAmountInput(amountText) : card.amount
  if (amount === null) return 'Enter an amount greater than 0 with up to 2 decimals.'
  if (amount > account.available) return 'Not enough balance in this account.'
  return null
}

export function formatMoney(amount: number, currency: string): string {
  const value = amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return `${currencyLabel(currency)} ${value}`
}

// La fecha es un día sin hora: se formatea en UTC para que no se corra un día según la zona del navegador
export function formatExpiry(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString('en-US', {
    timeZone: 'UTC',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}
