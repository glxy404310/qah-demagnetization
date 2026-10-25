"""Build the 5-minute progress deck: 汇报PPT/1.pptx.

Numbers on the slides are recomputed from the verified analytic scripts and the
saved JSON summaries, never hand-copied. Run with the bundled Python:

    python 汇报PPT/build_deck.py

Output: 汇报PPT/1.pptx (8 slides, 16:9, speaker notes with timing).
"""
import json
import math
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
DEMAG_DIR = ROOT / "理论学习资料" / "辅助文件" / "output" / "demag-learning"
FIDIMAG_DIR = ROOT / "理论学习资料" / "辅助文件" / "output" / "fidimag-learning"
OUT = Path(__file__).resolve().parent / "1.pptx"

sys.path.insert(0, str(DEMAG_DIR))
from rectangular_demag import center_factors, rectangular_factors  # noqa: E402

# ---------------------------------------------------------------- palette ----
INK = "172E36"
BODY = "3A4A50"
MUTED = "53676D"
ACCENT = "136C69"
ACCENT_LIGHT = "E9F1EA"
LINE = "DCE6E3"
PAPER = "FFFEFA"
AMBER = "B45309"
AMBER_LIGHT = "FBF3E8"
WHITE = "FFFFFF"
FAINT = "F3F6F4"

EA = "Microsoft YaHei"
LATIN = "Segoe UI"

W, H, L, CW = 13.333, 7.5, 0.7, 11.933
TOTAL_SLIDES = 8

# ------------------------------------------------------------------ data ----
MU0 = 4 * math.pi * 1e-7
MS, AEX, KU = 3.0e5, 5.0e-12, 8.0e4  # teaching parameters, see guide 3 section 7

SHAPES = [
    ("200×200×4", (200.0, 200.0, 4.0)),
    ("400×100×4", (400.0, 100.0, 4.0)),
    ("200×200×20", (200.0, 200.0, 20.0)),
]
N = [rectangular_factors(*dims) for _, dims in SHAPES]
N_CENTER_SQ = center_factors(200.0, 200.0, 4.0)
N_SQ = N[0]

REF = json.loads((DEMAG_DIR / "example_200x200x4.json").read_text(encoding="utf-8"))
QUAD = json.loads((DEMAG_DIR / "independent_quadrature_check.json").read_text(encoding="utf-8"))
LLG = json.loads((FIDIMAG_DIR / "macrospin_results" / "verification.json").read_text(encoding="utf-8"))

# The slide numbers must be the verified numbers.
assert abs(N_SQ[0] - REF["N_magnetometric"]["x"]) < 1e-12
assert abs(N_SQ[2] - REF["N_magnetometric"]["z"]) < 1e-12
assert abs(N_CENTER_SQ[2] - REF["N_center_point"]["z"]) < 1e-12
assert abs(N[1][2] - 0.929169087) < 1e-8
assert abs(N[2][2] - 0.805077634) < 1e-8

KD = MU0 * MS ** 2 / 2
DELTA_N = N_SQ[2] - N_SQ[0]
THRESHOLD = KD * DELTA_N
KEFF = KU - THRESHOLD
LEX_NM = math.sqrt(2 * AEX / (MU0 * MS ** 2)) * 1e9

CENTER_ERR = (N_CENTER_SQ[2] / N_SQ[2] - 1) * 100
INFINITE_ERR = (1.0 / N_SQ[2] - 1) * 100

REF_ERR = REF["verification"]["reference_max_abs_error"]
TRACE_ERR = REF["verification"]["sampled_max_trace_error"]
QUAD_ERR = QUAD["results"][-1]["absolute_error"]
LLG_COMP = max(v["max_component_error"] for v in LLG.values())
LLG_NORM = max(v["max_length_error"] for v in LLG.values())
LLG_HALF = max(v["dt_halving_difference"] for v in LLG.values())


def sup(text):
    return (text, {"sup": True})


def sub(text):
    return (text, {"sub": True})


def sci(value, digits=2):
    """Return parts for mantissa×10^exp, e.g. 5.65×10⁴."""
    exp = int(math.floor(math.log10(abs(value))))
    mant = value / 10 ** exp
    return [(f"{mant:.{digits}f}×10", {}), sup(str(exp))]


# Subscripts are written inline as K_eff, N_z, M_s ... and only these short
# tokens are converted, so file names such as thinfilm_fidimag.py stay intact.
SUB_ALLOWED = {"x", "y", "z", "s", "u", "d", "eff", "ex", "0", "1", "2"}
SUB_RE = re.compile(r"([A-Za-zμℓ])_([A-Za-z0-9]{1,3})(?![A-Za-z0-9])")


