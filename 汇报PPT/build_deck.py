"""Build the 8-page theory deck: 汇报PPT/1.pptx.

The deck covers only what the simulation stage actually needs: the four energy
terms, the demagnetizing factor, the K_eff criterion, the exchange length and
domain wall, the LLG equation, and the five-stage plan. Numbers on the slides
are recomputed from the verified analytic scripts and the saved JSON summaries,
never hand-copied. Run with the bundled Python:

    python 汇报PPT/build_deck.py

Output: 汇报PPT/1.pptx (8 slides, 16:9, speaker notes). If 1.pptx is locked by
another program, the deck is saved as 阶段汇报_理论版.pptx instead.
"""
import json
import math
import os
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
OUT = Path(__file__).resolve().parent / os.environ.get("DECK_NAME", "1.pptx")

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
TOTAL_SLIDES = 7

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

MU0MS = MU0 * MS  # μ0·M_s, the field scale in tesla (≈0.377 T)
MU0_MS2 = MU0 * MS ** 2  # μ0·M_s², energy density scale (≈1.13×10⁵ J/m³)
Q_VALUE = 2 * KU / MU0_MS2
WALL_DELTA_NM = math.sqrt(AEX / KU) * 1e9
WALL_NM = math.pi * WALL_DELTA_NM
SIGMA_WALL = 4 * math.sqrt(AEX * KU)
assert abs(MU0MS - 0.377) < 1e-3
assert abs(MU0_MS2 - 1.1310e5) < 5
assert abs(Q_VALUE - 1.4147) < 5e-3
assert abs(WALL_NM - 24.84) < 0.2

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


SUP_TRANS = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def sci_text(value, digits=1):
    """Return plain text such as 2.8×10⁻¹², for footers."""
    exp = int(math.floor(math.log10(abs(value))))
    mant = value / 10 ** exp
    return f"{mant:.{digits}f}×10{str(exp).translate(SUP_TRANS)}"


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
            style_run(r, sz, opt.get("color", color), opt.get("bold", bold),
                      opt.get("italic", False))
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


def footer(slide, page):
    textbox(slide, 11.2, 7.02, 1.43, 0.26, [[(f"{page} / {TOTAL_SLIDES}", {})]],
            size=9, color=MUTED, align=PP_ALIGN.RIGHT)


