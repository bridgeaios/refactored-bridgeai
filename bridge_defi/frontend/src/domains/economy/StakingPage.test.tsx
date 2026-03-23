declare const describe: any
declare const expect: any
declare const it: any

import { renderToStaticMarkup } from 'react-dom/server'
import { StakingPage } from './StakingPage'

describe('StakingPage', () => {
  it('renders the staking heading', () => {
    const markup = renderToStaticMarkup(<StakingPage />)
    expect(markup).toContain('Staking')
  })
})
