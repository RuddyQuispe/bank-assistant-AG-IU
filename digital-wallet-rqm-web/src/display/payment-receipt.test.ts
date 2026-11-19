import { describe, expect, it } from 'vitest'
import { formatPaidAt, parsePaymentReceipt } from './payment-receipt'

const ARGS = {
  receipt_number: 'PAY-3F9A1C2B7D',
  qr_code: 'qr_af9bd6ff81dc2525a2fba110bf390946',
  recipient_name: 'Juan Pérez',
  bank: 'Banco Unión',
  destination_account: '12345678',
  from_account: '1001234567',
  amount: '350.00',
  currency: 'BOB',
  balance_after: '1150.50',
  paid_at: '2026-11-18T15:30:00+00:00',
}

describe('parsePaymentReceipt', () => {
  it('reads the receipt the backend sends with show_payment_receipt', () => {
    expect(parsePaymentReceipt(ARGS)).toEqual({
      receiptNumber: 'PAY-3F9A1C2B7D',
      recipientName: 'Juan Pérez',
      bank: 'Banco Unión',
      destinationAccount: '12345678',
      fromAccount: '1001234567',
      amount: 350,
      currency: 'BOB',
      balanceAfter: 1150.5,
      paidAt: '2026-11-18T15:30:00+00:00',
    })
  })

  it.each([
    ['missing args', undefined],
    ['non numeric amount', { ...ARGS, amount: 'mucho' }],
    ['a date that is not a date', { ...ARGS, paid_at: 'ayer' }],
    ['missing receipt number', { ...ARGS, receipt_number: '' }],
  ])('rejects %s', (_case, args) => {
    expect(parsePaymentReceipt(args)).toBeNull()
  })
})

describe('formatPaidAt', () => {
  it('shows the date and time of the payment in La Paz time', () => {
    expect(formatPaidAt('2026-11-18T15:30:00+00:00')).toBe('Nov 18, 2026, 11:30 AM')
  })
})
