import { isQrToken } from './scan-qr'

// El backend pausa el grafo (interrupt) hasta que el cliente confirme o cancele el pago de un QR.
// La pausa llega como evento CUSTOM "on_interrupt" y se reanuda con forwardedProps.command.resume.

export const PAYMENT_PAUSE_EVENT = 'on_interrupt'

// Token del QR que espera la confirmación, o null si el valor no es una pausa de pago.
export function parsePaymentPause(value: unknown): string | null {
  if (typeof value !== 'string') return null
  try {
    const pause = JSON.parse(value) as { type?: unknown; code?: unknown }
    if (pause.type !== 'qr_payment' || typeof pause.code !== 'string' || !isQrToken(pause.code)) return null
    return pause.code
  } catch {
    return null
  }
}

// forwardedProps para reanudar: el QR no viaja, lo fija el backend al escanear.
export function confirmPayment(accountNumber: string, amount: number) {
  return { command: { resume: { action: 'pay', account_number: accountNumber, amount: amount.toFixed(2) } } }
}

export function cancelPayment() {
  return { command: { resume: { action: 'cancel' } } }
}
