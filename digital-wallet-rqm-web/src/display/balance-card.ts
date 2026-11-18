// Datos de la tarjeta del saldo. Llegan en los args de show_account_balance, que arma el backend
// con los datos de su tool (no los escribe el LLM); igual se validan antes de dibujarlos.
export interface BalanceCardData {
  accountNumber: string
  accountType: string
  // Código ISO 4217 (BOB, USD)
  currency: string
  available: number
}

// Cómo se escribe cada moneda en pantalla; igual que en el texto del backend
const CURRENCY_LABELS: Record<string, string> = { BOB: 'Bs', USD: 'USD' }

const AMOUNT = /^-?\d+(\.\d+)?$/

function isText(value: unknown): value is string {
  return typeof value === 'string' && value.trim() !== ''
}

// Devuelve los datos de la tarjeta, o null si los args no tienen la forma esperada.
export function parseBalanceCard(args: unknown): BalanceCardData | null {
  if (typeof args !== 'object' || args === null) return null
  const { account_number, account_type, currency, available } = args as Record<string, unknown>
  // El saldo viaja como texto ("1500.50") para no perder decimales en el JSON
  if (!isText(account_number) || !isText(account_type) || !isText(currency)) return null
  if (typeof available !== 'string' || !AMOUNT.test(available)) return null
  return { accountNumber: account_number, accountType: account_type, currency, available: Number(available) }
}

export function currencyLabel(currency: string): string {
  return Object.hasOwn(CURRENCY_LABELS, currency) ? CURRENCY_LABELS[currency] : currency
}

// Parte entera y centavos por separado: la tarjeta dibuja los centavos más chicos
export function splitAmount(amount: number): { whole: string; cents: string } {
  const [whole, cents] = amount
    .toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    .split('.')
  return { whole, cents }
}

// Visible: el número completo en bloques de 4. Oculto: solo los últimos 4 dígitos.
export function formatAccountNumber(accountNumber: string, visible: boolean): string {
  if (!visible) return `•••• •••• ${accountNumber.slice(-4)}`
  return accountNumber.match(/.{1,4}/g)?.join(' ') ?? accountNumber
}
