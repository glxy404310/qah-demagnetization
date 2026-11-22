r"""Build the balanced concise-yet-rigorous 8+4 slide group-meeting PPTX (2026-11-22).

Run with the Python interpreter that has python-pptx & Pillow installed:
    C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe 汇报PPT\build_concise_report_20261122.py

Output:
    汇报PPT/同面积薄膜形状退磁与翻转_精简完整版_20261122.pptx
"""
from __future__ import annotations

import csv
import json
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

OUT_PPTX = Path(__file__).resolve().parent / "同面积薄膜形状退磁与翻转_精简完整版_20261122_v2.pptx"

# ----------------------------------------------------------------- palette ----
WHITE = "FFFFFF"
INK = "111827"         # Deep charcoal-black for titles & primary text
NAVY = "1B365D"        # Restrained academic navy accent
NAVY_SOFT = "EBF0F6"   # Soft navy tint for highlight boxes
BODY = "2D3748"        # Readable dark slate for body text
MUTED = "5A6577"       # Captions, kickers, page numbers
PANEL = "F5F7FA"       # Subtle neutral gray for cards & table headers
TABLE_ALT = "FAFBFD"   # Faint alternating row tint
BORDER = "D5DCE4"      # Crisp hairline border
BAR_LIGHT = "C8D4E3"   # Secondary bar color

EA = "Microsoft YaHei"
LATIN = "Segoe UI"

W, H = 13.333, 7.5
L, R = 0.65, 0.65
CW = W - L - R  # 12.033 in
MAIN_SLIDES = 8

# --------------------------------------------------------- verified evidence --
RESULTS = json.loads((EVIDENCE_DIR / "results.json").read_text(encoding="utf-8"))
VERIF = json.loads((EVIDENCE_DIR / "verification_details.json").read_text(encoding="utf-8"))
LOCAL_REV = json.loads((EVIDENCE_DIR / "local_reversal.json").read_text(encoding="utf-8"))
FINAL_AUDIT = json.loads((EVIDENCE_DIR / "final_audit.json").read_text(encoding="utf-8"))

with (EVIDENCE_DIR / "demag_factors.csv").open(encoding="utf-8-sig", newline="") as f:
    DEMAG_CSV = list(csv.DictReader(f))

assert RESULTS["completed_runs"] == 488
assert RESULTS["failed_checks"] == []
assert RESULTS["pending"] == []
assert len(RESULTS["checks"]) == 82 and all(RESULTS["checks"].values())
assert len(VERIF) == 12
assert len(FINAL_AUDIT["refined_reversal"]) == 24

DOMAIN_COMP = {d["shape"]: d for d in RESULTS["domain_energy_comparison"]}
LOCAL_FIELDS = {(f["shape"], f["cell_nm"]): f for f in LOCAL_REV["fields"]}
DEMAG = {(r["shape"], int(r["cell_nm"]), r["axis"]): float(r["N_field"]) for r in DEMAG_CSV}
REFINED_REV = {(r["shape"], r["cell_nm"], r["branch"], r["stop"]): r for r in FINAL_AUDIT["refined_reversal"]}
VERIF_MAP = {(v["shape"], v["cell_nm"], v["branch"]): v for v in VERIF}

# ----------------------------------------------------------- low-level helpers
def rgb(hex_str: str) -> RGBColor:
    return RGBColor.from_string(hex_str)


def set_run_font(run, size_pt: float, color_hex: str = BODY, bold: bool = False, italic: bool = False,
                 latin: str = LATIN, ea: str = EA, baseline: int | None = None):
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = rgb(color_hex)
    run.font.name = latin
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        old = rPr.find(qn(tag))
        if old is not None:
            rPr.remove(old)
    el_lat = parse_xml(f'<a:latin {nsdecls("a")} typeface="{latin}"/>')
    el_ea = parse_xml(f'<a:ea {nsdecls("a")} typeface="{ea}"/>')
    el_cs = parse_xml(f'<a:cs {nsdecls("a")} typeface="{latin}"/>')
    rPr.append(el_lat)
    rPr.append(el_ea)
    rPr.append(el_cs)
    if baseline is not None:
        rPr.set("baseline", str(baseline))


def sub(text: str, **kw):
    d = {"baseline": -25000}
    d.update(kw)
    return (text, d)


def sup(text: str, **kw):
    d = {"baseline": 30000}
    d.update(kw)
    return (text, d)


