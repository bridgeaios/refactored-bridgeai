declare const describe: any
declare const expect: any
declare const it: any

import { renderToStaticMarkup } from 'react-dom/server'
import { CfoPage } from './CfoPage'

describe('CfoPage', () => {
  it('renders the CFO dashboard heading', () => {
    const markup = renderToStaticMarkup(<CfoPage />)
    expect(markup).toContain('CFO Dashboard')
  })
})