def split_subscripts(text):
    pieces, pos = [], 0
    for m in SUB_RE.finditer(text):
        if m.group(2) not in SUB_ALLOWED:
            continue
        if m.start() > pos:
            pieces.append((text[pos:m.start()], False))
        pieces.append((m.group(1), False))
        pieces.append((m.group(2), True))
        pos = m.end()
    if pos < len(text):
        pieces.append((text[pos:], False))
    return [(t, s) for t, s in pieces if t]


# --------------------------------------------------------------- drawing ----
def style_run(run, size, color, bold=False, italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.name = LATIN
    f.color.rgb = RGBColor.from_string(color)
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        if latin is not None:
            latin.addnext(ea)
        else:
            rPr.append(ea)
    ea.set("typeface", EA)


def add_runs(p, parts, size, color, bold=False):
    if isinstance(parts, str):
        parts = [(parts, {})]
    for text, opt in parts:
        sub_flag = opt.get("sub")
        sup_flag = opt.get("sup")
        if sub_flag or sup_flag:
            chunks = [(text, bool(sub_flag), bool(sup_flag))]
        else:
            chunks = [(piece, is_sub, False) for piece, is_sub in split_subscripts(text)]
        for chunk, is_sub, is_sup in chunks:
            r = p.add_run()
            r.text = chunk
            sz = opt.get("size", size) * (0.72 if (is_sub or is_sup) else 1.0)
            style_run(r, sz, opt.get("color", color), opt.get("bold", bold))
            if is_sub:
                r._r.get_or_add_rPr().set("baseline", "-25000")
            elif is_sup:
                r._r.get_or_add_rPr().set("baseline", "30000")
            if "spc" in opt:
                r._r.get_or_add_rPr().set("spc", str(int(opt["spc"] * 100)))


def textbox(slide, x, y, w, h, lines, size=14, color=BODY, bold=False,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.15,
            space_after=0, margins=(0, 0, 0, 0)):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left, tf.margin_right, tf.margin_top, tf.margin_bottom = (
        Inches(margins[0]), Inches(margins[1]), Inches(margins[2]), Inches(margins[3]))
    tf.vertical_anchor = anchor
    if isinstance(lines, list) and lines and isinstance(lines[0], tuple):
        lines = [lines]
    for i, spec in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_before = Pt(0)
        p.space_after = Pt(space_after)
        add_runs(p, spec, size, color, bold)
    return box


def strip_theme_style(shp):
    """Remove <p:style> so LibreOffice/PowerPoint do not add theme shadows."""
    el = shp._element
    style = el.find(qn("p:style"))
    if style is not None:
        el.remove(style)


def card(slide, x, y, w, h, fill=WHITE, line=LINE, width=1.0, dash=None,
         radius=0.06):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = radius
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = RGBColor.from_string(line)
        shp.line.width = Pt(width)
        if dash is not None:
            shp.line.dash_style = dash
    shp.shadow.inherit = False
    strip_theme_style(shp)
    return shp


def rect(slide, x, y, w, h, fill, line=None, width=1.0):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = RGBColor.from_string(line)
        shp.line.width = Pt(width)
    shp.shadow.inherit = False
    strip_theme_style(shp)
    return shp


def arrow(slide, x, y, w, h, fill, orient="right"):
    kind = {"right": MSO_SHAPE.RIGHT_ARROW, "up": MSO_SHAPE.UP_ARROW,
            "down": MSO_SHAPE.DOWN_ARROW}[orient]
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    shp.line.fill.background()
    shp.shadow.inherit = False
    strip_theme_style(shp)
    return shp


def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(PAPER)
    return slide


def kicker(slide, number, label):
    textbox(slide, L, 0.5, 8.0, 0.3,
            [[(number, {"color": ACCENT, "bold": True, "spc": 1.5}),
              ("   ", {}),
              (label, {"color": ACCENT, "spc": 1.5})]],
            size=11)


def title(slide, text, size=28):
    textbox(slide, L, 0.88, CW, 0.66, [[(text, {})]], size=size, color=INK,
            bold=True, line_spacing=1.0, anchor=MSO_ANCHOR.MIDDLE)


def rule(slide):
    rect(slide, L, 1.63, 1.15, 0.035, ACCENT)


def footer(slide, page, source=None):
    if source:
        textbox(slide, L, 7.02, 9.7, 0.26, [[(source, {})]], size=8.5, color=MUTED)
    textbox(slide, 11.2, 7.02, 1.43, 0.26, [[(f"{page} / {TOTAL_SLIDES}", {})]],
            size=9, color=MUTED, align=PP_ALIGN.RIGHT)


def note(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def set_cell(cell, parts, size, color, bold=False, align=PP_ALIGN.CENTER):
    cell.margin_left = Inches(0.08)
    cell.margin_right = Inches(0.08)
    cell.margin_top = Inches(0.02)
    cell.margin_bottom = Inches(0.02)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = cell.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = align
    add_runs(p, parts, size, color, bold)


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "基于微磁学模拟探讨量子反常霍尔效应的退磁场效应"
    prs.core_properties.subject = "理论学习阶段汇报（5 分钟）"
    prs.core_properties.author = "孙煜凡、韦中天"

    # ------------------------------------------------------------- slide 1 --
    s = new_slide(prs)
    rect(s, L, 1.28, 0.055, 3.7, ACCENT)
    textbox(s, 0.95, 1.22, 7.4, 0.3,
            [[("电磁学课程项目 · 阶段汇报", {"spc": 2.0})]], size=11.5, color=ACCENT)
    textbox(s, 0.95, 1.62, 7.6, 2.05,
            [[("基于微磁学模拟探讨", {})], [("量子反常霍尔效应的退磁场效应", {})]],
            size=35, color=INK, bold=True, line_spacing=1.12)
    textbox(s, 0.95, 3.82, 7.4, 0.42,
            [[("理论学习完成情况与下一步计划", {})]], size=18, color=BODY)
    textbox(s, 0.95, 4.38, 7.4, 0.34,
            [[("孙煜凡　韦中天", {})]], size=14.5, color=INK, bold=True)
    textbox(s, 0.95, 4.76, 7.4, 0.28,
            [[("2026 年 10 月 · 理论学习阶段", {})]], size=11, color=MUTED)

    # schematic: film + out-of-plane M + opposing demag field
    card(s, 8.55, 1.55, 4.15, 3.15, fill=ACCENT_LIGHT, line=None)
    rect(s, 9.0, 3.52, 3.25, 0.16, INK)
    arrow(s, 10.42, 2.42, 0.26, 0.95, ACCENT, "up")
    textbox(s, 10.82, 2.62, 0.9, 0.35, [[("M", {})]], size=15, color=ACCENT, bold=True)
    arrow(s, 10.42, 3.85, 0.26, 0.72, AMBER, "down")
    textbox(s, 10.82, 3.98, 1.0, 0.35, [[("H", {}), sub("d")]], size=14, color=AMBER, bold=True)
    textbox(s, 8.55, 4.8, 4.15, 0.3, [[("面外磁化与退磁场方向相反", {})]],
            size=9.5, color=MUTED, align=PP_ALIGN.CENTER)

    chips = [("5", "份专题资料"), ("2", "项数值校验通过"), ("3", "种几何退磁因子已算")]
    for i, (num, label) in enumerate(chips):
        x = 0.85 + i * 3.95
        card(s, x, 5.62, 3.75, 0.9)
        textbox(s, x + 0.26, 5.66, 3.2, 0.82,
                [[(num, {"size": 24, "color": ACCENT, "bold": True}),
                  ("    ", {}),
                  (label, {"size": 12, "color": BODY})]],
                size=12, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 1)
    note(s, "各位老师好。我们汇报这个电磁学课程项目的进展。题目是《基于微磁学模拟探讨量子反常霍尔效应的退磁场效应》。"
            "目前理论学习已经完成，模拟即将启动，今天主要讲已经做完的准备和下一步安排。")

    # ------------------------------------------------------------- slide 2 --
    s = new_slide(prs)
    kicker(s, "01", "研究问题")
    title(s, "形状改变退磁场，退磁场决定面外磁化能不能稳住")
    rule(s)

    chain = [
        ("01", "形状与厚度", "正方形 · 圆形 · 长方形"),
        ("02", "退磁场与退磁能", [("H", {}), sub("d"), (" 与 E", {}), sub("d"), (" 随几何改变", {})]),
        ("03", "与交换、各向异性竞争", "总能量决定平衡态"),
        ("04", "面外磁化与磁畴", "剩磁、边缘倾斜、翻转"),
    ]
    bw, gap, by, bh = 2.21, 0.22, 2.1, 2.0
    for i, (num, head, body) in enumerate(chain):
        x = L + i * (bw + gap)
        card(s, x, by, bw, bh, fill=WHITE)
        textbox(s, x + 0.2, by + 0.18, bw - 0.4, 0.25, [[(num, {"spc": 1.5})]],
                size=10, color=ACCENT, bold=True)
        textbox(s, x + 0.2, by + 0.52, bw - 0.4, 0.62, [[(head, {})]],
                size=14.5, color=INK, bold=True, line_spacing=1.1)
        textbox(s, x + 0.2, by + 1.2, bw - 0.4, 0.62, [body], size=10.5, color=MUTED,
                line_spacing=1.15)
        if i < len(chain) - 1:
            arrow(s, x + bw + 0.035, by + 0.84, 0.16, 0.3, "9FB6BA", "right")

    x5 = L + 4 * (bw + gap)
    card(s, x5, by, bw, bh, fill=ACCENT_LIGHT, line=ACCENT, width=1.25,
         dash=MSO_LINE_DASH_STYLE.DASH)
    textbox(s, x5 + 0.2, by + 0.18, bw - 0.4, 0.25, [[("05", {"spc": 1.5})]],
            size=10, color=ACCENT, bold=True)
    textbox(s, x5 + 0.2, by + 0.52, bw - 0.4, 0.62, [[("QAH 的磁性条件", {})]],
            size=14.5, color=ACCENT, bold=True, line_spacing=1.1)
    textbox(s, x5 + 0.2, by + 1.2, bw - 0.4, 0.62, [[("只走到这里为止", {})]],
            size=10.5, color=ACCENT, line_spacing=1.15)

    card(s, L, 4.78, CW, 1.5, fill=WHITE)
    rect(s, L, 4.78, 0.055, 1.5, ACCENT)
    textbox(s, L + 0.28, 4.94, CW - 0.5, 0.3, [[("本项目的解释边界", {})]],
            size=11, color=ACCENT, bold=True, margins=(0, 0, 0, 0))
    textbox(s, L + 0.28, 5.22, CW - 0.55, 0.9,
            [[("微磁学能回答磁化与磁畴是否稳定，不能计算陈数、能隙或霍尔电导。", {})],
             [("因此结论只表述为“为 QAH 提供更有利的磁性条件”，不涉及输运证据。",
               {"bold": True})]],
            size=12.5, color=BODY, line_spacing=1.35)
    footer(s, 2, "研究范围见 README.md 与 4-QAH基本概念与面外磁化学习指南.md")
    note(s, "项目要回答的是：改变薄膜形状和厚度，退磁场怎么变；它和交换、各向异性的竞争，"
            "能不能让磁化更稳地指向面外。注意，微磁学只说明磁性条件，不算霍尔电导，结论会严格限定在这里。")

    # ------------------------------------------------------------- slide 3 --
    s = new_slide(prs)
    kicker(s, "02", "进度")
    title(s, "理论阶段完成，模拟阶段待启动")
    rule(s)

    stages = [("理论学习", "已完成"), ("基准模拟", "当前位置"), ("形状比较", "待启动"),
              ("数据分析", "待启动"), ("总结优化", "待启动")]
    tw, tgap, ty, th = 2.25, 0.17, 2.15, 1.5
    for i, (name, state) in enumerate(stages):
        x = L + i * (tw + tgap)
        if i == 0:
            card(s, x, ty, tw, th, fill=ACCENT, line=None)
            textbox(s, x + 0.2, ty + 0.22, tw - 0.4, 0.4, [[(name, {})]], size=15,
                    color=WHITE, bold=True)
            textbox(s, x + 0.2, ty + 0.82, tw - 0.4, 0.3, [[("✓ 已完成", {})]], size=11,
                    color=WHITE)
        elif i == 1:
            card(s, x, ty, tw, th, fill=WHITE, line=ACCENT, width=2.0)
            textbox(s, x + 0.2, ty + 0.22, tw - 0.4, 0.4, [[(name, {})]], size=15,
                    color=ACCENT, bold=True)
            textbox(s, x + 0.2, ty + 0.82, tw - 0.4, 0.3, [[(state, {})]], size=11,
                    color=ACCENT)
        else:
            card(s, x, ty, tw, th, fill=FAINT)
            textbox(s, x + 0.2, ty + 0.22, tw - 0.4, 0.4, [[(name, {})]], size=15,
                    color=MUTED, bold=True)
            textbox(s, x + 0.2, ty + 0.82, tw - 0.4, 0.3, [[(state, {})]], size=11,
                    color=MUTED)

    card(s, L, 4.55, CW, 1.5, fill=WHITE)
    rect(s, L, 4.55, 0.055, 1.5, ACCENT)
    textbox(s, L + 0.28, 4.71, CW - 0.5, 0.32, [[("现在的位置", {})]], size=11,
            color=ACCENT, bold=True)
    textbox(s, L + 0.28, 5.11, CW - 0.6, 0.9,
            [[("已就绪：", {"bold": True, "color": INK}),
              ("5 份专题资料、2 项数值校验、可复现的解析脚本。", {})],
             [("尚未具备：", {"bold": True, "color": AMBER}),
              ("本机没有 MuMax3 / Fidimag / OOMMF，薄膜模型一次都还没有跑过。", {})]],
            size=13, color=BODY, line_spacing=1.55)
    footer(s, 3, "阶段划分见 README.md 第 8 节；求解器与 GPU 检查于 2026-10-25")
    note(s, "计划分五个阶段。理论学习和资料准备已完成；基准模拟是下一步；形状比较、数据分析、总结还没开始。"
            "资料、解析校验和脚本骨架都就绪，但这台电脑还没有任何微磁求解器，薄膜模型一次都没跑过。")

    # ------------------------------------------------------------- slide 4 --
    s = new_slide(prs)
    kicker(s, "03", "理论学习")
    title(s, "五份专题，覆盖“电磁学 → 微磁学 → QAH”")
    rule(s)

    topics = [
        ("01", "磁化与退磁场",
         "MIT 第 9 章 9.1 / 9.2 / 9.5 全文中译注；M、H、B、边界条件与等效磁荷。",
         "能解释 M、H、B 与边界条件"),
        ("02", "四种能量竞争",
         "交换 · 各向异性 · 退磁 · 塞曼；畴壁宽度 Δ=√(A/K)、有效各向异性判据与自测题。",
         "能判断面外方向是否有利"),
        ("03", "LLG 与材料参数",
         "两套单位制必须成对使用；LLG 推导、弛豫设置，附 8 条原页勘误。",
         "能读懂并设置一次弛豫"),
        ("04", "QAH 与面外磁化",
         "面外磁化打开质量隙，面内只移动狄拉克点；明确“不能证明 QAH”的边界。",
         "能说清结论的适用边界"),
        ("05", "退磁因子与校验",
         "椭球与长方体；体积平均、中心点两种定义；可运行的解析计算脚本。",
         "能算 N 并做数值校验"),
        ("06", "资料形态",
         "三种格式成稿 · 自测题 · 来源清单 · HTML 渲染审校。",
         "三格式可读、来源可查"),
    ]
    cw, cgap, ch = 3.83, 0.22, 2.02
    for i, (num, head, body, outcome) in enumerate(topics):
        row, col = divmod(i, 3)
        x = L + col * (cw + cgap)
        y = 2.12 + row * (ch + 0.2)
        if num == "06":
            card(s, x, y, cw, ch, fill=ACCENT_LIGHT, line=None)
        else:
            card(s, x, y, cw, ch, fill=WHITE)
        color = ACCENT if num == "06" else MUTED
        textbox(s, x + 0.22, y + 0.14, cw - 0.44, 0.24, [[(num, {"spc": 1.5})]],
                size=10, color=ACCENT, bold=True)
        textbox(s, x + 0.22, y + 0.44, cw - 0.44, 0.34, [[(head, {})]], size=15,
                color=ACCENT if num == "06" else INK, bold=True)
        textbox(s, x + 0.22, y + 0.86, cw - 0.44, 0.72, [[(body, {})]], size=11,
                color=color, line_spacing=1.25)
        textbox(s, x + 0.22, y + 1.58, cw - 0.44, 0.3,
                [[("→ ", {"color": ACCENT}), (outcome, {})]], size=9,
                color=ACCENT if num == "06" else MUTED)
    footer(s, 4, "详细内容见 理论学习资料/ 下五份专题文档")
    note(s, "理论部分拆成五个专题：电磁学基础、四种能量竞争、LLG 与参数、QAH 背景、退磁因子与校验。"
            "每份都有 PDF、HTML 或 Markdown，附自测题，来源可查。")

    # ------------------------------------------------------------- slide 5 --
    s = new_slide(prs)
    kicker(s, "04", "结论一 · 能量竞争")
    title(s, "面外是否有利，看 K_eff 的符号")
    rule(s)

    rows = [
        ("交换能", "让磁化在空间上平滑，不选择绝对方向"),
        ("各向异性能", "K_u > 0 时偏好 ±z，即面外"),
        ("退磁能", "偏好面内或分畴；代价由 N 决定"),
        ("外场能", "偏好沿外场，区分 +z 与 −z"),
    ]
    for i, (name, desc) in enumerate(rows):
        y = 2.05 + i * 1.02
        rect(s, L, y + 0.06, 0.04, 0.72, ACCENT if i != 2 else AMBER)
        textbox(s, L + 0.2, y, 5.1, 0.34, [[(name, {})]], size=14.5, color=INK, bold=True)
        textbox(s, L + 0.2, y + 0.36, 5.3, 0.45, [[(desc, {})]], size=11, color=MUTED,
                line_spacing=1.15)

    card(s, 6.45, 2.05, 6.15, 1.3, fill=ACCENT_LIGHT, line=None)
    textbox(s, 6.7, 2.14, 5.7, 0.26, [[("均匀态判据", {"spc": 1.5})]], size=9.5,
            color=ACCENT, bold=True)
    textbox(s, 6.7, 2.44, 5.7, 0.6,
            [[("K", {}), sub("eff"), (" = K", {}), sub("u"), (" − (μ", {}), sub("0"),
              ("M", {}), sub("s"), ("²/2)(N", {}), sub("z"), (" − N", {}), sub("x"), (")", {})]],
            size=20, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)

    card(s, 6.45, 3.55, 6.15, 2.3, fill=WHITE)
    textbox(s, 6.7, 3.68, 5.7, 0.26, [[("代入教学参数（假设值）", {"spc": 1.5})]],
            size=9.5, color=MUTED, bold=True)
    lines = [
        [("M", {}), sub("s"), (" = 3×10", {}), sup("5"), (" A/m   A = 5 pJ/m   K", {}),
         sub("u"), (" = 8×10", {}), sup("4"), (" J/m³", {})],
        [("μ", {}), sub("0"), ("M", {}), sub("s"), ("²/2 = ", {}), *sci(KD),
         (" J/m³，N", {}), sub("z"), (" − N", {}), sub("x"), (" = ", {}),
         (f"{DELTA_N:.3f}", {})],
        [("阈值 ", {}), *sci(THRESHOLD),
         (" < K", {}), sub("u"), ("  ⇒  K", {}), sub("eff"), (" = ", {}),
         *sci(KEFF), (" J/m³ > 0", {"color": ACCENT})],
        [("ℓ", {}), sub("ex"), (" = ", {}), (f"{LEX_NM:.1f}", {}),
         (" nm  ⇒ 网格 2 nm 起步，再以 1 nm 复算", {})],
    ]
    textbox(s, 6.7, 4.02, 5.65, 1.95, lines, size=11.5, color=BODY, line_spacing=1.5,
            space_after=4)

    textbox(s, L, 6.05, CW, 0.5,
            [[("注：无限薄膜近似给出 K", {}), sub("eff"), (" ≈ 2.35×10", {}), sup("4"),
              (" J/m³；本页用 200×200×4 的实际 N", {}), sub("z"), (" − N", {}), sub("x"),
              ("。判据只比较均匀态，多畴与边缘成核仍需模拟。", {})]],
            size=9, color=MUTED, line_spacing=1.2)
    footer(s, 5, "推导见 2-微磁学四种能量竞争_学习笔记.md §8；参数见 3-Fidimag…md §7")
    note(s, "第一个结论：均匀态下面外是否有利，看 K_eff 的符号。用 200×200×4 的教学参数，"
            "阈值约 5.2 乘 10 的 4 次方，小于 K_u 的 8 乘 10 的 4 次方，所以 K_eff 约 2.8 乘 10 的 4 次方，"
            "是正的。但这只比较均匀态，大样品仍可能分畴。")

    # ------------------------------------------------------------- slide 6 --
    s = new_slide(prs)
    kicker(s, "05", "结论二 · 形状")
    title(s, "平面形状改的是面内各向异性，厚度才主导 N_z")
    rule(s)

    tbl_w = 6.9
    shape = s.shapes.add_table(4, 4, Inches(L), Inches(2.08), Inches(tbl_w), Inches(1.8))
    tbl = shape.table
    tblPr = tbl._tbl.tblPr
    for el in tblPr.findall(qn("a:tableStyleId")):
        tblPr.remove(el)
    for idx, width in enumerate((2.4, 1.5, 1.5, 1.5)):
        tbl.columns[idx].width = Inches(width)
    for r in range(4):
        tbl.rows[r].height = Inches(0.45)
    heads = [[("全尺寸 (nm)", {})], [("N", {}), sub("x")],
             [("N", {}), sub("y")], [("N", {}), sub("z")]]
    for c, parts in enumerate(heads):
        cell = tbl.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(ACCENT)
        set_cell(cell, parts, 11, WHITE, bold=True,
                 align=PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER)
    for r, (label, _) in enumerate(SHAPES, start=1):
        vals = (N[r - 1][0], N[r - 1][1], N[r - 1][2])
        for c in range(4):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor.from_string(WHITE if r % 2 else FAINT)
            if c == 0:
                set_cell(cell, [(label, {})], 11.5, INK, align=PP_ALIGN.LEFT)
            else:
                set_cell(cell, [(f"{vals[c - 1]:.6f}", {})], 11.5, BODY)

    textbox(s, L, 3.98, tbl_w, 0.28,
            [[("200×200×4：退磁代价几乎全部在厚度方向", {})]], size=10, color=MUTED)
    bar_y, bar_h = 4.3, 0.42
    x = L
    for val, color in zip(N_SQ, ("BFD6D1", "9FC3BD", ACCENT)):
        w = tbl_w * val
        rect(s, x, bar_y, w, bar_h, color)
        x += w
    textbox(s, L + tbl_w - 1.55, bar_y + 0.05, 1.4, 0.32,
            [[("N", {}), sub("z"), (" 94%", {})]], size=10, color=WHITE, bold=True,
            anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
    textbox(s, L, 4.84, tbl_w, 0.3,
            [[("面内 N", {}), sub("x"), ("、N", {}), sub("y"), (" 各约 3%，合计约 5.9%", {})]],
            size=9.5, color=MUTED)
    textbox(s, L, 5.35, tbl_w, 0.85,
            [[("想稳定面外：", {"bold": True, "color": ACCENT}),
              ("厚度是 N", {}), sub("z"), (" 的主控参数；平面轮廓主要改变面内各向异性。", {})]],
            size=11, color=BODY, line_spacing=1.35)

    insights = [
        ("0.941 → 0.929",
         "同面积同厚度，方形改长条：N_z 几乎不变，变的是面内 N_x 0.030→0.014、N_y 0.030→0.057。"),
        ("0.941 → 0.805",
         "厚度 4 → 20 nm：N_z 明显下降，厚度才是 N_z 的主控参数。"),
        (f"{CENTER_ERR:.2f}% / {INFINITE_ERR:.2f}%",
         "中心点 N_z 比体积平均高 4.37%；用无限薄膜 N_z=1 会高估 6.29%。"),
    ]
    for i, (big, desc) in enumerate(insights):
        y = 2.08 + i * 1.4
        textbox(s, 8.0, y, 4.63, 0.42, [[(big, {})]], size=19, color=ACCENT, bold=True)
        textbox(s, 8.0, y + 0.44, 4.63, 0.85, [[(desc, {})]], size=10.5, color=BODY,
                line_spacing=1.3)
        if i < 2:
            rect(s, 8.0, y + 1.26, 4.63, 0.012, LINE)
    footer(s, 6, "固定均匀磁化下的解析值（Newell/Aharoni），不是微磁模拟结果")
    note(s, "第二个结论是形状。同面积同厚度把方形改成长条，N_z 几乎不动，变的是面内 N_x、N_y；"
            "真正拉低 N_z 的是厚度。还有两个坑：中心点不等于体积平均，差 4.4%；无限薄膜 N_z=1 会高估 6.3%。")

    # ------------------------------------------------------------- slide 7 --
    s = new_slide(prs)
    kicker(s, "06", "可信度")
    title(s, "能离线验证的，已经验完")
    rule(s)

    checks = [
        ("矩形退磁因子（解析）",
         [[("对 OOMMF 基准：", {}), *sci(REF_ERR), ("", {})],
          [("迹误差：", {}), *sci(TRACE_ERR)],
          [("独立积分交叉验证：", {}), *sci(QUAD_ERR)]]),
        ("单磁矩 LLG（RK4）",
         [[("与解析解：", {}), *sci(LLG_COMP)],
          [("模长误差：", {}), *sci(LLG_NORM)],
          [("步长减半差：", {}), *sci(LLG_HALF)]]),
    ]
    for i, (head, lines) in enumerate(checks):
        x = L + i * 6.08
        card(s, x, 2.1, 5.85, 2.35, fill=WHITE)
        rect(s, x, 2.1, 0.055, 2.35, ACCENT)
        textbox(s, x + 0.26, 2.24, 3.3, 0.28, [[("已通过", {"spc": 1.5})]], size=10,
                color=ACCENT, bold=True)
        textbox(s, x + 0.26, 2.56, 5.3, 0.34, [[(head, {})]], size=14.5, color=INK, bold=True)
        textbox(s, x + 0.26, 3.02, 5.3, 1.25, lines, size=11.5, color=BODY, line_spacing=1.5)
        textbox(s, x + 0.26, 4.0, 5.3, 0.3,
                [[(("实现：标准库 · 双精度 · 不强制归一化" if i == 0
                    else "验证：解析解 + 步长减半 + 模长检查"), {})]],
                size=8.5, color=MUTED)

    card(s, L, 4.72, CW, 1.25, fill=AMBER_LIGHT, line=None)
    rect(s, L, 4.72, 0.055, 1.25, AMBER)
    textbox(s, L + 0.28, 4.86, 1.6, 0.26, [[("未执行", {"spc": 1.5})]], size=10,
            color=AMBER, bold=True)
    textbox(s, L + 1.55, 4.84, 9.9, 0.3,
            [[("薄膜脚本 thinfilm_fidimag.py", {})]], size=13.5, color=INK, bold=True)
    textbox(s, L + 0.28, 5.20, CW - 0.55, 0.6,
            [[("接口与语法已核对，但本机没有 Fidimag，尚未运行：目前没有任何薄膜模拟结果，",
               {}),
              ("这一步的结论还不能写。", {"bold": True, "color": AMBER})]],
            size=11.5, color=BODY, line_spacing=1.2)

    textbox(s, L, 6.3, CW, 0.4,
            [[("解析校验通过 ≠ 求解器验证通过。下一步第一件事，是在求解器里复现同一组 N。", {})]],
            size=12, color=ACCENT, bold=True)
    footer(s, 7, "结果来自 rectangular_demag.py 与 macrospin_results/verification.json")
    note(s, "能离线验证的都验了：解析退磁因子对 OOMMF 基准到 10 的负 15 次方量级，单磁矩 LLG 到 10 的负 12 次方。"
            "但薄膜脚本因为本机没有 Fidimag 还没跑，目前没有任何薄膜结果，这点我不会含糊。")

    # ------------------------------------------------------------- slide 8 --
    s = new_slide(prs)
    kicker(s, "07", "下一步")
    title(s, "四条动作，把模型跑起来")
    rule(s)

    steps = [
        ("01", "定软件路线",
         "OOMMF / WSL+Fidimag / MuMax3：先验证 GPU 与 CUDA 兼容性；本机 RTX 5060 可能不兼容旧版。"),
        ("02", "锁定参数表", "饱和磁化强度、交换刚度、各向异性、阻尼 α：一次定死并注明来源"),
        ("03", "均匀磁化静态校验",
         [("三个方向分别测 N，目标 |ΔN| < 10", {}), ("−4", {"sup": True}),
          ("，场法与能量法互校", {})]),
        ("04", "形状 → 磁畴 → 磁滞 → 收敛", "方形 / 圆形 / 长方形，等面积等厚度，再扫厚度"),
    ]
    for i, (num, head, desc) in enumerate(steps):
        y = 2.02 + i * 1.1
        textbox(s, L, y, 0.62, 0.42, [[(num, {})]], size=17, color=ACCENT, bold=True)
        textbox(s, L + 0.7, y - 0.02, CW - 0.7, 0.36, [[(head, {})]], size=14.5, color=INK,
                bold=True)
        textbox(s, L + 0.7, y + 0.36, CW - 0.7, 0.5, [desc], size=10.5, color=MUTED,
                line_spacing=1.2)
        if i < len(steps) - 1:
            rect(s, L, y + 0.98, CW, 0.009, LINE)

    card(s, L, 6.4, CW, 0.52, fill=ACCENT_LIGHT, line=None)
    textbox(s, L + 0.24, 6.4, CW - 0.4, 0.52,
            [[("理论地基已打好，下周开始出第一张退磁场云图。", {})]], size=13,
            color=ACCENT, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 8)
    note(s, "下一步四件事：定软件、锁参数、做静态校验，再跑三形状、磁畴、磁滞和收敛。"
            "软件路线还没定：这台机器有 RTX 5060，但新显卡和旧版 MuMax3 可能不兼容，"
            "也可能走 OOMMF 或 WSL 加 Fidimag。谢谢。")

    prs.save(OUT)
    return prs


def verify(path=OUT):
    prs = Presentation(str(path))
    assert len(prs.slides) == TOTAL_SLIDES, len(prs.slides)
    assert abs(prs.slide_width - Inches(W)) < 1000
    assert abs(prs.slide_height - Inches(H)) < 1000
    total_notes = 0
    report = []
    for idx, slide in enumerate(prs.slides, start=1):
        texts = []
        for shp in slide.shapes:
            left, top = shp.left / 914400, shp.top / 914400
            right, bottom = left + shp.width / 914400, top + shp.height / 914400
            assert -0.01 <= left and right <= W + 0.01, (idx, shp.name, left, right)
            assert -0.01 <= top and bottom <= H + 0.01, (idx, shp.name, top, bottom)
            if shp.has_text_frame:
                texts.append(shp.text_frame.text)
        body = " ".join(t for t in texts if t.strip())
        notes = slide.notes_slide.notes_text_frame.text
        assert notes.strip(), f"slide {idx} has no notes"
        total_notes += len(notes)
        report.append((idx, len(body), len(notes), shp_count(slide)))
    return report, total_notes


def shp_count(slide):
    return len(slide.shapes)


if __name__ == "__main__":
    build()
    report, total_notes = verify()
    print(f"saved {OUT} ({OUT.stat().st_size/1024:.1f} KB)")
    print(f"{'slide':>5} {'chars':>6} {'notes':>6} {'shapes':>6}")
    for idx, chars, notes, shapes in report:
        print(f"{idx:>5} {chars:>6} {notes:>6} {shapes:>6}")
    print(f"notes total: {total_notes} chars")
    for label, value in (("Nz(200x200x4)", N_SQ[2]), ("Nx", N_SQ[0]),
                         ("K_eff", KEFF), ("threshold", THRESHOLD),
                         ("center %", CENTER_ERR), ("infinite %", INFINITE_ERR),
                         ("lex nm", LEX_NM)):
        print(f"{label:>16}: {value:.6g}")