def new_slide(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = rgb(WHITE)
    return slide


def disable_shadow(sh):
    sh.shadow.inherit = False
    spPr = sh._element.spPr
    old = spPr.find(qn("a:effectLst"))
    if old is not None:
        spPr.remove(old)
    spPr.append(parse_xml(f'<a:effectLst {nsdecls("a")}/>'))


def rect(slide, x: float, y: float, w: float, h: float, fill_hex: str | None = None,
         line_hex: str | None = None, line_pt: float = 0.75, rounded: bool = False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded:
        sh.adjustments[0] = 0.04
    if fill_hex is not None:
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(fill_hex)
    else:
        sh.fill.background()
    if line_hex is not None:
        sh.line.color.rgb = rgb(line_hex)
        sh.line.width = Pt(line_pt)
    else:
        sh.line.fill.background()
    disable_shadow(sh)
    return sh


def oval(slide, x: float, y: float, w: float, h: float, fill_hex: str, line_hex: str, line_pt: float = 1.5):
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = rgb(fill_hex)
    sh.line.color.rgb = rgb(line_hex)
    sh.line.width = Pt(line_pt)
    disable_shadow(sh)
    return sh


def textbox(slide, x: float, y: float, w: float, h: float, paragraphs: list,
            size: float = 12.0, color: str = BODY, bold: bool = False,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
            line_spacing: float = 1.22, space_after: float = 3.0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(0.03)
    tf.margin_right = Inches(0.03)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    for idx, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after) if idx < len(paragraphs) - 1 else Pt(0)
        parts = [(para, {})] if isinstance(para, str) else para
        for text, style in parts:
            r = p.add_run()
            r.text = text
            set_run_font(
                r,
                size_pt=style.get("size", size),
                color_hex=style.get("color", color),
                bold=style.get("bold", bold),
                italic=style.get("italic", False),
                baseline=style.get("baseline"),
            )
    return tb


def add_bullets(slide, x: float, y: float, w: float, h: float, items: list,
                size: float = 12.0, space_after: float = 6.0, line_spacing: float = 1.24):
    paras = []
    for it in items:
        if isinstance(it, str):
            paras.append([("▪  ", {"color": NAVY, "bold": True}), (it, {})])
        else:
            paras.append([("▪  ", {"color": NAVY, "bold": True}), *it])
    return textbox(slide, x, y, w, h, paras, size=size, color=BODY,
                   line_spacing=line_spacing, space_after=space_after)


def add_picture_fitted(slide, filename: str, x: float, y: float, max_w: float, max_h: float):
    path = FIG_DIR / filename
    with Image.open(path) as im:
        iw, ih = im.size
    ratio = iw / ih
    box_ratio = max_w / max_h
    if ratio > box_ratio:
        w = max_w
        h = max_w / ratio
    else:
        h = max_h
        w = max_h * ratio
    px = x + (max_w - w) / 2.0
    py = y + (max_h - h) / 2.0
    return slide.shapes.add_picture(str(path), Inches(px), Inches(py), width=Inches(w), height=Inches(h))


def set_cell_border(cell, top=None, bottom=None, left=None, right=None):
    tcPr = cell._tc.get_or_add_tcPr()
    for edge, spec in (("lnT", top), ("lnB", bottom), ("lnL", left), ("lnR", right)):
        old = tcPr.find(qn(f"a:{edge}"))
        if old is not None:
            tcPr.remove(old)
        if spec is None:
            el = parse_xml(f'<a:{edge} {nsdecls("a")} w="0"><a:noFill/></a:{edge}>')
        else:
            hex_c, pt_w = spec
            emu_w = int(pt_w * 12700)
            el = parse_xml(
                f'<a:{edge} {nsdecls("a")} w="{emu_w}" cap="flat" cmpd="sng" algn="ctr">'
                f'<a:solidFill><a:srgbClr val="{hex_c}"/></a:solidFill>'
                f'</a:{edge}>'
            )
        tcPr.append(el)


def add_table(slide, x: float, y: float, w: float, col_widths: list[float],
              headers: list, rows: list, header_size: float = 11.0, body_size: float = 11.0,
              row_heights: list[float] | None = None, aligns: list | None = None,
              highlight_rows: set[int] | None = None):
    nrows = 1 + len(rows)
    ncols = len(headers)
    if row_heights is None:
        row_heights = [0.40] + [0.42] * len(rows)
    total_h = sum(row_heights)
    tbl_shape = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(total_h))
    tbl = tbl_shape.table
    tbl.first_row = False
    tbl.horz_banding = False
    for c, cw in enumerate(col_widths):
        tbl.columns[c].width = Inches(cw)
    for r, rh in enumerate(row_heights):
        tbl.rows[r].height = Inches(rh)

    all_rows = [headers] + rows
    for r_idx, row_data in enumerate(all_rows):
        is_hdr = r_idx == 0
        is_last = r_idx == nrows - 1
        is_hl = (not is_hdr) and highlight_rows and ((r_idx - 1) in highlight_rows)
        for c_idx, cell_val in enumerate(row_data):
            cell = tbl.cell(r_idx, c_idx)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.04)
            cell.margin_bottom = Inches(0.04)

            cell.fill.solid()
            if is_hdr:
                cell.fill.fore_color.rgb = rgb(PANEL)
            elif is_hl:
                cell.fill.fore_color.rgb = rgb(NAVY_SOFT)
            elif r_idx % 2 == 0:
                cell.fill.fore_color.rgb = rgb(TABLE_ALT)
            else:
                cell.fill.fore_color.rgb = rgb(WHITE)

            if is_hdr:
                set_cell_border(cell, top=(NAVY, 1.4), bottom=(NAVY, 1.0))
            elif is_last:
                set_cell_border(cell, bottom=(NAVY, 1.4))
            else:
                set_cell_border(cell, bottom=(BORDER, 0.5))

            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            if aligns is not None:
                p.alignment = aligns[c_idx]
            else:
                p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER

            parts = [(cell_val, {})] if isinstance(cell_val, str) else cell_val
            for txt, st in parts:
                run = p.add_run()
                run.text = txt
                set_run_font(
                    run,
                    size_pt=st.get("size", header_size if is_hdr else body_size),
                    color_hex=st.get("color", NAVY if is_hdr else (NAVY if is_hl else BODY)),
                    bold=st.get("bold", is_hdr or is_hl),
                    italic=st.get("italic", False),
                    baseline=st.get("baseline"),
                )
    return tbl_shape


