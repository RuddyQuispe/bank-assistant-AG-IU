import { useEffect } from 'react'
import { formatMoney, type QrPaymentCardData } from '../display/qr-payment-card'
import type { PaymentChoice } from './QrPaymentCard'
import './ConfirmPaymentDialog.css'

interface ConfirmPaymentDialogProps {
  card: QrPaymentCardData
  choice: PaymentChoice
  onConfirm: () => void
  onCancel: () => void
}

// "¿Desea confirmar el pago a ...?": el último paso antes de mover plata. Recién al confirmar se reanuda el grafo.
export function ConfirmPaymentDialog({ card, choice, onConfirm, onCancel }: ConfirmPaymentDialogProps) {
  // Escape equivale a "Cancel"
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onCancel])

  const rows: [string, string][] = [
    ['Bank', card.bank],
    ['Destination account', card.accountNumber],
    ['NIT / CI', card.documentId],
    ...(card.note ? ([['Note', card.note]] as [string, string][]) : []),
    ['Pay from', `${choice.account.accountType} ****${choice.account.accountNumber.slice(-4)}`],
  ]

  return (
    <div className="confirm-payment__backdrop">
      <div className="confirm-payment" role="alertdialog" aria-modal="true" aria-labelledby="confirm-payment-title">
        <h2 id="confirm-payment-title" className="confirm-payment__title">
          Confirm the payment to {card.recipientName}?
        </h2>
        <div className="confirm-payment__amount">{formatMoney(choice.amount, card.currency)}</div>
        <dl className="confirm-payment__rows">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <div className="confirm-payment__actions">
          <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary" onClick={onConfirm} autoFocus>
            Confirm payment
          </button>
        </div>
      </div>
    </div>
  )
}