def note(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def formula(slide, x, y, w, h, parts, size=20, color=INK, bold=False,
            fill=ACCENT_LIGHT, caption=None, caption_color=ACCENT,
            align=PP_ALIGN.CENTER, line_spacing=1.25):
    """Accent panel with an optional small caption and one centred equation."""
    card(slide, x, y, w, h, fill=fill, line=None)
    top = y
    if caption:
        textbox(slide, x + 0.24, y + 0.11, w - 0.48, 0.24,
                [[(caption, {"spc": 1.0})]], size=9.5, color=caption_color,
                bold=True)
        top = y + 0.4
    textbox(slide, x + 0.2, top, w - 0.4, y + h - top - 0.05, parts,
            size=size, color=color, bold=bold, align=align,
            anchor=MSO_ANCHOR.MIDDLE, line_spacing=line_spacing)


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
    prs.core_properties.subject = "核心理论、关键公式与后续计划（5 分钟）"
    prs.core_properties.author = "孙煜凡、韦中天"

    # ------------------------------------------------------------- slide 1 --
    s = new_slide(prs)
    rect(s, L, 1.28, 0.055, 3.7, ACCENT)
    textbox(s, 0.95, 1.22, 7.4, 0.3,
            [[("电磁学课程项目 · 理论汇报", {"spc": 2.0})]], size=11.5, color=ACCENT)
    textbox(s, 0.95, 1.62, 7.6, 2.05,
            [[("基于微磁学模拟探讨", {})], [("量子反常霍尔效应的退磁场效应", {})]],
            size=35, color=INK, bold=True, line_spacing=1.12)
    textbox(s, 0.95, 3.82, 7.4, 0.42,
            [[("核心理论、关键公式与后续计划", {})]], size=18, color=BODY)
    textbox(s, 0.95, 4.38, 7.4, 0.34,
            [[("孙煜凡　韦中天", {})]], size=14.5, color=INK, bold=True)
    textbox(s, 0.95, 4.76, 7.4, 0.28,
            [[("2026 年 10 月 · 理论学习阶段", {})]], size=11, color=MUTED)

    card(s, 8.55, 1.9, 4.15, 3.0, fill=ACCENT_LIGHT, line=None)
    rect(s, 9.0, 3.68, 3.25, 0.16, INK)
    arrow(s, 10.42, 2.62, 0.26, 0.9, ACCENT, "up")
    textbox(s, 10.82, 2.8, 0.9, 0.35, [[("M", {"italic": True})]], size=15,
            color=ACCENT, bold=True)
    arrow(s, 10.42, 4.0, 0.26, 0.7, AMBER, "down")
    textbox(s, 10.82, 4.12, 1.0, 0.35, [[("H", {"italic": True}), sub("d")]], size=14,
            color=AMBER, bold=True)
    textbox(s, 8.55, 5.0, 4.15, 0.3, [[("面外磁化与退磁场方向相反", {})]],
            size=9.5, color=MUTED, align=PP_ALIGN.CENTER)

    textbox(s, 0.95, 5.3, 7.0, 0.9,
            [[("面外磁化受到退磁场抑制；", {})],
             [("其稳定性由各向异性能与退磁能之差决定。", {"bold": True, "color": ACCENT})]],
            size=12.5, color=BODY, line_spacing=1.4)
    footer(s, 1)
    note(s, "各位老师好。我们汇报这个电磁学课程项目。今天讲三块：项目必需的理论、关键公式，以及下一步计划。"
            "题目可以概括为：面外磁化受到退磁场的抑制，其稳定性由形状与厚度决定。")

    # ------------------------------------------------------------- slide 2 --
    s = new_slide(prs)
    kicker(s, "01", "问题与框架")
    title(s, "面外磁化的稳定性由四项能量的相对大小决定")
    rule(s)

    rows = [
        ("交换能", "相邻自旋取向趋于一致，磁化弯曲需付出交换能代价"),
        ("各向异性能", "沿易轴时能量最低；本项目取易轴垂直膜面"),
        ("退磁能", "磁化在自身退磁场中的能量，以退磁因子 N 描述"),
        ("外场能", "塞曼能随磁化与外场夹角变化，撤场后为零"),
    ]
    for i, (name, desc) in enumerate(rows):
        y = 2.02 + i * 0.8
        rect(s, L, y + 0.05, 0.04, 0.56, AMBER if i == 1 else ACCENT)
        textbox(s, L + 0.2, y, 5.3, 0.3, [[(name, {})]], size=13, color=INK, bold=True)
        textbox(s, L + 0.2, y + 0.31, 5.5, 0.32, [[(desc, {})]], size=10.5, color=MUTED)

    formula(s, 6.6, 1.98, 6.03, 1.42,
            [("E", {"italic": True}), (" = ", {}),
             ("E", {"italic": True}), sub("ex"), (" + ", {}),
             ("E", {"italic": True}), sub("an"), (" + ", {}),
             ("E", {"italic": True}), sub("d"), (" + ", {}),
             ("E", {"italic": True}), sub("Z")],
            size=22, caption="总能量（四项之和）")
    textbox(s, 6.75, 3.5, 5.7, 0.3,
            [[("平衡态取总能量的极小值。", {})]], size=10.5, color=MUTED)

    card(s, 6.6, 3.9, 6.03, 1.62, fill=WHITE)
    textbox(s, 6.82, 4.02, 5.6, 0.26, [[("三条使用规则", {"spc": 1.5})]], size=9.5,
            color=ACCENT, bold=True)
    textbox(s, 6.82, 4.3, 5.6, 1.1,
            [[("形状只通过 ", {}), ("E", {"italic": True}), sub("d"),
              (" 进入；计入退磁能后，不再另设形状各向异性项。", {})],
             [("判据比较各向异性能与退磁能之差，而非单项绝对值。", {})],
             [("本工作只讨论磁性条件，不计算陈数、能隙或霍尔电导。", {})]],
            size=10.5, color=BODY, line_spacing=1.5)

    card(s, L, 5.75, CW, 0.95, fill=ACCENT_LIGHT, line=None)
    rect(s, L, 5.75, 0.055, 0.95, ACCENT)
    textbox(s, L + 0.28, 5.75, CW - 0.55, 0.95,
            [[("选择面外方向的原因：", {"bold": True, "color": ACCENT}),
              ("QAH 的质量隙源于面外磁化；但微磁学只能判断磁性条件，不能给出输运结论。", {})]],
            size=11.5, color=BODY, line_spacing=1.35, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 2)
    note(s, "磁化状态由四项能量相加决定：交换、各向异性、退磁、外场。平衡态取总能量极小。"
            "有两条规矩要记住：形状只通过退磁能进来，所以算了退磁就不用再加形状各向异性；"
            "判据比的是差值。最后，微磁学只到磁性条件，不算电导。")

    # ------------------------------------------------------------- slide 4 --
    s = new_slide(prs)
    kicker(s, "02", "四种能量")
    title(s, "四项能量均以焦耳为单位，可逐项比较")
    rule(s)

    cards = [
        ("交换能",
         [("E", {"italic": True}), sub("ex"), (" = ∫", {}), sub("V"), (" ", {}),
          ("A", {"italic": True}), (" |∇", {}), ("m", {"italic": True}), ("|² d", {}),
          ("V", {"italic": True})],
         "磁化不均匀时产生交换能；均匀态下为零。"),
        ("各向异性能",
         [("E", {"italic": True}), sub("an"), (" = ", {}),
          ("K", {"italic": True}), sub("u"), (" ", {}), ("V", {"italic": True}),
          (" sin²", {}), ("θ", {"italic": True})],
         "θ 为磁化与易轴夹角，偏离越大能量越高。"),
        ("退磁能",
         [("E", {"italic": True}), sub("d"), (" = (μ", {}), sub("0"), ("/2)∫|", {}),
          ("H", {"italic": True}), sub("d"), ("|² d", {}), ("V", {"italic": True})],
         "形成畴结构或闭合磁通可降低退磁能。"),
        ("外场能",
         [("E", {"italic": True}), sub("Z"), (" = −μ", {}), sub("0"),
          ("∫ ", {}), ("M", {"italic": True}), ("·", {}), ("H", {"italic": True}),
          sub("ext"), (" d", {}), ("V", {"italic": True})],
         "磁化与外场同向时最低；撤场后该项为零。"),
    ]
    cw2, gap2, ch2 = 5.846, 0.24, 1.86
    for i, (name, eq, desc) in enumerate(cards):
        row, col = divmod(i, 2)
        x = L + col * (cw2 + gap2)
        y = 1.98 + row * (ch2 + 0.2)
        card(s, x, y, cw2, ch2, fill=WHITE)
        textbox(s, x + 0.24, y + 0.12, 3.0, 0.26, [[(name, {"spc": 1.0})]], size=9.5,
                color=ACCENT, bold=True)
        textbox(s, x + 0.24, y + 0.44, cw2 - 0.48, 0.6, [eq], size=16, color=INK,
                anchor=MSO_ANCHOR.MIDDLE)
        textbox(s, x + 0.24, y + 1.14, cw2 - 0.48, 0.6, [[(desc, {})]], size=9.5,
                color=MUTED, line_spacing=1.35)

    card(s, L, 6.1, CW, 0.62, fill=ACCENT_LIGHT, line=None)
    textbox(s, L + 0.24, 6.1, CW - 0.45, 0.62,
            [[("畴壁参数：Δ = √(A/K)，δ", {}), sub("wall"), (" = πΔ，σ", {}), sub("wall"),
              (" = 4√(AK)；壁越窄，单位面积畴壁能越高", {})]],
            size=10, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 3)
    note(s, "四项能量各有一条公式。交换能看邻居同不同向；各向异性看偏离易轴多少；"
            "退磁能是退磁场平方的积分；外场能看顺不顺场。单位都是焦耳。"
            "最后一行是畴壁：宽度由交换和各向异性之比决定，单位面积能量是四倍根号 AK。")

    # ------------------------------------------------------------- slide 5 --
    s = new_slide(prs)
    kicker(s, "03", "判据")
    title(s, "面外稳定性取决于各向异性能与退磁能之差")
    rule(s)

    formula(s, L, 1.98, CW, 1.42,
            [("K", {"italic": True}), sub("eff"), (" = ", {}),
             ("K", {"italic": True}), sub("u"), (" − (μ", {}), sub("0"),
             ("M", {"italic": True}), sub("s"), ("²/2)(N", {}), sub("z"),
             (" − ", {}), ("N", {"italic": True}), sub("x"), (")", {})],
            size=24, caption="有效各向异性 = 各向异性能 − 退磁能之差")

    card(s, L, 3.62, 6.35, 1.75, fill=WHITE)
    textbox(s, L + 0.24, 3.74, 5.9, 0.26, [[("条件（两种写法等价）", {"spc": 0.6})]],
            size=9.5, color=ACCENT, bold=True)
    textbox(s, L + 0.24, 4.04, 5.9, 1.1,
            [[("K", {"italic": True}), sub("u"), (" > (μ", {}), sub("0"),
              ("M", {"italic": True}), sub("s"), ("²/2)(N", {}), sub("z"), (" − N", {}),
              sub("x"), (")", {})],
             [("Q", {"italic": True}), (" = 2", {}), ("K", {"italic": True}), sub("u"),
              (" / (μ", {}), sub("0"), ("M", {"italic": True}), sub("s"),
              ("²) ⇒ ", {}), ("Q", {"italic": True}), ("(N", {}), sub("z"),
              (" − ", {}), ("N", {"italic": True}), sub("x"), (") > 1", {})]],
            size=14, color=BODY, line_spacing=1.7)

    card(s, 7.35, 3.62, 5.28, 1.75, fill=WHITE)
    vals = [
        ("各向异性能", [*sci(KU), (" J/m³", {})], BODY, False),
        ("退磁能之差", [*sci(THRESHOLD), (" J/m³", {})], BODY, False),
        ("有效各向异性", [*sci(KEFF), (" J/m³ > 0", {})], ACCENT, True),
    ]
    for i, (lab, val, col, bold) in enumerate(vals):
        y = 3.9 + i * 0.44
        textbox(s, 7.6, y, 1.7, 0.32, [[(lab, {})]], size=10, color=MUTED)
        textbox(s, 9.2, y, 3.25, 0.32, [val], size=12, color=col, bold=bold,
                align=PP_ALIGN.RIGHT)

    textbox(s, L, 5.62, CW, 0.55,
            [[("仅对均匀态成立：", {}), ("K", {"italic": True}), sub("eff"),
              (" > 0 表示面外取向能量更低，不保证单畴；分畴可进一步降低退磁能。", {})]],
            size=11, color=BODY, line_spacing=1.35)
    textbox(s, L, 6.3, CW, 0.35,
            [[("解析给出均匀态的能量判据；畴结构与翻转过程须由微磁学模拟给出。", {})]],
            size=12, color=ACCENT, bold=True)
    footer(s, 4)
    note(s, "把各向异性减去退磁能之差，就是有效各向异性。这里 8.0 减 5.15，还剩 2.85 乘十的四次方，大于零，"
            "所以均匀态下面外取向能量更低。等价写法是 Q 乘上 N_z 减 N_x 大于一。但有效各向异性大于零不等于单畴，"
            "分畴还可能继续降低退磁能，这要模拟才能回答。")

    # ------------------------------------------------------------- slide 6 --
    s = new_slide(prs)
    kicker(s, "04", "尺度")
    title(s, "交换长度决定网格尺度，畴壁宽度决定分辨率")
    rule(s)

    card(s, L, 1.98, cw2, 1.66, fill=WHITE)
    textbox(s, L + 0.24, 2.08, 3.2, 0.24, [[("交换长度", {"spc": 1.0})]], size=9.5,
            color=ACCENT, bold=True)
    textbox(s, L + 0.24, 2.34, cw2 - 0.48, 0.5,
            [[("ℓ", {"italic": True}), sub("ex"), (" = √(2", {}), ("A", {"italic": True}),
              ("/(μ", {}), sub("0"), ("M", {"italic": True}), sub("s"), ("²)) ≈ ", {}),
              (f"{LEX_NM:.1f} nm", {"bold": True})]],
            size=15, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, L + 0.24, 2.9, cw2 - 0.48, 0.6,
            [[("磁化转向的特征长度；网格应显著小于该值。", {})]], size=9.5, color=MUTED)

    card(s, 6.787, 1.98, cw2, 1.66, fill=WHITE)
    textbox(s, 7.03, 2.08, 3.2, 0.24, [[("网格", {"spc": 1.0})]], size=9.5,
            color=ACCENT, bold=True)
    textbox(s, 7.03, 2.34, cw2 - 0.48, 0.5, [[("2 nm → 1 nm", {"bold": True})]],
            size=17, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, 7.03, 2.9, cw2 - 0.48, 0.6,
            [[("以 2 nm 起步；关键结果用 1 nm 复核。", {})]], size=9.5, color=MUTED)

    card(s, L, 3.84, cw2, 1.66, fill=WHITE)
    textbox(s, L + 0.24, 3.94, 3.2, 0.24, [[("畴壁", {"spc": 1.0})]], size=9.5,
            color=ACCENT, bold=True)
    textbox(s, L + 0.24, 4.2, cw2 - 0.48, 0.5,
            [[("Δ = √(", {}), ("A", {"italic": True}), ("/", {}), ("K", {"italic": True}),
              (")，δ", {}), sub("wall"), (" = πΔ ≈ ", {}),
              (f"{WALL_NM:.0f} nm", {"bold": True})]],
            size=14, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, L + 0.24, 4.76, cw2 - 0.48, 0.6,
            [[("壁宽定义不唯一（Δ 或 πΔ），引用文献前需核对。", {})]], size=9.5,
            color=MUTED)

    card(s, 6.787, 3.84, cw2, 1.66, fill=WHITE)
    textbox(s, 7.03, 3.94, 3.2, 0.24, [[("分辨率判断", {"spc": 1.0})]], size=9.5,
            color=ACCENT, bold=True)
    textbox(s, 7.03, 4.2, cw2 - 0.48, 0.5, [[("≥ 3–5 格 / 壁", {"bold": True})]],
            size=15, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, 7.03, 4.76, cw2 - 0.48, 0.6,
            [[("单一网格结果不足以判定收敛，至少比较两种网格。", {})]], size=9.5, color=MUTED)

    textbox(s, L, 5.72, CW, 0.5,
            [[("本参数：", {"bold": True}),
              ("M", {"italic": True}), sub("s"), (" = 3×10⁵ A/m，", {}),
              ("A", {"italic": True}), (" = 5 pJ/m，", {}),
              ("K", {"italic": True}), sub("u"), (" = 8×10⁴ J/m³；σ", {}), sub("wall"),
              (" = 4√(AK) ≈ 2.5×10⁻³ J/m²。", {})]],
            size=10, color=MUTED, line_spacing=1.3)

    card(s, L, 6.18, CW, 0.6, fill=ACCENT_LIGHT, line=None)
    textbox(s, L + 0.24, 6.18, CW - 0.45, 0.6,
            [[("经验判据：格距 ≤ ", {}), ("ℓ", {"italic": True}), sub("ex"),
              ("/4，且畴壁内不少于 3–5 个格点；取二者中较严者。", {})]],
            size=10, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 5)
    note(s, "尺度有两个来源。第一个是交换长度，本参数下 9.4 纳米，网格必须比它细，先用 2 纳米跑通，关键结果用 1 纳米复算。"
            "第二个是畴壁宽度，Δ 的 π 倍，约 25 纳米；要分辨畴壁，至少三到五个格点。"
            "注意壁宽的定义不唯一，比文献时要先对齐。")

    # ------------------------------------------------------------- slide 7 --
    s = new_slide(prs)
    kicker(s, "05", "动力学")
    title(s, "磁化动力学：绕有效场进动，并由阻尼趋向低能态")
    rule(s)

    formula(s, L, 1.95, CW, 1.05,
            [("H", {"italic": True}), sub("eff"), (" = −(1/μ", {}), sub("0"),
             ("M", {"italic": True}), sub("s"), (") δ", {}), ("E", {"italic": True}),
             ("/δ", {}), ("m", {"italic": True})],
            size=18, caption="有效场：能量对磁化求导")

    formula(s, L, 3.12, CW, 1.55,
            [("∂", {}), ("m", {"italic": True}), ("/∂", {}), ("t", {"italic": True}),
             (" = −γ", {}), sub("H"), ("/(1+α²)[ ", {}),
             ("m", {"italic": True}), (" × ", {}), ("H", {"italic": True}), sub("eff"),
             (" + α ", {}), ("m", {"italic": True}), (" × (", {}),
             ("m", {"italic": True}), (" × ", {}), ("H", {"italic": True}), sub("eff"),
             (") ]", {})],
            size=15, caption="LLG 方程（显式形式）")

    card(s, L, 4.85, cw2, 1.35, fill=WHITE)
    textbox(s, L + 0.24, 4.95, 3.2, 0.24, [[("两套单位制须配套使用", {"spc": 1.0})]],
            size=9.5, color=ACCENT, bold=True)
    textbox(s, L + 0.24, 5.24, cw2 - 0.48, 0.85,
            [[("H 用 A/m → γ", {}), sub("H"), (" = 2.21×10⁵", {})],
             [("μ", {}), sub("0"), ("H 用 T → γ", {}), sub("B"), (" = 1.76×10¹¹", {})]],
            size=10.5, color=BODY, line_spacing=1.5)

    card(s, 6.787, 4.85, cw2, 1.35, fill=WHITE)
    textbox(s, 7.03, 4.95, 3.2, 0.24, [[("阻尼系数 α 的作用", {"spc": 1.0})]], size=9.5,
            color=ACCENT, bold=True)
    textbox(s, 7.03, 5.24, cw2 - 0.48, 0.85,
            [[("仅改变演化路径与速率，不改变静态能量。", {})],
             [("求静态解可令进动项为零；报告翻转时间须实际积分。", {})]],
            size=10.5, color=BODY, line_spacing=1.5)
    footer(s, 6)
    note(s, "四项能量对磁化求导，就是 LLG 里的有效场。LLG 两项：一项绕有效场进动，一项被阻尼拉向低能。"
            "写代码时单位要配套：场用安每米配 2.2 乘十的五次方，用特斯拉配 1.8 乘十的十一次方。"
            "α 只改路径和速度，不改静态能量；但要报翻转时间，必须真的跑动力学。")

    # ------------------------------------------------------------- slide 8 --
    s = new_slide(prs)
    kicker(s, "06", "后续计划")
    title(s, "研究计划：先建立基准，再比较形状")
    rule(s)

    stages = [
        ("理论学习", "✓ 已完成", "明确四项能量与适用边界"),
        ("基准模拟", "当前位置", "跑通薄膜基准算例"),
        ("形状比较", "待启动", "方、圆、长条三种轮廓"),
        ("数据分析", "待启动", "曲线对比与网格收敛"),
        ("总结优化", "待启动", "设计建议与总结"),
    ]
    tw, tgap, ty, th = 2.25, 0.17, 1.98, 1.62
    for i, (name, state, std) in enumerate(stages):
        x = L + i * (tw + tgap)
        if i == 0:
            card(s, x, ty, tw, th, fill=ACCENT, line=None)
            textbox(s, x + 0.2, ty + 0.16, tw - 0.4, 0.32, [[(name, {})]], size=13.5,
                    color=WHITE, bold=True)
            textbox(s, x + 0.2, ty + 0.52, tw - 0.4, 0.26, [[(state, {})]], size=10,
                    color=WHITE)
            textbox(s, x + 0.2, ty + 0.88, tw - 0.4, 0.6, [[(std, {})]], size=8.5,
                    color=WHITE, line_spacing=1.2)
        elif i == 1:
            card(s, x, ty, tw, th, fill=WHITE, line=ACCENT, width=2.0)
            textbox(s, x + 0.2, ty + 0.16, tw - 0.4, 0.32, [[(name, {})]], size=13.5,
                    color=ACCENT, bold=True)
            textbox(s, x + 0.2, ty + 0.52, tw - 0.4, 0.26, [[(state, {})]], size=10,
                    color=ACCENT)
            textbox(s, x + 0.2, ty + 0.88, tw - 0.4, 0.6, [[(std, {})]], size=8.5,
                    color=BODY, line_spacing=1.2)
        else:
            card(s, x, ty, tw, th, fill=FAINT)
            textbox(s, x + 0.2, ty + 0.16, tw - 0.4, 0.32, [[(name, {})]], size=13.5,
                    color=MUTED, bold=True)
            textbox(s, x + 0.2, ty + 0.52, tw - 0.4, 0.26, [[(state, {})]], size=10,
                    color=MUTED)
            textbox(s, x + 0.2, ty + 0.88, tw - 0.4, 0.6, [[(std, {})]], size=8.5,
                    color=MUTED, line_spacing=1.2)

    textbox(s, L, 3.78, CW, 0.28, [[("近期工作", {"spc": 1.5})]], size=9.5,
            color=ACCENT, bold=True)
    near = [
        ("① 确定求解器", "在 OOMMF、WSL+Fidimag、MuMax3 中择一；先验证 CUDA 兼容性。"),
        ("② 锁定参数与网格", "参数一次确定并注明来源；网格自 2 nm 起步。"),
        ("③ 静态校验　|ΔN| < 10⁻⁴", "沿 x、y、z 分别施加均匀磁化，与解析 N 对比。"),
    ]
    for i, (head, desc) in enumerate(near):
        x = L + i * (3.84 + 0.2)
        textbox(s, x, 4.1, 3.84, 0.3, [[(head, {})]], size=12, color=INK, bold=True)
        textbox(s, x, 4.44, 3.8, 0.6, [[(desc, {})]], size=9.5, color=MUTED,
                line_spacing=1.3)

    card(s, L, 6.05, CW, 0.6, fill=ACCENT_LIGHT, line=None)
    textbox(s, L + 0.24, 6.05, CW - 0.4, 0.6,
            [[("下一步：在求解器中复现同一组 N。", {})]], size=12.5,
            color=ACCENT, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 7)
    note(s, "计划分五个阶段：理论已完成；基准模拟是当前位置，标准是跑通薄膜基准算例；"
            "然后是方形、圆形、长条形三种形状的比较，再做数据分析和总结。"
            "近期工作：确定求解器、锁定参数与网格、先做静态校验，x、y、z 三个方向的 N 要和解析值对上。"
            "下一步就是在求解器里复现同一组 N。谢谢。")

    global OUT
    try:
        prs.save(OUT)
    except PermissionError:
        OUT = OUT.with_name("阶段汇报_理论版.pptx")
        prs.save(OUT)
        print(f"note: 1.pptx 被占用，已另存为 {OUT.name}")
    return prs


def verify(path=None):
    path = OUT if path is None else path
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