def add_chrome(slide, page_label: str, kicker: str, title, footer_bar=None):
    # Top kicker & crisp title
    textbox(slide, L, 0.34, 9.5, 0.24, [[(kicker, {})]], size=10.5, color=NAVY, bold=True)
    title_parts = [(title, {})] if isinstance(title, str) else title
    textbox(slide, L, 0.60, CW, 0.52, [title_parts], size=21.5, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    rect(slide, L, 1.20, CW, 0.015, BORDER)
    rect(slide, L, 1.19, 1.25, 0.035, NAVY)

    # Optional clean bottom takeaway strip
    if footer_bar is not None:
        by, bh = 6.30, 0.54
        rect(slide, L, by, CW, bh, PANEL, line_hex=BORDER, line_pt=0.5)
        rect(slide, L, by, 0.065, bh, NAVY)
        parts = [(footer_bar, {})] if isinstance(footer_bar, str) else footer_bar
        textbox(slide, L + 0.20, by + 0.02, CW - 0.32, bh - 0.04, [parts],
                size=11.5, color=INK, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.15)

    # Subtle page number only (no left running footer)
    textbox(slide, W - R - 1.8, 7.02, 1.8, 0.26, [[(page_label, {})]],
            size=9.5, color=MUTED, bold=True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def set_note(slide, text: str):
    slide.notes_slide.notes_text_frame.text = text


# ------------------------------------------------------------------ build ----
def build() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "同面积薄膜的形状怎样影响退磁场与磁化翻转？"
    prs.core_properties.author = "孙煜凡、韦中天"
    prs.core_properties.subject = "课题组组会汇报（精简完整版，8正片+4备份）"

    # ============================================================== Slide 1 ==
    # Clean Cover with proportional vector geometries (no kicker, no bottom bar)
    s1 = new_slide(prs)
    rect(s1, L, 0.96, 0.08, 1.62, NAVY)
    textbox(s1, 0.94, 0.94, 11.6, 0.96,
            [[("同面积薄膜的形状怎样影响退磁场与磁化翻转？", {})]],
            size=31.0, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s1, 0.94, 1.98, 11.5, 0.46,
            [[("圆形、方形与 4:1 长方形的静态退磁分布、中心局部场与准静态翻转对比", {})]],
            size=15.5, color=BODY, anchor=MSO_ANCHOR.MIDDLE)

    rect(s1, L, 2.94, CW, 0.015, BORDER)

    # Subtle label for the geometry strip
    textbox(s1, L, 3.24, CW, 0.30,
            [[("等面积控制变量对比（按真实比例绘制）：目标面积 40,000 nm²  ·  厚度 4 nm  ·  1 nm & 2 nm 双网格", {})]],
            size=11.2, color=MUTED, align=PP_ALIGN.CENTER)

    # Equal-area proportional geometry illustration (1 nm = 0.0086 in)
    scale = 0.0086
    cy = 4.90  # vertical center of shapes
    # Circle: D = 225.676 nm -> 1.94 in
    d_in = 225.676 * scale
    c_cx = 2.35
    oval(s1, c_cx - d_in / 2, cy - d_in / 2, d_in, d_in, NAVY_SOFT, NAVY, 1.6)
    textbox(s1, c_cx - 1.3, 6.06, 2.6, 0.58,
            [[("圆形", {"bold": True, "size": 14.0, "color": INK})],
             [("R = 112.84 nm", {"size": 11.5, "color": MUTED})]],
            align=PP_ALIGN.CENTER, space_after=1.5)

    # Square: 200 x 200 nm -> 1.72 in
    sq_in = 200.0 * scale
    sq_cx = 5.75
    rect(s1, sq_cx - sq_in / 2, cy - sq_in / 2, sq_in, sq_in, NAVY_SOFT, NAVY, 1.6)
    textbox(s1, sq_cx - 1.3, 6.06, 2.6, 0.58,
            [[("方形", {"bold": True, "size": 14.0, "color": INK})],
             [("200 × 200 nm", {"size": 11.5, "color": MUTED})]],
            align=PP_ALIGN.CENTER, space_after=1.5)

    # Rectangle (4:1): 400 x 100 nm -> 3.44 x 0.86 in
    rw_in, rh_in = 400.0 * scale, 100.0 * scale
    rc_cx = 10.15
    rect(s1, rc_cx - rw_in / 2, cy - rh_in / 2, rw_in, rh_in, NAVY_SOFT, NAVY, 1.6)
    textbox(s1, rc_cx - 1.6, 6.06, 3.2, 0.58,
            [[("4:1 长方形", {"bold": True, "size": 14.0, "color": INK})],
             [("400 × 100 nm", {"size": 11.5, "color": MUTED})]],
            align=PP_ALIGN.CENTER, space_after=1.5)

    set_note(
        s1,
        "各位老师好，今天汇报“同面积薄膜的形状怎样影响退磁场与磁化翻转”。"
        "屏幕上按真实比例画出了三种薄膜：圆形、方形和 4:1 长方形。它们材料参数相同、厚度都是 4 nm、俯视面积都是 40,000 nm²，唯一变量是平面轮廓。"
        "长方形周长最大，靠边材料更多，全片平均退磁场明显更弱；那它的磁化翻转场是不是也会跟着变？接下来用 8 分钟把完整证据链讲清楚。"
    )

    # ============================================================== Slide 2 ==
    # 01 / Model & Simulation Protocol (clean, scannable, complete)
    s2 = new_slide(prs)
    add_chrome(
        s2,
        "2 / 8",
        "01 / 模型与仿真协议",
        "控制面积、厚度与微扰规则一致，建立三形状双网格公平基准",
        [("模型范围：", {"bold": True, "color": NAVY}),
         ("采用零温、无缺陷、无 DMI 教学模型参数，用于纯磁性几何效应对比，不代表真实 QAH 材料标定或输运验证。", {})],
    )

    textbox(s2, L, 1.38, 6.7, 0.28, [[("几何、材料参数与求解器设置", {})]], size=12.5, color=INK, bold=True)
    p_rows = [
        ["平面几何", "圆形 R = 112.84 nm；方形 200×200 nm；长方形 400×100 nm"],
        ["面积与厚度", "目标面积 40,000 nm²（2 nm 圆形 39,936 nm², −0.16%）；厚 4 nm"],
        ["材料参数", [("M", {}), sub("s"), (" = 3×10", {}), sup("5"), (" A/m；A = 5×10", {}), sup("−12"),
                    (" J/m；K", {}), sub("u"), (" = 8×10", {}), sup("4"), (" J/m", {}), sup("3"), ("（易轴 z）", {})]],
        ["特征尺度", [("交换长度 ℓ", {}), sub("ex"), (" = 9.403 nm；各向异性场 B", {}), sub("K"), (" = 533.33 mT", {})]],
        ["网格与求解", "OOMMF 2.0b0；α = 0.5 关进动；主算 2×2×2 nm，复核 1×1×1 nm"],
    ]
    add_table(
        s2, L, 1.72, 6.85, [1.45, 5.40],
        ["项目", "固定设置"],
        p_rows,
        header_size=11.0, body_size=11.0,
        row_heights=[0.40, 0.72, 0.72, 0.72, 0.72, 0.72],
        aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT],
    )

    rx, rw = 7.80, 4.88
    # Card 1: Sweep & convergence
    rect(s2, rx, 1.72, rw, 1.92, WHITE, line_hex=BORDER, line_pt=0.75)
    rect(s2, rx, 1.72, 0.06, 1.92, NAVY)
    textbox(s2, rx + 0.22, 1.84, rw - 0.36, 0.30, [[("扫场与双阈值收敛验收", {})]], size=12.5, color=NAVY, bold=True)
    add_bullets(
        s2, rx + 0.22, 2.22, rw - 0.36, 1.32,
        [
            [("完整磁滞：", {"bold": True}), ("±0.6 T，粗步 20 mT（121 点/回线）。", {})],
            [("翻转区加密：", {"bold": True}), ("10 mT → 5 mT 夹逼区间。", {})],
            [("双停止阈值：", {"bold": True}), ("常规 0.01 与严格 0.005 °/ns。", {})],
        ],
        size=11.2, space_after=5.0,
    )

    # Card 2: Transverse perturbation
    rect(s2, rx, 3.84, rw, 1.88, PANEL, line_hex=BORDER, line_pt=0.75)
    rect(s2, rx, 3.84, 0.06, 1.88, NAVY)
    textbox(s2, rx + 0.22, 3.96, rw - 0.36, 0.30, [[("统一反向场横向微扰协议", {})]], size=12.5, color=NAVY, bold=True)
    add_bullets(
        s2, rx + 0.22, 4.34, rw - 0.36, 1.28,
        [
            [("破除零力矩驻点：", {"bold": True}), ("反向场下加 (ε, 0.37ε, 0) 归一化（默认 ε = 10", {}), sup("−3"), ("）。", {})],
            [("幅度稳健性：", {"bold": True}), ("2 nm 网格验证 ε = 10", {}), sup("−4"), ("、10", {}), sup("−3"), ("、10", {}), sup("−2"), (" 结果一致。", {})],
        ],
        size=11.2, space_after=5.0,
    )

    set_note(
        s2,
        "先快速交代模型基准。左表是固定的几何和材料参数：三种形状同面积、同厚度 4 nm；两个关键特征尺度是交换长度 9.403 nm 和单轴各向异性场 533.33 mT。"
        "我们在 OOMMF 中用 2 nm 主算、1 nm 复核。右边是扫场与微扰协议：翻转区加密到 5 mT 并做 0.01 和 0.005 °/ns 双阈值校验；"
        "反向场下统一施加 ε = 10^-3 的小横向微扰破除零力矩驻点，并在 2 nm 验证了跨两个数量级的不变性。"
    )

    # ============================================================== Slide 3 ==
    # 02 / Mainline 1: Whole-film demag factor & edge band
    s3 = new_slide(prs)
    add_chrome(
        s3,
        "3 / 8",
        "02 / 主线一：全片平均退磁场为何不同",
        "弱退磁边缘带占比最高，拉低了长方形的全片平均退磁场",
        [("主线一结论：", {"bold": True, "color": NAVY}),
         ("1 nm 网格下全片平均 N", {}), sub("z"),
         (" 为 圆形 0.9443 > 方形 0.9409 > 长方形 0.9292；长方形全片平均退磁场比圆形弱 5.70 mT。", {})],
    )

    # Left: full demag_comparison.png (spatial maps + central profiles)
    rect(s3, L, 1.38, 6.80, 4.72, WHITE, line_hex=BORDER, line_pt=0.75)
    add_picture_fitted(s3, "demag_comparison.png", L + 0.08, 1.44, 6.64, 4.18)
    textbox(s3, L + 0.14, 5.64, 6.52, 0.40,
            [[("2 nm 网格，固定 +z 均匀磁化：底层面外退磁场 μ", {}), sub("0"), ("H", {}), sub("d,z"),
              (" 空间分布与中心剖面（边缘处反向退磁场明显衰减）", {})]],
            size=9.8, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # Right: compact 1 nm quantitative table + 2 crisp takeaways
    rx3, rw3 = 7.68, 5.00
    textbox(s3, rx3, 1.38, rw3, 0.30, [[("1 nm 网格全片与边缘带（距侧边 ≤ 9.40 nm）统计", {})]], size=11.5, color=INK, bold=True)

    edge_rows = []
    for sh_key, sh_cn in [("circle", "圆形"), ("square", "方形"), ("rectangle", "4:1 长方形")]:
        lf = LOCAL_FIELDS[(sh_key, 1)]
        pct = lf["edge"]["cells"] / lf["all"]["cells"] * 100.0
        edge_rows.append([
            sh_cn,
            f"{DEMAG[(sh_key, 1, 'z')]:.4f}",
            f"{lf['all']['B_mT']:.2f}",
            f"{pct:.2f}%",
        ])

    add_table(
        s3, rx3, 1.74, rw3, [1.30, 1.15, 1.35, 1.20],
        ["形状", [("全片 N", {}), sub("z")], [("全片均值 (mT)", {})], "边缘带占比"],
        edge_rows,
        header_size=10.5, body_size=11.2,
        row_heights=[0.42, 0.48, 0.48, 0.50],
        aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER],
        highlight_rows={2},
    )

    # Clean highlight callout below table
    rect(s3, rx3, 3.84, rw3, 2.26, PANEL, line_hex=BORDER, line_pt=0.75)
    rect(s3, rx3, 3.84, 0.06, 2.26, NAVY)
    textbox(s3, rx3 + 0.22, 3.98, rw3 - 0.34, 0.28, [[("为什么长方形全片平均场最弱？", {})]], size=12.0, color=NAVY, bold=True)
    add_bullets(
        s3, rx3 + 0.22, 4.34, rw3 - 0.34, 1.66,
        [
            [("边缘带占比高：", {"bold": True}), ("长方形周长最大，距边 ≤ ℓ", {}), sub("ex"), (" 的弱场边缘带占 ", {}), ("21.69%", {"bold": True, "color": NAVY}), ("（圆形仅 15.99%）。", {})],
            [("内部平台略弱：", {"bold": True}), ("短边仅 100 nm，内部面外场也弱约 3.05 mT。", {})],
            [("两项叠加：", {"bold": True}), ("全片平均退磁场比圆形弱 ", {}), ("5.70 mT", {"bold": True, "color": NAVY}), ("。", {})],
        ],
        size=11.0, space_after=5.0,
    )

    set_note(
        s3,
        "第一步，把磁化固定均匀朝上，看静态退磁场。左图是三种形状的空间云图和中心剖面：内部基本是深色强退磁平台，一到侧边曲线明显翘起，反向退磁场迅速变弱。"
        "看右表 1 nm 网格统计：按交换长度 9.40 nm 划定边缘带，长方形边缘带体积占比高达 21.69%，比圆形高出近 5.7 个百分点，加上内部平台也略弱，"
        "最终长方形全片平均 Nz 最低，平均退磁场比圆形弱 5.70 mT。"
    )

    # ============================================================== Slide 4 ==
    # 03 / Mainline 2: Whole-film average -> Central local field (Mechanism!)
    s4 = new_slide(prs)
    add_chrome(
        s4,
        "4 / 8",
        "03 / 主线二：从全片平均转向中心局部场",
        "聚焦中心核心区后，圆形与长方形的退磁场差由 5.70 缩至 3.27 mT",
        [("机制定位：", {"bold": True, "color": NAVY}),
         ("膜厚（4 nm）远小于最短边（100 nm），越靠近中心侧边界影响越弱；若翻转始于中心，全片均值差异不能直接代表局部驱动场差。", {})],
    )

    # Left: Visual comparison bar card (5.70 mT vs 3.27 mT)
    lx4, lw4 = L, 5.55
    rect(s4, lx4, 1.44, lw4, 4.62, WHITE, line_hex=BORDER, line_pt=0.75)
    textbox(s4, lx4 + 0.24, 1.60, lw4 - 0.48, 0.34,
            [[("圆形 vs 长方形：面外退磁场幅值差（1 nm）", {})]],
            size=12.5, color=INK, bold=True)

    # Bar 1: Whole film 5.70 mT
    textbox(s4, lx4 + 0.24, 2.16, 2.4, 0.28, [[("全片平均（含边缘带）", {})]], size=11.5, color=BODY, bold=True)
    rect(s4, lx4 + 0.24, 2.50, 3.65, 0.44, NAVY)
    textbox(s4, lx4 + 4.00, 2.46, 1.40, 0.50, [[("5.70 mT", {})]], size=17.5, color=NAVY, bold=True, anchor=MSO_ANCHOR.MIDDLE)

    # Bar 2: Core 3.27 mT (proportional width: 3.27/5.70 * 3.65 = 2.09 in)
    textbox(s4, lx4 + 0.24, 3.24, 3.4, 0.28, [[("中心核心区（r ≤ ℓ", {}), sub("ex"), (" = 9.40 nm）", {})]], size=11.5, color=BODY, bold=True)
    rect(s4, lx4 + 0.24, 3.58, 2.09, 0.44, BAR_LIGHT, line_hex=NAVY, line_pt=1.0)
    textbox(s4, lx4 + 2.45, 3.54, 1.50, 0.50, [[("3.27 mT", {})]], size=17.5, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s4, lx4 + 4.00, 3.58, 1.35, 0.42, [[("收窄 43%", {})]], size=11.5, color=NAVY, bold=True, anchor=MSO_ANCHOR.MIDDLE)

    # Short explanation inside left card
    rect(s4, lx4 + 0.24, 4.38, lw4 - 0.48, 1.44, PANEL)
    add_bullets(
        s4, lx4 + 0.38, 4.50, lw4 - 0.76, 1.22,
        [
            "全片差值被大面积边缘带放大；进入内部后侧边退磁衰减效应迅速减弱。",
            "核心区取几何中心半径 9.40 nm 圆区并沿厚度平均（约 1,104 单元）。",
        ],
        size=10.8, space_after=5.0,
    )

    # Right: Clean 1 nm regional field table + core highlight
    rx4, rw4 = 6.48, 6.20
    textbox(s4, rx4, 1.44, rw4, 0.30, [[("1 nm 网格各区域面外退磁场 μ", {}), sub("0"), ("H", {}), sub("d,z"), (" (mT)", {})]], size=12.0, color=INK, bold=True)

    reg_rows = []
    for sh_key, sh_cn in [("circle", "圆形"), ("square", "方形"), ("rectangle", "4:1 长方形")]:
        lf = LOCAL_FIELDS[(sh_key, 1)]
        reg_rows.append([
            sh_cn,
            f"{lf['all']['B_mT']:.2f}",
            f"{lf['interior']['B_mT']:.2f}",
            f"{lf['core']['B_mT']:.2f}",
            f"{lf['edge']['B_mT']:.2f}",
        ])
    add_table(
        s4, rx4, 1.80, rw4, [1.30, 1.22, 1.22, 1.24, 1.22],
        ["形状", "全片均值", "内部区", "中心核心区", "边缘带"],
        reg_rows,
        header_size=10.5, body_size=11.2,
        row_heights=[0.44, 0.54, 0.54, 0.56],
        aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER],
        highlight_rows={2},
    )

    # Key observation box on right
    rect(s4, rx4, 4.14, rw4, 1.92, NAVY_SOFT, line_hex=NAVY, line_pt=0.75)
    textbox(s4, rx4 + 0.24, 4.28, rw4 - 0.48, 0.30, [[("核心区对比：形状差异已明显钝化", {})]], size=12.5, color=NAVY, bold=True)
    add_bullets(
        s4, rx4 + 0.24, 4.66, rw4 - 0.48, 1.28,
        [
            [("圆形 vs 方形：", {"bold": True}), ("核心区仅差 ", {}), ("0.11 mT", {"bold": True, "color": NAVY}), ("（−370.29 对 −370.19 mT）。", {})],
            [("圆形 vs 长方形：", {"bold": True}), ("核心区场差缩至 ", {}), ("3.27 mT", {"bold": True, "color": NAVY}), ("，已小于 5 mT 扫场步长。", {})],
            [("物理含义：", {"bold": True}), ("静态局部场差提供了尺度参考，但实际翻转仍需看动态过程。", {})],
        ],
        size=11.0, space_after=4.5,
    )

    set_note(
        s4,
        "刚才看的是全片均值。但如果把镜头缩到几何中心附近——半径为一个交换长度 9.40 nm 的核心区，结果立刻不同。"
        "左图可以看到，圆形和长方形的退磁场差从全片的 5.70 mT 收窄到了 3.27 mT，降了超过四成；右表里圆形和方形在中心更是只差 0.11 mT。"
        "原因很直观：薄膜只有 4 nm 厚，长方形短边也有 100 nm，越往中心走，侧边界的影响越小。接下来我们看撤场零态和真正的扫场翻转。"
    )

    # ============================================================== Slide 5 ==
    # 04 / Zero-field background: Domain energy competition & full hysteresis
    s5 = new_slide(prs)
    add_chrome(
        s5,
        "5 / 8",
        "04 / 零场背景：能量竞争与完整磁滞回线",
        "分畴的畴壁代价高于退磁收益，撤场后三形状均保持近饱和剩磁",
        [("背景结论：", {"bold": True, "color": NAVY}),
         ("两套网格共 6 条完整回线（726 场点）高度重合，撤场后 |M", {}), sub("r"), ("|/M", {}), sub("s"),
         (" > 0.999999，均稳定于近单畴态。", {})],
    )

    # Left: domain_energy_competition.png
    w_half = 5.86
    rect(s5, L, 1.38, w_half, 4.74, WHITE, line_hex=BORDER, line_pt=0.75)
    textbox(s5, L + 0.18, 1.48, w_half - 0.36, 0.30, [[("零场双畴 − 近单畴能量差（2 nm 网格）", {})]], size=11.8, color=INK, bold=True)
    add_picture_fitted(s5, "domain_energy_competition.png", L + 0.10, 1.82, w_half - 0.20, 3.40)
    textbox(s5, L + 0.18, 5.26, w_half - 0.36, 0.78,
            [[("分畴虽降低退磁能（蓝柱），但交换 + 各向异性畴壁代价更高；三种形状总能量差均为正（", {}),
              ("+3.35 至 +7.11 kJ/m", {"bold": True, "color": NAVY}), sup("3", bold=True, color=NAVY), ("）。", {})]],
            size=10.5, color=BODY, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.20)

    # Right: hysteresis_comparison.png
    rx5 = L + w_half + 0.31
    rect(s5, rx5, 1.38, w_half, 4.74, WHITE, line_hex=BORDER, line_pt=0.75)
    textbox(s5, rx5 + 0.18, 1.48, w_half - 0.36, 0.30, [[("完整磁滞回线与总能曲线（1 nm & 2 nm）", {})]], size=11.8, color=INK, bold=True)
    add_picture_fitted(s5, "hysteresis_comparison.png", rx5 + 0.10, 1.82, w_half - 0.20, 3.40)
    textbox(s5, rx5 + 0.18, 5.26, w_half - 0.36, 0.78,
            [[("±0.6 T 完整回线呈近理想矩形；六条曲线在 20 mT 粗步下几乎完全重合，翻转均集中在 ", {}),
              ("±180–200 mT", {"bold": True, "color": NAVY}), (" 附近。", {})]],
            size=10.5, color=BODY, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.20)

    set_note(
        s5,
        "在看精细翻转场之前，先确认零场剩磁背景。左图对比了双畴态和近单畴态的能量：分畴确实降低退磁能，但交换能和各向异性能组成的畴壁代价更高，三形状总能都高出 3.35 到 7.11 kJ/m³。"
        "所以看右图完整磁滞回线，撤掉外场后三种薄膜都稳稳保持近饱和面外剩磁，6 条曲线几乎完全重合。接下来我们对翻转区做 5 mT 精细夹逼。"
    )

    # ============================================================== Slide 6 ==
    # 05 / Mainline 3 (Evidence 1): 12/12 Refined Switching Field Matrix
    s6 = new_slide(prs)
    add_chrome(
        s6,
        "6 / 8",
        "05 / 主线三（证据一）：精细翻转场验收",
        "12 条支路翻转场全部落在 180–185 mT，5 mT 分辨率下无法排序",
        [("证据一结论：", {"bold": True, "color": NAVY}),
         ("3 形状 × 2 网格 × 正反两支全部通过 5 mT 及双停止阈值验收，翻转场幅值均夹逼于 180–185 mT（中点 182.5 mT）。", {})],
    )

    # Left: clean 6-row verification matrix (all 12 branches!)
    textbox(s6, L, 1.38, 7.35, 0.28, [[("全部 12 支路 5 mT 夹逼区间与 ±185 mT 最小平均模长 |<m>|", {}), sub("min")]], size=11.8, color=INK, bold=True)
    m_rows = []
    for sh_key, sh_cn in [("circle", "圆形"), ("square", "方形"), ("rectangle", "4:1 长方形")]:
        for cell in (2, 1):
            r_desc = REFINED_REV[(sh_key, cell, 0, 0.01)]
            r_asc = REFINED_REV[(sh_key, cell, 1, 0.01)]
            m_rows.append([
                f"{sh_cn}（{cell} nm）",
                "−185 至 −180",
                "+180 至 +185",
                f"{r_desc['min_norm']:.3f} / {r_asc['min_norm']:.3f}",
                "通过",
            ])
    add_table(
        s6, L, 1.72, 7.45, [1.85, 1.45, 1.45, 1.75, 0.95],
        ["算例（形状 / 网格）", "下降支 (mT)", "返回支 (mT)", [("|<m>|", {}), sub("min"), (" (降/返)", {})], "双阈值"],
        m_rows,
        header_size=10.2, body_size=10.8,
        row_heights=[0.42] + [0.58] * 6,
        aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER],
        highlight_rows={4, 5},
    )

    # Right: 2 concise metric & robustness cards
    rx6, rw6 = 8.38, 4.30
    rect(s6, rx6, 1.72, rw6, 1.78, NAVY_SOFT, line_hex=NAVY, line_pt=0.9)
    textbox(s6, rx6 + 0.22, 1.84, rw6 - 0.44, 0.26, [[("12 / 12 支路统一夹逼区间", {})]], size=11.0, color=NAVY, bold=True)
    textbox(s6, rx6 + 0.22, 2.16, rw6 - 0.44, 0.56, [[("180 – 185 mT", {})]], size=26.0, color=NAVY, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s6, rx6 + 0.22, 2.80, rw6 - 0.44, 0.58,
            [[("场步由 10 mT 加密至 5 mT 后，区间从 180–190 收窄至 180–185 mT，三形状仍完全重叠。", {})]],
            size=10.5, color=BODY, line_spacing=1.22)

    rect(s6, rx6, 3.70, rw6, 2.34, PANEL, line_hex=BORDER, line_pt=0.75)
    rect(s6, rx6, 3.70, 0.06, 2.34, NAVY)
    textbox(s6, rx6 + 0.22, 3.84, rw6 - 0.36, 0.28, [[("数值稳健性复核", {})]], size=12.0, color=INK, bold=True)
    add_bullets(
        s6, rx6 + 0.22, 4.20, rw6 - 0.36, 1.72,
        [
            [("网格无关：", {"bold": True}), ("2 nm 与 1 nm 区间完全一致。", {})],
            [("阈值无关：", {"bold": True}), ("0.01 → 0.005 °/ns 区间不变。", {})],
            [("非均匀信号：", {"bold": True}), ("±185 mT 处 |<m>|", {}), sub("min"), (" 均远小于 1（长方形低至 ", {}), ("0.34", {"bold": True, "color": NAVY}), ("），预告非一致翻转。", {})],
        ],
        size=10.8, space_after=5.0,
    )

    set_note(
        s6,
        "左表汇总了 3 种形状、2 套网格、正反两个方向共 12 条支路的精细翻转场结果。所有下降支都在 −180 到 −185 mT 之间翻转，返回支都在 +180 到 +185 mT 之间翻转，"
        "收紧停止阈值一倍后区间完全不变。也就是说，在 5 mT 分辨率下排不出形状先后。"
        "但注意第四列：在翻转场点 ±185 mT，平均磁化模长最低掉到了 0.34 到 0.58，远远小于 1——这直接说明薄膜不是整片一致旋转的。下面看翻转空间过程。"
    )

    # ============================================================== Slide 7 ==
    # 06 / Mainline 3 (Evidence 2): Central Nucleation + Cross-mesh Verification
    s7 = new_slide(prs)
    add_chrome(
        s7,
        "7 / 8",
        "06 / 主线三（证据二）：翻转路径与跨网格复核",
        "翻转始于几何中心而非一致旋转，2 nm 快照与 1 nm 轨迹相互印证",
        [("证据二结论：", {"bold": True, "color": NAVY}),
         ("2 nm 空间快照定位成核于几何中心，1 nm / 2 nm 标量轨迹在 −200 mT 与 ±185 mT 均一致证实非均匀翻转。", {})],
    )

    # Left: reversal_trajectory.png (all 3 shapes!)
    lw7 = 6.18
    rect(s7, L, 1.38, lw7, 4.74, WHITE, line_hex=BORDER, line_pt=0.75)
    textbox(s7, L + 0.16, 1.46, lw7 - 0.32, 0.28, [[("空间演化：2 nm 网格 −200 mT 下降支快照（三形状）", {})]], size=11.2, color=INK, bold=True)
    add_picture_fitted(s7, "reversal_trajectory.png", L + 0.08, 1.76, lw7 - 0.16, 3.86)
    textbox(s7, L + 0.16, 5.66, lw7 - 0.32, 0.40,
            [[("红=+z，蓝=−z：方形与圆形由中心向外扩张；长方形先形成中央反向带再推向两端。", {})]],
            size=9.8, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # Right: cross_mesh_reversal_odt.png + concise ±185 mT cross-mesh verification note
    rx7, rw7 = L + lw7 + 0.25, CW - lw7 - 0.25
    rect(s7, rx7, 1.38, rw7, 3.42, WHITE, line_hex=BORDER, line_pt=0.75)
    textbox(s7, rx7 + 0.16, 1.46, rw7 - 0.32, 0.28, [[("跨网格标量轨迹：2 nm vs 1 nm（−200 mT）", {})]], size=11.2, color=INK, bold=True)
    add_picture_fitted(s7, "cross_mesh_reversal_odt.png", rx7 + 0.08, 1.76, rw7 - 0.16, 2.94)

    rect(s7, rx7, 4.94, rw7, 1.18, NAVY_SOFT, line_hex=NAVY, line_pt=0.75)
    add_bullets(
        s7, rx7 + 0.18, 5.04, rw7 - 0.32, 0.98,
        [
            [("跨网格重合：", {"bold": True}), ("−200 mT 下两套网格 |<m>| 均跌至 0.42–0.61。", {})],
            [("±185 mT 复核：", {"bold": True}), ("24 条细化轨迹均显非均匀翻转（长方形 2 nm / 1 nm 均为 ", {}), ("0.34", {"bold": True, "color": NAVY}), ("）；成核位置由 2 nm 快照确定。", {})],
        ],
        size=10.4, space_after=4.0, line_spacing=1.18,
    )

    set_note(
        s7,
        "这一页把空间快照和跨网格标量轨迹放在一起。看左图 2 nm 快照：不管是方形、圆形还是长方形，最早变浅变蓝的反向区域都在几何中心附近——"
        "方和圆从中心向外扩张，长方形先在中间形成反向带再向两头推进。"
        "看右图，1 nm 和 2 nm 的平均磁化模长曲线几乎完全叠在一起，翻转瞬间明显下探到 0.42 到 0.61；在更接近阈值的 ±185 mT 下，24 条细化轨迹同样证实非均匀翻转。"
        "到这里，全片均值分化、中心场差收敛、翻转场落同区间三条线就彻底闭环了。"
    )

    # ============================================================== Slide 8 ==
    # 07 / Summary & Scope Boundaries
    s8 = new_slide(prs)
    add_chrome(
        s8,
        "8 / 8",
        "07 / 总结与适用边界",
        "形状清晰改变全片平均退磁场，准静态翻转由中心局部过程主导",
    )

    items = [
        (
            "01",
            "全片平均退磁场清晰分化",
            [("1 nm 网格下全片 N", {}), sub("z"), (" 满足 ", {}),
             ("圆形 0.9443 > 方形 0.9409 > 长方形 0.9292", {"bold": True, "color": NAVY}),
             ("（全片场差 ", {}), ("5.70 mT", {"bold": True}),
             ("）。长方形弱退磁边缘带占比最高（21.69% 对 15.99%），是拉低全片均值的主因。", {})],
        ),
        (
            "02",
            "中心局部成核收敛形状差异",
            [("翻转并非一致旋转，而是始于几何中心附近；在半径 9.40 nm 的中心核心区，圆形与长方形的退磁场差已由 5.70 mT 收窄至 ", {}),
             ("3.27 mT", {"bold": True, "color": NAVY}),
             ("（圆形与方形仅差 0.11 mT），解释了为何全片均值无法直接映射为矫顽场排序。", {})],
        ),
        (
            "03",
            "12 / 12 支路验收闭合",
            [("3 形状 × 2 网格 × 正反两支全部落在 ", {}),
             ("180–185 mT", {"bold": True, "color": NAVY}),
             (" 同一区间；零场均稳定于近单畴态（|M", {}), sub("r"), ("|/M", {}), sub("s"),
             (" > 0.999999）。488 算例、82 项汇总检查与 3,118 项输出审计全部通过。", {})],
        ),
    ]

    y_cur = 1.46
    for num, heading, desc in items:
        rect(s8, L, y_cur, CW, 1.18, WHITE, line_hex=BORDER, line_pt=0.75)
        rect(s8, L, y_cur, 0.86, 1.18, NAVY)
        textbox(s8, L, y_cur, 0.86, 1.18, [[(num, {})]], size=20.0, color=WHITE, bold=True,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        textbox(s8, L + 1.08, y_cur + 0.12, CW - 1.30, 0.30, [[(heading, {})]], size=13.5, color=INK, bold=True)
        textbox(s8, L + 1.08, y_cur + 0.46, CW - 1.30, 0.62, [desc], size=11.2, color=BODY, line_spacing=1.22)
        y_cur += 1.34

    # Bottom Scope & Next-Step Box
    rect(s8, L, 5.54, CW, 1.24, PANEL, line_hex=BORDER, line_pt=0.75)
    rect(s8, L, 5.54, 0.07, 1.24, NAVY)
    textbox(s8, L + 0.24, 5.66, CW - 0.44, 0.28, [[("适用边界与后续方向", {})]], size=12.0, color=NAVY, bold=True)
    add_bullets(
        s8, L + 0.24, 5.98, CW - 0.44, 0.72,
        [
            [("当前边界：", {"bold": True}), ("零温、无缺陷、无 DMI 教学模型 + 5 mT 扫场步长，结论不外推至真实 QAH 器件或实验输运。", {})],
            [("后续扩展：", {"bold": True}), ("若需分辨 < 5 mT 的细微形状矫顽场差，可进一步加密至 1–2.5 mT，并引入边缘缺陷或热涨落检验成核点迁移。", {})],
        ],
        size=10.6, space_after=3.5, line_spacing=1.18,
    )

    set_note(
        s8,
        "最后用三点收尾：第一，形状确实清晰改变全片平均退磁场，边缘带占比让长方形全片平均场比圆形弱 5.70 mT；"
        "第二，翻转始于中心附近，核心区场差缩到 3.27 mT，因此不能用全片均值直接推断矫顽场高低；"
        "第三，12 条支路在 5 mT 步长下全部落在 180–185 mT，488 个算例验收全部通过。以上结论严格限定于零温无缺陷模型。我的汇报到这里，谢谢各位老师，欢迎提问。"
    )

    # ======================================================== Backup B1 ======
    b1 = new_slide(prs)
    add_chrome(
        b1,
        "备份 B1",
        "备份页 B1 / 完整静态退磁因子与分区场对照",
        [("1 nm 与 2 nm 网格完整退磁因子 N", {}), sub("x"), ("、N", {}), sub("y"), ("、N", {}), sub("z"), (" 与分区面外场", {})],
    )
    b1_rows = []
    for cell in (1, 2):
        for sh_key, sh_cn in [("circle", "圆形"), ("square", "方形"), ("rectangle", "4:1 长方形")]:
            lf = LOCAL_FIELDS[(sh_key, cell)]
            edge_pct = lf["edge"]["cells"] / lf["all"]["cells"] * 100.0
            b1_rows.append([
                f"{sh_cn}（{cell} nm）",
                f"{DEMAG[(sh_key, cell, 'x')]:.6f}",
                f"{DEMAG[(sh_key, cell, 'y')]:.6f}",
                f"{DEMAG[(sh_key, cell, 'z')]:.6f}",
                f"{lf['all']['B_mT']:.2f}",
                f"{lf['core']['B_mT']:.2f}",
                f"{lf['edge']['B_mT']:.2f}",
                f"{edge_pct:.2f}%",
            ])
    add_table(
        b1, L, 1.50, CW, [1.85, 1.38, 1.38, 1.38, 1.48, 1.54, 1.54, 1.48],
        ["形状 / 网格", [("N", {}), sub("x")], [("N", {}), sub("y")], [("N", {}), sub("z")],
         "全片 (mT)", "核心区 (mT)", "边缘带 (mT)", "边缘带占比"],
        b1_rows,
        header_size=10.5, body_size=10.8,
        row_heights=[0.46] + [0.64] * 6,
        aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 7,
        highlight_rows={2, 5},
    )
    textbox(b1, L, 6.00, CW, 0.60,
            [[("注：核心区定义为距几何中心 r ≤ ℓ", {}), sub("ex"), (" = 9.403 nm 的圆区；边缘带定义为距侧边 ≤ 9.403 nm 的外环区；圆形 2 nm 网格加密到 1 nm 后 N", {}),
              sub("z"), (" 变化 0.000327，三形状排序完全一致。", {})]],
            size=10.5, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)

    # ======================================================== Backup B2 ======
    b2 = new_slide(prs)
    add_chrome(
        b2,
        "备份 B2",
        "备份页 B2 / 12 支路收敛明细与 20 mT 粗步终态",
        "12 支路 ±185 mT 收敛指标与粗场步终态对照",
    )
    b2_rows = []
    for sh_key, sh_cn in [("circle", "圆"), ("square", "方"), ("rectangle", "长")]:
        for cell in (2, 1):
            for br, br_cn in [(0, "降"), (1, "返")]:
                rr = REFINED_REV[(sh_key, cell, br, 0.01)]
                b2_rows.append([
                    f"{sh_cn}/{cell}nm/{br_cn}",
                    "−185..−180" if br == 0 else "+180..+185",
                    f"{rr['min_norm']:.4f}",
                    f"{rr['iteration_end']:,}",
                    f"{rr['final_rate']:.5f}",
                ])
    add_table(
        b2, L, 1.42, 6.45, [1.35, 1.45, 1.15, 1.25, 1.25],
        ["支路", "5 mT 区间", [("|<m>|", {}), sub("min")], "收敛步数", "终态速率"],
        b2_rows,
        header_size=9.5, body_size=9.5,
        row_heights=[0.36] + [0.39] * 12,
        aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER],
    )
    rx_b2, rw_b2 = 7.34, 5.34
    rect(b2, rx_b2, 1.42, rw_b2, 4.18, WHITE, line_hex=BORDER, line_pt=0.75)
    add_picture_fitted(b2, "reversal_states.png", rx_b2 + 0.08, 1.48, rw_b2 - 0.16, 3.68)
    textbox(b2, rx_b2 + 0.12, 5.20, rw_b2 - 0.24, 0.34,
            [[("reversal_states.png（仅 2 nm，20 mT 粗场步 ±180/±200 mT 终态）", {})]],
            size=9.2, color=MUTED, align=PP_ALIGN.CENTER)
    rect(b2, rx_b2, 5.72, rw_b2, 0.90, PANEL, line_hex=BORDER, line_pt=0.75)
    textbox(b2, rx_b2 + 0.16, 5.78, rw_b2 - 0.32, 0.78,
            [[("严格阈值复核（0.005 °/ns）：12 支翻转区间完全不变；例如长方形 1 nm 返回支 +185 mT 经 117,111 步收敛，最小模长 0.3380。", {})]],
            size=9.8, color=BODY, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.20)

    # ======================================================== Backup B3 ======
    b3 = new_slide(prs)
    add_chrome(
        b3,
        "备份 B3",
        "备份页 B3 / 零场驻态与沿回线能量分项",
        "零场近单畴/双畴空间态与退磁、交换、各向异性能分解",
    )
    rect(b3, L, 1.42, 5.75, 4.90, WHITE, line_hex=BORDER, line_pt=0.75)
    textbox(b3, L + 0.16, 1.52, 5.43, 0.28, [[("零场驻态对比（近单畴态 vs 双畴态，2 nm）", {})]], size=11.0, color=INK, bold=True)
    add_picture_fitted(b3, "zero_states.png", L + 0.10, 1.88, 5.55, 4.28)

    rx_b3 = L + 5.98
    rw_b3 = CW - 5.98
    rect(b3, rx_b3, 1.42, rw_b3, 4.90, WHITE, line_hex=BORDER, line_pt=0.75)
    textbox(b3, rx_b3 + 0.16, 1.52, rw_b3 - 0.32, 0.28, [[("沿磁滞支路各能量分项演变（2 nm）", {})]], size=11.0, color=INK, bold=True)
    add_picture_fitted(b3, "energy_components.png", rx_b3 + 0.10, 2.25, rw_b3 - 0.20, 3.20)
    textbox(b3, rx_b3 + 0.16, 5.56, rw_b3 - 0.32, 0.64,
            [[("可见翻转前后主要能量释放来自 Zeeman 项，各向异性能与退磁能在静态平台区间基本保持恒定。", {})]],
            size=10.2, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)

    # ======================================================== Backup B4 ======
    b4 = new_slide(prs)
    add_chrome(
        b4,
        "备份 B4",
        "备份页 B4 / 数值复核与输出审计总览",
        "网格、场步、停止阈值、微扰幅度与 3,118 项输出审计全部闭合",
    )
    b4_rows = [
        ["网格收敛", "2×2×2 nm → 1×1×1 nm", "圆形 Nz 仅变化 0.000327；三形状排序与 12 支翻转区间完全一致"],
        ["场步加密", "20 mT → 10 mT → 5 mT", "翻转区间由 180–190 收窄为 180–185 mT（中点移 2.5 mT）"],
        ["停止阈值", "0.01 → 0.005 °/ns", "12 条支路严格阈值复核区间完全不变，最大能量增量为负"],
        ["横向微扰", "ε = 10⁻⁴, 10⁻³, 10⁻²", "2 nm 在 180/185 mT 端点三档一致；1 nm 采用默认 ε = 10⁻³"],
        ["完整审计", "488 算例目录", "82 项汇总检查与 3,118 项输出文件审计 100% 通过（pending = 0）"],
    ]
    add_table(
        b4, L, 1.55, CW, [1.80, 2.60, 7.63],
        ["复核维度", "验证范围", "核心结果"],
        b4_rows,
        header_size=11.5, body_size=11.5,
        row_heights=[0.48] + [0.84] * 5,
        aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
        highlight_rows={4},
    )

    return prs


if __name__ == "__main__":
    prs = build()
    out_path = OUT_PPTX
    try:
        prs.save(str(out_path))
    except PermissionError:
        out_path = OUT_PPTX.with_name(OUT_PPTX.stem.replace("_v2", "") + "_v3.pptx")
        prs.save(str(out_path))
    print(f"Saved: {out_path} ({len(prs.slides)} slides)")
