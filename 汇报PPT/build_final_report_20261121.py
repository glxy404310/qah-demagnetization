r"""Build the final 10+2 page minimalist white-and-black group-meeting PPTX (2026-11-21, 12/12 verified).

Run with the Python interpreter that has python-pptx & Pillow installed:
    C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe 汇报PPT\build_final_report_20261121.py

Outputs:
    1. 汇报PPT/同面积薄膜形状退磁与翻转_最终汇报_20261121.pptx
    2. refine-logs/GEMINI_FINAL_REPORT_PACKAGE_20261121_v2/同面积薄膜形状退磁与翻转_最终汇报_20261121.pptx
"""
from __future__ import annotations

import csv
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
PKG_DIR = ROOT / "refine-logs" / "GEMINI_FINAL_REPORT_PACKAGE_20261121_v2"
EVIDENCE_DIR = PKG_DIR / "evidence"
FIG_DIR = PKG_DIR / "figures"

OUT_MAIN = Path(__file__).resolve().parent / "同面积薄膜形状退磁与翻转_最终汇报_20261121.pptx"
OUT_COPY = PKG_DIR / "同面积薄膜形状退磁与翻转_最终汇报_20261121.pptx"

# ----------------------------------------------------------------- palette ----
WHITE = "FFFFFF"
INK = "111111"        # Pure dark black for titles, key numbers, primary rules
BODY = "222222"       # Dark neutral text
MUTED = "555555"      # Captions, kickers, page numbers
PANEL = "F6F6F6"      # Subtle neutral gray for callouts & table headers
PANEL_DARK = "EAEAEA" # Slightly stronger neutral tint for highlight rows / bars
TABLE_ALT = "FAFAFA"  # Faint row striping
BORDER = "D0D0D0"     # Thin neutral borders
RULE_LIGHT = "E2E2E2"

EA = "Microsoft YaHei"
LATIN = "Segoe UI"

W, H = 13.333, 7.5
L, R = 0.65, 0.65
CW = W - L - R  # 12.033 in
MAIN_SLIDES = 10
TOTAL_SLIDES = 12  # 10 main + 2 backup

# --------------------------------------------------------- verified evidence --
RESULTS = json.loads((EVIDENCE_DIR / "results.json").read_text(encoding="utf-8"))
VERIF = json.loads((EVIDENCE_DIR / "verification_details.json").read_text(encoding="utf-8"))
LOCAL_REV = json.loads((EVIDENCE_DIR / "local_reversal.json").read_text(encoding="utf-8"))
FINAL_AUDIT = json.loads((EVIDENCE_DIR / "final_audit.json").read_text(encoding="utf-8"))

with (EVIDENCE_DIR / "coercivity_refined.csv").open(encoding="utf-8-sig", newline="") as f:
    COERC_CSV = list(csv.DictReader(f))
with (EVIDENCE_DIR / "demag_factors.csv").open(encoding="utf-8-sig", newline="") as f:
    DEMAG_CSV = list(csv.DictReader(f))

# Strict consistency assertions against final verified evidence
assert RESULTS["completed_runs"] == 488
assert RESULTS["failed_checks"] == []
assert RESULTS["pending"] == []
assert RESULTS["numerical_acceptance_complete"] is True
assert len(RESULTS["checks"]) == 82 and all(RESULTS["checks"].values())
assert len(VERIF) == 12
assert len(COERC_CSV) == 6
assert len(DEMAG_CSV) == 18
assert len(FINAL_AUDIT["refined_reversal"]) == 24

METRICS = {(m["shape"], m["cell_nm"]): m for m in RESULTS["metrics"]}
DOMAIN_COMP = {d["shape"]: d for d in RESULTS["domain_energy_comparison"]}
TRAJ = {t["shape"]: t for t in RESULTS["reversal_trajectories"]}
LOCAL_FIELDS = {(f["shape"], f["cell_nm"]): f for f in LOCAL_REV["fields"]}
LOCAL_TRACES = {(t["shape"], t["cell_nm"]): t for t in LOCAL_REV["traces"]}
FIRST_REV = {f["shape"]: f for f in LOCAL_REV["first_reverse"]}
DEMAG = {(r["shape"], int(r["cell_nm"]), r["axis"]): float(r["N_field"]) for r in DEMAG_CSV}
DEMAG_AREA = {(r["shape"], int(r["cell_nm"])): int(r["area_nm2"]) for r in DEMAG_CSV}
REFINED_REV = {(r["shape"], r["cell_nm"], r["branch"], r["stop"]): r for r in FINAL_AUDIT["refined_reversal"]}

# Spot-check key headline numbers from prompt & evidence
assert abs(DEMAG[("circle", 1, "z")] - 0.944291) < 1e-6
assert abs(DEMAG[("square", 1, "z")] - 0.940862) < 1e-6
assert abs(DEMAG[("rectangle", 1, "z")] - 0.929169) < 1e-6
assert abs(LOCAL_REV["exchange_length_nm"] - 9.40316) < 1e-3
assert abs(LOCAL_REV["B_K_T"] * 1000.0 - 533.333) < 1e-2
assert abs(LOCAL_FIELDS[("square", 1)]["core"]["B_mT"] - (-370.186)) < 0.002
assert abs(LOCAL_FIELDS[("circle", 1)]["core"]["B_mT"] - (-370.294)) < 0.002
assert abs(LOCAL_FIELDS[("rectangle", 1)]["core"]["B_mT"] - (-367.020)) < 0.002
assert abs(abs(LOCAL_FIELDS[("rectangle", 1)]["all"]["B_mT"] - LOCAL_FIELDS[("circle", 1)]["all"]["B_mT"]) - 5.701) < 0.01
assert abs(abs(LOCAL_FIELDS[("rectangle", 1)]["core"]["B_mT"] - LOCAL_FIELDS[("circle", 1)]["core"]["B_mT"]) - 3.274) < 0.01
assert abs(REFINED_REV[("rectangle", 2, 0, 0.01)]["min_norm"] - 0.3392) < 1e-3
assert abs(REFINED_REV[("rectangle", 1, 0, 0.01)]["min_norm"] - 0.3380) < 1e-3
for v in VERIF:
    b_abs = sorted([abs(v["bracket_T"][0]), abs(v["bracket_T"][1])])
    t_abs = sorted([abs(v["tight_bracket_T"][0]), abs(v["tight_bracket_T"][1])])
    assert b_abs == [0.18, 0.185] and t_abs == [0.18, 0.185]

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
    header_size: float = 9.5,
    body_size: float = 9.2,
    col_aligns: list | None = None,
    row_heights: list[float] | None = None,
    highlight_rows: set[int] | None = None,
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
    highlight_rows = highlight_rows or set()

    def fill_cell(cell, spec, sz: float, col_hex: str, bold: bool, align, bg_hex: str):
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(bg_hex)
        cell.margin_left = Inches(0.065)
        cell.margin_right = Inches(0.065)
        cell.margin_top = Inches(0.025)
        cell.margin_bottom = Inches(0.025)
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
        if r_idx in highlight_rows:
            bg = PANEL_DARK
        else:
            bg = WHITE if r_idx % 2 == 0 else TABLE_ALT
        is_last = r_idx == len(rows) - 1
        for c_idx, cell_spec in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            bold_col = (c_idx == 0) or (r_idx in highlight_rows)
            fill_cell(cell, cell_spec, body_size, INK if r_idx in highlight_rows else BODY, bold_col, col_aligns[c_idx], bg)
            _set_cell_border(cell, "T", INK if r_idx in highlight_rows else None, 0.8 if r_idx in highlight_rows else 0.5)
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


