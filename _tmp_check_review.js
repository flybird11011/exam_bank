const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  await page.goto('http://127.0.0.1:4174/review', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '6. single_choice' }).click();
  await page.getByText('答案：B').waitFor({ state: 'visible' });
  const analysisTextarea = await page.locator('textarea[aria-label="解析"]').inputValue();
  const analysisPreviewText = await page.locator('section.panel').filter({ hasText: '答案与解析' }).first().textContent();
  console.log(JSON.stringify({ analysisTextarea, analysisPreviewText }));
  await browser.close();
})().catch(err => { console.error(err); process.exit(1); });
