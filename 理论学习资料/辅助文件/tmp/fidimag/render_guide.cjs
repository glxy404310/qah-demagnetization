const {createRequire} = require('module');
const req = createRequire('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/_entry.cjs');
const {chromium} = req('playwright');
const {pathToFileURL} = require('url');
const path = require('path');
const fs = require('fs');
const root = path.resolve(__dirname, '../..');
const reading = path.resolve(root, '..');
(async()=>{
 const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page = await browser.newPage({viewport:{width:1200,height:1500},deviceScaleFactor:1});
 await page.goto(pathToFileURL(path.join(reading, '3-Fidimag_材料参数与LLG方程学习指南.html')).href);
 await page.emulateMedia({media:'print'});
 await page.evaluate(()=>document.fonts.ready);
 const stats=await page.evaluate(()=>[...document.querySelectorAll('.sheet')].map(s=>{
   const a=s.getBoundingClientRect(),c=s.querySelector('.content').getBoundingClientRect(),f=s.querySelector('.footer').getBoundingClientRect();
   const eq=[...s.querySelectorAll('.equation')].map(e=>({w:e.scrollWidth,available:e.clientWidth}));
   return {page:s.dataset.page,contentHeight:Math.round(c.height),available:Math.round(f.top-c.top-10),bottom:Math.round(c.bottom-f.top),mathOverflow:eq.filter(e=>e.w>e.available+3)};
 }));
 fs.writeFileSync(path.join(root, 'tmp/fidimag/layout.json'),JSON.stringify(stats,null,2));
 console.log(JSON.stringify(stats));
 await page.pdf({path:path.join(reading, '3-Fidimag_材料参数与LLG方程学习指南.pdf'),preferCSSPageSize:true,printBackground:true,displayHeaderFooter:false});
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
