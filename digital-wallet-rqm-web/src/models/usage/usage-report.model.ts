// Consumo de tokens de un día, tal como lo devuelve GET /usage/daily.
export interface DailyUsage {
  day: string // YYYY-MM-DD (hora de Bolivia)
  input_tokens: number
  output_tokens: number
  runs: number
}

// Respuesta de GET /usage/daily: "today" lo decide el backend, así no depende del reloj del navegador.
export interface UsageReport {
  today: string
  days: DailyUsage[]
}
