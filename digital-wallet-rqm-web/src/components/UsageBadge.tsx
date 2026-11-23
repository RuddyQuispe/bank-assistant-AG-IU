import type { UsageReport } from '../models/usage/usage-report.model'
import { formatTokens, formatTokensCompact, todayUsage } from '../usage/usage-days'

interface UsageBadgeProps {
  report: UsageReport | null
  onOpen: () => void
  // compact: en móvil va debajo del título, con números cortos (18.5k)
  compact?: boolean
}

// Consumo de tokens de hoy en el header; al hacer clic abre el detalle de la semana.
export function UsageBadge({ report, onOpen, compact = false }: UsageBadgeProps) {
  if (!report) return null
  const today = todayUsage(report)
  return (
    <button
      type="button"
      className={`btn btn-link btn-sm text-body-secondary text-decoration-none text-nowrap ${compact ? 'p-0 small' : ''}`}
      title="Token usage of the last 7 days"
      onClick={onOpen}
    >
      {compact
        ? `↑ ${formatTokensCompact(today.input_tokens)} · ↓ ${formatTokensCompact(today.output_tokens)}`
        : `Today: ↑ ${formatTokens(today.input_tokens)} in · ↓ ${formatTokens(today.output_tokens)} out`}
    </button>
  )
}
