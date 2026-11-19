import { describe, expect, it } from 'vitest'
import { DISPLAY_TOOLS, isDisplayTool, parseDisplayCard } from './display-tools'

describe('DISPLAY_TOOLS', () => {
  it('declares the balance card so the backend knows the app can draw it', () => {
    expect(DISPLAY_TOOLS.map((tool) => tool.name)).toEqual(['show_account_balance', 'show_qr_payment', 'show_payment_receipt'])
  })
})

describe('isDisplayTool', () => {
  it('tells display tools apart from tools the browser runs', () => {
    expect(isDisplayTool('show_account_balance')).toBe(true)
    expect(isDisplayTool('show_qr_payment')).toBe(true)
    expect(isDisplayTool('set_theme')).toBe(false)
  })
})

describe('parseDisplayCard', () => {
  const balance = { account_number: '1001234567', account_type: 'Caja de ahorro', currency: 'BOB', available: '1500.50' }

  it('turns each display tool into the card the chat draws', () => {
    expect(parseDisplayCard('show_account_balance', balance)).toEqual({
      card: { accountNumber: '1001234567', accountType: 'Caja de ahorro', currency: 'BOB', available: 1500.5 },
    })
    const qr = {
      code: 'qr_af9bd6ff81dc2525a2fba110bf390946',
      recipient_name: 'Juan Pérez',
      bank: 'Banco Unión',
      account_number: '12345678',
      document_id: '87654321',
      amount: '350.00',
      currency: 'BOB',
      usage: 'single',
      expires_on: '2026-12-18',
      note: '',
      expired: false,
      already_paid: false,
      accounts: [balance],
    }
    expect(parseDisplayCard('show_qr_payment', qr)?.qrPayment?.recipientName).toBe('Juan Pérez')
    const receipt = {
      receipt_number: 'PAY-1',
      qr_code: qr.code,
      recipient_name: 'Juan Pérez',
      bank: 'Banco Unión',
      destination_account: '12345678',
      from_account: '1001234567',
      amount: '350.00',
      currency: 'BOB',
      balance_after: '1150.50',
      paid_at: '2026-11-18T15:30:00+00:00',
    }
    expect(parseDisplayCard('show_payment_receipt', receipt)?.receipt?.receiptNumber).toBe('PAY-1')
  })

  it('returns null for broken data or an unknown tool', () => {
    expect(parseDisplayCard('show_qr_payment', { code: 'x' })).toBeNull()
    expect(parseDisplayCard('show_account_balance', {})).toBeNull()
    expect(parseDisplayCard('set_theme', balance)).toBeNull()
  })
})
