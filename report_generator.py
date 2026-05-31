import io
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image
)

DARK_BLUE   = colors.HexColor("#003366")
ACCENT_TEAL = colors.HexColor("#008bb0") 
LIGHT_BLUE  = colors.HexColor("#eef4f9")
GREEN       = colors.HexColor("#1e8449")
RED         = colors.HexColor("#c0392b")
ORANGE      = colors.HexColor("#e67e22") 
LIGHT_GREY  = colors.HexColor("#f8f9fa")
MID_GREY    = colors.HexColor("#bdc3c7")
TABLE_HDR   = colors.HexColor("#1b4f72")
WHITE       = colors.white
BLACK       = colors.black

W, H = A4   # 595.3 x 841.9 pts

base_styles = getSampleStyleSheet()

def make_style(name, parent="Normal", **kwargs):
    return ParagraphStyle(name, parent=base_styles[parent], **kwargs)

STYLES = {
    "subtitle":    make_style("ReportSubtitle",fontSize=11, leading=14, textColor=DARK_BLUE, fontName="Helvetica"),
    "section_hdr": make_style("SectionHdr",    fontSize=11, leading=14, textColor=WHITE, fontName="Helvetica-Bold", spaceAfter=4),
    "body":        make_style("Body",           fontSize=9,  leading=13, textColor=BLACK, fontName="Helvetica"),
    "body_bold":   make_style("BodyBold",       fontSize=9,  leading=13, textColor=BLACK, fontName="Helvetica-Bold"),
    "small":       make_style("Small",          fontSize=8,  leading=10, textColor=colors.grey, fontName="Helvetica"),
    "bullet":      make_style("Bullet",         fontSize=9,  leading=13, textColor=BLACK, fontName="Helvetica", leftIndent=12, spaceAfter=4),
    "outlook":     make_style("Outlook",        fontSize=9,  leading=13, textColor=BLACK, fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6),
    "tag_hold":    make_style("TagHold",        fontSize=18, leading=22, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER),
    "footer":      make_style("Footer",         fontSize=7,  leading=9,  textColor=colors.grey, fontName="Helvetica", alignment=TA_CENTER),
}

def _fmt(val, decimals=1, suffix="", prefix=""):
    if val is None: return "—"
    try:
        v = float(val)
        return f"{prefix}{v:,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(val)

def _pct(val): return _fmt(val, decimals=1, suffix="%")
def _cr(val): return _fmt(val, decimals=0)

def _rating_color(rating):
    if not rating: return MID_GREY
    r = str(rating).upper()
    if r in ("BUY", "ACCUMULATE"): return GREEN
    if r == "HOLD": return ORANGE
    if r in ("SELL", "REDUCE"): return RED
    return DARK_BLUE

def section_header(title):
    tbl = Table([[Paragraph(title, STYLES["section_hdr"])]], colWidths=[W - 28*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), TABLE_HDR),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
    ]))
    return tbl

def _configure_axes(ax, title):
    ax.set_title(title, fontsize=8, fontweight="bold", pad=6, color="#003366")
    ax.tick_params(axis="both", labelsize=6, colors="#2c3e50")
    ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.7)
    ax.spines[["top", "right", "left"]].set_visible(False)

def _chart_to_image(fig, width_pt=220, height_pt=130):
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return Image(buf, width=width_pt, height=height_pt)

def build_revenue_chart(data: dict):
    trend = data.get("revenue_trend") or [{"period": r.get("year",""), "value": r.get("sales")} for r in data.get("annual_estimates", []) if r.get("sales")]
    if not trend: return None
    periods = [str(r.get("period","")) for r in trend]
    values  = [float(r.get("value") or 0) for r in trend]

    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    bars = ax.bar(periods, values, color="#008bb0", width=0.55, zorder=3)
    _configure_axes(ax, "Revenue (Rs. Cr)")
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02, f"{v:,.0f}", ha="center", va="bottom", fontsize=5.5)
    return _chart_to_image(fig)

def build_ebitda_chart(data: dict):
    trend = data.get("ebitda_trend") or [{"period": r.get("year",""), "value": r.get("ebitda"), "margin_pct": r.get("ebitda_margin_pct")} for r in data.get("annual_estimates", []) if r.get("ebitda")]
    if not trend: return None
    periods  = [str(r.get("period","")) for r in trend]
    values   = [float(r.get("value") or 0) for r in trend]
    margins  = [float(r.get("margin_pct") or 0) for r in trend]

    fig, ax1 = plt.subplots(figsize=(3.5, 2.2))
    ax2 = ax1.twinx()
    ax1.bar(periods, values, color="#008bb0", width=0.55, zorder=3)
    ax2.plot(periods, margins, color="#e67e22", marker="o", markersize=4, linewidth=1.5, zorder=4)
    _configure_axes(ax1, "EBITDA (Rs. Cr) & Margin %")
    ax2.spines[["top", "right", "left"]].set_visible(False)
    ax2.tick_params(axis="y", labelsize=6, colors="#e67e22")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    return _chart_to_image(fig)

