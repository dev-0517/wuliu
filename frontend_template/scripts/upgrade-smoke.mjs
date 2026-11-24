import { chromium } from '@playwright/test'
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'

const live = process.env.AI_LIVE === '1'
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()
const errors = []
page.on('pageerror', error => errors.push(error.message))
const account = `upgrade_${Date.now()}`
const headers = {}
const conversations = []
let caseId
await mkdir('test-artifacts', { recursive: true })
console.log('Upgrade test account:', account)
try {
  await page.goto('http://127.0.0.1:5173')
  await page.getByRole('button', { name: '注册账号', exact: true }).click()
  await page.getByLabel('账号', { exact: true }).fill(account)
  await page.getByLabel('昵称', { exact: true }).fill('升级验证用户')
  await page.getByLabel('密码', { exact: true }).fill(`Upgrade-${Date.now()}-test`)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '注册并开始使用' }).click()
  await page.waitForURL('**/cases')
  headers.Authorization = `Bearer ${await page.evaluate(() => sessionStorage.getItem('huanuo_token'))}`
  await page.goto('http://127.0.0.1:5173/assistant')
  await page.getByRole('heading', { name: '想到什么，就聊什么。' }).waitFor()
  await page.screenshot({ path: 'test-artifacts/assistant-v02-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: 'test-artifacts/assistant-v02-mobile.png', fullPage: true })
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.getByRole('button', { name: '开始聊天', exact: true }).click()
  await page.waitForURL(/\/chat\/\d+$/)
  const generalId = Number(page.url().split('/').pop())
  conversations.push(generalId)
  assert.equal(await page.locator('.context-card').count(), 0)
  if (!live) {
    await page.route(`**/api/conversations/${generalId}/messages`, route => route.fulfill({
      json: { question: { id: -10, role: 'user', content: '你好' }, reply: { id: -11, role: 'assistant', content: '你好，我是小诺，可以陪你聊天，也可以帮你整理思路。', sources: [] }, title: '你好' },
    }))
  }
  await page.getByRole('textbox', { name: '咨询问题' }).fill('你好，请用一句简短中文介绍你能帮我做什么。')
  const chatResponse = page.waitForResponse(r => r.url().endsWith('/messages') && r.request().method() === 'POST', { timeout: 220000 })
  await page.getByRole('button', { name: '发送问题', exact: true }).click()
  const chatResult = await chatResponse
  assert.ok(chatResult.ok(), `General chat failed HTTP ${chatResult.status()}: ${await chatResult.text()}`)
  const reply = (await chatResult.json()).reply
  assert.deepEqual(reply.sources, [])
  assert.ok(reply.content.length > 0)
  await page.getByRole('button', { name: '复制回答' }).waitFor({ timeout: 10000 })
  await page.screenshot({ path: 'test-artifacts/general-chat-v02-desktop.png', fullPage: true })
  if (live) {
    await page.reload()
    await page.getByRole('button', { name: '复制回答' }).waitFor()
  }
  await page.goto('http://127.0.0.1:5173/records')
  await page.getByLabel('对话类型', { exact: true }).selectOption('general')
  await page.getByRole('button', { name: '修改会话标题' }).first().click()
  await page.getByLabel('对话标题', { exact: true }).fill('日常聊天 · 升级验证')
  await page.getByRole('button', { name: '保存标题', exact: true }).click()
  await page.getByRole('heading', { name: '日常聊天 · 升级验证' }).waitFor()
  await page.getByRole('textbox', { name: '搜索聊天记录' }).fill('升级验证')
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await page.getByRole('heading', { name: '日常聊天 · 升级验证' }).waitFor()
  await page.setViewportSize({ width: 390, height: 844 })
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await page.screenshot({ path: 'test-artifacts/history-v02-mobile.png', fullPage: true })
  await page.setViewportSize({ width: 1440, height: 1000 })

  const caseResponse = await context.request.post('http://127.0.0.1:8000/api/cases', { headers, data: {
    title: '升级验证 · 虚构工资争议', category: '劳动纠纷',
    description: '【虚构测试数据】用户称2026年9月1日入职甲公司，10月份工资尚未收到。工资金额、约定支付日及公司完整名称尚未提供。', goal: '梳理事实和缺失材料，明确下一步。',
  } })
  assert.ok(caseResponse.ok())
  caseId = (await caseResponse.json()).id
  await context.request.post(`http://127.0.0.1:8000/api/cases/${caseId}/materials`, { headers, data: {
    name: '工资明细', description: '用户尚未提供工资明细，需要补充。', status: '待补充',
  } })
  await page.goto(`http://127.0.0.1:5173/cases/${caseId}`)
  await page.getByRole('button', { name: 'AI 案情梳理', exact: true }).click()
  if (!live) {
    const analysis = {
      summary: '用户陈述10月份工资未收到，实际支付情况有待核实。', facts: [{ statement: '用户称工资未收到', source_ref: `case:${caseId}`, quote: '10月份工资尚未收到', record_type: '用户陈述' }],
      issues: ['工资实际支付情况'], missing_information: ['缺少工资金额和支付日'], timeline: [{ date: '2026年9月1日', event: '用户称入职甲公司', source: `case:${caseId}`, quote: '2026年9月1日入职甲公司' }],
      suggested_materials: ['工资明细，用于核对工资金额'], risks: [{ title: '缺少支付记录', reason: '目前无法核对实际到账', source_refs: [`case:${caseId}`] }], next_steps: [{ priority: '优先', action: '整理工资约定与到账记录', reason: '核对差额' }], follow_up_questions: ['约定的工资是多少？'],
      sources: [{ ref: `case:${caseId}`, label: '案情与诉求', kind: '用户陈述', status: '待核实', text: '【虚构测试数据】用户称2026年9月1日入职甲公司，10月份工资尚未收到。' }], generated_at: new Date().toISOString(), schema_version: 2,
    }
    await page.route(`**/api/cases/${caseId}/analysis`, route => route.fulfill({ json: analysis }))
    // 生成后页面会重新读取详情和历史；只在浏览器中注入展示数据。
    await page.route(`**/api/cases/${caseId}`, async route => {
      if (route.request().method() !== 'GET') return route.continue()
      const response = await route.fetch()
      await route.fulfill({ response, json: { ...await response.json(), analysis } })
    })
    await page.route(`**/api/cases/${caseId}/analysis/history`, route => route.fulfill({ json: [{ id: 1, created_at: new Date().toISOString(), summary: analysis.summary }] }))
    await page.route(`**/api/cases/${caseId}/analysis/history/1`, route => route.fulfill({ json: { id: 1, analysis } }))
  }
  const analysisResponse = page.waitForResponse(r => r.url().endsWith('/analysis') && r.request().method() === 'POST', { timeout: 220000 })
  await page.getByRole('button', { name: '生成案情整理', exact: true }).click()
  const analysisResult = await analysisResponse
  assert.ok(analysisResult.ok(), `Analysis failed HTTP ${analysisResult.status()}: ${await analysisResult.text()}`)
  const analysis = await analysisResult.json()
  assert.equal(analysis.schema_version, 2)
  assert.ok(analysis.sources.length)
  await page.getByRole('heading', { name: '案情摘要', exact: true }).waitFor({ timeout: 10000 })
  await page.getByRole('heading', { name: '接下来可以做什么' }).waitFor()
  await page.locator('.source-list > summary').click()
  await page.locator('.source-record > summary').first().click()
  await page.screenshot({ path: 'test-artifacts/analysis-v02-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
  await page.screenshot({ path: 'test-artifacts/analysis-v02-mobile.png', fullPage: true })
  const versions = page.locator('.analysis-versions select')
  await versions.selectOption({ index: 1 })
  await page.getByText('正在查看生成时的历史快照，当前案情或材料可能已经变化。', { exact: true }).waitFor()
  await page.getByRole('heading', { name: '接下来可以做什么' }).waitFor()
  await versions.selectOption('current')
  if (analysis.follow_up_questions.length) {
    await page.locator('.followup-list button').first().click()
    await page.waitForURL(/\/chat\/\d+\?prompt=/)
    conversations.push(Number(new URL(page.url()).pathname.split('/').pop()))
    await page.locator('.context-card').waitFor()
    assert.ok((await page.getByRole('textbox', { name: '咨询问题' }).inputValue()).includes('我的补充是'))
    if (live) {
      await page.getByRole('textbox', { name: '咨询问题' }).fill('请根据当前案件记录，用两句话说明已有材料和待补充材料，不要把待补充当成已持有。')
      const answerResponse = page.waitForResponse(r => r.url().endsWith('/messages') && r.request().method() === 'POST', { timeout: 220000 })
      await page.getByRole('button', { name: '发送问题', exact: true }).click()
      const answerResult = await answerResponse
      assert.ok(answerResult.ok(), `Case answer failed: ${await answerResult.text()}`)
      assert.ok((await answerResult.json()).reply.sources.length >= 2)
      await page.getByRole('button', { name: '复制回答' }).waitFor()
      await page.locator('.source-list > summary').click()
      await page.screenshot({ path: 'test-artifacts/case-chat-v02-mobile.png', fullPage: true })
    }
  }
  assert.deepEqual(errors, [])
  console.log(`PASS v0.2 ${live ? 'LIVE' : 'UI'}: general chat, title/search/filter, grounded analysis, sources, follow-up, desktop/mobile`)
} finally {
  for (const id of conversations) await context.request.delete(`http://127.0.0.1:8000/api/conversations/${id}`, { headers })
  if (caseId) await context.request.delete(`http://127.0.0.1:8000/api/cases/${caseId}`, { headers })
  if (headers.Authorization) await context.request.post('http://127.0.0.1:8000/api/auth/logout', { headers })
  await browser.close()
}
