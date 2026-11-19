import { useId, useState } from 'react'
import type { BalanceCardData } from '../display/balance-card'
import {
  formatExpiry,
  formatMoney,
  parseAmountInput,
  paymentProblem,
  type QrPaymentCardData,
} from '../display/qr-payment-card'
import './QrPaymentCard.css'

export interface PaymentChoice {
  account: BalanceCardData
  // Monto que se va a pagar: el del QR, o el que escribió el pagador si el QR viene en 0
  amount: number
}

interface QrPaymentCardProps {
  card: QrPaymentCardData
  // Lo conecta el paso de confirmación (F5); sin él, el botón queda deshabilitado
  onPay?: (choice: PaymentChoice) => void
}

function maskNumber(accountNumber: string): string {
  return `****${accountNumber.slice(-4)}`
}

// Presentacional: el cobro QR escaneado, para elegir la cuenta (y el monto si el QR viene en 0) y pagar.
export function QrPaymentCard({ card, onPay }: QrPaymentCardProps) {
  const groupName = useId()
  // Arranca con la primera cuenta de la misma moneda que el QR
  const [selected, setSelected] = useState(
    () => card.accounts.find((account) => account.currency === card.currency)?.accountNumber,
  )
  const [amountText, setAmountText] = useState('')
  const account = card.accounts.find((candidate) => candidate.accountNumber === selected)
  const payerSetsAmount = card.amount === 0
  const problem = paymentProblem(card, account, amountText)
  const blocked = card.expired || card.alreadyPaid

  function handlePay() {
    if (problem || !account || !onPay) return
    const amount = payerSetsAmount ? (parseAmountInput(amountText) as number) : card.amount
    onPay({ account, amount })
  }

  return (
    <article className="qr-card" aria-label={`QR payment to ${card.recipientName}`}>
      <header className="qr-card__header">
        <div className="qr-card__eyebrow">QR payment</div>
        <div className="qr-card__recipient">{card.recipientName}</div>
        <div className="qr-card__bank">{card.bank}</div>
        <div className="qr-card__amount">
          {payerSetsAmount ? 'You set the amount' : formatMoney(card.amount, card.currency)}
        </div>
        {blocked && (
          <span className="qr-card__badge">{card.expired ? 'Expired' : 'Already paid'}</span>
        )}
      </header>

      <dl className="qr-card__details">
        <div>
          <dt>Destination account</dt>
          <dd>{card.accountNumber}</dd>
        </div>
        <div>
          <dt>NIT / CI</dt>
          <dd>{card.documentId}</dd>
        </div>
        <div>
          <dt>Valid for</dt>
          <dd>{card.usage === 'single' ? 'Single payment' : 'Multiple payments'}</dd>
        </div>
        <div>
          <dt>Expires</dt>
          <dd>{formatExpiry(card.expiresOn)}</dd>
        </div>
        {card.note && (
          <div className="qr-card__note">
            <dt>Note</dt>
            <dd>{card.note}</dd>
          </div>
        )}
      </dl>

      {!blocked && (
        <fieldset className="qr-card__accounts">
          <legend>Pay from</legend>
          {card.accounts.map((candidate) => {
            const otherCurrency = candidate.currency !== card.currency
            return (
              <label
                key={candidate.accountNumber}
                className={`qr-card__account ${otherCurrency ? 'qr-card__account--disabled' : ''}`}
              >
                <input
                  type="radio"
                  name={groupName}
                  value={candidate.accountNumber}
                  checked={selected === candidate.accountNumber}
                  disabled={otherCurrency}
                  onChange={() => setSelected(candidate.accountNumber)}
                />
                <span className="qr-card__account-name">
                  {candidate.accountType}
                  <span className="qr-card__account-number">{maskNumber(candidate.accountNumber)}</span>
                </span>
                <span className="qr-card__account-balance">
                  {formatMoney(candidate.available, candidate.currency)}
                </span>
              </label>
            )
          })}
        </fieldset>
      )}

      {!blocked && payerSetsAmount && (
        <label className="qr-card__amount-field">
          <span>Amount to pay</span>
          <input
            className="form-control"
            inputMode="decimal"
            placeholder="0.00"
            value={amountText}
            onChange={(event) => setAmountText(event.target.value)}
          />
        </label>
      )}

      <footer className="qr-card__footer">
        {problem && <p className="qr-card__problem">{problem}</p>}
        {!blocked && (
          <button type="button" className="btn btn-primary qr-card__pay" disabled={!!problem || !onPay} onClick={handlePay}>
            Pay
          </button>
        )}
      </footer>
    </article>
  )
}
