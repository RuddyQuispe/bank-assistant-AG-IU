import { useState } from 'react'
import { currencyLabel, formatAccountNumber, splitAmount, type BalanceCardData } from '../display/balance-card'
import './BalanceCard.css'

const HIDDEN_AMOUNT = '••••••'

function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" />
      {!open && <path d="M4 4l16 16" strokeLinecap="round" />}
    </svg>
  )
}

// Presentacional: la cuenta del cliente como una tarjeta dentro del chat.
// Arranca oculta: el saldo y el número completo solo se escriben en pantalla al tocar el ojo.
export function BalanceCard({ accountNumber, accountType, currency, available }: BalanceCardData) {
  const [visible, setVisible] = useState(false)
  const { whole, cents } = splitAmount(available)

  return (
    <article className="balance-card" aria-label={`${accountType} balance`}>
      <header className="balance-card__top">
        <span className="balance-card__brand">
          <span className="balance-card__logo" aria-hidden="true" />
          Digital Wallet
        </span>
        <span className="balance-card__currency">{currency}</span>
      </header>

      <div className="balance-card__label">Available balance</div>
      <div className="balance-card__amount-row">
        <p className="balance-card__amount" aria-live="polite">
          <span className="balance-card__symbol">{currencyLabel(currency)}</span>
          {visible ? (
            <>
              <span className="balance-card__whole">{whole}</span>
              <span className="balance-card__cents">.{cents}</span>
            </>
          ) : (
            <span className="balance-card__whole balance-card__whole--hidden">{HIDDEN_AMOUNT}</span>
          )}
        </p>
        <button
          type="button"
          className="balance-card__toggle"
          onClick={() => setVisible((current) => !current)}
          aria-pressed={visible}
          aria-label={visible ? 'Hide balance' : 'Show balance'}
        >
          <EyeIcon open={visible} />
        </button>
      </div>

      <footer className="balance-card__bottom">
        <span className="balance-card__chip" aria-hidden="true" />
        <div>
          <div className="balance-card__number">{formatAccountNumber(accountNumber, visible)}</div>
          <div className="balance-card__type">{accountType}</div>
        </div>
      </footer>
    </article>
  )
}
