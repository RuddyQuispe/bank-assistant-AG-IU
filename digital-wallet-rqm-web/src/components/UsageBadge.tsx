import type { UsageReport } from '../models/usage/usage-report.model'
import { formatTokens, todayUsage } from '../usage/usage-days'

interface UsageBadgeProps {
  report: UsageReport | null
  onOpen: () => void
}

// Consumo de tokens de hoy en el header; al hacer clic abre el detalle de la semana.
export function UsageBadge({ report, onOpen }: UsageBadgeProps) {
  if (!report) return null
  const today = todayUsage(report)
  return (
    <button
      type="button"
      className="btn btn-link btn-sm text-body-secondary text-decoration-none"
      title="Token usage of the last 7 days"
      onClick={onOpen}
    >
      Today: ↑ {formatTokens(today.input_tokens)} in · ↓ {formatTokens(today.output_tokens)} out
    </button>
  )
}
