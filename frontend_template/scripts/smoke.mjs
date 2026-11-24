import { chromium } from '@playwright/test'
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'

// 运行前启动前后端。默认不消耗模型额度；AI_LIVE=1 才验证真实调用。
const live = process.env.AI_LIVE === '1'
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await context.newPage()
const errors = []
page.on('pageerror', error => errors.push(error.message))
const account = `smoke_${Date.now()}`
const password = `Smoke-${Date.now()}-test`
await mkdir('test-artifacts', { recursive: true })
let token, caseId
try {
  await page.goto('http://127.0.0.1:5173')
  await page.getByRole('heading', { name: '欢迎回来' }).waitFor()
  await page.screenshot({path:'test-artifacts/login-desktop.png',fullPage:true})
  await page.getByRole('button',{name:'注册账号',exact:true}).click()
  await page.getByLabel('账号',{exact:true}).fill(account)
  await page.getByLabel('昵称',{exact:true}).fill('功能测试用户')
  await page.getByLabel('密码',{exact:true}).fill(password)
  await page.getByRole('checkbox').check()
  await page.getByRole('button',{name:'注册并开始使用'}).click()
  await page.waitForURL('**/cases')
  token = await page.evaluate(() => sessionStorage.getItem('huanuo_token'))
  await page.getByRole('link',{name:'新建案件',exact:true}).first().click()
  await page.getByLabel('案件名称').fill('测试示例 · 工资支付争议')
  await page.getByLabel('事情经过',{exact:false}).fill('【虚构测试案情】用户称2026年9月1日入职甲公司，10月份工资尚未收到，金额尚未提供。目前没有录入证明材料。')
  await page.getByLabel('你希望解决什么问题').fill('整理目前已知事实和待补充材料。')
  await page.getByRole('button',{name:'保存案件'}).click()
  await page.waitForURL(/\/cases\/\d+$/)
  caseId = Number(page.url().split('/').pop())
  await page.getByRole('button',{name:'材料清单'}).click()
  await page.getByRole('button',{name:'记录材料',exact:true}).click()
  await page.getByLabel('材料名称').fill('劳动合同（测试文字记录）')
  await page.getByLabel('说明',{exact:true}).fill('用户表示持有一份合同；本次仅录入文字说明，未上传文件。')
  await page.getByLabel('持有状态').selectOption('已有')
  await page.getByRole('button',{name:'保存材料',exact:true}).click()
  await page.getByRole('heading',{name:'劳动合同（测试文字记录）'}).waitFor()
  await page.getByRole('button',{name:'案情概览',exact:true}).click()
  await page.screenshot({path:'test-artifacts/case-desktop.png',fullPage:true})
  if (live) {
    await page.getByRole('button',{name:'AI 案情梳理',exact:true}).click()
    const analysisResponse = page.waitForResponse(r => r.url().endsWith('/analysis') && r.request().method() === 'POST', {timeout:120000})
    await page.getByRole('button',{name:'生成案情整理',exact:true}).click()
    const result = await analysisResponse
    assert.ok(result.ok(), `AI analysis HTTP ${result.status()}: ${await result.text()}`)
    await page.getByRole('heading',{name:'案情摘要',exact:true}).waitFor({timeout:180000})
    await page.screenshot({path:'test-artifacts/analysis-desktop.png',fullPage:true})
    console.log('LIVE analysis: success; validated JSON result persisted')
  }
  if (!live) {
    // 仅浏览器测试注入固定回复，验证 Markdown 排版与危险 HTML 的处理，不写入数据库。
    await page.route(/\/api\/conversations\/\d+$/, async route => {
      if (route.request().method() !== 'GET') return route.continue()
      const response = await route.fetch()
      const data = await response.json()
      data.messages = [{id:-1,role:'assistant',content:'## 材料记录（渲染测试）\n\n| 名称 | 状态 |\n|---|---|\n| 劳动合同 | 已录入 |\n\n<script>window.__unsafe=true</script>\n\n![图片](https://example.invalid/image.png)\n\n请核实原始材料。'}]
      await route.fulfill({response,json:data})
    })
  }
  await page.getByRole('button',{name:'咨询这个案件',exact:true}).click()
  await page.waitForURL(/\/chat\/\d+$/)
  await page.getByRole('textbox',{name:'咨询问题'}).fill('请查询当前案件，列出已经录入的材料和仍缺少的信息，不要补造事实。')
  if (live) {
    const chatResponse = page.waitForResponse(r => r.url().endsWith('/messages') && r.request().method() === 'POST', {timeout:120000})
    await page.getByRole('button',{name:'发送问题'}).click()
    const result = await chatResponse
    assert.ok(result.ok(), `AI chat HTTP ${result.status()}: ${await result.text()}`)
    await page.locator('.message.assistant .message-bubble').waitFor({timeout:180000})
    const answer = await page.locator('.message.assistant .message-bubble').innerText()
    assert.ok(answer.includes('合同'))
    assert.ok(answer.includes('仅供参考'))
    console.log('LIVE chat: success; tool-grounded response and disclaimer verified')
    await page.reload()
    await page.locator('.message.assistant .message-bubble').waitFor()
    console.log('Chat persisted after reload')
  }
  if (!live) {
    await page.locator('.markdown-content h2').waitFor()
    assert.equal(await page.locator('.markdown-content table').count(),1)
    assert.equal(await page.locator('.markdown-content script, .markdown-content img, .markdown-content a').count(),0)
    assert.equal(await page.evaluate(()=>window.__unsafe),undefined)
    console.log('Markdown headings/tables rendered; raw HTML and external images disabled')
  }
  await page.screenshot({path:'test-artifacts/chat-desktop.png',fullPage:true})
  await page.setViewportSize({width:390,height:844})
  await page.screenshot({path:'test-artifacts/chat-mobile.png',fullPage:true})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth),'mobile chat horizontal overflow')
  await page.goto('http://127.0.0.1:5173/cases')
  await page.getByRole('heading',{name:'测试示例 · 工资支付争议'}).waitFor()
  await page.screenshot({path:'test-artifacts/cases-mobile.png',fullPage:true})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth),'mobile cases horizontal overflow')
  await page.setViewportSize({width:1440,height:1000})
  await page.screenshot({path:'test-artifacts/cases-desktop.png',fullPage:true})
  await page.goto('http://127.0.0.1:5173/records')
  await page.locator('.record-row').waitFor()
  await page.goto('http://127.0.0.1:5173/profile')
  await page.getByLabel('昵称',{exact:true}).fill('修改后的测试昵称')
  await page.getByRole('button',{name:'保存修改'}).click()
  await page.getByRole('status').filter({hasText:'昵称已保存'}).waitFor()
  assert.deepEqual(errors,[])
  console.log('PASS: registration, case create, material create, chat entry, history, profile, desktop/mobile layout; no browser errors')
} finally {
  // 只删除本次新建的测试案件，保留用户数据。
  if(token && caseId) {
    const response = await context.request.delete(`http://127.0.0.1:8000/api/cases/${caseId}`,{headers:{Authorization:`Bearer ${token}`}})
    console.log('Test case cleanup:',response.status())
  }
  if(token) await context.request.post('http://127.0.0.1:8000/api/auth/logout',{headers:{Authorization:`Bearer ${token}`}})
  await browser.close()
}
