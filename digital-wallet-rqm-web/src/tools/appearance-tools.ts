import type { Tool } from '@ag-ui/client'

// Tools del cliente: el backend solo recibe su descripción (name, description, parameters).
// Gemini elige una y el navegador la ejecuta acá; los enum son los únicos valores permitidos.

const FONTS: Record<string, string> = {
  Inter: "'Inter', sans-serif",
  Roboto: "'Roboto', sans-serif",
  Georgia: "Georgia, serif",
  'Fira Code': "'Fira Code', monospace",
}

// Tamaño base de la página: Bootstrap usa rem, así que escala todo el texto.
const FONT_SIZES: Record<string, string> = {
  small: '14px',
  medium: '16px',
  large: '18px',
}

// Colores que acepta set_background: hex (#RGB, #RGBA, #RRGGBB, #RRGGBBAA), rgb(...) o rgba(...).
// El valor lo define el LLM, así que se valida: nunca llega CSS arbitrario (url(...), otras propiedades).
const HEX_COLOR = /^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i
const RGB_COLOR = /^rgba?\([\d.%\s,/]+\)$/i

function isSafeColor(value: unknown): value is string {
  if (typeof value !== 'string') return false
  const color = value.trim()
  return (HEX_COLOR.test(color) || RGB_COLOR.test(color)) && CSS.supports('color', color)
}

function enumParameter(name: string, description: string, values: string[]) {
  return {
    type: 'object',
    properties: { [name]: { type: 'string', enum: values, description } },
    required: [name],
  }
}

export const APPEARANCE_TOOLS: Tool[] = [
  {
    name: 'set_theme',
    description: 'Cambia la app a modo claro u oscuro',
    parameters: enumParameter('theme', 'Modo de color', ['light', 'dark']),
  },
  {
    name: 'set_background',
    description:
      'Cambia el fondo de la app. type "solid" usa color; "gradient" va de from a to; "default" vuelve al ' +
      'fondo original. Los colores van en hex (#001f3f) o rgb/rgba (rgba(255, 0, 0, 0.5)): si el cliente ' +
      'nombra un color ("azul marino", "atardecer"), conviértelo tú a esos formatos',
    parameters: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['solid', 'gradient', 'default'], description: 'Tipo de fondo' },
        color: { type: 'string', description: 'Color del fondo puro (solo type solid)' },
        from: { type: 'string', description: 'Color inicial del degradado (solo type gradient)' },
        to: { type: 'string', description: 'Color final del degradado (solo type gradient)' },
      },
      required: ['type'],
    },
  },
  {
    name: 'set_font',
    description: 'Cambia el tipo de letra de la app',
    parameters: enumParameter('font', 'Tipo de letra', Object.keys(FONTS)),
  },
  {
    name: 'set_font_size',
    description: 'Cambia el tamaño de letra de la app',
    parameters: enumParameter('size', 'Tamaño de letra', Object.keys(FONT_SIZES)),
  },
]

// Aplica un valor de una lista; devuelve el resultado como texto (es lo que se mandaría al agente en T7).
function applyFromList(list: Record<string, string>, value: unknown, apply: (css: string) => void): string {
  // Object.hasOwn: solo claves propias de la lista, nunca heredadas (toString, constructor...)
  const css = typeof value === 'string' && Object.hasOwn(list, value) ? list[value] : undefined
  if (css === undefined) return `error: valor no permitido "${String(value)}"`
  apply(css)
  return `ok: ${value}`
}

// Fondo puro, degradado o el original; si algún color no es válido no cambia nada.
function applyBackground(root: HTMLElement, args: Record<string, unknown>): string {
  if (args.type === 'default') {
    root.style.removeProperty('--app-background')
    return 'ok: default'
  }
  if (args.type === 'solid') {
    if (!isSafeColor(args.color)) return `error: color no válido "${String(args.color)}"`
    root.style.setProperty('--app-background', args.color.trim())
    return `ok: ${args.color}`
  }
  if (args.type === 'gradient') {
    if (!isSafeColor(args.from) || !isSafeColor(args.to)) {
      return `error: degradado no válido "${String(args.from)}" → "${String(args.to)}"`
    }
    root.style.setProperty('--app-background', `linear-gradient(135deg, ${args.from.trim()} 0%, ${args.to.trim()} 100%)`)
    return `ok: ${args.from} → ${args.to}`
  }
  return `error: tipo de fondo no válido "${String(args.type)}"`
}

// Ejecuta la tool que pidió el agente sobre el documento; tools desconocidas no hacen nada.
export function runAppearanceTool(name: string, rawArgs: unknown): string {
  // Los args vienen del LLM: si no llegan como objeto, se tratan como vacíos (cada tool responde con error)
  const args: Record<string, unknown> = typeof rawArgs === 'object' && rawArgs !== null ? { ...rawArgs } : {}
  const root = document.documentElement
  switch (name) {
    case 'set_theme':
      return applyFromList({ light: 'light', dark: 'dark' }, args.theme, (theme) =>
        root.setAttribute('data-bs-theme', theme),
      )
    case 'set_background':
      return applyBackground(root, args)
    case 'set_font':
      return applyFromList(FONTS, args.font, (css) => root.style.setProperty('--bs-body-font-family', css))
    case 'set_font_size':
      return applyFromList(FONT_SIZES, args.size, (css) => (root.style.fontSize = css))
    default:
      return `error: tool desconocida "${name}"`
  }
}
