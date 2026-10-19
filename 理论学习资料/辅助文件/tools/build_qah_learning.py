"""Build a self-contained Chinese reading page from the two QAH notes.

Uses only the Python standard library and the project's existing KaTeX JS.
This renderer supports the Markdown constructs used by these two documents.
"""
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent
DOCS = [
    ('guide', '概念与项目', OUTPUT / '4-QAH基本概念与面外磁化学习指南.md'),
    ('translation', '原文译读', OUTPUT / '4-QAH综述中文译读.md'),
]


def inline(text):
    saved = []

    def keep(value):
        saved.append(value)
        return f'ZZQAHPLACEHOLDER{len(saved) - 1}ZZ'

    text = re.sub(r'`([^`]+)`', lambda m: keep('<code>' + html.escape(m[1]) + '</code>'), text)
    text = re.sub(r'\$([^$\n]+)\$', lambda m: keep(
        '<span class="math" data-tex="' + html.escape(m[1], quote=True) + '">' + html.escape(m[1]) + '</span>'), text)
    text = html.escape(text)

    def link(match):
        label, target = match[1], html.unescape(match[2])
        if target == DOCS[0][2].name:
            target = '#guide'
        elif target == DOCS[1][2].name:
            target = '#translation'
        if not (target.startswith(('https://', '#'))):
            raise ValueError(f'Unexpected link target: {target}')
        return '<a href="' + html.escape(target, quote=True) + '">' + label + '</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    return re.sub(r'ZZQAHPLACEHOLDER(\d+)ZZ', lambda m: saved[int(m[1])], text)


