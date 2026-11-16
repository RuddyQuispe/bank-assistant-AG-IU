import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { APPEARANCE_TOOLS, runAppearanceTool } from './appearance-tools'

const root = document.documentElement

beforeEach(() => {
  // jsdom no trae CSS.supports: el filtro de seguridad real es la regex, que es lo que se prueba acá
  vi.stubGlobal('CSS', { supports: () => true })
})

afterEach(() => {
  vi.unstubAllGlobals()
  root.removeAttribute('data-bs-theme')
  root.removeAttribute('style')
})

describe('APPEARANCE_TOOLS', () => {
  it('declares the four tools the agent can call', () => {
    expect(APPEARANCE_TOOLS.map((tool) => tool.name)).toEqual([
      'set_theme',
      'set_background',
      'set_font',
      'set_font_size',
    ])
  })
})

describe('set_theme', () => {
  it('switches Bootstrap to dark mode', () => {
    expect(runAppearanceTool('set_theme', { theme: 'dark' })).toBe('ok: dark')
    expect(root.getAttribute('data-bs-theme')).toBe('dark')
  })

  it('rejects inherited object keys such as toString', () => {
    expect(runAppearanceTool('set_theme', { theme: 'toString' })).toBe('error: valor no permitido "toString"')
    expect(root.hasAttribute('data-bs-theme')).toBe(false)
  })

  it('rejects a value outside the list and changes nothing', () => {
    expect(runAppearanceTool('set_theme', { theme: 'sepia' })).toBe('error: valor no permitido "sepia"')
    expect(root.hasAttribute('data-bs-theme')).toBe(false)
  })
})

describe('set_background', () => {
  it.each(['#001f3f', '#fff', '#ff573380', 'rgb(255, 87, 51)', 'rgba(255,0,0,0.5)', 'rgb(255 0 0 / 50%)'])(
    'applies the solid color %s',
    (color) => {
      expect(runAppearanceTool('set_background', { type: 'solid', color })).toBe(`ok: ${color}`)
      expect(root.style.getPropertyValue('--app-background')).toBe(color)
    },
  )

  it.each(['red', 'url(https://evil.test/a.png)', '#fff; color: red', 'rgb(1,2,3)) url(x', '#12345', 42])(
    'rejects %s and keeps the current background',
    (color) => {
      expect(runAppearanceTool('set_background', { type: 'solid', color })).toMatch(/^error: color no válido/)
      expect(root.style.getPropertyValue('--app-background')).toBe('')
    },
  )

  it('rejects a color the browser does not understand even if the regex matches', () => {
    vi.stubGlobal('CSS', { supports: () => false })

    expect(runAppearanceTool('set_background', { type: 'solid', color: 'rgb(.,.,.)' })).toMatch(/^error: color no válido/)
    expect(root.style.getPropertyValue('--app-background')).toBe('')
  })

  it('builds a gradient from two colors', () => {
    expect(runAppearanceTool('set_background', { type: 'gradient', from: '#ff7e5f', to: 'rgb(254, 180, 123)' })).toBe(
      'ok: #ff7e5f → rgb(254, 180, 123)',
    )
    expect(root.style.getPropertyValue('--app-background')).toBe(
      'linear-gradient(135deg, #ff7e5f 0%, rgb(254, 180, 123) 100%)',
    )
  })

  it('rejects a gradient when one color is unsafe', () => {
    const result = runAppearanceTool('set_background', { type: 'gradient', from: '#ff7e5f', to: 'url(x)' })

    expect(result).toMatch(/^error: degradado no válido/)
    expect(root.style.getPropertyValue('--app-background')).toBe('')
  })

  it('default removes the override and goes back to the original background', () => {
    runAppearanceTool('set_background', { type: 'solid', color: '#001f3f' })

    expect(runAppearanceTool('set_background', { type: 'default' })).toBe('ok: default')
    expect(root.style.getPropertyValue('--app-background')).toBe('')
  })
})

describe('set_font and set_font_size', () => {
  it('sets the Bootstrap body font', () => {
    expect(runAppearanceTool('set_font', { font: 'Fira Code' })).toBe('ok: Fira Code')
    expect(root.style.getPropertyValue('--bs-body-font-family')).toBe("'Fira Code', monospace")
  })

  it('sets the base font size', () => {
    expect(runAppearanceTool('set_font_size', { size: 'large' })).toBe('ok: large')
    expect(root.style.fontSize).toBe('18px')
  })

  it('rejects a font that is not offered', () => {
    expect(runAppearanceTool('set_font', { font: 'Comic Sans' })).toBe('error: valor no permitido "Comic Sans"')
  })
})

describe('runAppearanceTool', () => {
  it('returns an error for an unknown tool', () => {
    expect(runAppearanceTool('delete_account', {})).toBe('error: tool desconocida "delete_account"')
  })

  it('returns an error instead of throwing when the args are missing', () => {
    expect(runAppearanceTool('set_theme', undefined)).toMatch(/^error:/)
  })
})