def build_pat_chart(data: dict):
    trend = data.get("pat_trend") or [{"period": r.get("year",""), "value": r.get("pat")} for r in data.get("annual_estimates", []) if r.get("pat")]
    if not trend: return None
    periods = [str(r.get("period","")) for r in trend]
    values  = [float(r.get("value") or 0) for r in trend]

    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    colors_bar = ["#c0392b" if v < 0 else "#008bb0" for v in values]
    ax.bar(periods, values, color=colors_bar, width=0.55, zorder=3)
    ax.axhline(0, color="grey", linewidth=0.8)
    _configure_axes(ax, "PAT (Rs. Cr)")
    return _chart_to_image(fig)


def generate_report(data: dict, output_path: str) -> str:
    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=14*mm, bottomMargin=14*mm, leftMargin=14*mm, rightMargin=14*mm)
    story = []
    col_w = (W - 28*mm)

    company   = data.get("company_name") or "Company Name"
    sector    = data.get("sector") or "Unknown Sector"
    rep_date  = data.get("report_date") or "Recently Updated"
    rating    = data.get("rating") or "N/A"
    target    = data.get("target_price")
    cmp_val   = data.get("cmp")
    ret_val   = data.get("return_pct")

    left_col = [
        [Paragraph("Retail Equity Research", STYLES["subtitle"])],
        [Paragraph(f"<b>{company}</b>", ParagraphStyle("BigTitle", fontSize=22, leading=26, textColor=DARK_BLUE, fontName="Helvetica-Bold"))],
        [Spacer(1, 4)],
        [Paragraph(f"<b>Sector:</b> {sector} | <b>Date:</b> {rep_date}", STYLES["body"])],
    ]
    left_tbl = Table(left_col, colWidths=[col_w * 0.60])
    left_tbl.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),0)]))

    rating_badge = Table([[Paragraph(rating, STYLES["tag_hold"])]], colWidths=[col_w * 0.35])
    rating_badge.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), _rating_color(rating)),
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))

    right_col = [
        [rating_badge],
        [Spacer(1, 6)],
        [Table([
            [Paragraph("<b>Target Price:</b>", STYLES["body"]), Paragraph(f"<b>Rs. {_cr(target)}</b>", STYLES["body_bold"])],
            [Paragraph("CMP:", STYLES["small"]), Paragraph(f"Rs. {_cr(cmp_val)}", STYLES["body"])],
            [Paragraph("Upside:", STYLES["small"]), Paragraph(f"{_pct(ret_val)}", STYLES["body_bold"])]
        ], colWidths=[col_w*0.20, col_w*0.15])]
    ]
    right_tbl = Table(right_col, colWidths=[col_w * 0.40])
    right_tbl.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"RIGHT"), ("VALIGN",(0,0),(-1,-1),"TOP")]))

    banner = Table([[left_tbl, right_tbl]], colWidths=[col_w*0.60, col_w*0.40])
    banner.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"), ("LINEBELOW",(0,0),(-1,-1), 1.5, DARK_BLUE), ("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story.append(banner)
    story.append(Spacer(1, 8))

    cd = data.get("company_data") or {}
    cd_rows = [
        [Paragraph("<b>Company Data</b>", STYLES["body_bold"]), ""],
        ["Market Cap (Rs. cr)", _cr(cd.get("market_cap"))],
        ["52 Wk High/Low (Rs.)", f"{_cr(cd.get('week_52_high'))} - {_cr(cd.get('week_52_low'))}"],
        ["Enterprise Value (Rs. cr)", _cr(cd.get("enterprise_value"))],
        ["Outstanding Shares (cr)", _cr(cd.get("outstanding_shares"))],
        ["Free Float (%)", _pct(cd.get("free_float_pct"))],
    ]
    cd_tbl = Table(cd_rows, colWidths=[col_w*0.23, col_w*0.15])
    cd_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), TABLE_HDR), ("TEXTCOLOR", (0,0),(-1,0), WHITE),
        ("SPAN", (0,0),(-1,0)), ("FONTSIZE", (0,0),(-1,-1), 8),
        ("LINEBELOW", (0,0),(-1,-1), 0.5, LIGHT_GREY), ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))

    hl_items = [Paragraph(f"• {h}", STYLES["bullet"]) for h in (data.get("key_highlights") or ["No highlights."])[:6]]
    hl_block = [section_header("Key Highlights")] + hl_items

    side_tbl = Table([[ [cd_tbl, Spacer(1,8)], hl_block ]], colWidths=[col_w*0.40, col_w*0.60])
    side_tbl.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(1,0),(1,0),12)]))
    story.append(side_tbl)
    story.append(Spacer(1, 8))

    story.append(section_header("Quarterly Financials"))
    story.append(Spacer(1, 3))
    qf = data.get("quarterly_financials") or {}
    q_rows = [
        ["Rs.cr", qf.get("current_quarter","Current"), qf.get("prior_year_quarter","Prior"), "YoY Growth (%)"],
        ["Sales", _cr(qf.get("sales_current")), _cr(qf.get("sales_prior_year")), _pct(qf.get("sales_yoy_growth"))],
        ["EBITDA", _cr(qf.get("ebitda_current")), _cr(qf.get("ebitda_prior_year")), _pct(qf.get("ebitda_yoy_growth"))],
        ["Margin (%)", _pct(qf.get("ebitda_margin_current")), _pct(qf.get("ebitda_margin_prior_year")), "—"],
        ["PAT", _cr(qf.get("pat_current")), _cr(qf.get("pat_prior_year")), _pct(qf.get("pat_yoy_growth"))],
    ]
    q_tbl = Table(q_rows, colWidths=[col_w*0.25, col_w*0.25, col_w*0.25, col_w*0.25])
    q_tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0),(-1,-1), 8),
        ("LINEABOVE", (0,0),(-1,0), 1.5, TABLE_HDR), ("LINEBELOW", (0,0),(-1,0), 1, TABLE_HDR),
        ("LINEBELOW", (0,1),(-1,-2), 0.5, LIGHT_GREY), ("LINEBELOW", (0,-1),(-1,-1), 1.5, TABLE_HDR),
        ("ALIGN", (1,0),(-1,-1), "RIGHT"), ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(q_tbl)
    story.append(Spacer(1, 10))

    story.append(section_header("Outlook & Valuation"))
    story.append(Spacer(1, 4))
    story.append(Paragraph(data.get("outlook_valuation") or "No outlook provided.", STYLES["outlook"]))
    story.append(Spacer(1, 6))

    ae = data.get("annual_estimates") or []
    if ae:
        years = [r.get("year","") for r in ae]
        ae_rows = [
            ["Y.E March (cr)"] + years,
            ["Sales"] + [_cr(r.get("sales")) for r in ae],
            ["Growth (%)"] + [_pct(r.get("sales_growth_pct")) for r in ae],
            ["EBITDA"] + [_cr(r.get("ebitda")) for r in ae],
            ["Margin (%)"] + [_pct(r.get("ebitda_margin_pct")) for r in ae],
            ["PAT"] + [_cr(r.get("pat")) for r in ae],
            ["Adj. EPS"] + [_fmt(r.get("eps"), 2) for r in ae],
        ]
        ae_col_w = [col_w * 0.28] + [(col_w * 0.72) / max(len(years),1)] * len(years)
        ae_tbl = Table(ae_rows, colWidths=ae_col_w)
        ae_tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0),(-1,-1), 8),
            ("LINEABOVE", (0,0),(-1,0), 1.5, TABLE_HDR), ("LINEBELOW", (0,0),(-1,0), 1, TABLE_HDR),
            ("LINEBELOW", (0,1),(-1,-2), 0.5, LIGHT_GREY), ("LINEBELOW", (0,-1),(-1,-1), 1.5, TABLE_HDR),
            ("ALIGN", (1,0),(-1,-1), "RIGHT"), ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        story.append(ae_tbl)
        story.append(Spacer(1, 10))

    chart_imgs = [img for img in [build_revenue_chart(data), build_ebitda_chart(data), build_pat_chart(data)] if img]
    if chart_imgs:
        cw = col_w / len(chart_imgs)
        chart_row = Table([chart_imgs], colWidths=[cw]*len(chart_imgs))
        chart_row.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER")]))
        story.append(chart_row)

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width=col_w, thickness=0.5, color=DARK_BLUE))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Report generated by Bull AI. Informational purposes only. Not investment advice.", STYLES["footer"]))

    doc.build(story)
    return output_path