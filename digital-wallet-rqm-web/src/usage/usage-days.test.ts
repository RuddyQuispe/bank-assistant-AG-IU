import { describe, expect, it } from 'vitest'
import type { UsageReport } from '../models/usage/usage-report.model'
import { formatDay, formatTokens, formatTokensCompact, lastDays, todayUsage } from './usage-days'

const report: UsageReport = {
  today: '2026-11-16',
  days: [
    { day: '2026-11-16', input_tokens: 812, output_tokens: 95, runs: 1 },
    { day: '2026-11-14', input_tokens: 12400, output_tokens: 1830, runs: 11 },
  ],
}

describe('todayUsage', () => {
  it("returns today's row", () => {
    expect(todayUsage(report)).toEqual({ day: '2026-11-16', input_tokens: 812, output_tokens: 95, runs: 1 })
  })

  it('starts from zero when there was no run today', () => {
    expect(todayUsage({ today: '2026-11-17', days: report.days })).toEqual({
      day: '2026-11-17',
      input_tokens: 0,
      output_tokens: 0,
      runs: 0,
    })
  })
})

describe('lastDays', () => {
  it('fills the days without usage with zero, newest first', () => {
    expect(lastDays(report, 3)).toEqual([
      { day: '2026-11-16', input_tokens: 812, output_tokens: 95, runs: 1 },
      { day: '2026-11-15', input_tokens: 0, output_tokens: 0, runs: 0 },
      { day: '2026-11-14', input_tokens: 12400, output_tokens: 1830, runs: 11 },
    ])
  })

  it('crosses month boundaries', () => {
    expect(lastDays({ today: '2026-12-01', days: [] }, 2).map((usage) => usage.day)).toEqual([
      '2026-12-01',
      '2026-11-30',
    ])
  })
})

describe('formatters', () => {
  it('shows days as dd/mm/yyyy and tokens with thousands separators', () => {
    expect(formatDay('2026-11-16')).toBe('16/11/2026')
    expect(formatTokens(48210)).toBe('48,210')
  })
})

describe('formatTokensCompact', () => {
  it('shortens thousands and millions for the mobile header', () => {
    expect(formatTokensCompact(812)).toBe('812')
    expect(formatTokensCompact(1000)).toBe('1k')
    expect(formatTokensCompact(1512)).toBe('1.5k')
    expect(formatTokensCompact(18539)).toBe('18.5k')
    expect(formatTokensCompact(1250000)).toBe('1.3M')
  })
})
