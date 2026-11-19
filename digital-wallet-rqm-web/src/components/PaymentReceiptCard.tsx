import { formatPaidAt, type PaymentReceiptData } from '../display/payment-receipt'
import { formatMoney } from '../display/qr-payment-card'
import './QrPaymentCard.css'

// Presentacional: comprobante de un pago con QR, con el mismo estilo que la tarjeta del cobro.
export function PaymentReceiptCard({ receipt }: { receipt: PaymentReceiptData }) {
  return (
    <article className="qr-card" aria-label={`Payment receipt ${receipt.receiptNumber}`}>
      <header className="qr-card__header qr-card__header--success">
        <div className="qr-card__eyebrow">
          <span className="qr-card__check" aria-hidden="true">
            ✓
          </span>
          Payment completed
        </div>
        <div className="qr-card__amount">{formatMoney(receipt.amount, receipt.currency)}</div>
        <div className="qr-card__bank">to {receipt.recipientName}</div>
      </header>

      <dl className="qr-card__details qr-card__details--receipt">
        <div>
          <dt>Bank</dt>
          <dd>{receipt.bank}</dd>
        </div>
        <div>
          <dt>Destination account</dt>
          <dd>{receipt.destinationAccount}</dd>
        </div>
        <div>
          <dt>Paid from</dt>
          <dd>****{receipt.fromAccount.slice(-4)}</dd>
        </div>
        <div>
          <dt>Balance after</dt>
          <dd>{formatMoney(receipt.balanceAfter, receipt.currency)}</dd>
        </div>
        <div>
          <dt>Receipt</dt>
          <dd className="qr-card__mono">{receipt.receiptNumber}</dd>
        </div>
        <div>
          <dt>Date</dt>
          <dd>{formatPaidAt(receipt.paidAt)}</dd>
        </div>
      </dl>
    </article>
  )
}
