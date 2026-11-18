import { test, expect } from '@playwright/test'

test('chart assistant controls and captured-result binding with labeled provider fixture', async ({ page }) => {
  test.skip(process.env.SMOKE_TEST !== '1', 'Uses isolated SmokeTest services')
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  await page.goto('/')
  await page.getByRole('button', { name:'CSV sample', exact:true }).click()
  await expect(page.getByLabel('Candle details')).toContainText('104.00')
  let count = 0, conversation
  await page.route('**/api/chat', async route => {
    const request = route.request().postDataJSON(); count++
    expect(request.snapshot.image).toMatch(/^data:image\/png;base64,/)
    expect(request.snapshot.mode).toBe('sample')
    if (count === 1) expect(request.conversation_id).toBeNull()
    else expect(request.conversation_id).toBe(conversation)
    conversation = 'controlled-browser-fixture'
    const assessment = count === 1 ? null : { status:'ok', choice:'WAIT', probability:0.44, symbol:request.snapshot.symbol, mode:request.snapshot.mode, chart_time:request.snapshot.chart_time }
    await route.fulfill({ json: { conversation_id:conversation, status:'ok', reply: count === 1 ? 'Fixture: WAIT means mixed or insufficient evidence.' : 'Fixture: WAIT, probability 0.44.', assessment, tools:[{name:count === 1 ? 'read_decision_rules' : 'assess_chart', result:assessment || { WAIT:'mixed evidence' }}] } })
  })
  await page.getByLabel('Your question').fill('What does WAIT mean in this app?')
  await page.getByRole('button', { name:'Send', exact:true }).click()
  await expect(page.locator('.chat-log')).toContainText('Fixture: WAIT means')
  await expect(page.getByTestId('chart-assessment')).toHaveCount(0)
  await page.getByLabel('Your question').fill('Run the decision on this chart')
  await page.getByRole('button', { name:'Send', exact:true }).click()
  await expect(page.getByTestId('chart-assessment')).toContainText('0.44')
  await page.locator('.chat-turn').last().getByText('Tool calls (1)').click()
  await expect(page.locator('.chat-turn').last()).toContainText('assess_chart')
  await page.screenshot({ path:'../docs/screenshots/agent-fixture-desktop.png', fullPage:true })
  await page.getByRole('button', { name:'New chat', exact:true }).click()
  await expect(page.locator('.chat-turn')).toHaveCount(0)
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path:'../docs/screenshots/agent-fixture-mobile.png', fullPage:true })
  expect(errors).toEqual([])
})
