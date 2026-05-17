import { chromium } from "playwright";

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  await page.goto('http://127.0.0.1:4174/review', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '7. single_choice' }).click();
  await page.getByText('答案：').waitFor({ state: 'visible' });
  const stem = await page.locator('[aria-label="题干预览"]').textContent();
  const answerPanel = await page.locator('section.panel').filter({ hasText: '答案与解析' }).first().textContent();
  console.log(JSON.stringify({ stem, answerPanel }));
  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
