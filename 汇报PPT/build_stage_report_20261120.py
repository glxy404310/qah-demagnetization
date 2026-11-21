r"""Build the 11-page minimalist white-and-black stage report PPTX (2026-11-20 evening update).

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
INK = "111111"        # Pure dark black for titles, bold text, primary rules
BODY = "222222"       # Dark neutral black for body text
MUTED = "555555"      # Secondary gray for labels, captions, footer
PANEL = "F6F6F6"      # Subtle light gray for conclusion bar & card headers
TABLE_ALT = "FAFAFA"  # Very faint striping for readability
BORDER = "D0D0D0"     # Thin neutral card border
RULE_LIGHT = "E2E2E2"

EA = "Microsoft YaHei"
LATIN = "Segoe UI"

W, H = 13.333, 7.5
L, R = 0.65, 0.65
CW = W - L - R  # 12.033 in
TOTAL_SLIDES = 11

# --------------------------------------------------------- verified evidence --
RESULTS = json.loads((EVIDENCE_DIR / "results.json").read_text(encoding="utf-8"))
VERIF = json.loads((EVIDENCE_DIR / "verification_details.json").read_text(encoding="utf-8"))
LOCAL_REV = json.loads((EVIDENCE_DIR / "local_reversal.json").read_text(encoding="utf-8"))

assert RESULTS["completed_runs"] == 459
assert RESULTS["failed_checks"] == []
assert RESULTS["numerical_acceptance_complete"] is False
assert all(RESULTS["checks"].values())
assert len(VERIF) == 10  # 10/12 branches verified as of 2026-11-20 evening

METRICS = {(m["shape"], m["cell_nm"]): m for m in RESULTS["metrics"]}
DOMAIN_COMP = {d["shape"]: d for d in RESULTS["domain_energy_comparison"]}
TRAJ = {t["shape"]: t for t in RESULTS["reversal_trajectories"]}
LOCAL_FIELDS = {(f["shape"], f["cell_nm"]): f for f in LOCAL_REV["fields"]}
LOCAL_TRACES = {(t["shape"], t["cell_nm"]): t for t in LOCAL_REV["traces"]}
FIRST_REV = {f["shape"]: f for f in LOCAL_REV["first_reverse"]}

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
assert abs(DEMAG_TABLE[3][4] - DEMAG_TABLE[2][4] - 3.27305e-4) < 1e-6
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

assert abs(LOCAL_REV["exchange_length_nm"] - 9.403) < 1e-2
assert abs(LOCAL_REV["B_K_T"] * 1000.0 - 533.333) < 1e-2
assert abs(abs(LOCAL_FIELDS[("rectangle", 1)]["core"]["B_mT"] - LOCAL_FIELDS[("circle", 1)]["core"]["B_mT"]) - 3.274) < 0.02
assert abs(abs(LOCAL_FIELDS[("rectangle", 1)]["all"]["B_mT"] - LOCAL_FIELDS[("circle", 1)]["all"]["B_mT"]) - 5.701) < 0.02

# Track inserted images for aspect-ratio verification
IMAGE_CHECKS: list[tuple[int, object, tuple[int, int]]] = []


# --------------------------------------------------------- text & subscript ---
def sub(text: str):
    return (text, {"sub": True})


def sup(text: str):
    return (text, {"sup": True})


SUB_ALLOWED = {"x", "y", "z", "s", "u", "d", "eff", "ex", "an", "0", "1", "2", "i", "c", "r", "ext", "Z", "K"}
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
        cell.margin_left = Inches(0.07)
        cell.margin_right = Inches(0.07)
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = align
        p.line_spacing = 1.08
        add_runs(p, spec, sz, col_hex, bold)

    for c_idx, h_spec in enumerate(headers):
        cell = table.cell(0, c_idx)
        fill_cell(cell, h_spec, header_size, INK, True, col_aligns[c_idx], PANEL)
        _set_cell_border(cell, "T", INK, 1.4)
        _set_cell_border(cell, "B", INK, 1.0)
        _set_cell_border(cell, "L", None)
        _set_cell_border(cell, "R", None)

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


def slide_chrome(slide, page: int, kicker: str, heading: str, conclusion):
    textbox(slide, L, 0.36, 9.5, 0.24, [[(kicker, {})]], size=10.5, color=MUTED, bold=True)
    textbox(slide, L, 0.62, CW, 0.54, [[(heading, {})]], size=22.0, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    rect(slide, L, 1.24, CW, 0.015, BORDER)
    rect(slide, L, 1.23, 1.15, 0.032, INK)

    bar_y, bar_h = 6.24, 0.60
    rect(slide, L, bar_y, CW, bar_h, PANEL, line=BORDER, width=0.5)
    rect(slide, L, bar_y, 0.06, bar_h, INK)
    parts = [(conclusion, {})] if isinstance(conclusion, str) else conclusion
    textbox(
        slide,
        L + 0.20,
        bar_y + 0.02,
        CW - 0.36,
        bar_h - 0.04,
        [parts],
        size=11.3,
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
        [[("数据截止：2026-11-20 晚间更新  |  OOMMF 2.0b0 微磁仿真阶段汇报", {})]],
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
    prs.core_properties.subject = "组会阶段性汇报（2026-11-20 晚间更新版）"
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
        [[("微磁仿真阶段进展：形状效应、局部成核机制与双网格数值验证", {})]],
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
        [[("汇报人：孙煜凡、韦中天    |    数据截止：2026 年 11 月 20 日晚    |    求解器：OOMMF 2.0b0", {})]],
        size=11.5,
        color=MUTED,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    rect(s1, L, 3.74, CW, 0.015, BORDER)

    cover_cards = [
        (
            "01 / 实验完成度",
            "验证 10 / 12 支  ·  P3 核查完成",
            [
                "2 nm 全三形状与 1 nm 方形、圆形均已完成并通过；6 条全回线（726 场点）与 P3 跨网格过程轨迹已闭环。",
                "目前仅剩长方形 1 nm 两支验证在跑（已为 4 个临界点预置 20 万步预算防停机）。",
            ],
        ),
        (
            "02 / 核心结论与物理解释",
            "全片 N_z 分化  ·  中心局域场相近",
            [
                "已验证 10 支翻转场均夹逼于 [0.180, 0.185] T，且 1/2 nm 非均匀成核轨迹一致。",
                "长方形全片 N_z 较低因弱退磁边缘带占比高（21.69% vs 圆 15.99%）；中心成核区仅差 3.27 mT，故翻转场相近。",
            ],
        ),
        (
            "03 / 模型范围与物理边界",
            "纯磁性条件分析  ·  不含输运",
            [
                "采用零温、无缺陷、关闭进动的教学模型参数，探讨 QAH 铁磁薄膜磁性基础条件。",
                "本轮不计算电子能带、拓扑陈数或霍尔电导，也不宣称针对特定真实材料完成标定。",
            ],
        ),
    ]
    cw3, gap3 = 3.85, 0.241
    for i, (tag, headline, bullets) in enumerate(cover_cards):
        cx = L + i * (cw3 + gap3)
        cy, ch = 4.02, 2.56
        card(s1, cx, cy, cw3, ch, fill=PANEL if i == 1 else WHITE, line=BORDER)
        rect(s1, cx, cy, cw3, 0.045, INK)
        textbox(s1, cx + 0.20, cy + 0.16, cw3 - 0.40, 0.24, [[(tag, {})]], size=10.0, color=MUTED, bold=True)
        textbox(s1, cx + 0.20, cy + 0.44, cw3 - 0.40, 0.36, [[(headline, {})]], size=13.5, color=INK, bold=True)
        add_bullets(s1, cx + 0.20, cy + 0.88, cw3 - 0.40, 1.56, bullets, size=10.1, space_after=5.0, line_spacing=1.20)

    footer(s1, 1)
    set_note(
        s1,
        "各位老师好，今天汇报“同面积铁磁薄膜的形状退磁效应与准静态翻转”的微磁仿真阶段进展（更新至 11 月 20 日晚）。"
        "目前两套网格主实验已全部完成，12 条逐支验证已完成 10 条（涵盖 2 nm 全部三种形状及 1 nm 方形、圆形），P3 跨网格翻转过程核查也已通过。"
        "此外，我们对“长方形全片平均 Nz 更低、为何翻转场仍与圆/方相近”给出了中心成核区局部退磁场的定量机制解释。",
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

    steps = [
        ("1. 环境与基准", "已完成", True),
        ("2. 三轴均匀退磁", "已完成", True),
        ("3. 零场能量竞争", "已完成", True),
        ("4. 完整磁滞回线", "已完成", True),
        ("5. 翻转区精细验证", "10 / 12 支", False),
        ("6. 跨网格与验收", "P3 完成 / P4 待收尾", False),
    ]
    sw, sgap = 1.79, 0.258
    for i, (st_title, st_stat, done) in enumerate(steps):
        sx = L + i * (sw + sgap)
        sy, sh = 1.48, 0.78
        card(s2, sx, sy, sw, sh, fill=PANEL if done else WHITE, line=INK if done else BORDER, width=1.1 if done else 0.75)
        textbox(s2, sx + 0.08, sy + 0.10, sw - 0.16, 0.30, [[(st_title, {})]], size=10.5, color=INK, bold=True, align=PP_ALIGN.CENTER)
        textbox(s2, sx + 0.08, sy + 0.42, sw - 0.16, 0.24, [[(st_stat, {})]], size=9.2, color=INK if done else MUTED, bold=done, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            textbox(s2, sx + sw, sy + 0.20, sgap, 0.36, [[("→", {})]], size=13.0, color=MUTED, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    q_cards = [
        (
            "问题 1  |  静态退磁效应",
            "仅改变平面轮廓，退磁因子与退磁场分布如何变化？",
            [
                "固定目标面积 40,000 nm² 与厚度 4 nm，对比方形、圆形与 4:1 长方形。",
                "定量比较全片体积平均 N_x、N_y、N_z 及边缘带与核心区局部退磁场差异。",
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
            "问题 3  |  准静态磁滞与成核机制",
            "静态退磁差异是否对应可分辨的剩磁、矫顽场或翻转路径？",
            [
                "由 +0.6 T → −0.6 T → +0.6 T 完整回线提取剩磁 M_r/M_s 与翻转区间。",
                "重放翻转过程并结合核心局部退磁场，揭示实际成核点与扩展路径。",
            ],
        ),
        (
            "问题 4  |  数值可信度检验",
            "观察到的差异能否经受网格、场步、停止阈值与微扰考验？",
            [
                "2 nm 主实验配合 1 nm 细网格复核，场步由 20 mT 加密至 10 / 5 mT。",
                "收紧停止阈值至 0.005 °/ns，并检验反向场微扰幅度 ε 与跨网格轨迹一致性。",
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
        "这一页说明核心研究问题与六步技术路线。前四步主实验已全部完成，第五步逐支精细验证已完成 10/12 支，第六步的跨网格过程核查（P3）也已通过。",
    )

    # ============================================================== Slide 3 ==
    s3 = new_slide(prs)
    slide_chrome(
        s3,
        3,
        "02 / 模型设计与统一协议",
        "控制面积与教学材料参数一致，统一双网格与反向场微扰协议",
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

    card(s3, L, 5.42, 5.85, 0.68, fill=PANEL, line=BORDER)
    textbox(
        s3,
        L + 0.16,
        5.45,
        5.53,
        0.62,
        [[("收敛与迭代预算：", {"bold": True, "color": INK}), ("常规 max|dm/dt| ≤ 0.01 °/ns，严格复核 ≤ 0.005 °/ns；默认 100,000 步，长方形 1 nm ±0.185 T 临界点例外提至 200,000 步（阈值不变）。", {})]],
        size=9.4,
        color=BODY,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.15,
    )

    rx, rw = 6.80, 5.88
    card(s3, rx, 1.44, rw, 4.66, fill=WHITE, line=BORDER)
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
        "这一页介绍模型设计与统一横向微扰协议。需要额外说明的是，长方形 1 nm 的 ±0.185 T 临界点因接近鞍点发生临界慢化，已按例外记录将迭代步上限提高至 200,000 步，停止阈值与物理参数保持完全不变。",
    )

    # ============================================================== Slide 4 ==
    s4 = new_slide(prs)
    slide_chrome(
        s4,
        4,
        "03 / 技术路线与完成度",
        "主实验与 P3 跨网格过程核查完成，翻转区验证已达 10 / 12 支",
        [("阶段状态：", {"bold": True}), ("2 nm 全部、1 nm 方形及圆形（共 10/12 支）与 P3 跨网格过程均已通过；仅剩长方形 1 nm 两支验证按串行队列推进。", {})],
    )

    textbox(s4, L, 1.44, 7.65, 0.28, [[("研究模块完成度清单（截至 2026-11-20 晚间）", {})]], size=11.8, color=INK, bold=True)
    prog_rows = [
        [[("环境与历史基准复核", {})], [("50 项历史检查 + 2 本机算例 + 状态继承", {})], [("已完成", {"bold": True})]],
        [[("三轴固定均匀退磁", {})], [("2 nm (9 组) + 1 nm (9 组)，共 18 组", {})], [("已完成", {"bold": True})]],
        [[("多初态零场弛豫", {})], [("2 nm (24 组) + 1 nm 代表态 (6 组+严格阈值)", {})], [("已完成", {"bold": True})]],
        [[("完整准静态磁滞回线", {})], [("2 nm (3 条/363 点) + 1 nm (3 条/363 点)", {})], [("已完成", {"bold": True})]],
        [[("2 nm 翻转区逐支验证", {})], [("6/6 支：10/5 mT、0.005 °/ns、3 幅度微扰", {})], [("已完成", {"bold": True})]],
        [[("2 nm 翻转过程快照", {})], [("3 形状 −0.20 T 重放，共 385 帧（终态差=0）", {})], [("已完成", {"bold": True})]],
        [[("1 nm 翻转区逐支验证", {})], [("方形 2 支 + 圆形 2 支完成；长方形 b0 5 mT 重算中", {})], [("4/6 支完成（运行中）", {"bold": True})]],
        [[("跨网格过程核查 (P3)", {})], [("2/1 nm ODT 标量轨迹对比 + 局部退磁机制定量分析", {})], [("已完成", {"bold": True})]],
        [[("最终独立数据验收 (P4)", {})], [("待长方形 1 nm 两支跑完后统一审计校验和与终稿", {})], [("待收尾", {"color": MUTED})]],
    ]
    add_booktabs_table(
        s4,
        L,
        1.78,
        7.65,
        4.28,
        [2.15, 3.85, 1.65],
        [[("模块", {})], [("执行范围与体量", {})], [("当前状态", {})]],
        prog_rows,
        header_size=9.8,
        body_size=9.0,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER],
        row_heights=[0.35] + [0.436] * 9,
    )

    rx4, rw4 = 8.55, 4.13
    card(s4, rx4, 1.46, rw4, 1.54, fill=PANEL, line=BORDER)
    rect(s4, rx4, 1.46, 0.055, 1.54, INK)
    textbox(s4, rx4 + 0.18, 1.56, rw4 - 0.30, 0.24, [[("关键体量与最新审计指标", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s4,
        rx4 + 0.18,
        1.86,
        rw4 - 0.30,
        1.08,
        [
            [("正式全回线：", {"bold": True}), ("6 条回线、726 个正式场点", {})],
            [("逐支验证：", {"bold": True}), ("10 / 12 支已完整通过（圆形 1 nm 今日全过）", {})],
            [("已分析目录：", {"bold": True}), ("459 目录、failed_checks = []（含聚合/诊断目录）", {})],
        ],
        size=9.5,
        space_after=3.5,
        line_spacing=1.15,
    )

    card(s4, rx4, 3.14, rw4, 1.56, fill=WHITE, line=BORDER)
    textbox(s4, rx4 + 0.18, 3.24, rw4 - 0.30, 0.24, [[("今日推进与预算预防处理", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s4,
        rx4 + 0.18,
        3.54,
        rw4 - 0.30,
        1.10,
        [
            "圆形 1 nm 下降支（5.02 h）与返回支（4.79 h）已于今日全部通过。",
            "19:47 长方形 −0.185 T 触及 10 万步上限归档后，已为长方形 4 个 ±0.185 T 临界点统一预置 20 万步预算。",
        ],
        size=9.4,
        space_after=4.0,
        line_spacing=1.16,
    )

    card(s4, rx4, 4.84, rw4, 1.24, fill=WHITE, line=BORDER)
    textbox(s4, rx4 + 0.18, 4.94, rw4 - 0.30, 0.24, [[("剩余计算量估计", {})]], size=11.0, color=INK, bold=True)
    textbox(
        s4,
        rx4 + 0.18,
        5.22,
        rw4 - 0.30,
        0.78,
        [[("单支实测均值约 4.88 h（不含慢收敛重算）。当前长方形两支为最后计算队列，近翻转点耗时显著高于尾段，不按场点数线性折算。", {})]],
        size=9.5,
        color=BODY,
        line_spacing=1.18,
    )

    set_note(
        s4,
        "这里按 11 月 20 日晚间最新状态核定完成度：圆形 1 nm 的下降支和返回支今日已全部通过，逐支验证进度推进至 10/12，"
        "同时 P3 跨网格过程对比也已通过。晚上长方形下降支 5 mT 的 -0.185 T 场点在 10 万步上限未收敛，已将其连同后续三个临界点统一预置为 20 万步上限后从前驱重算。",
    )

    # ============================================================== Slide 5 ==
    s5 = new_slide(prs)
    slide_chrome(
        s5,
        5,
        "04 / 静态退磁结果",
        "平面轮廓造成可分辨的静态退磁差异：N_z 呈 圆形 > 方形 > 长方形",
        [("阶段性结论 1：", {"bold": True}), ("固定均匀面外磁化下长方形全片平均退磁能最低；但体积平均 N_i 受边缘占比影响，不能直接等同于中心成核区局部场。", {})],
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
        "第一项明确物理结果是静态退磁差异。1 nm 下面外 Nz 从大到小依次为圆形 0.94429、方形 0.94086、长方形 0.92917，"
        "长方形面内 x、y 差异显著，且全片平均面外退磁能最低。圆形 2 到 1 nm 变化仅 3.27×10⁻⁴，网格收敛达标。",
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
        "第二项发现是零场能量竞争。三种形状下，双畴态虽然把退磁能压低了 3.57 到 8.70 kJ/m³，但在畴壁处付出了 6.93 到 15.81 kJ/m³ 的交换与各向异性能代价，"
        "总能量密度仍比近单畴态高出 3.35 到 7.11 kJ/m³。该差值为驻态差值，不代表翻转能垒。",
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
        hyst_rows.append([
            [(sh_cn, {})],
            [(f"{m2['remanence'][0]:.9f}", {})],
            [(f"{m1['remanence'][0]:.9f}", {})],
            [("[−0.20, −0.18] / [0.18, 0.20] T", {})],
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
        "第三部分是准静态完整磁滞回线。两套网格共 6 条回线全部顺利翻转并对称闭合，撤场剩磁均在 0.9999998 以上，20 mT 粗回线高度重合，翻转落在 [0.18, 0.20] T。",
    )

    # ============================================================== Slide 8 ==
    s8 = new_slide(prs)
    slide_chrome(
        s8,
        8,
        "07 / 翻转区间与精细数值验证",
        "已验证 10 / 12 支均夹逼于 [0.180, 0.185] T，当前尚不支持矫顽场排序",
        [("阶段性结论 4：", {"bold": True}), ("在 2 nm 三形状及 1 nm 方形、圆形共 10 支验证中翻转区间完全重叠；长方形 1 nm 两支正在收尾。", {})],
    )

    textbox(s8, L, 1.44, 7.05, 0.28, [[("逐支加密验证汇总（总进度 10 / 12 支已完整通过）", {})]], size=11.8, color=INK, bold=True)
    verif_rows = [
        [[("方形 (2 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT, 0.005, 3ε 全通过", {})]],
        [[("圆形 (2 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT, 0.005, 3ε 全通过", {})]],
        [[("长方形 (2 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT, 0.005, 3ε 全通过", {})]],
        [[("方形 (1 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT & 0.005 全通过", {})]],
        [[("圆形 (1 nm)", {})], [("[−0.185, −0.180]", {})], [("[+0.180, +0.185]", {})], [("0.1825 T", {"bold": True})], [("10/5 mT & 0.005 全通过", {})]],
        [[("长方形 (1 nm)", {})], [("10 mT [−0.19, −0.18]", {})], [("粗步 [0.18, 0.20]", {})], [("验证中", {"color": MUTED})], [("b0 5 mT 重算中；b1 待排", {})]],
    ]
    add_booktabs_table(
        s8,
        L,
        1.78,
        7.05,
        3.40,
        [1.40, 1.45, 1.35, 0.95, 1.90],
        [[("对象", {})], [("下降支夹逼/T", {})], [("返回支夹逼/T", {})], [("中点估计", {})], [("验证状态", {})]],
        verif_rows,
        header_size=9.2,
        body_size=8.8,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
        row_heights=[0.36] + [0.505] * 6,
    )

    card(s8, L, 5.30, 7.05, 0.78, fill=PANEL, line=BORDER)
    textbox(
        s8,
        L + 0.16,
        5.34,
        6.73,
        0.70,
        [[("今日新增确认：", {"bold": True, "color": INK}), ("圆形 1 nm 下降支（5.02 h）与返回支（4.79 h）的 10 mT、5 mT 及 0.005 °/ns 严格阈值路径均已全部通过，与 2 nm 区间完全一致。", {})]],
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
            [("停止阈值：", {"bold": True}), ("由 0.01 收紧至 0.005 °/ns 未改变已测 10 支的夹逼区间。", {})],
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
            [("待定范围：", {"bold": True}), ("长方形 1 nm 的 5 mT 及严格阈值两支待收尾。", {})],
        ],
        size=9.7,
        space_after=4.5,
        line_spacing=1.18,
    )

    set_note(
        s8,
        "这一页汇报精细验证状态。今天圆形 1 nm 正负两支均已完全通过，使完整通过支路达到 10/12 支，全部落入 [0.180, 0.185] T 区间。"
        "长方形 1 nm 下降支 10 mT 已通过（[-0.190, -0.180] T），5 mT 临界点正在以 20 万步预算重算。",
    )

    # ============================================================== Slide 9 ==
    s9 = new_slide(prs)
    slide_chrome(
        s9,
        9,
        "08 / 定量物理机制（为什么平均 N_z 更低，翻转场仍落入相近区间？）",
        "全片 N_z 差异由边缘带体积占比主导，而中心成核区局部退磁场高度接近",
        [("阶段性结论 5（机制）：", {"bold": True}), ("区分“全片体积平均”与“中心成核局部场”后，长方形较低的 N_z 与三形状相近的翻转场完全物理自洽。", {})],
    )

    textbox(
        s9,
        L,
        1.40,
        CW,
        0.24,
        [[("1 nm 均匀 +z 态空间分区退磁系数 N_z = −H_d,z/M_s 与退磁场 μ₀H_d,z / mT（ℓ_ex = 9.403 nm，B_K = 533.33 mT）", {})]],
        size=10.6,
        color=INK,
        bold=True,
    )
    mech_rows = []
    bk_mT = LOCAL_REV["B_K_T"] * 1000.0
    for sh_key, sh_cn in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        lf = LOCAL_FIELDS[(sh_key, 1)]
        edge_pct = lf["edge"]["cells"] / lf["all"]["cells"] * 100.0
        scale_mT = bk_mT + lf["core"]["B_mT"]
        mech_rows.append([
            [(sh_cn, {})],
            [(f"{lf['all']['N']:.6f} / {lf['all']['B_mT']:.2f}", {})],
            [(f"{lf['point']['N']:.6f} / {lf['point']['B_mT']:.2f}", {})],
            [(f"{lf['core']['N']:.6f} / {lf['core']['B_mT']:.2f}", {"bold": True})],
            [(f"{lf['edge']['N']:.6f} / {lf['edge']['B_mT']:.2f}", {})],
            [(f"{edge_pct:.2f}%", {"bold": sh_key == "rectangle"})],
            [(f"{scale_mT:.2f} mT", {"bold": True})],
        ])
    add_booktabs_table(
        s9,
        L,
        1.70,
        CW,
        1.64,
        [0.85, 2.05, 2.05, 2.05, 2.05, 1.38, 1.603],
        [
            [("形状", {})],
            [("全片平均 N_z / B_d", {})],
            [("中心点 (4 格柱)", {})],
            [("核心区 (r ≤ ℓ_ex)", {})],
            [("边缘带 (≤ ℓ_ex)", {})],
            [("边缘体积占比", {})],
            [("B_K + μ₀H_d,z(core)", {})],
        ],
        mech_rows,
        header_size=9.2,
        body_size=9.0,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
        row_heights=[0.36, 0.42, 0.42, 0.42],
    )

    mw, mh, mgap = 5.88, 2.58, 0.273
    card(s9, L, 3.50, mw, mh, fill=WHITE, line=BORDER)
    rect(s9, L, 3.50, 0.055, mh, INK)
    textbox(s9, L + 0.20, 3.60, mw - 0.36, 0.28, [[("1. 为何长方形全片平均 N_z 明显较低？", {})]], size=11.5, color=INK, bold=True)
    add_bullets(
        s9,
        L + 0.20,
        3.94,
        mw - 0.36,
        2.04,
        [
            [("边缘退磁显著偏弱：", {"bold": True}), ("距侧边 ≤ 1 个交换长度（9.403 nm）的边缘带退磁场仅 −308.4 ~ −309.6 mT（N_z ≈ 0.82），明显弱于中心核心区（≈ −370 mT）。", {})],
            [("周长与边缘占比：", {"bold": True}), ("长方形边缘带体积占比达 21.69%（圆形仅 15.99%），且内部均值亦略低。", {})],
            [("加权复现全片值：", {"bold": True}), ("0.2169×0.81926 + 0.7831×0.95961 ≈ 0.92917，拉低全片平均场（与圆形全片场相差 5.70 mT）。", {})],
        ],
        size=9.8,
        space_after=5.0,
        line_spacing=1.18,
    )

    rx9 = L + mw + mgap
    card(s9, rx9, 3.50, mw, mh, fill=PANEL, line=BORDER)
    rect(s9, rx9, 3.50, 0.055, mh, INK)
    textbox(s9, rx9 + 0.20, 3.60, mw - 0.36, 0.28, [[("2. 为何三者翻转场仍落入同一区间？", {})]], size=11.5, color=INK, bold=True)
    add_bullets(
        s9,
        rx9 + 0.20,
        3.94,
        mw - 0.36,
        2.04,
        [
            [("中心强退磁驱动成核：", {"bold": True}), ("厚度 4 nm ≪ 100 nm 最窄短轴，无缺陷翻转率先在退磁场最强的几何中心失稳，而非弱退磁边缘。", {})],
            [("核心区场差极微：", {"bold": True}), ("核心区（r ≤ ℓ_ex）退磁场均接近 μ₀M_s = 377.0 mT，长方形与圆形仅差 3.27 mT（小于全片均值差与 5 mT 场步）。", {})],
            [("局部轴向尺度：", {"bold": True}), ("B_K + μ₀H_d,z(core) 为 163.04 ~ 166.31 mT（实际失稳含横向退磁响应、交换与空间模式，故落入 180–185 mT）。", {})],
        ],
        size=9.8,
        space_after=5.0,
        line_spacing=1.18,
    )

    set_note(
        s9,
        "这一页是新增的定量物理机制分析，直接从 1 nm 原始静态退磁场文件统计得到。可以看到：边缘一个交换长度（9.403 nm）内退磁场只有大约 -309 mT，而中心核心区高达 -370 mT。"
        "长方形有 21.69% 的体积落在边缘带（圆形只有 15.99%），所以它的全片平均 Nz 被拉低了 5.70 mT；"
        "但因为 4 nm 厚度远小于 100 nm 短轴，中心核心区的退磁场长方形与圆形只相差 3.27 mT，且局部轴向场尺度都在 163 到 166 mT，所以 5 mT 场步下翻转区间重合完全合乎物理。",
    )

    # ============================================================= Slide 10 ==
    s10 = new_slide(prs)
    slide_chrome(
        s10,
        10,
        "09 / 空间成核证据与跨网格过程核查（P3）",
        "2 nm 快照证实中心首次成核，1 nm 与 2 nm 翻转标量轨迹高度一致",
        [("阶段性结论 6（过程）：", {"bold": True}), ("1 nm 与 2 nm 轨迹重合确认细网格下同样经历非均匀成核翻转，无需补算 1 nm 快照；长方形磁矩抵消最强。", {})],
    )

    textbox(s10, L, 1.40, 7.45, 0.24, [[("下降支 b = −0.20 T 两套网格 ODT 轨迹与 2 nm 首次反向范围", {})]], size=10.8, color=INK, bold=True)
    p3_rows = []
    for sh_key, sh_cn in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        t2 = LOCAL_TRACES[(sh_key, 2)]
        t1 = LOCAL_TRACES[(sh_key, 1)]
        fr = FIRST_REV[sh_key]
        if fr["x_min_nm"] == fr["y_min_nm"] and fr["x_max_nm"] == fr["y_max_nm"]:
            span = f"x, y ∈ [{fr['x_min_nm']:+.0f}, {fr['x_max_nm']:+.0f}] nm"
        else:
            span = f"x∈[{fr['x_min_nm']:+.0f},{fr['x_max_nm']:+.0f}], y∈[{fr['y_min_nm']:+.0f},{fr['y_max_nm']:+.0f}]"
        p3_rows.append([
            [(sh_cn, {})],
            [(f"{t2['min_norm']:.4f} / {t1['min_norm']:.4f}", {"bold": True})],
            [(f"{t2['iteration_min_norm']} / {t1['iteration_min_norm']}", {})],
            [(f"{t2['iteration_end']} / {t1['iteration_end']}", {})],
            [(span, {})],
        ])
    add_booktabs_table(
        s10,
        L,
        1.68,
        7.45,
        1.48,
        [0.85, 1.65, 1.55, 1.45, 1.95],
        [
            [("形状", {})],
            [("最小模长 2/1 nm", {})],
            [("极小值步 2/1 nm", {})],
            [("停止步 2/1 nm", {})],
            [("2 nm 首次 m_z<0", {})],
        ],
        p3_rows,
        header_size=9.0,
        body_size=8.8,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER],
        row_heights=[0.34, 0.36, 0.36, 0.36],
    )

    card(s10, 8.28, 1.40, 4.40, 1.76, fill=WHITE, line=BORDER)
    textbox(s10, 8.44, 1.48, 4.08, 0.24, [[("跨网格过程核查结论（P3 通过）", {})]], size=10.5, color=INK, bold=True)
    add_bullets(
        s10,
        8.44,
        1.76,
        4.08,
        1.34,
        [
            [("中心首次成核：", {"bold": True}), ("每 50 步采样首次捕捉到 m_z < 0 均在原点附近，与核心强退磁吻合。", {})],
            [("跨网格一致：", {"bold": True}), ("2/1 nm 最小模长差 ≤ 0.0042，总能量单调不增，无需补算 1 nm 快照。", {})],
            [("非时间尺度：", {"bold": True}), ("横轴为归一化弛豫迭代步，不作物理翻转速度对比。", {})],
        ],
        size=9.3,
        space_after=4.0,
        line_spacing=1.15,
    )

    fw10, fh10 = 5.88, 2.82
    card(s10, L, 3.28, fw10, fh10, fill=WHITE, line=BORDER)
    add_picture_fitted(s10, 10, "reversal_trajectory.png", L + 0.14, 3.35, fw10 - 0.28, 2.38)
    textbox(s10, L + 0.14, 5.76, fw10 - 0.28, 0.28, [[("左图：2 nm −0.20 T 空间演化快照（方/圆中心扩展，长方形中央带推进）", {})]], size=9.0, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    rx10 = L + fw10 + 0.273
    card(s10, rx10, 3.28, fw10, fh10, fill=WHITE, line=BORDER)
    add_picture_fitted(s10, 10, "cross_mesh_reversal_odt.png", rx10 + 0.14, 3.35, fw10 - 0.28, 2.38)
    textbox(s10, rx10 + 0.14, 5.76, fw10 - 0.28, 0.28, [[("右图：2 nm 与 1 nm 同场点标量轨迹对比（最小模长与能量下降重合）", {})]], size=9.0, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    set_note(
        s10,
        "这一页展示中心成核的直接空间证据和 P3 跨网格对照。在 2 nm −0.20 T 重放中，首次出现 mz < 0 的区域全部位于几何中心周围，"
        "方形和圆形在 ±21~23 nm 内，长方形在 ±7×±3 nm 内。同时右图对比了 2 nm 和 1 nm 的 ODT 标量轨迹，两套网格的最小平均模长仅差千分之几，"
        "能量完全单调下降，确认 1 nm 同样遵循非均匀成核翻转，因此 P3 无需再补跑耗时的 1 nm 快照。",
    )

    # ============================================================= Slide 11 ==
    s11 = new_slide(prs)
    slide_chrome(
        s11,
        11,
        "10 / 数值可信度、总结与收尾里程碑",
        "主线结论与物理机制已闭环，待长方形 1 nm 跑完即执行 P4 独立验收",
        [("汇报小结：", {"bold": True}), ("静态退磁差异、零场竞争、中心局域成核机制及跨网格过程已获充分验证；待最后 2 支长方形 1 nm 完成后闭合验收。", {})],
    )

    card(s11, L, 1.46, 5.75, 1.88, fill=WHITE, line=BORDER)
    rect(s11, L, 1.46, 0.055, 1.88, INK)
    textbox(s11, L + 0.18, 1.56, 5.40, 0.24, [[("数值可信度与过程审计保障", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s11,
        L + 0.18,
        1.86,
        5.40,
        1.42,
        [
            [("驻点隔离：", {"bold": True}), ("无扰动诊断路径与正式微扰数据完全隔离。", {})],
            [("全链路追溯：", {"bold": True}), ("每算例保存输入 MIF、前驱 SHA256 与 ODT 独立 RHS 校验。", {})],
            [("例外可控：", {"bold": True}), ("中断或超限点全部归档重算；459 目录检查零失败，仅长方形 4 个临界点设 20 万步例外预算。", {})],
        ],
        size=9.5,
        space_after=3.5,
        line_spacing=1.15,
    )

    card(s11, L, 3.48, 5.75, 2.60, fill=PANEL, line=BORDER)
    rect(s11, L, 3.48, 0.055, 2.60, INK)
    textbox(s11, L + 0.18, 3.58, 5.40, 0.24, [[("本阶段已确立的四条明确成果", {})]], size=11.0, color=INK, bold=True)
    textbox(
        s11,
        L + 0.18,
        3.90,
        5.40,
        2.10,
        [
            [("1. 静态退磁差异：", {"bold": True, "color": INK}), ("1 nm 全片 N_z 为圆 (0.9443) > 方 (0.9409) > 长方形 (0.9292)，跨网格误差 < 10⁻³。", {})],
            [("2. 零场能量竞争：", {"bold": True, "color": INK}), ("双畴退磁收益不敌畴壁交换/各向异性代价，近单畴态能量更低。", {})],
            [("3. 磁滞与验证：", {"bold": True, "color": INK}), ("剩磁近饱和；10/12 支已验证均夹逼于 [0.180, 0.185] T（中点 0.1825 T）。", {})],
            [("4. 局部成核机制：", {"bold": True, "color": INK}), ("全片 N_z 差异源于边缘带占比（21.69% vs 15.99%）；中心区仅差 3.27 mT，且 1/2 nm 非均匀翻转轨迹一致。", {})],
        ],
        size=9.5,
        color=BODY,
        space_after=4.5,
        line_spacing=1.16,
    )

    rx11, rw11 = 6.65, 6.03
    textbox(s11, rx11, 1.44, rw11, 0.28, [[("最新任务状态与收尾路线（P2 – P4）", {})]], size=11.8, color=INK, bold=True)
    todo_rows = [
        [[("P2-A\n(已完成)", {"bold": True})], [("圆形 1 nm 下降支与返回支全部局部验证", {})], [("10/5 mT 与 0.005 °/ns 全部通过（10/12 支）", {})]],
        [[("P3\n(已完成)", {"bold": True})], [("1/2 nm 跨网格翻转轨迹与局部成核定量解释", {})], [("标量轨迹高度重合，机制报告已写就，无需补快照", {})]],
        [[("P2-B\n(进行中)", {"bold": True})], [("长方形 1 nm 下降支 5 mT/严格阈值 + 返回支", {})], [("4 个 ±0.185 T 点已预置 20 万步上限；补齐 12/12", {})]],
        [[("P2-C\n(条件)", {})], [("仅既定容差不满足时补 2.5 mT 或微扰复核", {})], [("不忽略超差项，不无条件扩大扫描", {})]],
        [[("P4\n(待收尾)", {"bold": True})], [("独立原始数据验收、校验和审计与终稿冻结", {})], [("12/12 集齐后清零待办，更新终版图表", {})]],
    ]
    add_booktabs_table(
        s11,
        rx11,
        1.78,
        rw11,
        4.30,
        [0.98, 2.45, 2.60],
        [[("阶段", {})], [("工作内容", {})], [("进展与完成标准", {})]],
        todo_rows,
        header_size=9.5,
        body_size=9.0,
        col_aligns=[PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT],
        row_heights=[0.36, 0.78, 0.78, 0.80, 0.78, 0.80],
    )

    set_note(
        s11,
        "最后总结收尾节点。目前数值质量体系和核心机制分析均已完备，P2-A 圆形 1 nm 和 P3 跨网格核查都已经完成并通过。"
        "现在只需要等待长方形 1 nm 最后两条支路跑完（因为已经预置 20 万步预算，预计可平滑推进），随后执行 P4 独立数据验收并替换最后两支的数据即可。谢谢各位老师！",
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
