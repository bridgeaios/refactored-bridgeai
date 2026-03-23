declare const describe: any
declare const expect: any
declare const it: any

import { renderToStaticMarkup } from 'react-dom/server'
import { LendingPage } from './LendingPage'

describe('LendingPage', () => {
  it('renders the lending heading', () => {
    const markup = renderToStaticMarkup(<LendingPage />)
    expect(markup).toContain('Lending')
  })
})
