import { describe, expect, it } from 'vitest'
import { cancelPayment, confirmPayment, parsePaymentPause } from './qr-payment-resume'

const TOKEN = 'qr_af9bd6ff81dc2525a2fba110bf390946'

describe('parsePaymentPause', () => {
  it('reads the QR the graph is waiting to pay from the on_interrupt value', () => {
    expect(parsePaymentPause(JSON.stringify({ type: 'qr_payment', code: TOKEN }))).toBe(TOKEN)
  })

  it.each([
    ['another kind of pause', JSON.stringify({ type: 'approval', code: TOKEN })],
    ['a code that is not a QR token', JSON.stringify({ type: 'qr_payment', code: 'QR-1' })],
    ['broken JSON', '{nope'],
    ['a value that is not text', 42],
  ])('ignores %s', (_case, value) => {
    expect(parsePaymentPause(value)).toBeNull()
  })
})

describe('resume commands', () => {
  it('confirms with the chosen account and the amount with two decimals', () => {
    expect(confirmPayment('1001234567', 25.5)).toEqual({
      command: { resume: { action: 'pay', account_number: '1001234567', amount: '25.50' } },
    })
  })

  it('cancels the pending payment', () => {
    expect(cancelPayment()).toEqual({ command: { resume: { action: 'cancel' } } })
  })
})
