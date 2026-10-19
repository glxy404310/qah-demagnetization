const { chromium } = require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { pathToFileURL } = require('url');
const path = require('path');
const fs = require('fs');
const root = path.resolve(__dirname, '../..');
const reading = path.resolve(root, '..');
(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1100}, deviceScaleFactor: 1});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const url = pathToFileURL(path.join(reading, '2-微磁学四种能量竞争_学习版.html')).href;
  await page.goto(url, {waitUntil: 'networkidle'});
  await page.screenshot({path:path.join(root, 'tmp/mumax3/study-desktop.png')});
  const stats = await page.evaluate(() => ({
    title: document.title,
    h2: document.querySelectorAll('main h2').length,
    math: document.querySelectorAll('main math').length,
    tables: document.querySelectorAll('main table').length,
    brokenAnchors: [...document.querySelectorAll('a[href^="#"]')].filter(a => !document.getElementById(decodeURIComponent(a.hash.slice(1)))) .map(a=>a.hash),
    horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
    rawMathDelimiters: document.querySelector('main').innerText.includes('$$'),
    externalResources: performance.getEntriesByType('resource').filter(x => x.name.startsWith('http')).map(x=>x.name)
  }));
  await page.locator('h2').filter({hasText:'8. 薄膜重点'}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(root, 'tmp/mumax3/study-competition.png')});
  await page.setViewportSize({width: 430, height: 932});
  await page.evaluate(() => window.scrollTo(0,0));
  await page.screenshot({path:path.join(root, 'tmp/mumax3/study-mobile.png')});
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  console.log(JSON.stringify({...stats, mobileOverflow, errors},null,2));
  fs.writeFileSync(path.join(root, 'tmp/mumax3/browser-check.json'), JSON.stringify({...stats,mobileOverflow,errors},null,2));
  await browser.close();
})();
