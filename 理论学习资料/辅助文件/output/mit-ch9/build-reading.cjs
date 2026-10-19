const fs = require('fs');
const path = require('path');
const runtimeModules = 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const { marked } = require(path.join(runtimeModules, 'marked'));
const { chromium } = require(path.join(runtimeModules, 'playwright'));
const root = path.resolve(__dirname, '../..');
const katex = require(path.join(root, 'sources/mit-ch9/katex.min.js'));
const reading = path.resolve(root, '..');
const name = '1-磁化与退磁场_中文译注';
const input = fs.readFileSync(path.join(reading, name + '.md'), 'utf8');

function math(tex, display = false) {
  return katex.renderToString(tex.trim(), {
    output: 'mathml', displayMode: display, throwOnError: true,
    strict: 'error', trust: false,
  });
}

const pages = [...input.matchAll(/<!-- PAGE: (.*?) -->\s*([\s\S]*?)(?=<!-- PAGE:|$)/g)];
const rendered = pages.map((match, i) => {
  const tokens = [];
  const token = (html) => { const key = `MATHPLACEHOLDER${tokens.length}END`; tokens.push(html); return key; };
  let md = match[2].replace(/:::eq ([^\n]+)\n([\s\S]*?)\n:::/g, (_, label, tex) => {
    const boxed = / boxed$/.test(label);
    label = label.replace(/ boxed$/, '');
    return '\n\n' + token(`<div class="equation"><div class="eq-math${boxed ? ' boxed' : ''}">${math(tex, true)}</div><span class="eq-number">(${label})</span></div>`) + '\n\n';
  });
  md = md.replace(/\$([^$\n]+)\$/g, (_, tex) => token(math(tex)));
  let body = marked.parse(md, { gfm: true });
  body = body.replace(/MATHPLACEHOLDER(\d+)END/g, (_, n) => tokens[Number(n)]);
  body = body.replace(/<p>(<div class="equation">[\s\S]*?<\/div><span class="eq-number">[\s\S]*?<\/span><\/div>)<\/p>/g, '$1');
  body = body.replace(/<figure data-image="([^"]+)" data-width="(\d+)">/g, (_, file, width) => {
    const img = fs.readFileSync(path.join(__dirname, 'assets', file));
    return `<figure style="--image-width:${width}px"><img alt="原书插图 ${file.replace('fig-', '').replace('.png', '')}" src="data:image/png;base64,${img.toString('base64')}">`;
  });
  return `<section class="sheet" id="p${i + 1}" aria-label="${match[1]}"><header><span>第 9 章　磁化 · 中文译注</span><span>${match[1]}</span></header><article>${body}</article><footer><span>Haus &amp; Melcher · MIT OCW · CC BY-NC-SA 4.0</span><span>${i + 1} / ${pages.length}</span></footer></section>`;
});

