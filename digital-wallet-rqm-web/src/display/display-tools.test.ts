import { describe, expect, it } from 'vitest'
import { DISPLAY_TOOLS, isDisplayTool } from './display-tools'

describe('DISPLAY_TOOLS', () => {
  it('declares the balance card so the backend knows the app can draw it', () => {
    expect(DISPLAY_TOOLS.map((tool) => tool.name)).toEqual(['show_account_balance'])
  })
})

describe('isDisplayTool', () => {
  it('tells display tools apart from tools the browser runs', () => {
    expect(isDisplayTool('show_account_balance')).toBe(true)
    expect(isDisplayTool('set_theme')).toBe(false)
  })
})