def footer(slide, page_label: str):
    textbox(
        slide,
        L,
        6.98,
        9.4,
        0.26,
        [[("2026-11-21 最终验收版（12/12 支通过）  |  OOMMF 2.0b0 微磁学模拟", {})]],
        size=9.0,
        color=MUTED,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    textbox(
        slide,
        W - R - 1.5,
        6.98,
        1.5,
        0.26,
        [[(page_label, {})]],
        size=9.5,
        color=MUTED,
        align=PP_ALIGN.RIGHT,
        anchor=MSO_ANCHOR.MIDDLE,
    )


def slide_chrome(slide, page_label: str, kicker: str, heading: str, conclusion=None):
    textbox(slide, L, 0.36, 9.8, 0.24, [[(kicker, {})]], size=10.5, color=MUTED, bold=True)
    textbox(slide, L, 0.62, CW, 0.54, [[(heading, {})]], size=21.5, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    rect(slide, L, 1.24, CW, 0.015, BORDER)
    rect(slide, L, 1.23, 1.15, 0.032, INK)

    if conclusion is not None:
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
            size=11.2,
            color=INK,
            anchor=MSO_ANCHOR.MIDDLE,
            line_spacing=1.15,
        )

    footer(slide, page_label)


def add_bullets(slide, x: float, y: float, w: float, h: float, items: list, size: float = 10.5, space_after: float = 5.5, line_spacing: float = 1.20):
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
    prs.core_properties.title = "同面积薄膜的形状怎样影响退磁场与磁化翻转？"
    prs.core_properties.subject = "课题组组会汇报（2026-11-21，12/12 支最终验收通过）"
    prs.core_properties.author = "孙煜凡、韦中天"

    # ============================================================== Slide 1 ==
    # Cover + Opening Paradox (put the two observations side-by-side up front!)
    s1 = new_slide(prs)
    rect(s1, L, 0.78, 0.075, 2.25, INK)
    textbox(s1, 0.92, 0.78, 11.4, 0.28, [[("课题组组会汇报  ·  微磁学仿真最终验收版（12 / 12 支通过）", {"spc": 1.0})]], size=11.0, color=MUTED, bold=True)
    textbox(
        s1,
        0.92,
        1.14,
        11.6,
        0.86,
        [[("同面积薄膜的形状怎样影响退磁场与磁化翻转？", {})]],
        size=30.0,
        color=INK,
        bold=True,
        line_spacing=1.10,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    textbox(
        s1,
        0.92,
        2.06,
        11.5,
        0.42,
        [[("从全片平均退磁因子到中心局部成核：方形、圆形与长方形的 OOMMF 对比", {})]],
        size=16.5,
        color=BODY,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    textbox(
        s1,
        0.92,
        2.62,
        11.5,
        0.34,
        [[("汇报人：孙煜凡、韦中天    |    2026 年 11 月 21 日    |    OOMMF 2.0b0（2 nm & 1 nm）", {})]],
        size=11.0,
        color=MUTED,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    rect(s1, L, 3.24, CW, 0.015, BORDER)

    # Opening juxtaposition: Observation 1 vs Observation 2
    ow, oh, ogap = 5.88, 2.05, 0.273
    card(s1, L, 3.44, ow, oh, fill=WHITE, line=BORDER)
    rect(s1, L, 3.44, ow, 0.045, INK)
    textbox(s1, L + 0.22, 3.60, ow - 0.44, 0.26, [[("观察 1  |  全片静态退磁因子清晰分化（1 nm 网格）", {})]], size=10.5, color=MUTED, bold=True)
    textbox(s1, L + 0.22, 3.92, ow - 0.44, 0.44, [[("N_z：圆形 0.9443  >  方形 0.9409  >  长方形 0.9292", {})]], size=14.5, color=INK, bold=True)
    add_bullets(
        s1,
        L + 0.22,
        4.44,
        ow - 0.44,
        0.96,
        [
            "固定均匀 +z 磁化时，长方形全片平均退磁场比圆形弱 5.70 mT。",
            "直觉疑问：平均面外退磁能最低的长方形，翻转场是否应该最高？",
        ],
        size=10.2,
        space_after=4.0,
    )

    rx1 = L + ow + ogap
    card(s1, rx1, 3.44, ow, oh, fill=PANEL, line=BORDER)
    rect(s1, rx1, 3.44, ow, 0.045, INK)
    textbox(s1, rx1 + 0.22, 3.60, ow - 0.44, 0.26, [[("观察 2  |  准静态翻转场全部落在同一区间（12 / 12 支）", {})]], size=10.5, color=MUTED, bold=True)
    textbox(s1, rx1 + 0.22, 3.92, ow - 0.44, 0.44, [[("全部 12 条支路幅值均夹逼于 180–185 mT", {})]], size=14.5, color=INK, bold=True)
    add_bullets(
        s1,
        rx1 + 0.22,
        4.44,
        ow - 0.44,
        0.96,
        [
            "3 形状 × 2 网格 × 下降/返回两支全部通过 5 mT 及双阈值验收。",
            "区间中点均为 182.5 mT；在 5 mT 分辨率下无法按形状排序。",
        ],
        size=10.2,
        space_after=4.0,
    )

    # Central Question Banner
    rect(s1, L, 5.72, CW, 1.02, PANEL_DARK, line=INK, width=0.8)
    rect(s1, L, 5.72, 0.08, 1.02, INK)
    textbox(
        s1,
        L + 0.26,
        5.78,
        CW - 0.44,
        0.90,
        [
            [("整场汇报核心问题：", {"bold": True, "size": 12.5, "color": INK}), ("长方形全片平均 N_z 最低，为什么三种形状的准静态翻转场仍落在同一测得区间？", {"bold": True, "size": 13.0, "color": INK})],
            [("主线拆解：① 全片平均为何不同（边缘带占比）  →  ② 转向中心局部场（核心区仅差 3.27 mT）  →  ③ 翻转场与非均匀过程双重证据收束", {"size": 10.2, "color": BODY})],
        ],
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.28,
    )

    footer(s1, "1 / 10")
    set_note(
        s1,
        "各位老师好，今天汇报“同面积薄膜的形状怎样影响退磁场与磁化翻转”，这是全部 12 条支路通过最终验收后的完整结果。"
        "我一开场就把两组最核心、也最值得追问的观察并排放在这里：左边是 1 nm 网格下的静态退磁因子，长方形的全片平均 Nz 明显最低，平均退磁场比圆形弱 5.70 mT；"
        "按直觉，长方形似乎更抗翻转。但看右边，三种形状在两套网格、正负两支共 12 条支路上，准静态翻转场全部落在 180 到 185 mT 这同一个区间，5 mT 分辨率下排不出先后。"
        "接下来 12 分钟，我就围绕“这两件事为什么并不矛盾”展开：先看全片平均为什么拉开差距，再把镜头切到真正起作用的中心局部场，最后用 12 支翻转场数据和空间/标量翻转过程两类独立证据把逻辑收拢。",
    )

    # ============================================================== Slide 2 ==
    # Model setup & fair comparison protocol
    s2 = new_slide(prs)
    slide_chrome(
        s2,
        "2 / 10",
        "01 / 模型与扫场协议",
        "控制面积、厚度与微扰规则一致，建立三形状双网格的公平基准",
        [("模型范围：", {"bold": True}), ("教学模型参数（零温、无缺陷、关闭进动），用于纯磁性条件对比，不代表真实 QAH 材料标定或电子输运验证。", {})],
    )

    textbox(s2, L, 1.44, 5.95, 0.28, [[("几何模型与固定物理参数", {})]], size=11.8, color=INK, bold=True)
    param_rows = [
        [[("方形", {})], [("200 × 200 × 4 nm（面积 40,000 nm²）", {})]],
        [[("圆形", {})], [("名义半径 112.838 nm（1 nm: 40,000 nm²；2 nm: 39,936 nm², −0.16%）", {})]],
        [[("长方形 (4:1)", {})], [("400 × 100 × 4 nm，长轴沿 x（面积 40,000 nm²）", {})]],
        [[("材料参数", {})], [("M_s = 3×10⁵ A/m；A = 5×10⁻¹² J/m；K_u = 8×10⁴ J/m³（易轴 z）", {})]],
        [[("特征尺度", {})], [("交换长度 ℓ_ex = √[2A/(μ₀M_s²)] = 9.403 nm；B_K = 2K_u/M_s = 533.33 mT", {})]],
        [[("能量与条件", {})], [("交换 + 单轴各向异性 + 退磁 + Zeeman；零温、开放边界、无缺陷/DMI", {})]],
        [[("求解与网格", {})], [("OOMMF 2.0b0；α = 0.5 关闭进动；主实验 2×2×2 nm，复核 1×1×1 nm", {})]],
    ]
    add_booktabs_table(
        s2,
        L,
        1.78,
        5.95,
        4.26,
        [1.35, 4.60],
        [[("项目", {})], [("固定设置", {})]],
        param_rows,
        header_size=9.8,
        body_size=9.2,
        row_heights=[0.36] + [0.555] * 7,
    )

    rx2, rw2 = 6.85, 5.83
    card(s2, rx2, 1.46, rw2, 2.02, fill=WHITE, line=BORDER)
    rect(s2, rx2, 1.46, 0.055, 2.02, INK)
    textbox(s2, rx2 + 0.20, 1.56, rw2 - 0.36, 0.26, [[("扫场与收敛验收协议", {})]], size=11.5, color=INK, bold=True)
    add_bullets(
        s2,
        rx2 + 0.20,
        1.90,
        rw2 - 0.36,
        1.48,
        [
            [("完整磁滞：", {"bold": True}), ("b = μ₀H_ext 从 +0.6 T → −0.6 T → +0.6 T，粗步 20 mT（每回线 121 点）。", {})],
            [("局部加密：", {"bold": True}), ("翻转区重放 10 mT、5 mT；仅当预设容差不满足时才继续到 2.5 mT。", {})],
            [("双停止阈值：", {"bold": True}), ("常规 max|dm/dt| ≤ 0.01 °/ns；严格复核 ≤ 0.005 °/ns。", {})],
        ],
        size=9.8,
        space_after=4.5,
    )

    card(s2, rx2, 3.64, rw2, 2.40, fill=PANEL, line=BORDER)
    rect(s2, rx2, 3.64, 0.055, 2.40, INK)
    textbox(s2, rx2 + 0.20, 3.74, rw2 - 0.36, 0.26, [[("统一反向场横向微扰协议（破除零力矩驻点）", {})]], size=11.5, color=INK, bold=True)
    add_bullets(
        s2,
        rx2 + 0.20,
        4.08,
        rw2 - 0.36,
        1.86,
        [
            [("触发规则：", {"bold": True}), ("仅在外场与上一收敛态平均 m_z 反向的场点，向继承磁化加 (ε, 0.37ε, 0) 后归一化（默认 ε = 10⁻³）。", {})],
            [("幅度检验：", {"bold": True}), ("仅 2 nm 网格在 180/185 mT 端点完成 ε = 10⁻⁴、10⁻³、10⁻² 三幅度校验；1 nm 采用默认 ε = 10⁻³。", {})],
            [("物理界定：", {"bold": True}), ("属于确定性数值稳定性协议，不是热噪声；原无扰动回线保留作驻点诊断。", {})],
        ],
        size=9.7,
        space_after=4.5,
    )

    set_note(
        s2,
        "在进正文结果前，先快速交代比较基准。左表是固定的几何和材料参数：三种形状目标面积都是 40,000 nm²、厚度 4 nm，唯一变量是平面轮廓。"
        "这里请记住两个后面会反复用到的特征尺度：交换长度 ℓ_ex 是 9.403 nm，单轴各向异性场 B_K 是 533.33 mT。"
        "右边是统一的扫场和数值协议：全回线按 20 mT 扫，翻转区加密到 10 和 5 mT，并用 0.01 和 0.005 °/ns 两档停止阈值校验。"
        "因为零温无缺陷轴对称模型在反向场下容易卡在零力矩驻点，我们在每个反向场点对继承磁化施加统一微扰 ε = 10⁻³，并在 2 nm 验证了跨两个数量级的微扰不变性。下面直接进入主线第一步。",
    )

    # ============================================================== Slide 3 ==
    # Mainline Step 1: Why whole-film average Nz differs
    s3 = new_slide(prs)
    slide_chrome(
        s3,
        "3 / 10",
        "02 / 主线一：全片平均退磁因子为何不同",
        "弱退磁边缘带占比与内部场强差异，共同拉低了长方形的全片平均 N_z",
        [("主线一步小结：", {"bold": True}), ("1 nm 下全片 N_z 为圆 0.944291 > 方 0.940862 > 长方形 0.929169；边缘带占比高（21.69% 对 15.99%）是拉低长方形均值的关键因素。", {})],
    )

    # Left: demag_comparison.png (explicitly labeled 2 nm!)
    fx3, fw3 = L, 6.28
    card(s3, fx3, 1.46, fw3, 4.62, fill=WHITE, line=BORDER)
    add_picture_fitted(s3, 3, "demag_comparison.png", fx3 + 0.12, 1.54, fw3 - 0.24, 3.68)
    textbox(
        s3,
        fx3 + 0.16,
        5.32,
        fw3 - 0.32,
        0.68,
        [[("图源：demag_comparison.png（", {"bold": True}), ("仅 2 nm 网格", {"bold": True, "color": INK}), ("，固定 +z 均匀磁化，底层面外退磁场 μ", {}), sub("0"), ("H", {}), sub("d,z"), (" / T 及中心线剖面）。可见边缘退磁场明显弱于内部平台。", {})]],
        size=9.2,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.18,
    )

    # Right: 1 nm whole-film Nz + edge volume fraction analysis
    rx3, rw3 = 7.16, 5.52
    textbox(s3, rx3, 1.44, rw3, 0.26, [[("1 nm 网格全片平均 N_z 与边缘带（距边界 ≤ 9.403 nm）统计", {})]], size=10.8, color=INK, bold=True)

    edge_rows = []
    for sh_key, sh_cn in [("circle", "圆形"), ("square", "方形"), ("rectangle", "长方形")]:
        lf = LOCAL_FIELDS[(sh_key, 1)]
        edge_pct = lf["edge"]["cells"] / lf["all"]["cells"] * 100.0
        edge_rows.append([
            [(sh_cn, {})],
            [(f"{DEMAG[(sh_key, 1, 'z')]:.6f}", {"bold": True})],
            [(f"{lf['edge']['N']:.5f}", {})],
            [(f"{lf['interior']['N']:.5f}", {})],
            [(f"{edge_pct:.2f}%", {"bold": sh_key == "rectangle"})],
        ])
    add_booktabs_table(
        s3,
        rx3,
        1.76,
        rw3,
        1.64,
        [0.85, 1.15, 1.15, 1.15, 1.22],
        [
            [("形状", {})],
            [("全片 N_z", {})],
            [("边缘带 N_z", {})],
            [("其余内部 N_z", {})],
            [("边缘体积占比", {})],
        ],
        edge_rows,
        header_size=9.0,
        body_size=8.9,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
        row_heights=[0.36, 0.42, 0.42, 0.42],
    )

    card(s3, rx3, 3.56, rw3, 2.52, fill=PANEL, line=BORDER)
    rect(s3, rx3, 3.56, 0.055, 2.52, INK)
    textbox(s3, rx3 + 0.18, 3.66, rw3 - 0.32, 0.24, [[("全片均值拉开差距的定量分解（1 nm）", {})]], size=10.8, color=INK, bold=True)
    add_bullets(
        s3,
        rx3 + 0.18,
        3.96,
        rw3 - 0.32,
        2.04,
        [
            [("边缘退磁显著偏弱：", {"bold": True}), ("距侧边 ≤ 1 个交换长度（9.403 nm）的边缘带等效 N_z 仅约 0.82（−308.4 ~ −309.6 mT）。", {})],
            [("长方形边缘占比最高：", {"bold": True}), ("4:1 周长效应使长方形 21.69% 体积处于边缘带，显著高于圆形的 15.99%。", {})],
            [("分区加权复现：", {"bold": True}), ("长方形 0.2169×0.81926 + 0.7831×0.95961 ≈ 0.92917；圆形 0.1599×0.82132 + 0.8401×0.96770 ≈ 0.94429。", {})],
            [("网格收敛：", {"bold": True}), ("圆形 2→1 nm 的 N_z 仅变化 0.000327（< 0.001），面内长方形 N_x = 0.013690 < N_y = 0.057141。", {})],
        ],
        size=9.2,
        space_after=4.0,
        line_spacing=1.16,
    )

    set_note(
        s3,
        "先看第一步：为什么全片平均退磁因子会不同？左边这张图是 2 nm 网格下固定 +z 磁化时的底层面外退磁场分布和中心线剖面。"
        "请大家看下排三条剖面线：三种形状在中间都是一段很平的深谷，大约 −0.37 T；一靠近侧边界，退磁场就迅速变弱。"
        "再看右边 1 nm 网格的分区统计：我们以一个交换长度 9.403 nm 划出边缘带。边缘带的局部等效 Nz 只有 0.82 左右，比内部低很多。"
        "长方形是 4:1 的细长条，周长最长，有 21.69% 的磁性体积落在边缘带，而圆形只有 15.99%，再加上长方形内部均值也略低，一加权就把全片平均 Nz 拉到了 0.929169。"
        "但是请注意：这只是全片平均。真正触发翻转的地方，并不在边缘，而在中间。接下来我们看全场最关键的一页。",
    )

    # ============================================================== Slide 4 ==
    # Mainline Step 2: MOST IMPORTANT SLIDE — Whole-film average vs Center local field
    s4 = new_slide(prs)
    slide_chrome(
        s4,
        "4 / 10",
        "03 / 主线二：从全片平均转到中心局部场（核心机制页）",
        "长方形与圆形全片平均退磁场差 5.70 mT，但中心核心区仅差 3.27 mT",
        [("机制定位：", {"bold": True}), ("中心局部场尺度相近是与数据相容的物理解释；不可用 B", {}), sub("K"), (" + μ", {}), sub("0"), ("H", {}), sub("d,z"), (" 直接预测翻转场，也不把“3.27 mT < 5 mT”当成因果证明。", {})],
    )

    textbox(
        s4,
        L,
        1.40,
        CW,
        0.24,
        [[("1 nm 网格固定 +z 磁化对比（μ", {}), sub("0"), ("H", {}), sub("d,z"), (" 负号表示与 +z 磁化方向相反的退磁场；核心区半径 ℓ", {}), sub("ex"), (" = 9.403 nm，沿 4 nm 厚度平均）", {})]],
        size=10.3,
        color=INK,
        bold=True,
    )

    comp_rows = []
    bk_mT = LOCAL_REV["B_K_T"] * 1000.0
    for sh_key, sh_cn in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        lf = LOCAL_FIELDS[(sh_key, 1)]
        scale_mT = bk_mT + lf["core"]["B_mT"]
        comp_rows.append([
            [(sh_cn, {})],
            [(f"{lf['all']['B_mT']:.3f}", {})],
            [(f"{lf['all']['N']:.6f}", {})],
            [(f"{lf['core']['B_mT']:.3f}", {"bold": True})],
            [(f"{lf['core']['N']:.6f}", {"bold": True})],
            [(f"{lf['point']['B_mT']:.3f}", {})],
            [(f"{scale_mT:.2f}", {"bold": True})],
        ])
    diff_all = abs(LOCAL_FIELDS[("rectangle", 1)]["all"]["B_mT"] - LOCAL_FIELDS[("circle", 1)]["all"]["B_mT"])
    diff_core = abs(LOCAL_FIELDS[("rectangle", 1)]["core"]["B_mT"] - LOCAL_FIELDS[("circle", 1)]["core"]["B_mT"])
    comp_rows.append([
        [("长方形 vs 圆形 最大差", {})],
        [(f"{diff_all:.2f} mT", {"bold": True})],
        [("0.015122", {})],
        [(f"{diff_core:.2f} mT", {"bold": True})],
        [("0.008684", {})],
        [("3.21 mT", {})],
        [(f"{diff_core:.2f} mT", {"bold": True})],
    ])

    add_booktabs_table(
        s4,
        L,
        1.68,
        CW,
        1.94,
        [2.05, 1.65, 1.45, 1.85, 1.45, 1.68, 1.903],
        [
            [("形状（1 nm 网格）", {})],
            [("全片 μ", {}), sub("0"), ("H", {}), sub("d,z"), (" (mT)", {})],
            [("全片 N", {}), sub("z")],
            [("核心 μ", {}), sub("0"), ("H", {}), sub("d,z"), (" (mT)", {})],
            [("核心等效 N", {}), sub("z")],
            [("中心点场 (mT)", {})],
            [("B", {}), sub("K"), (" + μ", {}), sub("0"), ("H", {}), sub("d,z"), ("(core)", {})],
        ],
        comp_rows,
        header_size=9.1,
        body_size=9.1,
        col_aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.RIGHT] * 6,
        row_heights=[0.36, 0.39, 0.39, 0.39, 0.41],
        highlight_rows={3},
    )

    # Bottom Left: Clean minimalist visual comparison bar (5.70 mT vs 3.27 mT + B_K scale)
    lw4, lh4 = 5.45, 2.34
    card(s4, L, 3.76, lw4, lh4, fill=WHITE, line=BORDER)
    textbox(s4, L + 0.20, 3.86, lw4 - 0.40, 0.26, [[("空间尺度对比：长方形相对圆形的退磁场强差（1 nm）", {})]], size=10.5, color=INK, bold=True)

    # Bar 1: Whole-film diff 5.70 mT
    bx = L + 0.22
    max_bar_w = 2.65
    textbox(s4, bx, 4.24, 1.35, 0.32, [[("全片平均差", {"bold": True})]], size=10.0, color=BODY, anchor=MSO_ANCHOR.MIDDLE)
    rect(s4, bx + 1.38, 4.30, max_bar_w, 0.24, PANEL, line=BORDER, width=0.5)
    rect(s4, bx + 1.38, 4.30, max_bar_w * (5.70 / 6.0), 0.24, INK)
    textbox(s4, bx + 1.38 + max_bar_w + 0.12, 4.24, 0.90, 0.32, [[("5.70 mT", {"bold": True})]], size=10.5, color=INK, anchor=MSO_ANCHOR.MIDDLE)

    # Bar 2: Core diff 3.27 mT
    textbox(s4, bx, 4.74, 1.35, 0.32, [[("核心区最大差", {"bold": True})]], size=10.0, color=BODY, anchor=MSO_ANCHOR.MIDDLE)
    rect(s4, bx + 1.38, 4.80, max_bar_w, 0.24, PANEL, line=BORDER, width=0.5)
    rect(s4, bx + 1.38, 4.80, max_bar_w * (3.27 / 6.0), 0.24, MUTED)
    textbox(s4, bx + 1.38 + max_bar_w + 0.12, 4.74, 0.90, 0.32, [[("3.27 mT", {"bold": True})]], size=10.5, color=INK, anchor=MSO_ANCHOR.MIDDLE)

    textbox(
        s4,
        bx,
        5.22,
        lw4 - 0.44,
        0.78,
        [[("几何原因：", {"bold": True, "color": INK}), ("膜厚 4 nm 远小于最短横向尺寸 100 nm，因此三种形状中心核心区的反向退磁场均逼近无限大薄板极限 μ₀M_s = 377.0 mT（差值收窄近一半）。", {})]],
        size=9.5,
        color=BODY,
        line_spacing=1.20,
    )

    # Bottom Right: Mechanism explanation & strict boundaries
    rx4, rw4 = L + lw4 + 0.28, CW - lw4 - 0.28
    card(s4, rx4, 3.76, rw4, lh4, fill=PANEL, line=BORDER)
    rect(s4, rx4, 3.76, 0.055, lh4, INK)
    textbox(s4, rx4 + 0.20, 3.86, rw4 - 0.36, 0.26, [[("为何与共同翻转区间相容？（局部场尺度与实际失稳）", {})]], size=10.8, color=INK, bold=True)
    add_bullets(
        s4,
        rx4 + 0.20,
        4.18,
        rw4 - 0.36,
        1.82,
        [
            [("相近的局部轴向场尺度：", {"bold": True}), ("单轴各向异性场 B_K = 533.33 mT 与核心退磁场相加，三者依次为 163.15（方）、163.04（圆）、166.31 mT（长方形），差异极小。", {})],
            [("实际失稳机制：", {"bold": True}), ("上述差值仅刻画均匀 +z 态局部轴向场尺度；真实失稳还涉及交换作用、横向偏转引起的退磁场响应以及有限尺寸允许的空间模式。", {})],
            [("严谨界定：", {"bold": True}), ("直接用 B", {}), sub("K"), (" + μ", {}), sub("0"), ("H", {}), sub("d,z"), (" 预测翻转场会低估绝对值；局部场接近只提供与数据相容的物理机制，而非因果证明。", {})],
        ],
        size=9.4,
        space_after=4.0,
        line_spacing=1.16,
    )

    set_note(
        s4,
        "这一页是整场汇报最核心的一页。我们把观察尺度从“全片平均”切换到“中心局部场”。"
        "请看上表 1 nm 网格的数据，负号表示在固定 +z 磁化时退磁场方向与磁化相反。"
        "全片平均上，长方形和圆形相差 5.70 mT；但一旦聚焦到薄膜几何中心半径一个交换长度（9.403 nm）的核心区，方形是 −370.186 mT，圆形 −370.294 mT，长方形 −367.020 mT，最大差立刻收窄到只有 3.27 mT，就像左下角这两根条对比出来的那样。"
        "原因很直观：膜厚只有 4 nm，连长方形最窄的边也有 100 nm，对中心区域来说四周边界都足够远，局部退磁场都逼近 μ0Ms = 377 mT。"
        "把这个核心退磁场和单轴各向异性场 B_K = 533.33 mT 叠加，三者的局部轴向场尺度都在 163 到 166 mT。"
        "这里要特别严谨：不能直接拿 163 mT 去预测翻转场，也不能简单说“3.27 小于 5 所以区间重合”——真实翻转失稳还包含交换作用、横向退磁响应和空间模式。我们把它界定为与观测完全相容的局部成核机制。接下来看零场状态与两类独立证据。",
    )

    # ============================================================== Slide 5 ==
    # Zero-field energy competition & hysteresis overview
    s5 = new_slide(prs)
    slide_chrome(
        s5,
        "5 / 10",
        "04 / 零场能量竞争与完整磁滞背景",
        "分畴降低退磁能但畴壁代价更高，三形状撤场后均保持近饱和面外剩磁",
        [("背景结论：", {"bold": True}), ("两套网格 6 条完整回线高度重合（|M_r/M_s| > 0.999999），零场近单畴能量低于双畴；驻态能量差不是翻转能垒。", {})],
    )

    # Left half: Zero-field domain competition (2 nm)
    hw = 5.88
    card(s5, L, 1.46, hw, 4.62, fill=WHITE, line=BORDER)
    textbox(s5, L + 0.18, 1.56, hw - 0.36, 0.26, [[("2 nm 零场初态竞争：双畴退磁收益不抵畴壁代价", {})]], size=10.8, color=INK, bold=True)
    dom_rows = []
    for sh_key, sh_cn in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        d = DOMAIN_COMP[sh_key]
        dom_rows.append([
            [(sh_cn, {})],
            [(f"{d['single_J_m3']/1000:.2f}", {})],
            [(f"{d['domains_J_m3']/1000:.2f}", {})],
            [(f"{d['delta_total_J_m3']/1000:+.2f}", {"bold": True})],
            [(f"{d['domain_mean_abs_mz']:.3f}", {})],
        ])
    add_booktabs_table(
        s5,
        L + 0.16,
        1.88,
        hw - 0.32,
        1.38,
        [0.85, 1.15, 1.15, 1.25, 1.16],
        [[("形状", {})], [("近单畴/kJ·m⁻³", {})], [("双畴/kJ·m⁻³", {})], [("双畴−单畴", {})], [("双畴<|m_z|>", {})]],
        dom_rows,
        header_size=8.6,
        body_size=8.7,
        col_aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.RIGHT] * 4,
        row_heights=[0.32, 0.34, 0.34, 0.34],
    )
    add_picture_fitted(s5, 5, "domain_energy_competition.png", L + 0.16, 3.36, hw - 0.32, 2.28)
    textbox(
        s5,
        L + 0.16,
        5.70,
        hw - 0.32,
        0.32,
        [[("图源：domain_energy_competition.png（仅 2 nm 网格，零场驻态分项差，单位 kJ/m³）", {})]],
        size=8.8,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    # Right half: Full hysteresis loops (2 nm + 1 nm)
    rx5 = L + hw + 0.273
    card(s5, rx5, 1.46, hw, 4.62, fill=WHITE, line=BORDER)
    textbox(s5, rx5 + 0.18, 1.56, hw - 0.36, 0.26, [[("完整磁滞回线：两套网格 6 条曲线高度重合，剩磁近饱和", {})]], size=10.8, color=INK, bold=True)
    add_picture_fitted(s5, 5, "hysteresis_comparison.png", rx5 + 0.14, 1.90, hw - 0.28, 2.34)
    textbox(
        s5,
        rx5 + 0.16,
        4.28,
        hw - 0.32,
        0.34,
        [[("图源：hysteresis_comparison.png（左图 2 nm + 1 nm 完整回线，20 mT 步长；右图仅 2 nm 下降支总能量密度，J/m³）", {})]],
        size=8.8,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    add_bullets(
        s5,
        rx5 + 0.18,
        4.68,
        hw - 0.36,
        1.32,
        [
            [("全回线体量：", {"bold": True}), ("3 形状 × 2 网格共 6 条回线、726 场点，正负支 |M_r/M_s| 均 > 0.999999。", {})],
            [("粗步长区间：", {"bold": True}), ("20 mT 扫描下六条曲线全部在 180–200 mT 区间内完成翻转，末尾小数差不用于排序。", {})],
            [("引出精细验证：", {"bold": True}), ("为分辨 180–200 mT 内是否存在形状分化，对全部 12 条支路做场步加密。", {})],
        ],
        size=9.3,
        space_after=4.0,
        line_spacing=1.15,
    )

    set_note(
        s5,
        "在进入两类核心收束证据前，先快速确认零场状态和完整磁滞背景。"
        "看左边 2 nm 零场多初态结果：三种形状如果强行分成双畴，退磁能确实会下降，但畴壁的交换能和各向异性能代价更大，总能量反倒比近单畴高出 3.35 到 7.11 kJ/m³。注意这是两个驻态之差，不是翻转能垒。"
        "看右边完整磁滞回线图：左半图叠了 2 nm 和 1 nm 共 6 条回线，几乎完全重合，撤场剩磁都大于 0.999999；右半图是 2 nm 下降支的总能量密度。在 20 mT 粗步长下，翻转全落在 180 到 200 mT。接下来就看两类独立证据中的第一类：12 条支路的精细翻转场验证。",
    )

    # ============================================================== Slide 6 ==
    # Mainline Step 3a: Evidence 1 — 12/12 switching field verification
    s6 = new_slide(prs)
    slide_chrome(
        s6,
        "6 / 10",
        "05 / 主线三（证据一）：12 / 12 支精细翻转场验收",
        "三形状双网格 12 条支路全部通过验收，翻转场幅值均夹逼于 180–185 mT",
        [("证据一结论：", {"bold": True}), ("10→5 mT 场步收敛（中点移 2.5 mT < 9.125 mT 容差）且双停止阈值一致，182.5 mT 为区间中点，5 mT 下无法排序。", {})],
    )

    textbox(s6, L, 1.44, 6.85, 0.26, [[("全部 12 条支路加密翻转夹逼区间（0.01 与 0.005 °/ns 均通过）", {})]], size=11.2, color=INK, bold=True)
    v_rows = []
    for row in COERC_CSV:
        sh_cn = {"square": "方形", "circle": "圆形", "rectangle": "长方形"}[row["shape"]]
        cell = int(row["cell_nm"])
        lo_m = round(float(row["bc_minus_low_T"]) * 1000)
        hi_m = round(float(row["bc_minus_high_T"]) * 1000)
        lo_p = round(float(row["bc_plus_low_T"]) * 1000)
        hi_p = round(float(row["bc_plus_high_T"]) * 1000)
        est = float(row["coercivity_estimate_T"]) * 1000
        pert = "3 幅度 ε 通过" if cell == 2 else "默认 ε = 10⁻³"
        v_rows.append([
            [(f"{sh_cn} ({cell} nm)", {})],
            [(f"[{lo_m}, {hi_m}]", {})],
            [(f"[+{lo_p}, +{hi_p}]", {})],
            [(f"{est:.1f} mT", {"bold": True})],
            [(f"双阈值通过 · {pert}", {})],
        ])
    add_booktabs_table(
        s6,
        L,
        1.76,
        6.85,
        3.40,
        [1.30, 1.25, 1.25, 0.95, 2.10],
        [[("形状 (网格)", {})], [("下降支 / mT", {})], [("返回支 / mT", {})], [("区间中点", {})], [("数值检验状态", {})]],
        v_rows,
        header_size=9.2,
        body_size=9.0,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
        row_heights=[0.36] + [0.505] * 6,
    )

    card(s6, L, 5.28, 6.85, 0.80, fill=PANEL, line=BORDER)
    textbox(
        s6,
        L + 0.16,
        5.32,
        6.53,
        0.72,
        [[("区间定义说明：", {"bold": True, "color": INK}), ("矫顽场幅值由 (b_c+ − b_c−)/2 传播得到，180–185 mT 为离散场步夹逼区间（非统计置信区间），182.5 mT 为区间中点，不宣称三者精确相等。", {})]],
        size=9.4,
        color=BODY,
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.18,
    )

    # Right column: Convergence proof & protocol checks
    rx6, rw6 = 7.75, 4.93
    card(s6, rx6, 1.46, rw6, 2.22, fill=WHITE, line=BORDER)
    rect(s6, rx6, 1.46, 0.055, 2.22, INK)
    textbox(s6, rx6 + 0.20, 1.56, rw6 - 0.34, 0.26, [[("场步逐级收窄与收敛判据", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s6,
        rx6 + 0.20,
        1.88,
        rw6 - 0.34,
        1.72,
        [
            [("20 → 10 mT：", {"bold": True}), ("12 支幅值均夹逼在 180–190 mT（中点 185.0 mT）。", {})],
            [("10 → 5 mT：", {"bold": True}), ("全部收窄至 180–185 mT（中点 182.5 mT），中点移动 2.5 mT。", {})],
            [("满足容差：", {"bold": True}), ("2.5 mT < max(2 mT, 5% × 182.5 mT) = 9.125 mT，六组均无需继续加密至 2.5 mT。", {})],
        ],
        size=9.6,
        space_after=4.5,
        line_spacing=1.18,
    )

    card(s6, rx6, 3.82, rw6, 2.26, fill=PANEL, line=BORDER)
    rect(s6, rx6, 3.82, 0.055, 2.26, INK)
    textbox(s6, rx6 + 0.20, 3.92, rw6 - 0.34, 0.26, [[("停止阈值与微扰稳健性检验", {})]], size=11.0, color=INK, bold=True)
    add_bullets(
        s6,
        rx6 + 0.20,
        4.24,
        rw6 - 0.34,
        1.76,
        [
            [("双停止阈值：", {"bold": True}), ("全部 12 支在 0.01 与 0.005 °/ns 下给出完全相同的 180–185 mT 区间。", {})],
            [("2 nm 三幅度微扰：", {"bold": True}), ("在 180 与 185 mT 端点重放 ε = 10⁻⁴、10⁻³、10⁻²，三形状两支均保持同一翻转区间。", {})],
            [("1 nm 协议说明：", {"bold": True}), ("采用默认 ε = 10⁻³，未出现区间分歧，故未触发额外三幅度补验。", {})],
        ],
        size=9.6,
        space_after=4.5,
        line_spacing=1.18,
    )

    set_note(
        s6,
        "第一类收束证据是全部 12 条支路的精细翻转场。左表列出了 3 种形状、2 套网格、正负两支的最终结果：全部 12 条支路无一例外，"
        "下降支都夹在 −185 到 −180 mT，返回支都夹在 +180 到 +185 mT，区间中点是 182.5 mT。"
        "右边说明这组区间为什么站得住：第一，从 10 mT 加密到 5 mT，区间从 180–190 mT 收窄到 180–185 mT，中点只移动了 2.5 mT，远小于预设容差 9.125 mT；"
        "第二，把停止阈值收紧一倍到 0.005 °/ns，12 条支路的区间一个都没动；第三，在 2 nm 上把微扰幅度拉宽两个数量级，结果同样不变。"
        "确认完“在哪儿翻”，接下来看第二类独立证据：“怎么翻”。",
    )

    # ============================================================== Slide 7 ==
    # Mainline Step 3b (Part 1): 2 nm spatial snapshots confirm center nucleation
    s7 = new_slide(prs)
    slide_chrome(
        s7,
        "7 / 10",
        "06 / 主线三（证据二 · 空间路径）：2 nm 翻转过程快照",
        "2 nm 空间快照证实翻转始于几何中心，并非均匀一致旋转",
        [("空间证据结论：", {"bold": True}), ("−200 mT 粗场步快照显示方/圆中心成核扩展、长方形中央成带推进，直接呼应中心强退磁机制；step 非物理时间。", {})],
    )

    lw7 = 4.90
    textbox(s7, L, 1.44, lw7, 0.26, [[("2 nm 下降支 −200 mT 粗场步重放统计（每 50 步采样）", {})]], size=10.6, color=INK, bold=True)
    snap_rows = []
    for sh_key, sh_cn, frames, feat in [
        ("square", "方形", 126, "中心反向核 → 向四周扩展"),
        ("circle", "圆形", 123, "中心反向核 → 径向扩展"),
        ("rectangle", "长方形", 136, "中央反向带 → 向两端推进"),
    ]:
        fr = FIRST_REV[sh_key]
        if fr["x_min_nm"] == fr["y_min_nm"]:
            loc = f"x,y ∈ [−{abs(int(fr['x_min_nm']))},+{int(fr['x_max_nm'])}] nm"
        else:
            loc = f"x∈[−{abs(int(fr['x_min_nm']))},+{int(fr['x_max_nm'])}], y∈[−{abs(int(fr['y_min_nm']))},+{int(fr['y_max_nm'])}]"
        snap_rows.append([
            [(sh_cn, {})],
            [(str(frames), {})],
            [(loc, {})],
            [(feat, {})],
        ])
    add_booktabs_table(
        s7,
        L,
        1.76,
        lw7,
        1.74,
        [0.76, 0.56, 1.72, 1.86],
        [[("形状", {})], [("帧数", {})], [("首次 m_z<0 范围", {})], [("空间扩展模式", {})]],
        snap_rows,
        header_size=8.8,
        body_size=8.5,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
        row_heights=[0.36, 0.45, 0.45, 0.45],
    )

    card(s7, L, 3.66, lw7, 2.42, fill=PANEL, line=BORDER)
    rect(s7, L, 3.66, 0.055, 2.42, INK)
    textbox(s7, L + 0.18, 3.76, lw7 - 0.34, 0.24, [[("读图要点与严格限定", {})]], size=10.8, color=INK, bold=True)
    add_bullets(
        s7,
        L + 0.18,
        4.06,
        lw7 - 0.34,
        1.94,
        [
            [("中心成核实证：", {"bold": True}), ("首次观测到 m_z < 0 的单元均在原点附近，与第 4 页核心区强退磁场直接呼应。", {})],
            [("终态逐单元一致：", {"bold": True}), ("重放仅加密输出频率，三形状终态与原 −200 mT 算例最大分量差均为 0。", {})],
            [("场点与时间限定：", {"bold": True}), ("本页为 2 nm、−200 mT 粗场步快照（非 ±185 mT 细化点）；关闭进动的 step 不代表物理翻转速度。", {})],
        ],
        size=9.4,
        space_after=4.5,
        line_spacing=1.18,
    )

    # Right: large reversal_trajectory.png
    rx7, rw7 = L + lw7 + 0.25, CW - lw7 - 0.25
    card(s7, rx7, 1.46, rw7, 4.62, fill=WHITE, line=BORDER)
    add_picture_fitted(s7, 7, "reversal_trajectory.png", rx7 + 0.14, 1.54, rw7 - 0.28, 3.96)
    textbox(
        s7,
        rx7 + 0.16,
        5.56,
        rw7 - 0.32,
        0.46,
        [[("图源：reversal_trajectory.png（仅 2 nm 网格，−200 mT 下降支粗场步重放，底层 m_z 分布；step 为数值迭代步）", {})]],
        size=9.0,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    set_note(
        s7,
        "第二类证据先看空间形态。右边是 2 nm 网格在 −200 mT 下降支粗场步下的重放快照，每 50 步保存一次磁化，终态和原算例逐单元一致。"
        "大家看图从左到右：第一列首次出现反向（蓝白色）时，无论方形、圆形还是长方形，全部在几何中心附近——方形和圆形在正负 21 到 23 nm 以内，长方形只在 x 方向正负 7 nm、y 方向正负 3 nm。"
        "随后方形和圆形向四周扩展，长方形则先横跨短轴形成一条中央反向带，再向左右两端推进。"
        "这组图像独立印证了第 4 页的中心成核机制。需要区分两点：第一，这是 −200 mT 粗场步快照，不是 ±185 mT 细化点；第二，图上的 step 是关闭进动后的数值迭代步，不能用来比物理快慢。那 1 nm 细网格以及 ±185 mT 细化场点下，是不是也同样非均匀翻转？我们看下一页。",
    )

    # ============================================================== Slide 8 ==
    # Mainline Step 3b (Part 2): Cross-mesh scalar trajectories at -200 mT AND ±185 mT
    s8 = new_slide(prs)
    slide_chrome(
        s8,
        "8 / 10",
        "07 / 主线三（证据二 · 跨网格与细化场点复核）",
        "2 nm 与 1 nm 标量轨迹在 −200 mT 与 ±185 mT 下均证实非均匀翻转",
        [("跨网格结论：", {"bold": True}), ("两套网格在粗、细场步下均出现显著磁矩方向抵消（长方形最明显）；1 nm 标量无空间坐标，无法单独定位成核点。", {})],
    )

    textbox(s8, L, 1.40, CW, 0.24, [[("最小平均磁化矢量模长 min|<m>|（2 nm / 1 nm，普通阈值 0.01 °/ns；一致旋转应始终接近 1）", {})]], size=10.5, color=INK, bold=True)
    od_rows = []
    for sh_key, sh_cn in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        c2 = LOCAL_TRACES[(sh_key, 2)]["min_norm"]
        c1 = LOCAL_TRACES[(sh_key, 1)]["min_norm"]
        m2_d = REFINED_REV[(sh_key, 2, 0, 0.01)]["min_norm"]
        m1_d = REFINED_REV[(sh_key, 1, 0, 0.01)]["min_norm"]
        m2_u = REFINED_REV[(sh_key, 2, 1, 0.01)]["min_norm"]
        m1_u = REFINED_REV[(sh_key, 1, 1, 0.01)]["min_norm"]
        is_rect = sh_key == "rectangle"
        od_rows.append([
            [(sh_cn, {})],
            [(f"{c2:.4f} / {c1:.4f}", {"bold": is_rect})],
            [(f"{m2_d:.4f} / {m1_d:.4f}", {"bold": is_rect})],
            [(f"{m2_u:.4f} / {m1_u:.4f}", {"bold": is_rect})],
            [("两套网格与粗/细场步均显著 < 1，长方形抵消最强" if is_rect else "两套网格高度一致，均经历非均匀多畴过渡", {})],
        ])
    add_booktabs_table(
        s8,
        L,
        1.68,
        CW,
        1.54,
        [1.10, 2.25, 2.35, 2.35, 3.983],
        [
            [("形状", {})],
            [("−200 mT 下降支（粗步）", {})],
            [("−185 mT 下降支（细化）", {})],
            [("+185 mT 返回支（细化）", {})],
            [("跨网格一致性解读", {})],
        ],
        od_rows,
        header_size=9.1,
        body_size=9.0,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
        row_heights=[0.34, 0.39, 0.39, 0.39],
    )

    # Bottom Left: cross_mesh_reversal_odt.png
    lw8, lh8 = 7.15, 2.82
    card(s8, L, 3.30, lw8, lh8, fill=WHITE, line=BORDER)
    add_picture_fitted(s8, 8, "cross_mesh_reversal_odt.png", L + 0.14, 3.36, lw8 - 0.28, 2.38)
    textbox(
        s8,
        L + 0.14,
        5.76,
        lw8 - 0.28,
        0.30,
        [[("图源：cross_mesh_reversal_odt.png（2 nm + 1 nm，−200 mT 下降支 ODT 轨迹；上排共用 0.38–1.03 纵轴，下排为总能量变化 kJ/m³）", {})]],
        size=8.6,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    # Bottom Right: Key takeaways on ±185 mT & 1 nm boundary
    rx8, rw8 = L + lw8 + 0.25, CW - lw8 - 0.25
    card(s8, rx8, 3.30, rw8, lh8, fill=PANEL, line=BORDER)
    rect(s8, rx8, 3.30, 0.055, lh8, INK)
    textbox(s8, rx8 + 0.18, 3.40, rw8 - 0.32, 0.24, [[("细化场点复核与空间证据边界", {})]], size=10.6, color=INK, bold=True)
    add_bullets(
        s8,
        rx8 + 0.18,
        3.70,
        rw8 - 0.32,
        2.32,
        [
            [("±185 mT 抵消更强：", {"bold": True}), ("接近临界场时，长方形最小模长进一步降至 0.339 / 0.338（严格阈值 0.3380），说明非均匀反转在粗、细场步均成立。", {})],
            [("能量单调下降：", {"bold": True}), ("−200 mT 的 6 条与 ±185 mT 双阈值共 24 条轨迹，采样总能量均未上升。", {})],
            [("明确边界：", {"bold": True}), ("1 nm 标量轨迹足以确认非均匀性，但不含空间坐标，无法单独定位成核点。", {})],
        ],
        size=9.2,
        space_after=4.5,
        line_spacing=1.16,
    )

    set_note(
        s8,
        "这一页把 −200 mT 粗场步和 ±185 mT 细化场点分开对比。左下角是 −200 mT 下降支 2 nm 和 1 nm 的 ODT 标量轨迹，上排三张图用了统一的 0.38 到 1.03 纵轴，可以一眼看出两条网格曲线几乎重合，而且长方形的谷底明显更深。"
        "再看上面表格里的 ±185 mT 细化场点：长方形的最小平均磁化矢量模长在 2 nm 和 1 nm 上分别降到 0.339 和 0.338，严格阈值下同样是 0.3380；"
        "所有 24 条细化翻转轨迹的能量都严格单调不增。这就用两套网格共同确认了非均匀翻转。当然我们也要实事求是：1 nm 的 ODT 标量没有空间坐标，不能单独定位成核点，空间定位结论来自上一页的 2 nm 快照。",
    )

    # ============================================================== Slide 9 ==
    # Independent numerical acceptance & explicit scope boundaries
    s9 = new_slide(prs)
    slide_chrome(
        s9,
        "9 / 10",
        "08 / 最终数值验收与适用边界",
        "82 项汇总检查与 3,118 项输出审计全部通过，结论严格限定于模型范围内",
        [("验收结论：", {"bold": True}), ("P0–P4 既定核查全部闭合（pending 与 failed_checks 均为空）；结论仅适用于零温无缺陷教学参数与准静态弛豫协议。", {})],
    )

    lw9 = 5.88
    card(s9, L, 1.46, lw9, 4.62, fill=WHITE, line=BORDER)
    rect(s9, L, 1.46, lw9, 0.045, INK)
    textbox(s9, L + 0.22, 1.62, lw9 - 0.44, 0.28, [[("独立数值审计与全链路溯源（P4 最终核验）", {})]], size=11.5, color=INK, bold=True)
    audit_rows = [
        [[("验收总状态", {})], [("pending = []，failed_checks = []，全部通过", {"bold": True})]],
        [[("自动化检查", {})], [("82 项汇总布尔检查 + 3,118 项输出审计全通过", {})]],
        [[("复核规模", {})], [("488 个目录（427 个直接求解目录、2,228 个阶段终态）", {})]],
        [[("原始文件校验", {})], [("读取 7,111 个 ODT / 磁化 / 场文件，逐目录记录指纹", {})]],
        [[("物理守恒复算", {})], [("核对单位模长、能量求和、场能一致及有效场独立 RHS", {})]],
        [[("几何与收敛", {})], [("圆形 N_z 网格变化 0.000327 < 0.001；12/12 支双阈值闭环", {})]],
    ]
    add_booktabs_table(
        s9,
        L + 0.20,
        1.98,
        lw9 - 0.40,
        3.86,
        [1.45, 4.03],
        [[("核验项", {})], [("实际验收结果（evidence/final_audit.json）", {})]],
        audit_rows,
        header_size=9.3,
        body_size=9.1,
        row_heights=[0.36] + [0.58] * 6,
    )

    rx9, rw9 = L + lw9 + 0.273, CW - lw9 - 0.273
    card(s9, rx9, 1.46, rw9, 4.62, fill=PANEL, line=BORDER)
    rect(s9, rx9, 1.46, rw9, 0.045, INK)
    textbox(s9, rx9 + 0.22, 1.62, rw9 - 0.44, 0.28, [[("四条明确的结论边界（不外推、不越界）", {})]], size=11.5, color=INK, bold=True)
    textbox(
        s9,
        rx9 + 0.22,
        2.04,
        rw9 - 0.44,
        3.82,
        [
            [("1. 纯磁性教学模型：", {"bold": True, "color": INK}), ("参数未针对特定真实 QAH 材料标定；未计算电子能带、陈数或量子化霍尔电导，不宣称验证 QAH 输运。", {})],
            [("2. 驻态能量差 ≠ 翻转能垒：", {"bold": True, "color": INK}), ("零场双畴与近单畴能量差仅代表所测初态集合的驻态对比，不证明全局基态或有限温稳定性。", {})],
            [("3. 迭代步 ≠ 物理翻转时间：", {"bold": True, "color": INK}), ("求解关闭进动项仅用于准静态能量弛豫，迭代步数不用于比较真实动力学翻转速度。", {})],
            [("4. 细网格与排序边界：", {"bold": True, "color": INK}), ("1 nm 未做翻转过程空间快照与三幅度微扰；5 mT 下区间重叠只说明无法排序，不宣称三者矫顽场精确相等。", {})],
        ],
        size=10.0,
        color=BODY,
        space_after=8.5,
        line_spacing=1.22,
    )

    set_note(
        s9,
        "这一页简要交代最终验收的可靠度和结论边界。左边是 P4 独立审计汇总：82 项汇总检查和 3,118 项输出审计全部通过，"
        "覆盖 488 个目录、7,111 个原始文件，每个阶段都独立复算了有效场右端项和停止指标，保证没有未收敛样本混入。"
        "右边列出四条明确的边界：不外推到真实 QAH 材料和输运、不把驻态能量差当能垒、不把关闭进动的迭代步当物理时间、不把 5 mT 重叠说成精确相等。下面进入最后一页，直接回答开场问题。",
    )

    # ============================================================= Slide 10 ==
    # Conclusion: Direct answer to the opening question
    s10 = new_slide(prs)
    slide_chrome(
        s10,
        "10 / 10",
        "09 / 总结与结论",
        "形状清晰改变全片平均退磁场，但在本模型和 5 mT 分辨率下三形状矫顽场无法排序",
        [("最终回答：", {"bold": True}), ("形状对全片平均退磁场的影响清晰可辨，中心局部场更接近；在当前零温教学模型和 5 mT 分辨率下，三种形状的矫顽场无法排序。", {})],
    )

    # Three crisp answer pillars aligned with the 3-step spine
    pillars = [
        (
            "01 / 全片平均清晰可辨",
            "长方形全片 N_z 最低",
            [
                "1 nm 网格全片 N_z：圆形 0.944291 > 方形 0.940862 > 长方形 0.929169。",
                "长方形有 21.69% 体积处于弱退磁边缘带（圆形 15.99%），边缘占比与内部场强共同拉低全片均值（全片平均场差 5.70 mT）。",
            ],
        ),
        (
            "02 / 中心局部场更接近",
            "核心区最大差仅 3.27 mT",
            [
                "膜厚 4 nm 远小于最短横向尺寸 100 nm，中心半径 9.403 nm 核心区退磁场均逼近 μ₀M_s = 377.0 mT（−370.19 / −370.29 / −367.02 mT）。",
                "结合 B_K = 533.33 mT，三者中心局部场尺度相近；配合交换作用与横向响应，构成与观测相容的机制。",
            ],
        ),
        (
            "03 / 双重证据收束",
            "12/12 支同落 180–185 mT",
            [
                "全部 12 支通过 10→5 mT 及双阈值验收，幅值均夹逼于 180–185 mT（中点 182.5 mT），5 mT 下无法按形状排序。",
                "2 nm −200 mT 快照证实中心成核扩展；2/1 nm 标量轨迹在 −200 与 ±185 mT 下均证实非均匀翻转（长方形抵消最强）。",
            ],
        ),
    ]
    pw, pgap, py, ph = 3.85, 0.241, 1.50, 3.65
    for i, (ptag, phead, pbullets) in enumerate(pillars):
        px = L + i * (pw + pgap)
        card(s10, px, py, pw, ph, fill=PANEL if i == 1 else WHITE, line=BORDER)
        rect(s10, px, py, pw, 0.05, INK)
        textbox(s10, px + 0.20, py + 0.18, pw - 0.40, 0.24, [[(ptag, {})]], size=10.0, color=MUTED, bold=True)
        textbox(s10, px + 0.20, py + 0.48, pw - 0.40, 0.38, [[(phead, {})]], size=14.0, color=INK, bold=True)
        add_bullets(s10, px + 0.20, py + 0.96, pw - 0.40, 2.52, pbullets, size=10.0, space_after=6.5, line_spacing=1.22)

    # Bottom Q&A pointer box
    card(s10, L, 5.32, CW, 0.76, fill=WHITE, line=BORDER)
    textbox(
        s10,
        L + 0.22,
        5.36,
        CW - 0.44,
        0.68,
        [[("致谢与备份资料说明：", {"bold": True, "color": INK}), ("感谢各位老师指导，欢迎提问！备份页 B1–B2 汇总了两套网格完整静态因子、中心/边缘局部场及全部 12 支验证与细化轨迹明细，供随时查阅。", {})]],
        size=10.2,
        color=BODY,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    set_note(
        s10,
        "最后用三句话直接回答开场提出的问题："
        "第一，形状对全片平均退磁场的影响清晰可辨，长方形因 21.69% 的弱退磁边缘带和内部场强，全片 Nz 最低，比圆形弱 5.70 mT；"
        "第二，但膜厚 4 nm 远小于 100 nm 短轴，几何中心核心区的局部退磁场三者最大只差 3.27 mT，结合各向异性场、交换作用与空间模式，提供了与观测相容的机制；"
        "第三，全部 12 条支路经双网格、双阈值验收均夹逼于 180–185 mT，且空间快照和两套网格标量轨迹均证实非均匀翻转。"
        "因此结论很明确：在本模型和 5 mT 分辨率下，三种形状的矫顽场无法排序。后面附有两页完整数据备份表，欢迎各位老师提问！",
    )

    # ============================================================ Backup B1 ==
    # Full 2 nm & 1 nm static demag factors & local fields lookup table
    sb1 = new_slide(prs)
    slide_chrome(
        sb1,
        "B1 / 备份",
        "备份页 B1 / 两套网格完整静态退磁因子与局部场对照表",
        "固定均匀磁化下 1 nm 与 2 nm 网格的完整 N_x、N_y、N_z 与中心/边缘局部场",
        [("数据出处：", {"bold": True}), ("evidence/demag_factors.csv 与 evidence/local_reversal.json；中心点取距轴最近 4 格柱，核心与边缘均按交换长度 9.403 nm 定义，沿 4 nm 厚度平均。", {})],
    )

    b1_rows = []
    for sh_key, sh_cn in [("square", "方形"), ("circle", "圆形"), ("rectangle", "长方形")]:
        for cell in (1, 2):
            lf = LOCAL_FIELDS[(sh_key, cell)]
            edge_pct = lf["edge"]["cells"] / lf["all"]["cells"] * 100.0
            b1_rows.append([
                [(f"{sh_cn} ({cell} nm)", {})],
                [(f"{DEMAG_AREA[(sh_key, cell)]:,}", {})],
                [(f"{DEMAG[(sh_key, cell, 'x')]:.6f}", {})],
                [(f"{DEMAG[(sh_key, cell, 'y')]:.6f}", {})],
                [(f"{DEMAG[(sh_key, cell, 'z')]:.6f}", {"bold": True})],
                [(f"{lf['point']['B_mT']:.3f} / {lf['point']['N']:.6f}", {})],
                [(f"{lf['core']['B_mT']:.3f} / {lf['core']['N']:.6f}", {"bold": True})],
                [(f"{lf['edge']['B_mT']:.3f} / {edge_pct:.2f}%", {})],
            ])
    add_booktabs_table(
        sb1,
        L,
        1.52,
        CW,
        4.42,
        [1.22, 0.88, 1.05, 1.05, 1.08, 2.25, 2.25, 2.253],
        [
            [("形状 (网格)", {})],
            [("面积/nm²", {})],
            [("全片 N_x", {})],
            [("全片 N_y", {})],
            [("全片 N_z", {})],
            [("中心点场(mT) / 等效 N_z", {})],
            [("核心场(mT) / 等效 N_z", {})],
            [("边缘场(mT) / 占比", {})],
        ],
        b1_rows,
        header_size=8.8,
        body_size=8.8,
        col_aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.RIGHT] * 7,
        row_heights=[0.42] + [0.665] * 6,
    )

    set_note(
        sb1,
        "备份页 B1：汇总 1 nm 和 2 nm 两套网格的全部全片退磁因子、离散面积，以及中心点、核心区（半径 9.403 nm）和边缘带的完整 μ0Hd,z 与等效 Nz，供提问时直接查数。",
    )

    # ============================================================ Backup B2 ==
    # Full 12 branches + ±185 mT refined trajectory details + reversal_states.png
    sb2 = new_slide(prs)
    slide_chrome(
        sb2,
        "B2 / 备份",
        "备份页 B2 / 全部 12 支验证明细与粗/细场点对比",
        "12 支夹逼区间、±185 mT 代表收敛指标与 20 mT 粗步终态对照",
        [("配图区分：", {"bold": True}), ("右图 reversal_states.png 为 2 nm 网格 20 mT 粗场步终态（±180 / ±200 mT），不含 5 mT 细化态；左表列出 12 支完整明细。", {})],
    )

    # Left: compact 12-branch & ±185 mT verification table
    lw_b2 = 7.35
    textbox(sb2, L, 1.42, lw_b2, 0.24, [[("全部 12 支翻转夹逼与 ±185 mT 普通阈值最小模长明细", {})]], size=10.5, color=INK, bold=True)
    b2_rows = []
    for v in VERIF:
        sh_cn = {"square": "方形", "circle": "圆形", "rectangle": "长方形"}[v["shape"]]
        br_cn = "下降支" if v["branch"] == 0 else "返回支"
        b0, b1 = sorted([round(v["bracket_T"][0] * 1000), round(v["bracket_T"][1] * 1000)])
        t0, t1 = sorted([round(v["tight_bracket_T"][0] * 1000), round(v["tight_bracket_T"][1] * 1000)])
        rr = REFINED_REV[(v["shape"], v["cell_nm"], v["branch"], 0.01)]
        pert_txt = "3ε通过" if v["cell_nm"] == 2 else "默认ε"
        b2_rows.append([
            [(f"{sh_cn} {v['cell_nm']}nm {br_cn}", {})],
            [(f"[{b0:+d}, {b1:+d}]", {})],
            [(f"[{t0:+d}, {t1:+d}]", {})],
            [(f"{v['field_check_T']*1000:.1f}", {})],
            [(f"{rr['min_norm']:.4f}", {})],
            [(f"{rr['iteration_end']:,}", {})],
            [(pert_txt, {})],
        ])
    add_booktabs_table(
        sb2,
        L,
        1.70,
        lw_b2,
        4.38,
        [1.55, 1.15, 1.15, 0.72, 0.88, 1.05, 0.85],
        [
            [("支路", {})],
            [("5 mT 普通", {})],
            [("5 mT 严格", {})],
            [("Δ中点/mT", {})],
            [("±185 min|m|", {})],
            [("普通收敛步", {})],
            [("微扰", {})],
        ],
        b2_rows,
        header_size=8.4,
        body_size=8.1,
        col_aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER],
        row_heights=[0.34] + [0.335] * 12,
    )

    # Right: reversal_states.png + representative strict convergence stats
    rx_b2, rw_b2 = L + lw_b2 + 0.25, CW - lw_b2 - 0.25
    card(sb2, rx_b2, 1.46, rw_b2, 3.38, fill=WHITE, line=BORDER)
    add_picture_fitted(sb2, 12, "reversal_states.png", rx_b2 + 0.12, 1.54, rw_b2 - 0.24, 2.84)
    textbox(
        sb2,
        rx_b2 + 0.12,
        4.42,
        rw_b2 - 0.24,
        0.38,
        [[("reversal_states.png（仅 2 nm，20 mT 粗场步 ±180/±200 mT 终态）", {})]],
        size=8.5,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )

    card(sb2, rx_b2, 4.96, rw_b2, 1.12, fill=PANEL, line=BORDER)
    textbox(
        sb2,
        rx_b2 + 0.16,
        5.02,
        rw_b2 - 0.32,
        1.00,
        [
            [("代表严格阈值复核（长方形 1 nm 返回支 +185 mT）：", {"bold": True, "size": 8.9, "color": INK})],
            [("普通 / 严格分别经 111,873 / 117,111 步收敛，终点 max|dm/dt| = 0.00994 / 0.00499 °/ns，严格阈值最小模长 0.3380。", {"size": 8.7, "color": BODY})],
        ],
        anchor=MSO_ANCHOR.MIDDLE,
        line_spacing=1.18,
    )

    set_note(
        sb2,
        "备份页 B2：列出全部 12 支的普通与严格阈值夹逼区间（单位 mT）、10 到 5 mT 中点移动 2.5 mT、±185 mT 普通阈值最小平均模长与收敛步数，"
        "以及 2 nm 20 mT 粗场步翻转前后终态图 reversal_states.png，供提问时查阅。",
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