const css = `
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#e9ebed;color:#17191b;font-family:"SimSun","Songti SC",serif;font-size:15px}a{color:#31556a;text-decoration:none;overflow-wrap:anywhere}nav{position:fixed;left:16px;top:20px;width:176px;font:12px/1.7 "Microsoft YaHei",sans-serif}nav b{display:block;margin-bottom:10px;color:#294451}nav a{display:block;padding:5px 8px;border-left:2px solid #c9d2d7}nav a:hover{background:#dde5e9}main{padding:24px 0 24px 145px}.sheet{--body-size:15px;width:210mm;height:297mm;padding:17mm 20mm 17mm;position:relative;margin:0 auto 24px;background:#fff;box-shadow:0 4px 20px #0001;break-after:page}header{position:absolute;top:9mm;left:20mm;right:20mm;display:flex;justify-content:space-between;color:#555d62;font:10px/1.4 "Microsoft YaHei",sans-serif;border-bottom:.5px solid #c2c8cc;padding-bottom:5px}footer{position:absolute;left:20mm;right:20mm;bottom:8mm;display:flex;justify-content:space-between;font:9px/1.4 "Microsoft YaHei",sans-serif;color:#70767b}article{font-size:var(--body-size);line-height:1.65;display:flow-root}h1,h2,h3{font-family:"Microsoft YaHei",sans-serif;line-height:1.4;color:#151a1e;break-after:avoid}h1{font-size:1.4em;letter-spacing:.02em;margin:0 0 4px}h2{font-size:1.08em;margin:17px 0 8px}h3{font-size:1.01em;margin:14px 0 8px}p{margin:7px 0;text-align:justify}article>p,.example>p{text-indent:2em}.english{font:italic .82em/1.5 Georgia,"Times New Roman",serif;color:#616c73;margin:2px 0 17px}.edition{font:9.5px/1.6 "Microsoft YaHei",sans-serif;color:#66727a;margin-bottom:11px}.source-note{font-size:.76em;line-height:1.65;border-left:2px solid #bcc7cf;padding:6px 10px;margin:12px 0 15px;color:#505e67}.example{margin-left:18px}.equation{display:flex;align-items:center;justify-content:center;position:relative;min-height:36px;margin:9px 0;padding:3px 60px 3px 25px;break-inside:avoid;clear:both}.eq-math{max-width:100%;text-align:center;padding:2px 5px}.eq-number{position:absolute;right:0;top:50%;transform:translateY(-50%);font-family:"Times New Roman",serif;font-size:.93em;color:#333;white-space:nowrap}.boxed{border:1px solid #343434;padding:5px 9px}math{font-family:"Cambria Math","STIX Two Math",serif;font-size:1.08em}math[display="block"]{margin:0}.katex{display:inline}aside{background:#f2f5f7;border-left:2px solid #8196a3;padding:9px 12px;margin:13px 0 10px;font-size:.82em;line-height:1.65;text-align:justify}aside.compact{padding:7px 11px}aside b{color:#385266}.footnote{border-top:.5px solid #c9ced2;font-size:.72em;line-height:1.6;margin-top:16px;padding-top:8px;color:#4f565b}figure{margin:12px auto;max-width:100%;text-align:center;break-inside:avoid}figure img{width:var(--image-width);max-width:100%;height:auto;display:block;margin:auto}figcaption{font-size:.76em;line-height:1.5;text-align:justify;max-width:520px;margin:7px auto 0;color:#40464b}.figure-pair{display:flex;align-items:flex-start;justify-content:center;gap:20px}.figure-pair figure{width:49%;margin:10px 0}.figure-pair img{max-height:190px;width:auto;max-width:100%}table{width:100%;border-collapse:collapse;font-size:.8em;line-height:1.6;margin:14px 0}th,td{border-bottom:.5px solid #cbd1d6;padding:7px 8px;text-align:left;vertical-align:top}th{background:#edf1f4;font-family:"Microsoft YaHei",sans-serif;font-weight:500}tr{break-inside:avoid}ol{font-size:.82em;line-height:1.7;padding-left:23px}li{padding-left:2px;margin:7px 0}.license{font-size:.73em;line-height:1.65;border-top:.5px solid #c3ccd2;margin-top:16px;padding-top:12px;color:#5e666d}
@media(max-width:1100px){nav{display:none}main{padding-left:0}}@media print{@page{size:A4;margin:0}html,body{background:white}nav{display:none}main{padding:0}.sheet{margin:0;box-shadow:none;break-after:page}.sheet:last-child{break-after:auto}a{color:inherit;text-decoration:none}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
`;
const nav = `<nav><b>磁化与退磁场<br>9.1 · 9.2 · 9.5 中文译注</b>${pages.map((m,i)=>`<a href="#p${i+1}">${i+1}. ${m[1]}</a>`).join('')}</nav>`;
const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>磁化与退磁场 · MIT 第9章中文译注</title><style>${css}</style></head><body>${nav}<main>${rendered.join('\n')}</main></body></html>`;

(async () => {
  const htmlPath = path.join(reading, name + '.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  const page = await browser.newPage({viewport:{width:1280,height:1100},deviceScaleFactor:1});
  await page.goto('file:///' + htmlPath.replace(/\\/g,'/'));
  await page.evaluate(() => document.fonts.ready);
  const audit = await page.evaluate(() => [...document.querySelectorAll('.sheet')].map((sheet,i)=>{
    const article=sheet.querySelector('article');
    const available = sheet.getBoundingClientRect().height - parseFloat(getComputedStyle(sheet).paddingTop) - parseFloat(getComputedStyle(sheet).paddingBottom);
    let font=15;
    while(article.getBoundingClientRect().height>available && font>12.4){font-=.1;sheet.style.setProperty('--body-size',font.toFixed(1)+'px');}
    return {page:i+1,font:Number(font.toFixed(1)),height:Math.round(article.getBoundingClientRect().height),available:Math.round(available),overflow:article.getBoundingClientRect().height>available+1};
  }));
  // Persist fitted font sizes into the standalone HTML.
  const finalHtml = await page.content();
  fs.writeFileSync(htmlPath, finalHtml, 'utf8');
  fs.writeFileSync(path.join(root,'tmp/pdfs/layout-audit.json'), JSON.stringify(audit,null,2));
  if(audit.some(x=>x.overflow)) throw new Error('Page overflow: '+JSON.stringify(audit.filter(x=>x.overflow)));
  const mathAudit=await page.evaluate(()=>[...document.querySelectorAll('.eq-math')].map(x=>({width:x.scrollWidth,available:x.clientWidth})).filter(x=>x.width>x.available+1));
  if(mathAudit.length)throw new Error('Math overflow: '+JSON.stringify(mathAudit));
  await page.pdf({path:path.join(reading,name+'.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
  await browser.close();
  console.log(JSON.stringify({pages:pages.length,audit,html:htmlPath,pdf:path.join(reading,name+'.pdf')},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
