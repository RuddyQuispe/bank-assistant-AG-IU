import type { DailyUsage, UsageReport } from '../models/usage/usage-report.model'

// El backend solo devuelve días con consumo: estos helpers completan los que faltan con cero.

function emptyDay(day: string): DailyUsage {
  return { day, input_tokens: 0, output_tokens: 0, runs: 0 }
}

// Resta días a una fecha YYYY-MM-DD sin pasar por la zona horaria del navegador (todo en UTC).
function minusDays(day: string, count: number): string {
  const date = new Date(`${day}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() - count)
  return date.toISOString().slice(0, 10)
}

// Consumo de hoy (cero si todavía no hubo runs: cada día empieza desde cero).
export function todayUsage(report: UsageReport): DailyUsage {
  return report.days.find((usage) => usage.day === report.today) ?? emptyDay(report.today)
}

// Los últimos `count` días contando hoy, el más reciente primero, con cero en los días sin consumo.
export function lastDays(report: UsageReport, count: number): DailyUsage[] {
  const byDay = new Map(report.days.map((usage) => [usage.day, usage]))
  return Array.from({ length: count }, (_, index) => {
    const day = minusDays(report.today, index)
    return byDay.get(day) ?? emptyDay(day)
  })
}

// "2026-11-16" → "16/11/2026"
export function formatDay(day: string): string {
  const [year, month, date] = day.split('-')
  return `${date}/${month}/${year}`
}

// 48210 → "48,210"
export function formatTokens(tokens: number): string {
  return tokens.toLocaleString('en-US')
}

const COMPACT = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

// Versión corta para el header en móvil: 18539 -> "18.5k"
export function formatTokensCompact(tokens: number): string {
  return COMPACT.format(tokens).replace('K', 'k')
}
