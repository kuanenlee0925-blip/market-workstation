import { test, expect } from '@playwright/test'

test('honest unavailable state, symbol selection, and replay command', async ({ page }) => {
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  let commands = []
  await page.routeWebSocket('**/ws/*', ws => {
    ws.send(JSON.stringify({ bars: [], count: 0, mode: 'live', feed: { status: 'unavailable', detail: 'Test fixture: source unavailable' } }))
    ws.onMessage(message => {
      commands.push(JSON.parse(message))
      ws.send(JSON.stringify({ bars: [], count: 0, mode: 'replay', replay_finished: true, feed: { status: 'unavailable' } }))
    })
  })
  await page.goto('http://127.0.0.1:8000')
  await expect(page.getByRole('heading', { name: 'Apple Inc.', exact: true })).toBeVisible()
  await expect(page.getByText('Waiting for market observations')).toBeVisible()
  await expect(page.getByText('Test fixture: source unavailable')).toBeVisible()
  await page.getByRole('button', { name: 'Replay stored' }).click()
  await expect(page.getByText('No recorded observations yet')).toBeVisible()
  expect(commands).toEqual([{ mode: 'replay' }])
  await page.getByLabel('Market symbol').selectOption('BTC-USD')
  await expect(page.getByRole('heading', { name: 'Bitcoin / US Dollar', exact: true })).toBeVisible()
  await page.getByLabel('Search markets').fill('Microsoft')
  await expect(page.locator('.watch-row')).toHaveCount(1)
  await page.locator('.watch-row').click()
  await expect(page.getByRole('heading', { name: 'Microsoft Corporation', exact: true })).toBeVisible()
  await page.getByLabel('Search markets').fill('')
  await page.getByRole('button', { name: 'Fit chart' }).click()
  await expect(page.getByText('Waiting for market observations')).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('button', { name: 'Live feed' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  expect(errors).toEqual([])
})

test('live backend snapshot renders and replay works', async ({ page }) => {
  test.skip(!process.env.LIVE_TEST, 'Opt in with LIVE_TEST=1; requires real Yahoo observations')
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto('http://127.0.0.1:8000')
  await page.getByLabel('Market symbol').selectOption('BTC-USD')
  await expect(page.locator('.quote strong')).not.toHaveText('—', { timeout: 45000 })
  await page.getByRole('button', { name: 'Replay stored' }).click()
  await expect(page.locator('.chart-foot')).toContainText('Recorded replay')
  await page.screenshot({ path: 'test-results/dashboard.png', fullPage: true })
  await page.getByRole('button', { name: 'Live feed' }).click()
  await expect(page.locator('.chart-foot')).toContainText('Live')
  expect(errors).toEqual([])
})
