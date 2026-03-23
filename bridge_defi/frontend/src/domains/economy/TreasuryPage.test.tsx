declare const describe: any
declare const expect: any
declare const it: any

import { renderToStaticMarkup } from 'react-dom/server'
import { TreasuryPage } from './TreasuryPage'

describe('TreasuryPage', () => {
  it('renders the treasury heading', () => {
    const markup = renderToStaticMarkup(<TreasuryPage />)
    expect(markup).toContain('Treasury')
  })
})
