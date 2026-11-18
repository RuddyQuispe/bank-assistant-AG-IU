import { describe, expect, it } from 'vitest'
import { currencyLabel, formatAccountNumber, parseBalanceCard, splitAmount } from './balance-card'

const ARGS = {
  account_number: '1001234567',
  account_type: 'Caja de ahorro',
  currency: 'BOB',
  available: '1500.50',
}

describe('parseBalanceCard', () => {
  it('reads the data the backend sends with show_account_balance', () => {
    expect(parseBalanceCard(ARGS)).toEqual({
      accountNumber: '1001234567',
      accountType: 'Caja de ahorro',
      currency: 'BOB',
      available: 1500.5,
    })
  })

  it.each([
    ['missing args', undefined],
    ['missing account number', { ...ARGS, account_number: undefined }],
    ['non numeric balance', { ...ARGS, available: 'mucho' }],
    ['balance sent as a number', { ...ARGS, available: 1500.5 }],
    ['empty currency', { ...ARGS, currency: '' }],
  ])('rejects %s', (_case, args) => {
    expect(parseBalanceCard(args)).toBeNull()
  })
})

describe('currencyLabel', () => {
  it('writes bolivianos as Bs', () => {
    expect(currencyLabel('BOB')).toBe('Bs')
  })

  it('keeps any other currency code', () => {
    expect(currencyLabel('EUR')).toBe('EUR')
  })
})

describe('splitAmount', () => {
  it('splits the whole part and the cents so the card can draw them in two sizes', () => {
    expect(splitAmount(1500.5)).toEqual({ whole: '1,500', cents: '50' })
  })

  it('keeps two digits of cents for round amounts', () => {
    expect(splitAmount(20)).toEqual({ whole: '20', cents: '00' })
  })
})

describe('formatAccountNumber', () => {
  it('groups the full number in blocks of four when visible', () => {
    expect(formatAccountNumber('1001234567', true)).toBe('1001 2345 67')
  })

  it('shows only the last four digits when hidden', () => {
    expect(formatAccountNumber('1001234567', false)).toBe('•••• •••• 4567')
  })
})
