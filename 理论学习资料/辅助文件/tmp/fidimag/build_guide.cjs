const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');
const requireBundle = createRequire('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/_entry.cjs');
const { marked } = requireBundle('marked');
const root = path.resolve(__dirname, '../..');
const reading = path.resolve(root, '..');
const katex = require(path.join(root, 'sources/mit-ch9/katex.min.js'));
const out = path.join(root, 'output/fidimag-learning');
let md = fs.readFileSync(path.join(reading, '3-Fidimag_材料参数与LLG方程学习指南.md'), 'utf8');
const license = fs.readFileSync(path.join(root, 'sources/fidimag/LICENSE.txt'), 'utf8');
md = md.replace('{{LICENSE}}', '```text\n' + license.trim() + '\n```');
const blocks = md.split('<!-- PAGE -->');
// Chromium MathML Core ignores most mathvariant values. Use the corresponding
// Unicode mathematical alphabet so vectors and calligraphic energy symbols
// retain their meaning in both offline HTML and the printed PDF.
function retainVariants(markup) {
  const scriptExceptions = {B:'ℬ',E:'ℰ',F:'ℱ',H:'ℋ',I:'ℐ',L:'ℒ',M:'ℳ',R:'ℛ'};
  const greek='αβγδεζηθικλμνξοπρςστυφχψω';
  return markup.replace(/<mi mathvariant="(bold|bold-italic|script)">([^<]+)<\/mi>/g, (_,variant,chars)=>{
    const changed=[...chars].map(c=>{
      const cp=c.codePointAt(0), upper=cp>=65&&cp<=90,lower=cp>=97&&cp<=122;
      if(variant==='script'&&upper) return scriptExceptions[c]||String.fromCodePoint(0x1d49c+cp-65);
      if(variant==='bold'&&(upper||lower)) return String.fromCodePoint((upper?0x1d400:0x1d41a)+cp-(upper?65:97));
      if(variant==='bold-italic'&&(upper||lower)) return String.fromCodePoint((upper?0x1d468:0x1d482)+cp-(upper?65:97));
      if(variant==='bold-italic'&&greek.includes(c)) return String.fromCodePoint(0x1d736+greek.indexOf(c));
      return c;
    }).join('');
    return `<mi mathvariant="normal">${changed}</mi>`;
  });
}
function render(content) {
  const maths = [];
  content = content.replace(/\$\$([\s\S]+?)\$\$|\$([^\n$]+?)\$/g, (_, display, inline) => {
    const markup = katex.renderToString(display || inline, {
      displayMode: !!display, output: 'mathml', throwOnError: true,
      strict: 'error', trust: false
    });
    const stable = retainVariants(markup);
    const index = maths.push(display ? `<div class="equation">${stable}</div>` : stable) - 1;
    return `MATHPLACEHOLDER${index}END`;
  });
  let html = marked.parse(content, {gfm:true});
  html = html.replace(/<p>(MATHPLACEHOLDER\d+END)<\/p>/g, '$1');
  html = html.replace(/MATHPLACEHOLDER(\d+)END/g, (_, n) => maths[+n]);
  html = html.replace(/<img src="辅助文件\/output\/fidimag-learning\/macrospin_results\/llg_trajectory.svg"[^>]*>/, () =>
    `<figure>${fs.readFileSync(path.join(out,'macrospin_results/llg_trajectory.svg'),'utf8')}</figure>`);
  return html;
}
const css = `
*{box-sizing:border-box}html{background:#e9edf0;color:#191919}body{margin:0;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;font-size:10.3pt;line-height:1.62}
.sheet{width:210mm;height:297mm;position:relative;margin:22px auto;background:white;padding:16mm 18mm 17mm;box-shadow:0 3px 18px #0001;break-after:page}
.content{display:flow-root}.sheet:last-child{break-after:auto}h1,h2,h3{color:black;line-height:1.35;break-after:avoid}h1{font-size:23pt;letter-spacing:.3px;margin:0 0 13px}h2{font-size:18pt;margin:0 0 15px}h3{font-size:11.5pt;margin:17px 0 7px;font-weight:700}p{margin:7px 0 9px;text-align:left;overflow-wrap:anywhere}strong{font-weight:700}a{color:#205d79;text-decoration:none;overflow-wrap:anywhere}
table{border-collapse:collapse;table-layout:fixed;width:100%;font-size:9.3pt;line-height:1.55;margin:12px 0 15px;break-inside:avoid}th,td{border:1px solid #d9d9d9;padding:7px 8px;vertical-align:middle;text-align:left;overflow-wrap:anywhere}th{background:#edf1f4;color:black;font-weight:700}tr:nth-child(even) td{background:#fafbfc}table th:first-child,table td:first-child{width:26%}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:8.5pt;line-height:1.47;background:#f4f5f6;padding:12px 14px;border:0;margin:10px 0 12px;tab-size:4;break-inside:avoid}code{font-family:Consolas,"Microsoft YaHei",monospace;font-size:.9em}pre code{font-size:inherit}ol,ul{padding-left:23px;margin:10px 0}li{margin:5px 0}
.equation{text-align:center;margin:13px 0;font-size:11.4pt;line-height:1.5;break-inside:avoid}math{font-family:"Cambria Math","STIX Two Math",math;font-size:1em}math[display="block"]{margin:0}.katex{display:inline}.katex-mathml{display:contents}figure{margin:12px 0 5px;break-inside:avoid}figure svg{display:block;width:100%;height:auto}.footer{position:absolute;left:18mm;right:18mm;bottom:8mm;display:flex;justify-content:space-between;color:#666;font-size:8pt}.sheet[data-page="13"]{font-size:9.5pt;line-height:1.53}.sheet[data-page="13"] p{margin:7px 0 9px}.sheet[data-page="14"] pre{background:white;font-size:9pt;line-height:1.65;padding:10px 0}
@page{size:A4;margin:0}@media print{html{background:white}.sheet{box-shadow:none;margin:0}a{color:#191919}body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
@media screen and (max-width:850px){.sheet{width:100%;height:auto;min-height:297mm;padding:25px 24px 65px;margin:0 0 15px}.footer{left:24px;right:24px}.equation{overflow-x:auto}table{font-size:9pt}}
`;
const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fidimag 材料参数与 LLG 方程学习指南</title><style>${css}</style></head><body>${blocks.map((s,i)=>`<article class="sheet" data-page="${i+1}"><div class="content">${render(s)}</div><footer class="footer"><span>Fidimag 材料参数与 LLG 方程 · 中文学习指南</span><span>${i+1} / ${blocks.length}</span></footer></article>`).join('')}</body></html>`;
fs.writeFileSync(path.join(reading, '3-Fidimag_材料参数与LLG方程学习指南.html'), html);
console.log(JSON.stringify({pages:blocks.length,maths:(html.match(/<math/g)||[]).length,bytes:Buffer.byteLength(html)}));
