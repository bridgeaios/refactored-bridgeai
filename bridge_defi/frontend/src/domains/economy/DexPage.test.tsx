declare const describe: any
declare const expect: any
declare const it: any

import { renderToStaticMarkup } from 'react-dom/server'
import { DexPage } from './DexPage'

describe('DexPage', () => {
  it('renders the DEX heading', () => {
    const markup = renderToStaticMarkup(<DexPage />)
    expect(markup).toContain('DEX')
  })
})
