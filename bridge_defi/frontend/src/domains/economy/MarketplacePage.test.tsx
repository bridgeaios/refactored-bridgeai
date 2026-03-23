declare const describe: any
declare const expect: any
declare const it: any

import { renderToStaticMarkup } from 'react-dom/server'
import { MarketplacePage } from './MarketplacePage'

describe('MarketplacePage', () => {
  it('renders the marketplace heading', () => {
    const markup = renderToStaticMarkup(<MarketplacePage />)
    expect(markup).toContain('Marketplace')
  })
})
