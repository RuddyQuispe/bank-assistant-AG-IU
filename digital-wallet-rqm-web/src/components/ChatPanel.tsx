import { useState, type FormEvent } from 'react'
import type { ChatMessage } from '../models/chat/chat-message.model'
import type { QrPaymentCardData } from '../display/qr-payment-card'
import { BalanceCard } from './BalanceCard'
import { PaymentReceiptCard } from './PaymentReceiptCard'
import { QrPaymentCard, type PaymentChoice } from './QrPaymentCard'

interface ChatPanelProps {
  messages: ChatMessage[]
  running: boolean
  step: string | null
  error: string | null
  onSend: (question: string) => void
  // Token del QR que el agente espera pagar: solo esa tarjeta habilita "Pay"
  payableQr?: string | null
  onPayQr?: (card: QrPaymentCardData, choice: PaymentChoice) => void
}

// Presentacional: dibuja los mensajes y la caja de pregunta.
export function ChatPanel({ messages, running, step, error, onSend, payableQr, onPayQr }: ChatPanelProps) {
  const [question, setQuestion] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSend(question.trim())
    setQuestion('')
  }

  return (
    <>
      <div className="chat-messages flex-grow-1 overflow-auto p-3 bg-body-tertiary">
        {messages.length === 0 && (
          <p className="text-body-secondary text-center my-5">Ask anything about your wallet.</p>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`d-flex mb-2 ${message.role === 'user' ? 'justify-content-end' : 'justify-content-start'} ${
              message.card || message.qrPayment || message.receipt
                ? 'chat-msg-card'
                : message.role === 'user'
                  ? 'chat-msg-user'
                  : 'chat-msg-assistant'
            }`}
          >
            {message.card ? (
              <BalanceCard {...message.card} />
            ) : message.qrPayment ? (
              <QrPaymentCard
                card={message.qrPayment}
                onPay={
                  onPayQr && !running && message.qrPayment.code === payableQr
                    ? (choice) => onPayQr(message.qrPayment as QrPaymentCardData, choice)
                    : undefined
                }
              />
            ) : message.receipt ? (
              <PaymentReceiptCard receipt={message.receipt} />
            ) : (
              <div
                className={`px-3 py-2 rounded-3 ${message.role === 'user' ? 'bg-primary text-white' : 'bg-body border'}`}
                style={{ maxWidth: '80%', whiteSpace: 'pre-wrap' }}
              >
                {message.content || (
                  <span className="typing-dots" aria-label="Typing">
                    <span />
                    <span />
                    <span />
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
        {step && (
          // key = paso: cada paso nuevo del grafo vuelve a animarse
          <div key={step} className="chat-step d-flex align-items-center gap-2 text-body-secondary small mb-2">
            <span className="spinner-border spinner-border-sm" aria-hidden="true" />
            <span role="status">{step}</span>
          </div>
        )}
        {error && (
          <div className="alert alert-danger py-2 small mt-2" role="alert">
            {error}
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="chat-composer d-flex gap-2 p-3 border-top">
        <input
          className="form-control"
          placeholder="Type your question…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={running}
          autoFocus
        />
        <button type="submit" className="btn btn-primary" disabled={running || !question.trim()}>
          {running ? <span className="spinner-border spinner-border-sm" aria-label="Sending" /> : 'Send'}
        </button>
      </form>
    </>
  )
}
