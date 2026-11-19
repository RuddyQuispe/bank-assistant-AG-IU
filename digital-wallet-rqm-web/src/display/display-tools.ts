import type { Tool } from '@ag-ui/client'
import { parseBalanceCard, type BalanceCardData } from './balance-card'
import { parsePaymentReceipt, type PaymentReceiptData } from './payment-receipt'
import { parseQrPaymentCard, type QrPaymentCardData } from './qr-payment-card'

// Tools de solo mostrar: el agente las manda con datos y el chat las dibuja como un componente.
// No se ejecutan ni devuelven resultado. Declararlas le dice al backend que la app sabe dibujarlas;
// el backend nunca se las ofrece al LLM, las emite él con los datos reales.
export const SHOW_ACCOUNT_BALANCE = 'show_account_balance'
export const SHOW_QR_PAYMENT = 'show_qr_payment'
export const SHOW_PAYMENT_RECEIPT = 'show_payment_receipt'

export const DISPLAY_TOOLS: Tool[] = [
  {
    name: SHOW_ACCOUNT_BALANCE,
    description: 'Muestra en el chat una tarjeta con el saldo de la cuenta del cliente',
    parameters: {
      type: 'object',
      properties: {
        account_number: { type: 'string', description: 'Número de cuenta' },
        account_type: { type: 'string', description: 'Tipo de cuenta' },
        currency: { type: 'string', description: 'Moneda ISO 4217' },
        available: { type: 'string', description: 'Saldo disponible, por ejemplo "1500.50"' },
      },
      required: ['account_number', 'account_type', 'currency', 'available'],
    },
  },
  {
    name: SHOW_QR_PAYMENT,
    description: 'Muestra en el chat el cobro de un QR escaneado, con las cuentas del cliente para pagarlo',
    parameters: {
      type: 'object',
      properties: {
        code: { type: 'string', description: 'Token del QR' },
        recipient_name: { type: 'string' },
        bank: { type: 'string' },
        account_number: { type: 'string', description: 'Cuenta destino (8 dígitos)' },
        document_id: { type: 'string', description: 'NIT o carnet (8 dígitos)' },
        amount: { type: 'string', description: 'Monto del QR; "0" si lo asigna el pagador' },
        currency: { type: 'string' },
        usage: { type: 'string', enum: ['single', 'multiple'] },
        expires_on: { type: 'string', description: 'Fecha ISO' },
        note: { type: 'string' },
        expired: { type: 'boolean' },
        already_paid: { type: 'boolean' },
        accounts: { type: 'array', items: { type: 'object' } },
      },
    },
  },
  {
    name: SHOW_PAYMENT_RECEIPT,
    description: 'Muestra en el chat el comprobante de un pago con QR',
    parameters: {
      type: 'object',
      properties: {
        receipt_number: { type: 'string' },
        recipient_name: { type: 'string' },
        bank: { type: 'string' },
        destination_account: { type: 'string' },
        from_account: { type: 'string' },
        amount: { type: 'string' },
        currency: { type: 'string' },
        balance_after: { type: 'string' },
        paid_at: { type: 'string', description: 'Fecha y hora ISO' },
      },
    },
  },
]

const DISPLAY_TOOL_NAMES = new Set(DISPLAY_TOOLS.map((tool) => tool.name))

export function isDisplayTool(name: string): boolean {
  return DISPLAY_TOOL_NAMES.has(name)
}

// Lo que dibuja el chat para cada tool de solo mostrar
export interface DisplayCard {
  card?: BalanceCardData
  qrPayment?: QrPaymentCardData
  receipt?: PaymentReceiptData
}

// Datos validados de una tarjeta, o null si la tool no es de solo mostrar o sus datos están rotos.
export function parseDisplayCard(name: string, args: unknown): DisplayCard | null {
  if (name === SHOW_ACCOUNT_BALANCE) {
    const card = parseBalanceCard(args)
    return card ? { card } : null
  }
  if (name === SHOW_QR_PAYMENT) {
    const qrPayment = parseQrPaymentCard(args)
    return qrPayment ? { qrPayment } : null
  }
  if (name === SHOW_PAYMENT_RECEIPT) {
    const receipt = parsePaymentReceipt(args)
    return receipt ? { receipt } : null
  }
  return null
}
