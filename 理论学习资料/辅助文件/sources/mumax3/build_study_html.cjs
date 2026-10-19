// Generate the reading view from the canonical Markdown, with offline MathML.
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');

const root = path.resolve(__dirname, '../..');
const source = path.join(root, '..', '2-微磁学四种能量竞争_学习笔记.md');
const output = path.join(root, '..', '2-微磁学四种能量竞争_学习版.html');
const base = path.join(root, 'tmp', 'mumax3', 'study-base.html');
const helper = path.join(os.homedir(), '.codex', 'skills', 'render-html', 'scripts', 'render_html.py');
const katex = require(path.join(root, 'sources', 'mit-ch9', 'katex.min.js'));

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.mkdirSync(path.dirname(base), { recursive: true });
execFileSync('python', [helper, source, '--template', 'academic', '--offline', '--out', base,
  '--eyebrow', '微磁学 · 中文学习笔记',
  '--subtitle', '四种能量如何共同决定磁化方向、磁畴与畴壁'], { cwd: root, stdio: 'inherit' });

const unescape = value => value.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
let html = fs.readFileSync(base, 'utf8');
// The hero already displays the source H1; avoid repeating it in the body.
html = html.replace(/<h1 id="[^"]*">[\s\S]*?<\/h1>/, '');
html = html.replace(/>Contents</gi, '>目录<')
  .replace(/>Source:</g, '>原稿：<').replace(/>Rendered:</g, '>生成时间：<');
let mathCount = 0;
html = html.replace(/\$\$([\s\S]*?)\$\$|\$([^$\n]+?)\$/g, (match, display, inline) => {
  const isDisplay = display !== undefined;
  const expression = unescape(isDisplay ? display : inline).trim();
  const rendered = katex.renderToString(expression, {
    displayMode: isDisplay, output: 'mathml', throwOnError: true, strict: 'error'
  });
  mathCount++;
  return `<span class="${isDisplay ? 'formula-display' : 'formula-inline'}">${rendered}</span>`;
});

const localTime = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hour12: false
}).format(new Date()) + ' UTC+08:00';
html = html.replace(/\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC/g, localTime);
html = html.replace('<!-- offline mode: MathJax + highlight.js skipped; math and code blocks render as plain text -->',
  '<!-- Formulas are compiled to native MathML; no network request is needed. -->');
html = html.replace('</head>', `<style>
body {font-family: "Microsoft YaHei", "PingFang SC", sans-serif; font-size: 16px; line-height: 1.85;}
h1,h2,h3 {font-family: inherit;}
h2 {scroll-margin-top: 24px;}
nav.toc {font-size: 13px; line-height: 1.65;}
nav.toc ol li::before {content: none;}
table {font-size: 14px;}
th,td {line-height: 1.75;}
math {font-family: "Cambria Math", "STIX Two Math", math;}
.formula-display {display: block; overflow-x: auto; padding: 18px 12px; margin: 12px 0;
  background: #f2f5f7; border-radius: 6px; text-align: center;}
.formula-display math {font-size: 1.07em; margin: 0 auto;}
.formula-inline math {font-size: 1em;}
@media(max-width: 700px) {body {font-size: 16px;} table {display: block; overflow-x: auto;}
  nav.toc {max-height: 200px; overflow-y: auto; padding-bottom: 14px;}}
@media print {nav.toc {display: none;} .layout {display: block; padding: 0;}
  .formula-display {break-inside: avoid; background: transparent;} body {font-size: 11pt;}}
</style></head>`);
fs.writeFileSync(output, html, 'utf8');
console.log(JSON.stringify({output, mathCount, bytes: Buffer.byteLength(html)}));
