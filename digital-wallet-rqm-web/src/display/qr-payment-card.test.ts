import { describe, expect, it } from 'vitest'
import {
  formatExpiry,
  formatMoney,
  paymentProblem,
  parseAmountInput,
  parseQrPaymentCard,
  type QrPaymentCardData,
} from './qr-payment-card'

const ARGS = {
  code: 'qr_af9bd6ff81dc2525a2fba110bf390946',
  recipient_name: 'Juan Pérez',
  bank: 'Banco Unión',
  account_number: '12345678',
  document_id: '87654321',
  amount: '350.00',
  currency: 'BOB',
  usage: 'single',
  expires_on: '2026-12-18',
  note: 'Alquiler noviembre',
  expired: false,
  already_paid: false,
  accounts: [
    { account_number: '1001234567', account_type: 'Caja de ahorro', currency: 'BOB', available: '1500.50' },
    { account_number: '2009876543', account_type: 'Cuenta corriente', currency: 'BOB', available: '100.00' },
    { account_number: '3005551234', account_type: 'Caja de ahorro', currency: 'USD', available: '320.00' },
  ],
}

function card(changes: Partial<QrPaymentCardData> = {}): QrPaymentCardData {
  return { ...(parseQrPaymentCard(ARGS) as QrPaymentCardData), ...changes }
}

describe('parseQrPaymentCard', () => {
  it('reads the payment data and the accounts the backend sends with show_qr_payment', () => {
    const parsed = parseQrPaymentCard(ARGS)

    expect(parsed).toMatchObject({
      code: ARGS.code,
      recipientName: 'Juan Pérez',
      bank: 'Banco Unión',
      accountNumber: '12345678',
      documentId: '87654321',
      amount: 350,
      currency: 'BOB',
      usage: 'single',
      expiresOn: '2026-12-18',
      note: 'Alquiler noviembre',
      expired: false,
      alreadyPaid: false,
    })
    expect(parsed?.accounts.map((account) => account.accountNumber)).toEqual([
      '1001234567',
      '2009876543',
      '3005551234',
    ])
  })

  it.each([
    ['missing args', undefined],
    ['non numeric amount', { ...ARGS, amount: 'mucho' }],
    ['unknown usage', { ...ARGS, usage: 'forever' }],
    ['flags that are not booleans', { ...ARGS, expired: 'no' }],
    ['a broken account', { ...ARGS, accounts: [{ account_number: '1' }] }],
    ['accounts that are not a list', { ...ARGS, accounts: 'none' }],
  ])('rejects %s', (_case, args) => {
    expect(parseQrPaymentCard(args)).toBeNull()
  })
})

describe('parseAmountInput', () => {
  it.each([
    ['20', 20],
    ['30.5', 30.5],
    ['30.25', 30.25],
  ])('reads %s', (text, amount) => {
    expect(parseAmountInput(text)).toBe(amount)
  })

  it.each(['', '0', '0.00', '-5', '10.001', 'abc', '1e3'])('rejects %s', (text) => {
    expect(parseAmountInput(text)).toBeNull()
  })
})

describe('paymentProblem', () => {
  const [savings, checking, dollars] = card().accounts

  it('is null when the payment can go ahead', () => {
    expect(paymentProblem(card(), savings, '')).toBeNull()
  })

  it('blocks an expired or already paid QR', () => {
    expect(paymentProblem(card({ expired: true }), savings, '')).toBe('This QR has expired.')
    expect(paymentProblem(card({ alreadyPaid: true }), savings, '')).toBe('This QR was already paid.')
  })

  it('asks for an account', () => {
    expect(paymentProblem(card(), undefined, '')).toBe('Choose the account to pay from.')
  })

  it('rejects an account in another currency', () => {
    expect(paymentProblem(card(), dollars, '')).toBe('This account is in USD and the QR charges in Bs.')
  })

  it('rejects an account without enough balance', () => {
    expect(paymentProblem(card(), checking, '')).toBe('Not enough balance in this account.')
  })

  it('asks the payer for the amount when the QR amount is 0', () => {
    const open = card({ amount: 0, usage: 'multiple' })

    expect(paymentProblem(open, savings, '')).toBe('Enter an amount greater than 0 with up to 2 decimals.')
    expect(paymentProblem(open, savings, '25.50')).toBeNull()
    expect(paymentProblem(open, savings, '2000')).toBe('Not enough balance in this account.')
  })
})

describe('formatting', () => {
  it('writes money with the currency label first', () => {
    expect(formatMoney(1500.5, 'BOB')).toBe('Bs 1,500.50')
    expect(formatMoney(20, 'USD')).toBe('USD 20.00')
  })

  it('writes the expiry date without shifting the day', () => {
    expect(formatExpiry('2026-12-18')).toBe('Dec 18, 2026')
  })
})
