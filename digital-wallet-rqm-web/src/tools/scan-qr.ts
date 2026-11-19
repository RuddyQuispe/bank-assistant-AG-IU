import { randomUUID, type Tool, type ToolMessage } from '@ag-ui/client'
import jsQR from 'jsqr'

// Tool del cliente que necesita al usuario: el navegador abre el escáner y espera a que elija un QR.
// No tiene parámetros: el LLM solo decide abrir el escáner; el QR lo elige el cliente.
export const SCAN_QR_TOOL: Tool = {
  name: 'scan_qr',
  description:
    'Abre el escáner de QR de la app para que el cliente escanee un QR de cobro y lo pague. ' +
    'Devuelve el código del QR escaneado, o "cancelled" si el cliente cerró el escáner',
  parameters: { type: 'object', properties: {} },
}

export const SCAN_CANCELLED = 'cancelled'

// El QR de cobro solo lleva un token opaco ("qr_" + 32 hex); los datos del cobro los da el backend
const QR_TOKEN = /^qr_[0-9a-f]{32}$/

export function isQrToken(code: string): boolean {
  return QR_TOKEN.test(code)
}

export type DecodedQr = { code: string } | { error: string }

// Lee el QR de los píxeles RGBA de una imagen (canvas). Todo pasa en el navegador: la imagen no se sube.
export function decodeQrToken(pixels: Uint8ClampedArray, width: number, height: number): DecodedQr {
  const qr = jsQR(pixels, width, height)
  if (!qr) return { error: 'No QR code found in the image.' }
  if (!isQrToken(qr.data)) return { error: 'This QR is not a payment QR.' }
  return { code: qr.data }
}

// Resultado del escaneo que vuelve al agente: el código del QR, o "cancelled".
export function scanResultMessage(toolCallId: string, code: string | null): ToolMessage {
  return { id: randomUUID(), role: 'tool', toolCallId, content: code ?? SCAN_CANCELLED }
}
