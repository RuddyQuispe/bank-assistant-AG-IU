import QRCode from 'qrcode'
import { describe, expect, it } from 'vitest'
import { SCAN_CANCELLED, SCAN_QR_TOOL, decodeQrToken, isQrToken, scanResultMessage } from './scan-qr'

const TOKEN = 'qr_af9bd6ff81dc2525a2fba110bf390946'

// Dibuja un QR real como píxeles RGBA (lo mismo que da un canvas al leer una imagen)
function qrPixels(text: string, scale = 4, margin = 4) {
  const { modules } = QRCode.create(text, { errorCorrectionLevel: 'M' })
  const size = (modules.size + margin * 2) * scale
  const data = new Uint8ClampedArray(size * size * 4).fill(255)
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const row = Math.floor(y / scale) - margin
      const col = Math.floor(x / scale) - margin
      const inside = row >= 0 && col >= 0 && row < modules.size && col < modules.size
      if (inside && modules.get(row, col)) data.fill(0, (y * size + x) * 4, (y * size + x) * 4 + 3)
    }
  }
  return { data, width: size, height: size }
}

describe('SCAN_QR_TOOL', () => {
  it('declares scan_qr without parameters: the browser asks the user, not the LLM', () => {
    expect(SCAN_QR_TOOL.name).toBe('scan_qr')
    expect(SCAN_QR_TOOL.parameters).toEqual({ type: 'object', properties: {} })
  })
})

describe('isQrToken', () => {
  it('accepts only "qr_" plus 32 lowercase hex chars', () => {
    expect(isQrToken(TOKEN)).toBe(true)
    expect(isQrToken('QR-DEMO-001')).toBe(false)
    expect(isQrToken(TOKEN.toUpperCase())).toBe(false)
    expect(isQrToken(`${TOKEN}0`)).toBe(false)
  })
})

describe('decodeQrToken', () => {
  it('reads the payment token from the pixels of a QR image', () => {
    const { data, width, height } = qrPixels(TOKEN)

    expect(decodeQrToken(data, width, height)).toEqual({ code: TOKEN })
  })

  it('rejects a QR that is not a payment QR', () => {
    const { data, width, height } = qrPixels('https://example.com')

    expect(decodeQrToken(data, width, height)).toEqual({ error: 'This QR is not a payment QR.' })
  })

  it('reports an image without a QR', () => {
    const blank = new Uint8ClampedArray(64 * 64 * 4).fill(255)

    expect(decodeQrToken(blank, 64, 64)).toEqual({ error: 'No QR code found in the image.' })
  })
})

describe('scanResultMessage', () => {
  it('returns the scanned token as the tool result for the agent', () => {
    expect(scanResultMessage('call-1', TOKEN)).toMatchObject({ role: 'tool', toolCallId: 'call-1', content: TOKEN })
  })

  it('reports a cancelled scan', () => {
    expect(scanResultMessage('call-1', null).content).toBe(SCAN_CANCELLED)
  })

  it('gives every result its own id', () => {
    expect(scanResultMessage('call-1', null).id).not.toBe(scanResultMessage('call-1', null).id)
  })
})
