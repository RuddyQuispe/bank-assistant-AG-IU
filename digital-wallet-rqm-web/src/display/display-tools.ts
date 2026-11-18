import type { Tool } from '@ag-ui/client'

// Tools de solo mostrar: el agente las manda con datos y el chat las dibuja como un componente.
// No se ejecutan ni devuelven resultado. Declararlas le dice al backend que la app sabe dibujarlas;
// el backend nunca se las ofrece al LLM, las emite él con los datos reales.
export const SHOW_ACCOUNT_BALANCE = 'show_account_balance'

export const DISPLAY_TOOLS: Tool[] = [
  {
    name: SHOW_ACCOUNT_BALANCE,
    description: 'Muestra en el chat una tarjeta con el saldo de la cuenta del cliente',
    parameters: {
      type: 'object',
      properties: {
        account_number: { type: 'string', description: 'Número de cuenta' },
        account_type: { type: 'string', description: 'Tipo de cuenta' },
        currency: { type: 'string', description: 'Moneda ISO 4217' },
        available: { type: 'string', description: 'Saldo disponible, por ejemplo "1500.50"' },
      },
      required: ['account_number', 'account_type', 'currency', 'available'],
    },
  },
]

const DISPLAY_TOOL_NAMES = new Set(DISPLAY_TOOLS.map((tool) => tool.name))

export function isDisplayTool(name: string): boolean {
  return DISPLAY_TOOL_NAMES.has(name)
}
