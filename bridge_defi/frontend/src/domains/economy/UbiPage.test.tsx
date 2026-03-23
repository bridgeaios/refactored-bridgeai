declare const describe: any
declare const expect: any
declare const it: any

import { renderToStaticMarkup } from 'react-dom/server'
import { UbiPage } from './UbiPage'

describe('UbiPage', () => {
  it('renders the UBI heading', () => {
    const markup = renderToStaticMarkup(<UbiPage />)
    expect(markup).toContain('UBI')
  })
})
