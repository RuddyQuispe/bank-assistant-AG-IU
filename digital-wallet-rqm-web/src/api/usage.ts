import type { UsageReport } from '../models/usage/usage-report.model'
import { API_URL, ensureOk } from './config'

// GET /usage/daily: consumo de tokens del usuario del token; sin rango, los últimos 7 días.
export async function getDailyUsage(token: string): Promise<UsageReport> {
  const response = await fetch(`${API_URL}/usage/daily`, { headers: { Authorization: `Bearer ${token}` } })
  await ensureOk(response)
  return (await response.json()) as UsageReport
}
