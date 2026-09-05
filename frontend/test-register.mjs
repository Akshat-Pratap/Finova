import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on('console', msg => console.log('BROWSER:', msg.text()));
page.on('pageerror', err => console.log('PAGEERROR:', err.message));
await page.goto('http://localhost:5173/register', { waitUntil: 'networkidle' });
await page.screenshot({ path: 'D:\\My Projects\\Finova\\frontend\\pre-register.png', fullPage: true });
console.log('pre-register done');
// fill register form: Full Name, Org Name, Work Email, Password
const inputs = page.locator('input');
console.log('inputs count', await inputs.count());
for (let i=0;i<await inputs.count();i++) {
  const ph = await inputs.nth(i).getAttribute('placeholder');
  console.log(i, ph, await inputs.nth(i).getAttribute('name'), await inputs.nth(i).getAttribute('type'));
}
await page.locator('input[placeholder="Sarah Jenkins"]').fill('Test User');
await page.locator('input[placeholder="Acme FinTech Ltd"]').fill('Test Org ' + Date.now());
const email = `test${Date.now()}@finova.test`;
console.log('using email', email);
await page.locator('input[placeholder="sarah@acme.com"]').fill(email);
await page.locator('input[placeholder="••••••••••••"]').fill('TestPass123!');
await page.screenshot({ path: 'D:\\My Projects\\Finova\\frontend\\register-filled.png', fullPage: true });
await page.locator('button[type="submit"]').click();
await page.waitForTimeout(5000);
console.log('after register url', page.url());
await page.screenshot({ path: 'D:\\My Projects\\Finova\\frontend\\post-register.png', fullPage: true });
console.log('body snippet', (await page.locator('body').innerText()).slice(0, 1500));
await browser.close();
