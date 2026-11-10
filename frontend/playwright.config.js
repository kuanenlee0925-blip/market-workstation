import { defineConfig } from '@playwright/test'
export default defineConfig({ testDir: './tests', timeout: 60000, use: { headless: true, baseURL: process.env.MARKET_BASE_URL || 'http://127.0.0.1:8000' }, workers: 1 })
