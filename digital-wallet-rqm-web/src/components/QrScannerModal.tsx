import { useEffect, useState, type ChangeEvent } from 'react'
import QRCode from 'qrcode'
import { getDemoQrs } from '../api/qr'
import { toErrorMessage } from '../api/config'
import { decodeQrToken } from '../tools/scan-qr'
import './QrScannerModal.css'

// Imágenes más grandes se achican antes de leerlas: jsQR no necesita más y así no se traba la página
const MAX_SIDE = 1024
const MAX_FILE_BYTES = 5 * 1024 * 1024

interface DemoQrImage {
  code: string
  image: string
}

interface QrScannerModalProps {
  token: string
  onScan: (code: string) => void
  onCancel: () => void
}

// Píxeles RGBA de la imagen elegida, achicada si hace falta. No sale del navegador.
async function readPixels(file: File): Promise<{ data: Uint8ClampedArray; width: number; height: number }> {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
  const width = Math.round(bitmap.width * scale)
  const height = Math.round(bitmap.height * scale)
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas is not available.')
  context.drawImage(bitmap, 0, 0, width, height)
  bitmap.close()
  return { data: context.getImageData(0, 0, width, height).data, width, height }
}

// Escáner: sube una imagen con el QR o elige un QR de prueba. El QR solo lleva un token;
// los datos del cobro los muestra el agente después de escanearlo.
export function QrScannerModal({ token, onScan, onCancel }: QrScannerModalProps) {
  const [demoQrs, setDemoQrs] = useState<DemoQrImage[]>([])
  const [error, setError] = useState<string | null>(null)
  const [reading, setReading] = useState(false)

  // 1. Trae los QR de prueba del backend y los dibuja
  useEffect(() => {
    let active = true
    getDemoQrs(token)
      .then((codes) =>
        Promise.all(
          codes.map(async (code) => ({ code, image: await QRCode.toDataURL(code, { margin: 2, width: 240 }) })),
        ),
      )
      .then((images) => {
        if (active) setDemoQrs(images)
      })
      .catch((err) => {
        if (active) setError(toErrorMessage(err))
      })
    return () => {
      active = false
    }
  }, [token])

  // 2. Escape cierra el escáner como "Cancel"
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onCancel])

  // 3. Imagen subida: se decodifica en el navegador; solo el token vuelve al agente
  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!file.type.startsWith('image/')) return setError('Choose an image file.')
    if (file.size > MAX_FILE_BYTES) return setError('The image is larger than 5 MB.')
    setReading(true)
    setError(null)
    try {
      const { data, width, height } = await readPixels(file)
      const decoded = decodeQrToken(data, width, height)
      if ('error' in decoded) setError(decoded.error)
      else onScan(decoded.code)
    } catch {
      setError('The image could not be read.')
    } finally {
      setReading(false)
    }
  }

  return (
    <div className="qr-scanner__backdrop">
      <div className="qr-scanner" role="dialog" aria-modal="true" aria-labelledby="qr-scanner-title">
        <header className="qr-scanner__header">
          <h2 id="qr-scanner-title" className="qr-scanner__title">
            Scan a QR to pay
          </h2>
          <button type="button" className="btn-close btn-close-white" aria-label="Cancel" onClick={onCancel} />
        </header>

        <div className="qr-scanner__viewfinder" aria-hidden="true">
          <span className="qr-scanner__corner qr-scanner__corner--tl" />
          <span className="qr-scanner__corner qr-scanner__corner--tr" />
          <span className="qr-scanner__corner qr-scanner__corner--bl" />
          <span className="qr-scanner__corner qr-scanner__corner--br" />
          <span className="qr-scanner__line" />
        </div>

        <label className={`btn btn-light w-100 mt-3 ${reading ? 'disabled' : ''}`}>
          {reading ? 'Reading the QR…' : 'Upload QR image'}
          <input type="file" accept="image/*" className="d-none" onChange={handleUpload} disabled={reading} />
        </label>
        {error && (
          <div className="qr-scanner__error" role="alert">
            {error}
          </div>
        )}

        <p className="qr-scanner__help">Or use a demo QR: tap it to scan it, or download it to try the upload.</p>
        <ul className="qr-scanner__list">
          {demoQrs.map((qr, index) => (
            <li key={qr.code} className="qr-scanner__item">
              <button type="button" className="qr-scanner__option" onClick={() => onScan(qr.code)}>
                <img src={qr.image} alt={`Demo QR ${index + 1}`} className="qr-scanner__image" />
                <span className="qr-scanner__label">Demo QR {index + 1}</span>
              </button>
              <a className="qr-scanner__download" href={qr.image} download={`demo-qr-${index + 1}.png`}>
                Download
              </a>
            </li>
          ))}
        </ul>

        <button type="button" className="btn btn-outline-light w-100 mt-3" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  )
}