def render(text, prefix):
    lines = text.splitlines()
    parts, toc = [], []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith('```'):
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i])
                i += 1
            parts.append('<pre><code>' + html.escape('\n'.join(block)) + '</code></pre>')
            i += 1
            continue
        if s.startswith('$$'):
            block = [s[2:]]
            while not block[-1].endswith('$$'):
                i += 1
                if i == len(lines):
                    raise ValueError('Unclosed display math')
                block.append(lines[i])
            block[-1] = block[-1][:-2]
            tex = '\n'.join(block).strip()
            parts.append('<div class="math display" data-tex="' + html.escape(tex, quote=True) + '">' + html.escape(tex) + '</div>')
            i += 1
            continue
        heading = re.match(r'^(#{1,3}) (.+)', s)
        if heading:
            level, title = len(heading[1]), heading[2]
            anchor = prefix + '-h' + str(i)
            parts.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
            if level == 2:
                toc.append(f'<a href="#{anchor}">{html.escape(title)}</a>')
            i += 1
            continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [cell.strip() for cell in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', cell) for cell in cells):
                    rows.append(cells)
                i += 1
            width = len(rows[0])
            if not all(len(row) == width for row in rows):
                raise ValueError('Table column mismatch')
            parts.append('<div class="table-wrap"><table><thead><tr>' + ''.join('<th>' + inline(c) + '</th>' for c in rows[0]) + '</tr></thead><tbody>')
            parts.extend('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in row) + '</tr>' for row in rows[1:])
            parts.append('</tbody></table></div>')
            continue
        if s.startswith('>'):
            block = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                block.append(lines[i].strip()[1:].strip())
                i += 1
            parts.append('<aside class="note">' + inline(' '.join(block)) + '</aside>')
            continue
        if re.match(r'^(\d+\. |[-] )', s):
            ordered = bool(re.match(r'^\d+\.', s))
            tag = 'ol' if ordered else 'ul'
            parts.append('<' + tag + '>')
            pattern = r'^\d+\. (.*)' if ordered else r'^- (.*)'
            while i < len(lines):
                item = re.match(pattern, lines[i].strip())
                if not item:
                    break
                parts.append('<li>' + inline(item[1]) + '</li>')
                i += 1
            parts.append('</' + tag + '>')
            continue
        block = [s]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,3} |\||>|\$\$|```|\d+\. |[-] )', lines[i].strip()):
            block.append(lines[i].strip())
            i += 1
        parts.append('<p>' + inline(' '.join(block)) + '</p>')
    return '\n'.join(parts), '\n'.join(toc)


STYLE = '''
:root{color-scheme:light;--ink:#172e36;--muted:#53676d;--accent:#136c69;--line:#dce6e3;--paper:#fffefa;--wash:#f0f5f1}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:100px}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.9 "Microsoft YaHei","PingFang SC",sans-serif}
header{padding:44px max(6vw,24px) 32px;background:#e9f1ea;border-bottom:1px solid var(--line)}header .eyebrow{font:13px/1.4 sans-serif;letter-spacing:.1em;color:var(--accent)}header h1{font-size:clamp(28px,3.3vw,46px);line-height:1.4;margin:12px 0}header p{max-width:850px;margin:10px 0;color:var(--muted)}
.tabs{position:sticky;top:0;z-index:5;background:#fffefaf5;backdrop-filter:blur(8px);border-bottom:1px solid var(--line);display:flex;gap:10px;padding:12px max(6vw,24px)}button{font:inherit;border:1px solid var(--line);background:white;color:var(--ink);padding:7px 20px;border-radius:6px;cursor:pointer}button[aria-selected="true"]{background:var(--accent);color:white;border-color:var(--accent)}.print{margin-left:auto;font-size:14px}
.layout{max-width:1400px;margin:auto;display:grid;grid-template-columns:245px minmax(0,900px);gap:50px;padding:40px 30px 100px}nav{position:sticky;top:93px;align-self:start;max-height:calc(100vh - 115px);overflow:auto;padding-right:12px}nav .nav-title{font-size:13px;font-weight:bold;color:var(--muted);margin-bottom:14px}nav a{display:block;padding:8px 0;font-size:13px;line-height:1.6;border-bottom:1px solid var(--line)}a{color:var(--accent);text-underline-offset:4px;overflow-wrap:anywhere}a:hover{color:#0a4644}article{min-width:0}article h1{font-size:30px;line-height:1.5;margin:0 0 24px}h2{font-size:25px;line-height:1.5;margin:56px 0 22px;padding-top:15px;border-top:2px solid var(--accent)}h3{font-size:20px;margin:30px 0 15px}p{margin:16px 0}strong{font-weight:700;color:#113d42}code{font-family:Consolas,monospace;background:#edf3ef;padding:2px 5px;border-radius:3px;font-size:.9em}pre{overflow:auto;padding:22px;background:#f0f4f0;border:1px solid var(--line);line-height:1.6}pre code{padding:0;background:none}li{margin:10px 0}.note{margin:24px 0;padding:18px 22px;background:#f1f5f0;border-left:4px solid #6d9181;font-size:15px}.table-wrap{overflow-x:auto;margin:25px 0}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.8;min-width:620px}td,th{border:1px solid var(--line);padding:12px 14px;text-align:left;vertical-align:top}th{background:#e9f0ea;font-weight:bold}tr:nth-child(even){background:#f8faf6}.math{font-family:"Cambria Math",serif}.math.display{overflow-x:auto;padding:18px 4px;margin:22px 0}.math.display math{margin:auto;font-size:1.1em}.math-error{color:#a42121;background:#fff0ee}.footer{font-size:13px;color:var(--muted);padding:24px;border-top:1px solid var(--line);text-align:center}[hidden]{display:none!important}
@media(max-width:1000px){.layout{grid-template-columns:1fr;padding:25px 22px;gap:20px}nav{position:static;max-height:210px;border:1px solid var(--line);padding:15px}article h1{font-size:26px}h2{font-size:22px}}@media(max-width:550px){body{font-size:16px}.tabs{padding:10px 14px;gap:7px}button{font-size:14px;padding:7px 12px}.print{display:none}}
@media print{header{padding:0;background:white}.tabs,nav,.footer{display:none}.layout{display:block;padding:0;max-width:none}article[hidden]{display:block!important}h2{break-after:avoid}table{min-width:0;font-size:10pt}.table-wrap{overflow:visible}pre{white-space:pre-wrap;font-size:10pt}body{font-size:11pt}article{break-before:page}a{color:inherit}.math.display{overflow:visible}.note{break-inside:avoid}}
'''


def main():
    docs, navs, buttons = [], [], []
    for index, (key, label, path) in enumerate(DOCS):
        text, toc = render(path.read_text(encoding='utf-8'), key)
        hidden = ' hidden' if index else ''
        docs.append(f'<article id="{key}" role="tabpanel" aria-labelledby="tab-{key}"{hidden}>{text}</article>')
        navs.append(f'<div data-nav="{key}"{hidden}><div class="nav-title">阅读目录 · {label}</div>{toc}</div>')
        buttons.append(f'<button id="tab-{key}" role="tab" aria-controls="{key}" aria-selected="{str(index == 0).lower()}" data-tab="{key}">{label}</button>')
    katex = (ROOT / 'sources/mit-ch9/katex.min.js').read_text(encoding='utf-8').replace('</script', '<\\/script')
    logic = '''
const mathErrors=[];
document.querySelectorAll('[data-tex]').forEach(el=>{try{katex.render(el.dataset.tex,el,{displayMode:el.classList.contains('display'),output:'mathml',throwOnError:true,strict:'error'});}catch(e){el.classList.add('math-error');el.textContent=el.dataset.tex;mathErrors.push(e.message);}});
window.qahMathErrors=mathErrors;
function selectTab(key){document.querySelectorAll('article').forEach(el=>el.hidden=el.id!==key);document.querySelectorAll('[data-nav]').forEach(el=>el.hidden=el.dataset.nav!==key);document.querySelectorAll('[data-tab]').forEach(el=>el.setAttribute('aria-selected',String(el.dataset.tab===key)));}
document.querySelectorAll('[data-tab]').forEach(el=>el.addEventListener('click',()=>{selectTab(el.dataset.tab);location.hash=el.dataset.tab;}));
document.querySelector('.print').addEventListener('click',()=>window.print());
function route(){let id=decodeURIComponent(location.hash.slice(1));if(!id)return;let el=document.getElementById(id);let article=el?.closest('article');if(article){selectTab(article.id);setTimeout(()=>el.scrollIntoView(),0);}}
window.addEventListener('hashchange',route);route();
'''
    result = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QAH：基本概念、面外磁化与退磁场</title><style>' + STYLE + '</style></head><body>'
    result += '<header><div class="eyebrow">QAH · 电磁学课程项目学习资料</div><h1>从量子反常霍尔效应<br>理解面外磁化为什么重要</h1><p>先建立“体内绝缘、边缘导电”的图像，再理解面外交换开隙与薄膜退磁作用的竞争。附原综述中文译读、读图指引和自测。</p><p style="font-size:13px">主文献：He、Wang、Xue · National Science Review 2014 · 整理于 2026-10-19</p></header>'
    result += '<div class="tabs" role="tablist" aria-label="学习材料">' + ''.join(buttons) + '<button class="print">打印两份资料</button></div>'
    result += '<div class="layout"><nav aria-label="章节目录">' + ''.join(navs) + '</nav><main>' + ''.join(docs) + '</main></div>'
    result += '<footer class="footer">非官方中文译读与教学整理 · 公式使用浏览器原生 MathML · 本页文字及公式可离线阅读，外部文献链接需联网</footer>'
    result += '<script>' + katex + '</script><script>' + logic + '</script></body></html>'
    target = OUTPUT / '4-QAH学习资料.html'
    target.write_text(result, encoding='utf-8')
    print(f'Built {target.name}: {len(result.encode("utf-8"))} bytes, {result.count("data-tex=")} equations')


if __name__ == '__main__':
    main()
