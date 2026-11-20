r"""Build the 10-page minimalist white-and-black stage report PPTX (2026-11-20).

Run with the Python interpreter that has python-pptx & Pillow installed:
    C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe 汇报PPT\build_stage_report_20261120.py

Outputs:
    1. 汇报PPT/QAH形状效应仿真_阶段汇报_20261120.pptx
    2. refine-logs/GEMINI_STAGE_REPORT_PACKAGE_20261120/QAH形状效应仿真_阶段汇报_20261120.pptx
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches, Pt

# ------------------------------------------------------------------- paths ----
ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "refine-logs" / "GEMINI_STAGE_REPORT_PACKAGE_20261120"
EVIDENCE_DIR = PKG_DIR / "evidence"
FIG_DIR = PKG_DIR / "figures"

OUT_MAIN = Path(__file__).resolve().parent / "QAH形状效应仿真_阶段汇报_20261120.pptx"
OUT_COPY = PKG_DIR / "QAH形状效应仿真_阶段汇报_20261120.pptx"

# ----------------------------------------------------------------- palette ----
WHITE = "FFFFFF"
INK = "111111"       # Pure dark black for titles, bold text, primary rules
BODY = "222222"      # Dark neutral black for body text
MUTED = "555555"     # Secondary gray for labels, captions, footer
PANEL = "F6F6F6"     # Subtle light gray for conclusion bar & card headers
TABLE_ALT = "FAFAFA" # Very faint striping for readability
BORDER = "D0D0D0"    # Thin neutral card border
RULE_LIGHT = "E2E2E2"

EA = "Microsoft YaHei"
LATIN = "Segoe UI"

W, H = 13.333, 7.5
L, R = 0.65, 0.65
CW = W - L - R  # 12.033 in
TOTAL_SLIDES = 10

# --------------------------------------------------------- verified evidence --
RESULTS = json.loads((EVIDENCE_DIR / "results.json").read_text(encoding="utf-8"))
VERIF = json.loads((EVIDENCE_DIR / "verification_details.json").read_text(encoding="utf-8"))

assert RESULTS["completed_runs"] == 426
assert RESULTS["failed_checks"] == []
assert RESULTS["numerical_acceptance_complete"] is False
assert all(RESULTS["checks"].values())
assert len(VERIF) == 8  # 8/12 branches verified as of 2026-11-20 morning

METRICS = {(m["shape"], m["cell_nm"]): m for m in RESULTS["metrics"]}
DOMAIN_COMP = {d["shape"]: d for d in RESULTS["domain_energy_comparison"]}
TRAJ = {t["shape"]: t for t in RESULTS["reversal_trajectories"]}

# Static uniform-magnetization demagnetizing factors from evidence/RESULTS.md
DEMAG_TABLE = [
    ("方形", "2 nm", 0.029568913, 0.029568913, 0.940862174, 40000),
    ("方形", "1 nm", 0.029568913, 0.029568913, 0.940862174, 40000),
    ("圆形", "2 nm", 0.028018126, 0.028018126, 0.943963748, 39936),
    ("圆形", "1 nm", 0.027854473, 0.027854473, 0.944291053, 40000),
    ("长方形", "2 nm", 0.013690285, 0.057140628, 0.929169087, 40000),
    ("长方形", "1 nm", 0.013690285, 0.057140628, 0.929169087, 40000),
]

for _, _, nx, ny, nz, _ in DEMAG_TABLE:
    assert abs((nx + ny + nz) - 1.0) < 1e-6

# Verify key numeric facts used in slides
assert abs(DEMAG_TABLE[3][4] - DEMAG_TABLE[2][4] - 3.27305e-4) < 1e-6  # circle 2->1 nm dNz
assert abs(DOMAIN_COMP["square"]["delta_total_J_m3"] - 6331.24) < 0.05
assert abs(DOMAIN_COMP["circle"]["delta_total_J_m3"] - 7106.34) < 0.05
assert abs(DOMAIN_COMP["rectangle"]["delta_total_J_m3"] - 3354.49) < 0.05
assert abs(TRAJ["square"]["minimum_mean_norm"] - 0.58866) < 1e-4
assert abs(TRAJ["circle"]["minimum_mean_norm"] - 0.60507) < 1e-4
assert abs(TRAJ["rectangle"]["minimum_mean_norm"] - 0.42423) < 1e-4
assert all(t["final_spin_max_difference"] == 0.0 for t in TRAJ.values())
for sh_key in ("square", "circle", "rectangle"):
    for cell_nm in (2, 1):
        assert METRICS[(sh_key, cell_nm)]["coarse_brackets_T"] == [[-0.18, -0.2], [0.18, 0.2]]

# Track inserted images for aspect-ratio verification
IMAGE_CHECKS: list[tuple[int, object, tuple[int, int]]] = []


# --------------------------------------------------------- text & subscript ---
def sub(text: str):
    return (text, {"sub": True})


def sup(text: str):
    return (text, {"sup": True})


SUB_ALLOWED = {"x", "y", "z", "s", "u", "d", "eff", "ex", "an", "0", "1", "2", "i", "c", "r", "ext", "Z"}
SUB_RE = re.compile(r"([A-Za-zμℓ])_([A-Za-z0-9]{1,3})(?![A-Za-z0-9])")


def split_subscripts(text: str) -> list[tuple[str, bool]]:
    pieces: list[tuple[str, bool]] = []
    pos = 0
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


def style_run(run, size: float, color: str, bold: bool = False, italic: bool = False):
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


def add_runs(p, parts, size: float, color: str, bold: bool = False):
    if isinstance(parts, str):
        parts = [(parts, {})]
    for text, opt in parts:
        sub_flag = opt.get("sub", False)
        sup_flag = opt.get("sup", False)
        raw_flag = opt.get("raw", False)
        if sub_flag or sup_flag or raw_flag:
            chunks = [(text, bool(sub_flag), bool(sup_flag))]
        else:
            chunks = [(piece, is_sub, False) for piece, is_sub in split_subscripts(text)]
        for chunk, is_sub, is_sup in chunks:
            r = p.add_run()
            r.text = chunk
            sz = opt.get("size", size) * (0.72 if (is_sub or is_sup) else 1.0)
            style_run(
                r,
                sz,
                opt.get("color", color),
                opt.get("bold", bold),
                opt.get("italic", False),
            )
            if is_sub:
                r._r.get_or_add_rPr().set("baseline", "-25000")
            elif is_sup:
                r._r.get_or_add_rPr().set("baseline", "30000")
            if "spc" in opt:
                r._r.get_or_add_rPr().set("spc", str(int(opt["spc"] * 100)))


# --------------------------------------------------------- shape primitives ---
def strip_theme_style(shp):
    el = shp._element
    style = el.find(qn("p:style"))
    if style is not None:
        el.remove(style)


def textbox(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    lines,
    size: float = 12,
    color: str = BODY,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    line_spacing: float = 1.18,
    space_after: float = 0,
    margins=(0.0, 0.0, 0.0, 0.0),
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Inches(margins[0])
    tf.margin_right = Inches(margins[1])
    tf.margin_top = Inches(margins[2])
    tf.margin_bottom = Inches(margins[3])
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


def rect(slide, x: float, y: float, w: float, h: float, fill: str | None, line: str | None = None, width: float = 0.75):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
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
    shp.shadow.inherit = False
    strip_theme_style(shp)
    return shp


def card(slide, x: float, y: float, w: float, h: float, fill: str | None = WHITE, line: str | None = BORDER, width: float = 0.75, radius: float = 0.02):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
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
    shp.shadow.inherit = False
    strip_theme_style(shp)
    return shp


def add_picture_fitted(slide, slide_idx: int, fig_name: str, box_x: float, box_y: float, box_w: float, box_h: float):
    """Fit PNG proportionally inside (box_x, box_y, box_w, box_h), centered."""
    path = FIG_DIR / fig_name
    assert path.exists(), f"Missing figure: {path}"
    with Image.open(path) as im:
        px_w, px_h = im.size
    aspect = px_w / px_h
    if box_w / box_h >= aspect:
        draw_h = box_h
        draw_w = draw_h * aspect
    else:
        draw_w = box_w
        draw_h = draw_w / aspect
    draw_x = box_x + (box_w - draw_w) / 2.0
    draw_y = box_y + (box_h - draw_h) / 2.0
    pic = slide.shapes.add_picture(str(path), Inches(draw_x), Inches(draw_y), Inches(draw_w), Inches(draw_h))
    IMAGE_CHECKS.append((slide_idx, pic, (px_w, px_h)))
    return pic


# ------------------------------------------------------------ booktabs table --
def _set_cell_border(cell, side: str, color: str | None, width_pt: float = 0.75):
    tcPr = cell._tc.get_or_add_tcPr()
    tag = f"a:ln{side}"
    old = tcPr.find(qn(tag))
    if old is not None:
        tcPr.remove(old)
    if color is None:
        xml = f'<{tag} {nsdecls("a")}><a:noFill/></{tag}>'
    else:
        w_emu = int(width_pt * 12700)
        xml = (
            f'<{tag} {nsdecls("a")} w="{w_emu}" cap="flat" cmpd="sng" algn="ctr">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:prstDash val="solid"/>'
            f'</{tag}>'
        )
    tcPr.append(parse_xml(xml))


def _clear_table_style(table):
    tblPr = table._tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    style_id = tblPr.find(qn("a:tableStyleId"))
    if style_id is not None:
        tblPr.remove(style_id)


def add_booktabs_table(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    col_widths: list[float],
    headers: list,
    rows: list[list],
    header_size: float = 10.0,
    body_size: float = 9.5,
    col_aligns: list | None = None,
    row_heights: list[float] | None = None,
):
    assert abs(sum(col_widths) - w) < 0.02, (sum(col_widths), w)
    nrows = 1 + len(rows)
    ncols = len(headers)
    shape = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(h))
    table = shape.table
    _clear_table_style(table)

    for c_idx, cw in enumerate(col_widths):
        table.columns[c_idx].width = Inches(cw)

    if row_heights is not None:
        assert len(row_heights) == nrows
        for r_idx, rh in enumerate(row_heights):
            table.rows[r_idx].height = Inches(rh)

    if col_aligns is None:
        col_aligns = [PP_ALIGN.LEFT] * ncols

    def fill_cell(cell, spec, sz: float, col_hex: str, bold: bool, align, bg_hex: str):
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(bg_hex)
        cell.margin_left = Inches(0.08)
        cell.margin_right = Inches(0.08)
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = align
        p.line_spacing = 1.08
        add_runs(p, spec, sz, col_hex, bold)

    # Header row
    for c_idx, h_spec in enumerate(headers):
        cell = table.cell(0, c_idx)
        fill_cell(cell, h_spec, header_size, INK, True, col_aligns[c_idx], PANEL)
        _set_cell_border(cell, "T", INK, 1.4)
        _set_cell_border(cell, "B", INK, 1.0)
        _set_cell_border(cell, "L", None)
        _set_cell_border(cell, "R", None)

    # Body rows
    for r_idx, row in enumerate(rows):
        bg = WHITE if r_idx % 2 == 0 else TABLE_ALT
        is_last = r_idx == len(rows) - 1
        for c_idx, cell_spec in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            bold_col = c_idx == 0
            fill_cell(cell, cell_spec, body_size, BODY, bold_col, col_aligns[c_idx], bg)
            _set_cell_border(cell, "T", None)
            _set_cell_border(cell, "B", INK if is_last else RULE_LIGHT, 1.4 if is_last else 0.5)
            _set_cell_border(cell, "L", None)
            _set_cell_border(cell, "R", None)

    return shape


# ----------------------------------------------------------- slide template ---
def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(WHITE)
    return slide


def slide_chrome(slide, page: int, kicker: str, heading: str, conclusion: str):
    """Add unified header, thin rule, bottom stage-conclusion bar, and footer."""
    textbox(slide, L, 0.36, 9.5, 0.24, [[(kicker, {})]], size=10.5, color=MUTED, bold=True)
    textbox(slide, L, 0.62, CW, 0.54, [[(heading, {})]], size=22.5, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    rect(slide, L, 1.24, CW, 0.015, BORDER)
    rect(slide, L, 1.23, 1.15, 0.032, INK)

    # Bottom conclusion bar
    bar_y, bar_h = 6.24, 0.60
    rect(slide, L, bar_y, CW, bar_h, PANEL, line=BORDER, width=0.5)
    rect(slide, L, bar_y, 0.06, bar_h, INK)
    if isinstance(conclusion, str):
        parts = [(conclusion, {})]
    else:
        parts = conclusion
    textbox(
        slide,
        L + 0.20,
        bar_y + 0.02,
        CW - 0.36,
        bar_h - 0.04,
        [parts],
        size=11.5,
        color=INK,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.15,
    )

    footer(slide, page)


def footer(slide, page: int):
    textbox(
        slide,
        L,
        6.98,
        9.0,
        0.26,
        [[("数据截止：2026-11-20  |  OOMMF 2.0b0 微磁仿真阶段汇报", {})]],
        size=9.0,
        color=MUTED,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    textbox(
        slide,
        W - R - 1.4,
        6.98,
        1.4,
        0.26,
        [[(f"{page} / {TOTAL_SLIDES}", {})]],
        size=9.5,
        color=MUTED,
        align=PP_ALIGN.RIGHT,
        anchor=MSO_ANCHOR.MIDDLE,
    )


def add_bullets(slide, x: float, y: float, w: float, h: float, items: list, size: float = 11.2, space_after: float = 6.0, line_spacing: float = 1.22):
    lines = []
    for item in items:
        if isinstance(item, str):
            lines.append([("▪  ", {"color": INK, "bold": True}), (item, {})])
        else:
            lines.append([("▪  ", {"color": INK, "bold": True}), *item])
    return textbox(
        slide,
        x,
        y,
        w,
        h,
        lines,
        size=size,
        color=BODY,
        line_spacing=line_spacing,
        space_after=space_after,
    )


def set_note(slide, text: str):
    slide.notes_slide.notes_text_frame.text = text


# ------------------------------------------------------------------ slides ---
def build() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "同面积铁磁薄膜的形状退磁效应与准静态翻转：微磁仿真阶段进展"
    prs.core_properties.subject = "组会阶段性汇报（数据截止 2026-11-20）"
    prs.core_properties.author = "孙煜凡、韦中天"

    # ============================================================== Slide 1 ==
    s1 = new_slide(prs)
    rect(s1, L, 0.92, 0.075, 2.55, INK)
    textbox(s1, 0.92, 0.92, 11.4, 0.30, [[("物理学院科研项目阶段汇报  ·  微磁学仿真", {"spc": 1.2})]], size=11.5, color=MUTED, bold=True)
    textbox(
        s1,
        0.92,
        1.32,
        11.6,
        0.96,
        [[("同面积铁磁薄膜的形状退磁效应与准静态翻转", {})]],
        size=30.0,
        color=INK,
        bold=True,
        line_spacing=1.12,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    textbox(
        s1,
        0.92,
        2.34,
        11.5,
        0.46,
        [[("微磁仿真阶段进展：方形、圆形、长方形对比与数值验证", {})]],
        size=18.0,
        color=BODY,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    textbox(
        s1,
        0.92,
        3.02,
        11.5,
        0.38,
        [[("汇报人：孙煜凡、韦中天    |    数据截止：2026 年 11 月 20 日    |    求解器：OOMMF 2.0b0", {})]],
        size=11.5,
        color=MUTED,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    rect(s1, L, 3.74, CW, 0.015, BORDER)

    cover_cards = [
        (
            "01 / 实验完成度",
            "主实验全部完成  ·  验证 8 / 12",
            [
                "2 nm 与 1 nm 双网格的均匀退磁、零场弛豫及 6 条完整回线（726 场点）全部完成。",
                "2 nm 6/6 支翻转验证闭环；1 nm 完成方形 2 支，圆形下降支严格阈值运行中。",
            ],
        ),
        (
            "02 / 阶段性核心结论",
            "退磁可分辨  ·  矫顽场暂未分化",
            [
                "静态面外退磁因子排序明确：N_z 呈 圆形 (0.9443) > 方形 (0.9409) > 长方形 (0.9292)。",
                "三形状面外剩磁 M_r/M_s ≈ 1；已验证 8 支翻转场均夹逼于 [0.180, 0.185] T，过程呈非均匀成核。",
            ],
        ),
        (
            "03 / 模型范围与物理边界",
            "纯磁性条件分析  ·  不含输运",
            [
                "采用零温、无缺陷、关闭进动的教学模型参数，探讨 QAH 铁磁薄膜磁性基础条件。",
                "本轮不计算电子能带、拓扑陈数或量子反常霍尔电导，也不宣称材料参数标定。",
            ],
        ),
    ]
    cw3, gap3 = 3.85, 0.241
    for i, (tag, headline, bullets) in enumerate(cover_cards):
        cx = L + i * (cw3 + gap3)
        cy, ch = 4.02, 2.52
        card(s1, cx, cy, cw3, ch, fill=PANEL if i == 1 else WHITE, line=BORDER)
        rect(s1, cx, cy, cw3, 0.045, INK)
        textbox(s1, cx + 0.20, cy + 0.16, cw3 - 0.40, 0.24, [[(tag, {})]], size=10.0, color=MUTED, bold=True)
        textbox(s1, cx + 0.20, cy + 0.44, cw3 - 0.40, 0.36, [[(headline, {})]], size=13.5, color=INK, bold=True)
        add_bullets(s1, cx + 0.20, cy + 0.90, cw3 - 0.40, 1.48, bullets, size=10.5, space_after=6.0, line_spacing=1.22)

    footer(s1, 1)
    set_note(
        s1,
        "各位老师好，今天汇报“同面积铁磁薄膜的形状退磁效应与准静态翻转”的微磁仿真阶段进展（数据截止 11 月 20 日上午）。"
        "目前 2 nm 与 1 nm 两套网格的主实验已经全部完成，翻转区精细验证完成了 8/12 支。"
        "现阶段已经能清楚分辨三种轮廓的静态退磁差异和空间非均匀翻转过程，但在当前 5 mT 分辨率下尚未观察到可区分的矫顽场排序。"
        "需要说明的是，本项目聚焦磁性条件本身，不含电子结构和 QAH 输运计算。",
    )

    # ============================================================== Slide 2 ==
    s2 = new_slide(prs)
    slide_chrome(
        s2,
        2,
        "01 / 研究问题与技术路线",
        "形状改变静态退磁，但是否带来翻转性能优势须独立验证",
        [("研究边界：", {"bold": True}), ("基于零温、无缺陷教学模型检验几何形状对磁性条件的影响；所有物理结论均须经跨网格与收敛协议核查。", {})],
    )

    # 6-step roadmap strip
    steps = [
        ("1. 环境与基准", "已完成", True),
        ("2. 三轴均匀退磁", "已完成", True),
        ("3. 零场能量竞争", "已完成", True),
        ("4. 完整磁滞回线", "已完成", True),
        ("5. 翻转区精细验证", "8 / 12 支", False),
        ("6. 过程与独立验收", "待收尾", False),
    ]
    sw, sgap = 1.79, 0.258
    for i, (st_title, st_stat, done) in enumerate(steps):
        sx = L + i * (sw + sgap)
        sy, sh = 1.48, 0.78
        card(s2, sx, sy, sw, sh, fill=PANEL if done else WHITE, line=INK if done else BORDER, width=1.1 if done else 0.75)
        textbox(s2, sx + 0.10, sy + 0.10, sw - 0.20, 0.30, [[(st_title, {})]], size=10.5, color=INK, bold=True, align=PP_ALIGN.CENTER)
        textbox(s2, sx + 0.10, sy + 0.42, sw - 0.20, 0.24, [[(st_stat, {})]], size=9.5, color=INK if done else MUTED, bold=done, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            textbox(s2, sx + sw, sy + 0.20, sgap, 0.36, [[("→", {})]], size=13.0, color=MUTED, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # 2x2 question cards
    q_cards = [
        (
            "问题 1  |  静态退磁效应",
            "仅改变平面轮廓，退磁因子与退磁场分布如何变化？",
            [
                "固定目标面积 40,000 nm² 与厚度 4 nm，对比方形、圆形与 4:1 长方形。",
                "定量比较三轴体积平均退磁因子 N_x、N_y、N_z 与边缘退磁场削弱特征。",
            ],
        ),
        (
            "问题 2  |  零场能量竞争",
            "分畴降低退磁能的收益，能否抵消交换与各向异性能代价？",
            [
                "测试近单畴、双畴等多初态零场弛豫，核算四项分项能量密度。",
                "判断在当前参数下分畴是否真的比近单畴态总能量更低。",
            ],
        ),
        (
            "问题 3  |  准静态磁滞与路径",
            "静态退磁差异是否对应可分辨的剩磁、矫顽场或翻转路径？",
            [
                "由 +0.6 T → −0.6 T → +0.6 T 完整回线提取剩磁 M_r/M_s 与翻转区间。",
                "重放翻转场点内部演化过程，检验是否满足一致旋转或成核扩展机制。",
            ],
        ),
        (
            "问题 4  |  数值可信度检验",
            "观察到的差异能否经受网格、场步、停止阈值与微扰考验？",
            [
                "2 nm 主实验配合 1 nm 细网格复核，场步由 20 mT 加密至 10 / 5 mT。",
                "收紧停止阈值至 0.005 °/ns，并检验反向场微扰幅度 ε 的敏感性。",
            ],
        ),
    ]
    qw, qh, qgap_x, qgap_y = 5.88, 1.66, 0.273, 0.20
    for idx, (qtag, qtitle, qbullets) in enumerate(q_cards):
        row, col = divmod(idx, 2)
        qx = L + col * (qw + qgap_x)
        qy = 2.48 + row * (qh + qgap_y)
        card(s2, qx, qy, qw, qh, fill=WHITE, line=BORDER)
        rect(s2, qx, qy, 0.055, qh, INK)
        textbox(s2, qx + 0.22, qy + 0.14, qw - 0.38, 0.24, [[(qtag, {})]], size=10.0, color=MUTED, bold=True)
        textbox(s2, qx + 0.22, qy + 0.40, qw - 0.38, 0.34, [[(qtitle, {})]], size=12.5, color=INK, bold=True)
        add_bullets(s2, qx + 0.22, qy + 0.80, qw - 0.38, 0.78, qbullets, size=10.2, space_after=4.0, line_spacing=1.18)

    set_note(
        s2,
        "这一页说明核心研究问题与六步技术路线。核心出发点是：同面积、同厚度的薄膜改变平面形状后，静态退磁因子确实会改变，"
        "但这并不自动保证能转化为更优的剩磁或更高的矫顽场。因此我们沿“静态退磁 → 零场多初态能量竞争 → 完整准静态磁滞 → 翻转区精细验证 → 过程与跨网格核查”逐步检验。",
    )

    # ============================================================== Slide 3 ==
    s3 = new_slide(prs)
    slide_chrome(
        s3,
        3,
        "02 / 模型设计与统一协议",
        "固定面积与教学材料参数，统一双网格与反向场微扰协议",
        [("协议界定：", {"bold": True}), ("横向微扰是消除轴对称零力矩驻点的数值破缺协议，不代表热噪声；两套网格、三种形状采用完全一致的判定规则。", {})],
    )

    textbox(s3, L, 1.44, 5.85, 0.28, [[("几何模型与固定物理参数", {})]], size=12.0, color=INK, bold=True)
    param_rows = [
        [[("方形", {})], [("200 × 200 × 4 nm（目标面积 40,000 nm²）", {})]],
        [[("圆形", {})], [("名义半径 112.838 nm（1 nm: 40,000 nm²；2 nm: 39,936 nm², −0.16%）", {})]],
        [[("长方形 (4:1)", {})], [("400 × 100 × 4 nm，长轴沿 x（面积 40,000 nm²）", {})]],
        [[("材料参数", {})], [("M_s = 3×10⁵ A/m；A = 5×10⁻¹² J/m；K_u = 8×10⁴ J/m³（易轴 z）", {})]],
        [[("能量与条件", {})], [("交换 + 单轴各向异性 + 退磁 + Zeeman；零温、开放边界、无缺陷/DMI", {})]],
        [[("求解设置", {})], [("OOMMF 2.0b0；阻尼 α = 0.5；关闭进动进行准静态弛豫", {})]],
        [[("网格与扫场", {})], [("2×2×2 nm 与 1×1×1 nm；b = μ₀H_ext ∈ [+0.6, −0.6, +0.6] T（粗步 20 mT）", {})]],
    ]
    add_booktabs_table(
        s3,
        L,
        1.78,
        5.85,
        3.50,
        [1.45, 4.40],
        [[("项目", {})], [("固定设置（公平比较基准）", {})]],
        param_rows,
        header_size=10.0,
        body_size=9.4,
        row_heights=[0.36] + [0.445] * 7,
    )

    card(s3, L, 5.42, 5.85, 0.66, fill=PANEL, line=BORDER)
    textbox(
        s3,
        L + 0.16,
        5.46,
        5.53,
        0.58,
        [[("停止阈值：", {"bold": True, "color": INK}), ("常规 max|dm/dt| ≤ 0.01 °/ns；严格复核 ≤ 0.005 °/ns；局部场步加密至 10 mT 与 5 mT（仅超差时才补 2.5 mT）。", {})]],
        size=9.8,
        color=BODY,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.18,
    )

    # Right column: Transverse perturbation protocol expanded
    rx, rw = 6.80, 5.88
    card(s3, rx, 1.44, rw, 4.64, fill=WHITE, line=BORDER)
    rect(s3, rx, 1.44, rw, 0.045, INK)
    textbox(s3, rx + 0.22, 1.60, rw - 0.44, 0.30, [[("关键数值协议：反向场横向微扰（解决零力矩驻点）", {})]], size=12.5, color=INK, bold=True)

    add_bullets(
        s3,
        rx + 0.22,
        2.02,
        rw - 0.44,
        1.25,
        [
            [("驻点现象：", {"bold": True}), ("无扰动方形 2 nm 回线在 −0.6 T 反向强场下仍保持 <m_z> ≈ +0.9999998，陷入轴对称零力矩亚稳态。", {})],
            [("触发条件：", {"bold": True}), ("仅当外场方向与上一收敛态平均磁化 <m_z> 反向时激活，同向尾段保持自然继承。", {})],
        ],
        size=10.5,
        space_after=6.0,
        line_spacing=1.22,
    )

    # Formula box
    rect(s3, rx + 0.22, 3.30, rw - 0.44, 0.78, PANEL, line=BORDER, width=0.5)
    textbox(
        s3,
        rx + 0.32,
        3.34,
        rw - 0.64,
        0.70,
        [
            [("微扰更新公式：", {"bold": True, "color": INK, "size": 10.5}), ("m", {"italic": True, "bold": True, "size": 12.0}), sub("init"), (" = normalize( ", {"size": 12.0}), ("m", {"italic": True, "size": 12.0}), sub("prev"), (" + (ε, 0.37ε, 0) )", {"size": 12.0})],
            [("默认幅度 ε = 10⁻³ ；2 nm 已完成 ε = 10⁻⁴、10⁻³、10⁻² 三幅度对比", {"size": 9.8, "color": MUTED})],
        ],
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.28,
    )

    add_bullets(
        s3,
        rx + 0.22,
        4.22,
        rw - 0.44,
        1.70,
        [
            [("数据隔离：", {"bold": True}), ("原无扰动回线保留作驻点诊断，绝不混入正式矫顽场提取与对比。", {})],
            [("全链路追溯：", {"bold": True}), ("每次实际施加的扰动记入 applied_epsilon，子算例保存完整 MIF 输入与前驱磁化 SHA256。", {})],
            [("参数声明：", {"bold": True}), ("以上为给定教学模型参数，未针对某一特定真实 QAH 薄膜材料完成参数标定。", {})],
        ],
        size=10.3,
        space_after=5.0,
        line_spacing=1.20,
    )

    set_note(
        s3,
        "这一页介绍模型设计，并重点展开反向场横向微扰协议。三形状面积固定在 40,000 nm²、厚度 4 nm，材料参数完全统一。"
        "由于完美无缺陷轴对称薄膜在反向场下会卡在 m×H_eff=0 的零力矩驻点，我们在场与上一态平均 mz 反向时施加 (ε, 0.37ε, 0) 微扰，默认 ε=10⁻³，"
        "并在 2 nm 做了跨两个数量级的敏感性检验，确保三种形状与两套网格的比较公平一致。",
    )

    # ============================================================== Slide 4 ==
    s4 = new_slide(prs)
    slide_chrome(
        s4,
        4,
        "03 / 技术路线与完成度",
        "两套网格主实验全部完成，翻转区逐支验证已完成 8 / 12",
        [("阶段状态：", {"bold": True}), ("全部主实验与 2 nm 验证链已闭环；剩余 3 条半 1 nm 局部验证与跨网格核查正按串行队列推进。", {})],
    )

    textbox(s4, L, 1.44, 7.65, 0.28, [[("研究模块完成度清单（按实际原始输出与通过记录核定）", {})]], size=11.8, color=INK, bold=True)
    prog_rows = [
        [[("环境与历史基准复核", {})], [("50 项历史检查 + 2 本机算例 + 状态继承", {})], [("已完成", {"bold": True})]],
        [[("三轴固定均匀退磁", {})], [("2 nm (9 组) + 1 nm (9 组)，共 18 组", {})], [("已完成", {"bold": True})]],
        [[("多初态零场弛豫", {})], [("2 nm (24 组) + 1 nm 代表态 (6 组+严格阈值)", {})], [("已完成", {"bold": True})]],
        [[("完整准静态磁滞回线", {})], [("2 nm (3 条/363 点) + 1 nm (3 条/363 点)", {})], [("已完成", {"bold": True})]],
        [[("2 nm 翻转区逐支验证", {})], [("6/6 支：10/5 mT、0.005 °/ns、3 幅度微扰", {})], [("已完成", {"bold": True})]],
        [[("2 nm 翻转过程快照", {})], [("3 形状 −0.20 T 重放，共 385 帧（终态差=0）", {})], [("已完成", {"bold": True})]],
        [[("1 nm 翻转区逐支验证", {})], [("完成方形 2 支 + 圆形下降支常规；目标 6 支", {})], [("2/6 支 + 运行中", {"bold": True})]],
        [[("跨网格核查与独立验收", {})], [("已有两网格回线及阶段图；待 1 nm 支路收尾", {})], [("待执行", {"color": MUTED})]],
    ]
    add_booktabs_table(
        s4,
        L,
        1.78,
        7.65,
        4.26,
        [2.15, 3.85, 1.65],
        [[("模块", {})], [("执行范围与体量", {})], [("当前状态", {})]],
        prog_rows,
        header_size=9.8,
        body_size=9.2,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER],
        row_heights=[0.36] + [0.487] * 8,
    )

    # Right summary cards
    rx4, rw4 = 8.55, 4.13
    card(s4, rx4, 1.46, rw4, 1.56, fill=PANEL, line=BORDER)
    rect(s4, rx4, 1.46, 0.055, 1.56, INK)
    textbox(s4, rx4 + 0.18, 1.56, rw4 - 0.30, 0.24, [[("关键体量与自动审计指标", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s4,
        rx4 + 0.18,
        1.86,
        rw4 - 0.30,
        1.08,
        [
            [("正式全回线：", {"bold": True}), ("6 条回线、726 个正式场点", {})],
            [("逐支验证：", {"bold": True}), ("8 / 12 支已完成（1 nm 8/18 路径）", {})],
            [("自动审计：", {"bold": True}), ("426 目录、2714 项检查，0 失败（目录含聚合与诊断路径）", {})],
        ],
        size=9.6,
        space_after=3.5,
        line_spacing=1.15,
    )

    card(s4, rx4, 3.16, rw4, 1.54, fill=WHITE, line=BORDER)
    textbox(s4, rx4 + 0.18, 3.26, rw4 - 0.30, 0.24, [[("最新中断恢复说明（2026-11-20）", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s4,
        rx4 + 0.18,
        3.56,
        rw4 - 0.30,
        1.06,
        [
            "01:08 关机中断圆形 1 nm 下降支严格阈值 −0.175 T（当时 dm/dt ≈ 0.00543 > 0.005，未计通过）。",
            "10:45 已完整归档现场并核对 −0.170 T 前驱校验和，原串行计算队列已恢复。",
        ],
        size=9.5,
        space_after=4.0,
        line_spacing=1.16,
    )

    card(s4, rx4, 4.84, rw4, 1.22, fill=WHITE, line=BORDER)
    textbox(s4, rx4 + 0.18, 4.94, rw4 - 0.30, 0.24, [[("计算耗时特征提醒", {})]], size=11.0, color=INK, bold=True)
    textbox(
        s4,
        rx4 + 0.18,
        5.22,
        rw4 - 0.30,
        0.76,
        [[("近翻转点弛豫显著变慢：如圆形 1 nm −0.185 T 单点实耗 71.5 min，而尾段 26 点共耗时 47 s。不可按完成场点数线性估算剩余时间。", {})]],
        size=9.5,
        color=BODY,
        line_spacing=1.18,
    )

    set_note(
        s4,
        "这里列出严格按原始通过记录核定的进度，不给含糊的百分比。两套网格的静态退磁、零场态和 6 条完整磁滞回线全部完成，"
        "2 nm 的 6 支翻转区验证和过程重放也已完成。1 nm 方面，方形两支已经完全通过，目前正在续跑圆形下降支严格阈值，预计后续还需约 16 到 20 小时完成剩余 1 nm 验证。",
    )

    # ============================================================== Slide 5 ==
    s5 = new_slide(prs)
    slide_chrome(
        s5,
        5,
        "04 / 静态退磁结果",
        "平面轮廓造成可分辨的静态退磁差异：N_z 呈 圆形 > 方形 > 长方形",
        [("阶段性结论 1：", {"bold": True}), ("固定均匀面外磁化下长方形平均退磁能最低；但体积平均 N_i 是均匀态参考量，不能直接替代非均匀翻转中的局部退磁场。", {})],
    )

    textbox(s5, L, 1.44, 5.45, 0.28, [[("固定均匀磁化体积平均退磁因子", {})]], size=11.8, color=INK, bold=True)
    demag_rows = []
    for sh, cell, nx, ny, nz, area in DEMAG_TABLE:
        demag_rows.append([
            [(f"{sh} ({cell})", {})],
            [(f"{nx:.6f}", {})],
            [(f"{ny:.6f}", {})],
            [(f"{nz:.6f}", {"bold": True})],
            [(f"{area:,}", {})],
        ])
    add_booktabs_table(
        s5,
        L,
        1.78,
        5.45,
        2.56,
        [1.30, 1.05, 1.05, 1.05, 1.00],
        [[("形状(网格)", {})], [("N_x", {})], [("N_y", {})], [("N_z", {})], [("面积/nm²", {})]],
        demag_rows,
        header_size=9.5,
        body_size=9.1,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
        row_heights=[0.34] + [0.365] * 6,
    )

    card(s5, L, 4.48, 5.45, 1.60, fill=WHITE, line=BORDER)
    textbox(s5, L + 0.18, 4.58, 5.10, 0.24, [[("核心发现与网格一致性", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s5,
        L + 0.18,
        4.88,
        5.10,
        1.14,
        [
            [("面外退磁排序：", {"bold": True}), ("N_z(圆形 0.94429) > N_z(方形 0.94086) > N_z(长方形 0.92917)。", {})],
            [("面内各向异性：", {"bold": True}), ("方、圆 N_x = N_y；长方形长轴 N_x 仅为短轴 N_y 的 24%。", {})],
            [("守恒与网格检验：", {"bold": True}), ("N_x+N_y+N_z ≈ 1；圆形 N_z 2→1 nm 变化 3.27×10⁻⁴（≤10⁻³ 目标）。", {})],
        ],
        size=9.6,
        space_after=4.0,
        line_spacing=1.16,
    )

    # Right figure card
    fx5, fw5 = 6.32, 6.36
    card(s5, fx5, 1.46, fw5, 4.62, fill=WHITE, line=BORDER)
    add_picture_fitted(s5, 5, "demag_comparison.png", fx5 + 0.14, 1.58, fw5 - 0.28, 3.68)
    textbox(
        s5,
        fx5 + 0.18,
        5.40,
        fw5 - 0.36,
        0.58,
        [[("图：固定均匀面外磁化下底层退磁场 μ", {}), sub("0"), ("H", {}), sub("d,z"), ("（上）及中心线轮廓（下）。边缘退磁场弱于内部（中心约 −0.37 T），长方形整体面外退磁能最低。", {})]],
        size=9.5,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.18,
    )

    set_note(
        s5,
        "第一项明确物理结果是静态退磁差异。在 1 nm 网格固定均匀磁化下，三者均为强面外退磁，"
        "Nz 从大到小依次为圆形 0.9443、方形 0.9409、长方形 0.9292。长方形在面内 x、y 方向差异显著，且面外平均退磁能最低。"
        "圆形在 2 nm 下因离散面积偏差 −0.16%，加密到 1 nm 后 Nz 变化仅 3.27×10⁻⁴，网格收敛性达标。",
    )

    # ============================================================== Slide 6 ==
    s6 = new_slide(prs)
    slide_chrome(
        s6,
        6,
        "05 / 零场能量竞争",
        "双畴虽能降低退磁能，但交换与各向异性能代价使总能量仍高于近单畴",
        [("阶段性结论 2：", {"bold": True}), ("判断稳定状态必须核算全部能量项；当前能量差不是翻转能垒，有限初态测试也不证明全局基态。", {})],
    )

    textbox(s6, L, 1.40, 7.25, 0.24, [[("2 nm 代表零场驻态分项能量密度账本（单位：kJ/m³）", {})]], size=10.8, color=INK, bold=True)
    dom_rows = []
    for key, label in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        d = DOMAIN_COMP[key]
        e_s = d["single_J_m3"] / 1000.0
        e_d = d["domains_J_m3"] / 1000.0
        d_dem = d["delta_demag_J_m3"] / 1000.0
        d_wall = (d["delta_exchange_J_m3"] + d["delta_anisotropy_J_m3"]) / 1000.0
        d_tot = d["delta_total_J_m3"] / 1000.0
        dom_rows.append([
            [(label, {})],
            [(f"{e_s:.2f}", {})],
            [(f"{e_d:.2f}", {})],
            [(f"{d_dem:+.2f}", {})],
            [(f"{d_wall:+.2f}", {})],
            [(f"{d_tot:+.2f}", {"bold": True})],
            [(f"{d['domain_mean_abs_mz']:.3f}", {})],
        ])
    add_booktabs_table(
        s6,
        L,
        1.68,
        7.25,
        1.48,
        [0.85, 1.05, 1.05, 1.05, 1.25, 1.00, 1.00],
        [
            [("形状", {})],
            [("近单畴", {})],
            [("双畴态", {})],
            [("ΔE", {}), sub("d")],
            [("Δ(E", {}), sub("ex"), ("+E", {}), sub("an"), (")", {})],
            [("ΔE", {}), sub("tot")],
            [("<|m", {}), sub("z"), ("|>", {})],
        ],
        dom_rows,
        header_size=9.2,
        body_size=9.0,
        col_aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.RIGHT] * 6,
        row_heights=[0.34, 0.36, 0.36, 0.36],
    )

    card(s6, 8.10, 1.40, 4.58, 1.76, fill=WHITE, line=BORDER)
    textbox(s6, 8.26, 1.48, 4.26, 0.24, [[("竞争机制要点", {})]], size=10.5, color=INK, bold=True)
    add_bullets(
        s6,
        8.26,
        1.76,
        4.26,
        1.34,
        [
            [("上下畴抵消：", {"bold": True}), ("双畴 <m_z> ≈ 0 但 <|m_z|> > 0.90，非面内倒伏。", {})],
            [("壁代价主导：", {"bold": True}), ("退磁能降低（−3.57~−8.70 kJ/m³）始终不抵交换与各向异性增幅（+6.93~+15.81 kJ/m³）。", {})],
            [("长方形壁最短：", {"bold": True}), ("沿 100 nm 短轴成壁使净代价最小（+3.35 kJ/m³）。", {})],
        ],
        size=9.6,
        space_after=4.5,
        line_spacing=1.16,
    )

    # Bottom two figure cards
    fw6, fh6 = 5.88, 2.82
    card(s6, L, 3.28, fw6, fh6, fill=WHITE, line=BORDER)
    add_picture_fitted(s6, 6, "zero_states.png", L + 0.14, 3.35, fw6 - 0.28, 2.38)
    textbox(s6, L + 0.14, 5.76, fw6 - 0.28, 0.28, [[("左图：2 nm 零场近单畴态 (上) 与双畴驻态 (下) 空间 m_z 分布", {})]], size=9.2, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    rx6 = L + fw6 + 0.273
    card(s6, rx6, 3.28, fw6, fh6, fill=WHITE, line=BORDER)
    add_picture_fitted(s6, 6, "domain_energy_competition.png", rx6 + 0.14, 3.35, fw6 - 0.28, 2.38)
    textbox(s6, rx6 + 0.14, 5.76, fw6 - 0.28, 0.28, [[("右图：双畴相对近单畴的分项能量密度差（退磁收益 vs 畴壁代价）", {})]], size=9.2, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    set_note(
        s6,
        "第二项发现是零场能量竞争。很多人直观认为分畴能降低退磁能，总能量就更低；但从表里的能量账本可以看到，"
        "三种形状下双畴态虽然把退磁能压低了 3.6 到 8.7 kJ/m³，却在畴壁处付出了 6.9 到 15.8 kJ/m³ 的交换与各向异性能代价，"
        "导致总能量密度仍比近单畴态高出 3.35 到 7.11 kJ/m³。还要严格区分：这里算的是两个驻态之间的能量差，不是翻转能垒。",
    )

    # ============================================================== Slide 7 ==
    s7 = new_slide(prs)
    slide_chrome(
        s7,
        7,
        "06 / 完整磁滞回线与剩磁",
        "双网格 6 条全回线高度重合，三种形状撤场后均保持近饱和面外剩磁",
        [("阶段性结论 3：", {"bold": True}), ("两套网格一致表明三形状均保持接近 100% 的面外剩磁；20 mT 粗回线高度重合，末尾小数差不用于优劣排序。", {})],
    )

    textbox(s7, L, 1.40, 7.25, 0.24, [[("完整准静态磁滞回线（20 mT 粗步长）剩磁与粗翻转夹逼", {})]], size=10.8, color=INK, bold=True)
    hyst_rows = []
    for sh_key, sh_cn in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        m2 = METRICS[(sh_key, 2)]
        m1 = METRICS[(sh_key, 1)]
        b_str = "[−0.20, −0.18] / [0.18, 0.20] T"
        hyst_rows.append([
            [(sh_cn, {})],
            [(f"{m2['remanence'][0]:.9f}", {})],
            [(f"{m1['remanence'][0]:.9f}", {})],
            [(b_str, {})],
        ])
    add_booktabs_table(
        s7,
        L,
        1.68,
        7.25,
        1.48,
        [1.00, 1.75, 1.75, 2.75],
        [[("形状", {})], [("2 nm M", {}), sub("r"), sup("+"), ("/M", {}), sub("s")], [("1 nm M", {}), sub("r"), sup("+"), ("/M", {}), sub("s")], [("两支粗步翻转区间", {})]],
        hyst_rows,
        header_size=9.3,
        body_size=9.1,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER],
        row_heights=[0.34, 0.36, 0.36, 0.36],
    )

    card(s7, 8.10, 1.40, 4.58, 1.76, fill=WHITE, line=BORDER)
    textbox(s7, 8.26, 1.48, 4.26, 0.24, [[("核心读图要点", {})]], size=10.5, color=INK, bold=True)
    add_bullets(
        s7,
        8.26,
        1.76,
        4.26,
        1.34,
        [
            [("近饱和剩磁：", {"bold": True}), ("正负支 |M_r/M_s| 均约 0.9999998+，10⁻⁷ 级差异属数值容差。", {})],
            [("回线重合提示：", {"bold": True}), ("左下图中 3 形状 × 2 网格共 6 条曲线高度重合，非缺失数据。", {})],
            [("能量主导项：", {"bold": True}), ("翻转前交换/各向异性/退磁项保持平坦，总能量斜率由 Zeeman 能主导。", {})],
        ],
        size=9.6,
        space_after=4.5,
        line_spacing=1.16,
    )

    fw7, fh7 = 5.88, 2.82
    card(s7, L, 3.28, fw7, fh7, fill=WHITE, line=BORDER)
    add_picture_fitted(s7, 7, "hysteresis_comparison.png", L + 0.14, 3.36, fw7 - 0.28, 2.36)
    textbox(s7, L + 0.14, 5.76, fw7 - 0.28, 0.28, [[("左图：两套网格 6 条磁滞回线与 2 nm 下降支总能量密度曲线", {})]], size=9.2, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    card(s7, rx6, 3.28, fw7, fh7, fill=WHITE, line=BORDER)
    add_picture_fitted(s7, 7, "energy_components.png", rx6 + 0.12, 3.44, fw7 - 0.24, 2.18)
    textbox(s7, rx6 + 0.14, 5.76, fw7 - 0.28, 0.28, [[("右图：2 nm 下降支分项能量密度（翻转处出现 Zeeman 能阶跃）", {})]], size=9.2, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    set_note(
        s7,
        "第三部分看完整的准静态磁滞回线。统一加入横向微扰后，三种形状在 2 nm 和 1 nm 下的 6 条回线全部顺利翻转并闭合。"
        "撤场后剩磁均在 0.9999998 以上，负支相应接近 −1。20 mT 粗场步下 6 条曲线几乎完全重合，翻转都落在 0.18 到 0.20 T 之间，因此必须做局部场步加密。",
    )

    # ============================================================== Slide 8 ==
    s8 = new_slide(prs)
    slide_chrome(
        s8,
        8,
        "07 / 翻转区间与精细数值验证",
        "已验证支路翻转场均夹逼于 [0.180, 0.185] T，当前尚不支持矫顽场排序",
        [("阶段性结论 4：", {"bold": True}), ("静态退磁因子约 1.5% 的差异在当前 5 mT 分辨率下未引起可分辨的翻转场分化，尚不能排序哪种形状更优。", {})],
    )

    textbox(s8, L, 1.44, 7.05, 0.28, [[("逐支加密验证汇总（总进度 8 / 12 支已完整通过）", {})]], size=11.8, color=INK, bold=True)
    verif_rows = [
        [[("方形 (2 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT, 0.005, 3ε 全通过", {})]],
        [[("圆形 (2 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT, 0.005, 3ε 全通过", {})]],
        [[("长方形 (2 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT, 0.005, 3ε 全通过", {})]],
        [[("方形 (1 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT & 0.005 全通过", {})]],
        [[("圆形 (1 nm 下降)", {})], [("[−0.185, −0.180]*", {})], [("—", {})], [("暂不列入", {"color": MUTED})], [("5 mT 常规通过；严格运行中", {})]],
        [[("圆形返回 & 长方形 1 nm", {})], [("粗步 [−0.20, −0.18]", {})], [("粗步 [0.18, 0.20]", {})], [("待精细验证", {"color": MUTED})], [("3 支待串行队列执行", {})]],
    ]
    add_booktabs_table(
        s8,
        L,
        1.78,
        7.05,
        3.35,
        [1.55, 1.35, 1.35, 0.98, 1.82],
        [[("对象", {})], [("下降支夹逼/T", {})], [("返回支夹逼/T", {})], [("中点估计", {})], [("验证状态", {})]],
        verif_rows,
        header_size=9.2,
        body_size=8.8,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
        row_heights=[0.36] + [0.495] * 6,
    )

    card(s8, L, 5.26, 7.05, 0.82, fill=PANEL, line=BORDER)
    textbox(
        s8,
        L + 0.16,
        5.30,
        6.73,
        0.74,
        [[("* 严谨口径：", {"bold": True, "color": INK}), ("圆形 1 nm 下降支虽在 0.01 °/ns 5 mT 路径获得 [−0.185, −0.180] T，但 0.005 °/ns 严格阈值尚未结束，故暂不纳入完整通过对象。", {})]],
        size=9.5,
        color=BODY,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.18,
    )

    rx8, rw8 = 7.95, 4.73
    card(s8, rx8, 1.46, rw8, 2.22, fill=WHITE, line=BORDER)
    rect(s8, rx8, 1.46, 0.055, 2.22, INK)
    textbox(s8, rx8 + 0.18, 1.56, rw8 - 0.30, 0.24, [[("已通过支路的数值稳定性检验", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s8,
        rx8 + 0.18,
        1.88,
        rw8 - 0.30,
        1.72,
        [
            [("场步收敛：", {"bold": True}), ("10 → 5 mT 区间中点移动 2.5 mT，满足容差 ≤ max(2 mT, 5%|b_c|) ≈ 9.1 mT。", {})],
            [("停止阈值：", {"bold": True}), ("由 0.01 收紧至 0.005 °/ns 未改变任何已测支路的夹逼区间。", {})],
            [("微扰不变：", {"bold": True}), ("2 nm 三形状在 ε ∈ {10⁻⁴, 10⁻³, 10⁻²} 下均保持相同区间。", {})],
        ],
        size=9.7,
        space_after=4.5,
        line_spacing=1.18,
    )

    card(s8, rx8, 3.82, rw8, 2.26, fill=WHITE, line=BORDER)
    rect(s8, rx8, 3.82, 0.055, 2.26, INK)
    textbox(s8, rx8 + 0.18, 3.92, rw8 - 0.30, 0.24, [[("数据解释与汇报边界", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s8,
        rx8 + 0.18,
        4.24,
        rw8 - 0.30,
        1.74,
        [
            [("区间性质：", {"bold": True}), ("[0.180, 0.185] T 为离散场步夹逼区间，不是统计置信区间；0.1825 T 为中点估计。", {})],
            [("禁止过推：", {"bold": True}), ("不可写成“三形状矫顽场精确相等”或“已证明某形状翻转最优”。", {})],
            [("待定范围：", {"bold": True}), ("圆形返回支与长方形 1 nm 仍待加密验证。", {})],
        ],
        size=9.7,
        space_after=4.5,
        line_spacing=1.18,
    )

    set_note(
        s8,
        "这一页汇报精细翻转区间验证。已完成全部 2 nm 的 6 条支路以及 1 nm 方形两支（共 8/12 支），"
        "全部给出相同的夹逼区间 [0.180, 0.185] T（中点估计 0.1825 T）。"
        "在 10 到 5 mT 加密中点变化仅 2.5 mT，已满足预设收敛容差，且严格阈值 0.005 °/ns 与三档微扰都不改变该区间。"
        "注意这里必须严格表述为：在当前 5 mT 分辨率下区间重叠，暂不支持矫顽场排序，而不能说三者精确相等。",
    )

    # ============================================================== Slide 9 ==
    s9 = new_slide(prs)
    slide_chrome(
        s9,
        9,
        "08 / 翻转空间演化过程",
        "翻转中间态呈强烈空间非均匀性，存在形状相关的成核扩展路径",
        [("阶段性结论 5：", {"bold": True}), ("不能仅凭近单畴终态假定一致旋转；2 nm 快照揭示中心成核与中央带推进差异，1 nm 一致性待 P3 核查。", {})],
    )

    textbox(s9, L, 1.44, 4.72, 0.28, [[("2 nm 下降支 b = −0.20 T 重放统计", {})]], size=11.5, color=INK, bold=True)
    traj_rows = [
        [[("方形", {})], [("126", {})], [(f"{TRAJ['square']['minimum_mean_norm']:.5f}", {"bold": True})], [("中心成核 → 向外扩展", {})]],
        [[("圆形", {})], [("123", {})], [(f"{TRAJ['circle']['minimum_mean_norm']:.5f}", {"bold": True})], [("中心成核 → 径向扩展", {})]],
        [[("长方形", {})], [("136", {})], [(f"{TRAJ['rectangle']['minimum_mean_norm']:.5f}", {"bold": True})], [("中央成带 → 向两端推进", {})]],
    ]
    add_booktabs_table(
        s9,
        L,
        1.78,
        4.72,
        1.70,
        [0.85, 0.65, 1.15, 2.07],
        [[("形状", {})], [("帧数", {})], [("min|<m>|", {})], [("空间演化特征", {})]],
        traj_rows,
        header_size=9.2,
        body_size=8.9,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.LEFT],
        row_heights=[0.36, 0.42, 0.42, 0.42],
    )

    card(s9, L, 3.64, 4.72, 2.44, fill=WHITE, line=BORDER)
    textbox(s9, L + 0.16, 3.74, 4.40, 0.24, [[("过程物理机制与使用限制", {})]], size=10.8, color=INK, bold=True)
    add_bullets(
        s9,
        L + 0.16,
        4.04,
        4.40,
        1.96,
        [
            [("重放零偏差：", {"bold": True}), ("每 50 接受步输出快照，三形状重放终态与原算例最大磁化分量差均为 0。", {})],
            [("否定一致旋转：", {"bold": True}), ("中间态平均矢量模长显著跌破 1（长方形低至 0.424），证实多畴成核翻转。", {})],
            [("时间属性限定：", {"bold": True}), ("关闭进动的迭代步（step）不代表真实物理翻转速度。", {})],
        ],
        size=9.9,
        space_after=6.5,
        line_spacing=1.20,
    )

    # Right two figure cards
    fw9, fh9 = 3.48, 4.62
    fx9_1 = 5.56
    fx9_2 = fx9_1 + fw9 + 0.163
    card(s9, fx9_1, 1.46, fw9, fh9, fill=WHITE, line=BORDER)
    textbox(s9, fx9_1 + 0.12, 1.56, fw9 - 0.24, 0.28, [[("翻转前后收敛终态（近单畴）", {})]], size=10.2, color=INK, bold=True, align=PP_ALIGN.CENTER)
    add_picture_fitted(s9, 9, "reversal_states.png", fx9_1 + 0.10, 1.92, fw9 - 0.20, 3.55)
    textbox(s9, fx9_1 + 0.12, 5.54, fw9 - 0.24, 0.44, [[("±0.180 T 仍为单畴态，±0.200 T 均已整体反向", {})]], size=9.0, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    card(s9, fx9_2, 1.46, fw9, fh9, fill=WHITE, line=BORDER)
    textbox(s9, fx9_2 + 0.12, 1.56, fw9 - 0.24, 0.28, [[("−0.20 T 翻转中间快照（2 nm）", {})]], size=10.2, color=INK, bold=True, align=PP_ALIGN.CENTER)
    add_picture_fitted(s9, 9, "reversal_trajectory.png", fx9_2 + 0.10, 1.92, fw9 - 0.20, 3.55)
    textbox(s9, fx9_2 + 0.12, 5.54, fw9 - 0.24, 0.44, [[("方/圆中心成核向外扩展；长方形中央成带推进", {})]], size=9.0, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    set_note(
        s9,
        "如果只看左图翻转前后的收敛终态，三种形状仿佛都是均匀单畴直接翻转；但标量轨迹显示平均磁化矢量模长在途中大幅降低，"
        "长方形甚至降到 0.424。右图是 −0.20 T 的每 50 步重放快照：因为薄膜中心退磁场最强，方和圆从中心成核向外扩张，"
        "而长方形则在中央形成一条贯穿短轴的反向带再向左右推进。注意这组证据来自 2 nm，且关闭进动后迭代步不能解释为真实物理快慢。",
    )

    # ============================================================= Slide 10 ==
    s10 = new_slide(prs)
    slide_chrome(
        s10,
        10,
        "09 / 数值可信度、总结与后续里程碑",
        "主线证据与审计框架已就绪，按 P2–P4 完成剩余 1 nm 验证与验收",
        [("汇报小结：", {"bold": True}), ("静态退磁差异与非均匀翻转路径已有充分证据；待剩余 4 支 1 nm 验证与跨网格核查完成后闭合最终验收。", {})],
    )

    # Left column: QA + 3 settled results
    card(s10, L, 1.46, 5.75, 2.12, fill=WHITE, line=BORDER)
    rect(s10, L, 1.46, 0.055, 2.12, INK)
    textbox(s10, L + 0.18, 1.56, 5.40, 0.24, [[("数值可信度与过程审计保障", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s10,
        L + 0.18,
        1.88,
        5.40,
        1.62,
        [
            [("驻点隔离：", {"bold": True}), ("无扰动诊断路径与正式微扰数据完全隔离。", {})],
            [("全链路可追溯：", {"bold": True}), ("每算例保存输入 MIF、前驱 SHA256 与 ODT 收敛指标。", {})],
            [("断点严控：", {"bold": True}), ("历次关机未达阈值现场全部归档重算，当前 2714 项检查零失败。", {})],
        ],
        size=9.7,
        space_after=4.0,
        line_spacing=1.18,
    )

    card(s10, L, 3.72, 5.75, 2.36, fill=PANEL, line=BORDER)
    rect(s10, L, 3.72, 0.055, 2.36, INK)
    textbox(s10, L + 0.18, 3.82, 5.40, 0.24, [[("本阶段已确立的三条明确成果", {})]], size=11.0, color=INK, bold=True)
    textbox(
        s10,
        L + 0.18,
        4.14,
        5.40,
        1.84,
        [
            [("1. 静态退磁差异：", {"bold": True, "color": INK}), ("1 nm 下 N_z 为圆 (0.9443) > 方 (0.9409) > 长方形 (0.9292)，跨网格误差 < 10⁻³。", {})],
            [("2. 零场竞争账本：", {"bold": True, "color": INK}), ("双畴退磁收益不敌畴壁交换/各向异性代价，近单畴态能量更低。", {})],
            [("3. 磁滞与机制：", {"bold": True, "color": INK}), ("剩磁均近饱和；已验证 8/12 支夹逼于 [0.180, 0.185] T；2 nm 证实非均匀成核翻转。", {})],
        ],
        size=9.8,
        color=BODY,
        space_after=5.5,
        line_spacing=1.20,
    )

    # Right column: P2-P4 roadmap table
    rx10, rw10 = 6.65, 6.03
    textbox(s10, rx10, 1.44, rw10, 0.28, [[("剩余工作优先级与完成标准（P2 – P4）", {})]], size=11.8, color=INK, bold=True)
    todo_rows = [
        [[("P2-A\n(运行中)", {"bold": True})], [("完成圆形 1 nm 下降支严格阈值（−0.175 T 起）", {})], [("dm/dt ≤ 0.005 °/ns 通过；对比常规区间", {})]],
        [[("P2-B\n(排队)", {"bold": True})], [("补齐圆形返回支、长方形两支 1 nm 验证", {})], [("集齐 12/12 支；预计连续计算 16～20 h", {})]],
        [[("P2-C\n(条件)", {})], [("仅既定容差不满足时补 2.5 mT 或细网格微扰", {})], [("不忽略超差项，不无条件扩大扫描", {})]],
        [[("P3", {"bold": True})], [("1 nm 与 2 nm 跨网格翻转过程对照", {})], [("核对前后磁化与轨迹；必要时每形状补 1 组 1 nm 重放", {})]],
        [[("P4", {"bold": True})], [("独立原始数据验收、图表核查与报告定稿", {})], [("校验和全对齐，汇报前至少 1 天冻结材料", {})]],
    ]
    add_booktabs_table(
        s10,
        rx10,
        1.78,
        rw10,
        4.30,
        [0.98, 2.45, 2.60],
        [[("优先级", {})], [("剩余任务", {})], [("明确完成标准", {})]],
        todo_rows,
        header_size=9.5,
        body_size=9.1,
        col_aligns=[PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT],
        row_heights=[0.36, 0.78, 0.78, 0.78, 0.80, 0.80],
    )

    set_note(
        s10,
        "最后总结后续收尾计划。数值可信度方面，我们建立了从 MIF 输入、前驱哈希到 ODT 停止指标的全链条自动审计，未达标中断点全部重新归档计算。"
        "接下来按 P2 到 P4 推进：首先完成当前在跑的圆形下降支严格阈值和另外 3 条 1 nm 支路（约需 16 到 20 小时串行计算）；"
        "然后核对 1 nm 与 2 nm 翻转过程是否一致，最后执行独立验收并更新汇报定稿。谢谢各位老师，请指正。",
    )

    OUT_MAIN.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_MAIN)
    shutil.copy2(OUT_MAIN, OUT_COPY)
    return prs


def verify(path: Path = OUT_MAIN):
    prs = Presentation(str(path))
    assert len(prs.slides) == TOTAL_SLIDES, f"Expected {TOTAL_SLIDES} slides, got {len(prs.slides)}"
    assert abs(prs.slide_width - Inches(W)) < 1000
    assert abs(prs.slide_height - Inches(H)) < 1000

    for slide_idx, pic, (px_w, px_h) in IMAGE_CHECKS:
        disp_ratio = pic.width / pic.height
        nat_ratio = px_w / px_h
        assert abs(disp_ratio - nat_ratio) < 1e-3, (slide_idx, disp_ratio, nat_ratio)

    report = []
    for idx, slide in enumerate(prs.slides, start=1):
        chars = 0
        for shp in slide.shapes:
            left = shp.left / 914400
            top = shp.top / 914400
            right = left + shp.width / 914400
            bottom = top + shp.height / 914400
            assert -0.01 <= left and right <= W + 0.01, (idx, shp.name, left, right)
            assert -0.01 <= top and bottom <= H + 0.01, (idx, shp.name, top, bottom)
            if shp.has_text_frame:
                chars += len(shp.text_frame.text.strip())
            if shp.has_table:
                for row in shp.table.rows:
                    for cell in row.cells:
                        chars += len(cell.text_frame.text.strip())
        notes = slide.notes_slide.notes_text_frame.text.strip()
        assert notes, f"Slide {idx} missing speaker notes"
        report.append((idx, chars, len(notes), len(slide.shapes)))
    return report


if __name__ == "__main__":
    build()
    report = verify(OUT_MAIN)
    verify(OUT_COPY)
    print(f"Saved main: {OUT_MAIN} ({OUT_MAIN.stat().st_size / 1024:.1f} KB)")
    print(f"Saved copy: {OUT_COPY} ({OUT_COPY.stat().st_size / 1024:.1f} KB)")
    print(f"{'slide':>5} {'chars':>6} {'notes':>6} {'shapes':>6}")
    for idx, chars, nlen, nshp in report:
        print(f"{idx:>5} {chars:>6} {nlen:>6} {nshp:>6}")
