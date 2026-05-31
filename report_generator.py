import io
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

INK         = colors.HexColor("#111111")     
PAPER       = colors.HexColor("#FAFAF8")     
RULE        = colors.HexColor("#CCCCCC")    
RULE_HEAVY  = colors.HexColor("#999999")      
ACCENT      = colors.HexColor("#B85C38")      
ACCENT_LIGHT= colors.HexColor("#F5E9E4")      
MUTED       = colors.HexColor("#666666")      
GREEN       = colors.HexColor("#2D6A4F")      
ORANGE      = colors.HexColor("#C77C2A")      
RED_DARK    = colors.HexColor("#8B2020")      
WHITE       = colors.white
BLACK       = colors.black

W, H = A4   
MARGIN      = 16 * mm
COL_W       = W - 2 * MARGIN

_base = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, parent=_base["Normal"], **kw)

STYLES = {
    "co_name":    S("CoName",   fontName="Times-Bold",    fontSize=22, leading=26,
                                textColor=INK, spaceAfter=2),
    "eyebrow":    S("Eyebrow",  fontName="Helvetica",      fontSize=7.5, leading=10,
                                textColor=MUTED, spaceAfter=2, spaceBefore=0,
                                letterSpacing=1.2),
    "kicker":     S("Kicker",   fontName="Helvetica-Bold", fontSize=7.5, leading=10,
                                textColor=ACCENT, spaceAfter=6, letterSpacing=1.0),

    "body":       S("Body",     fontName="Helvetica",      fontSize=8.5, leading=12, textColor=INK),
    "body_bold":  S("BodyBold", fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=INK),
    "body_muted": S("BodyMuted",fontName="Helvetica",      fontSize=8,   leading=11, textColor=MUTED),
    "body_serif": S("BodySerif",fontName="Times-Roman",     fontSize=9,   leading=13.5,
                                textColor=INK, alignment=TA_JUSTIFY, spaceAfter=4),

    "sec_label":  S("SecLabel", fontName="Helvetica-Bold", fontSize=7,   leading=9,
                                textColor=ACCENT, letterSpacing=1.5, spaceAfter=3),

    "tbl_hdr":    S("TblHdr",   fontName="Helvetica-Bold", fontSize=7.5, leading=10,
                                textColor=INK),
    "tbl_cell":   S("TblCell",  fontName="Helvetica",      fontSize=7.5, leading=10,
                                textColor=INK, alignment=TA_RIGHT),
    "tbl_label":  S("TblLabel", fontName="Helvetica",      fontSize=7.5, leading=10,
                                textColor=INK),
    "tbl_italic": S("TblItalic",fontName="Helvetica-Oblique",fontSize=7.5, leading=10,
                                textColor=MUTED),

    "badge":      S("Badge",    fontName="Helvetica-Bold", fontSize=13,  leading=16,
                                textColor=WHITE, alignment=TA_CENTER),
    "badge_sub":  S("BadgeSub", fontName="Helvetica",      fontSize=7,   leading=9,
                                textColor=WHITE, alignment=TA_CENTER),

    "bullet":     S("Bullet",   fontName="Helvetica",      fontSize=8.5, leading=13,
                                textColor=INK, leftIndent=10, spaceAfter=3),

    "footer":     S("Footer",   fontName="Helvetica",      fontSize=6.5, leading=9,
                                textColor=MUTED, alignment=TA_CENTER),
}

def _v(val, dec=0, suffix="", na="—"):
    if val is None: return na
    try:
        v = float(val)
        s = f"{v:,.{dec}f}{suffix}"
        return s
    except Exception:
        return str(val)

def _pct(val): return _v(val, 1, "%")
def _cr(val):  return _v(val, 0)
def _x(val):   return _v(val, 1, "x")

def _rating_color(r):
    if not r: return MUTED
    r = str(r).upper()
    if r in ("BUY",):            return GREEN
    if r in ("ACCUMULATE",):     return colors.HexColor("#3A7D44")
    if r in ("HOLD",):           return ORANGE
    if r in ("REDUCE", "SELL"): return RED_DARK
    return MUTED

def _section(title):
    return [
        Paragraph(title.upper(), STYLES["sec_label"]),
        HRFlowable(width=COL_W, thickness=0.75, color=ACCENT, spaceAfter=4),
    ]

def _light_rule():
    return HRFlowable(width=COL_W, thickness=0.4, color=RULE, spaceAfter=4, spaceBefore=4)

CHART_STYLE = {
    "figure.facecolor":   "#FAFAF8",
    "axes.facecolor":     "#FAFAF8",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.spines.left":   False,
    "axes.edgecolor":     "#CCCCCC",
    "axes.grid":          True,
    "grid.color":         "#E0E0E0",
    "grid.linewidth":     0.5,
    "grid.linestyle":     ":",
    "xtick.color":        "#666666",
    "ytick.color":        "#666666",
    "xtick.labelsize":    6,
    "ytick.labelsize":    6,
    "font.family":        "sans-serif",
}

def _fig(w=3.4, h=2.0):
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(w, h))
    return fig, ax

def _to_img(fig, w=210, h=125):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return Image(buf, width=w, height=h)

def _bar_colors(values, hi="#B85C38", lo="#CCCCCC"):
    if not values: return [lo]
    mx = max(values)
    return [hi if v == mx else lo for v in values]

def build_revenue_chart(data):
    trend = data.get("revenue_trend") or [
        {"period": r.get("year",""), "value": r.get("sales")}
        for r in data.get("annual_estimates", []) if r.get("sales")
    ]
    if not trend: return None
    periods = [str(r.get("period","")) for r in trend]
    values  = [float(r.get("value") or 0) for r in trend]

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(3.4, 2.0))
        bars = ax.bar(periods, values, color=_bar_colors(values), width=0.55, zorder=3)
        ax.set_title("Revenue  (Rs. cr)", fontsize=7.5, fontweight="bold",
                     color="#111111", pad=6, loc="left")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x/1000:.1f}k" if x>=1000 else f"{x:.0f}"))
        for bar, v in zip(bars, values):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(values)*0.015,
                    f"{v:,.0f}", ha="center", va="bottom", fontsize=5.5, color="#444")
    return _to_img(fig)

def build_ebitda_chart(data):
    trend = data.get("ebitda_trend") or [
        {"period": r.get("year",""), "value": r.get("ebitda"), "margin_pct": r.get("ebitda_margin_pct")}
        for r in data.get("annual_estimates", []) if r.get("ebitda")
    ]
    if not trend: return None
    periods = [str(r.get("period","")) for r in trend]
    values  = [float(r.get("value") or 0)      for r in trend]
    margins = [float(r.get("margin_pct") or 0) for r in trend]

    with plt.rc_context(CHART_STYLE):
        fig, ax1 = plt.subplots(figsize=(3.4, 2.0))
        ax2 = ax1.twinx()
        ax1.bar(periods, values, color="#CCCCCC", width=0.55, zorder=2)
        ax2.plot(periods, margins, color="#B85C38", marker="o",
                 markersize=3.5, linewidth=1.5, zorder=4)
        ax2.fill_between(range(len(periods)), margins, alpha=0.08, color="#B85C38")
        ax1.set_title("EBITDA  (Rs. cr)  &  Margin %", fontsize=7.5, fontweight="bold",
                      color="#111111", pad=6, loc="left")
        ax2.tick_params(axis="y", labelsize=6, colors="#B85C38")
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
        ax2.spines["right"].set_visible(False)
        ax2.spines["top"].set_visible(False)
    return _to_img(fig)

def build_pat_chart(data):
    trend = data.get("pat_trend") or [
        {"period": r.get("year",""), "value": r.get("pat")}
        for r in data.get("annual_estimates", []) if r.get("pat")
    ]
    if not trend: return None
    periods = [str(r.get("period","")) for r in trend]
    values  = [float(r.get("value") or 0) for r in trend]

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(3.4, 2.0))
        bar_c = ["#8B2020" if v < 0 else "#B85C38" for v in values]
        ax.bar(periods, values, color=bar_c, width=0.55, zorder=3)
        ax.axhline(0, color="#999", linewidth=0.6)
        ax.set_title("PAT  (Rs. cr)", fontsize=7.5, fontweight="bold",
                     color="#111111", pad=6, loc="left")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:,.0f}"))
    return _to_img(fig)

def _data_table(rows, col_widths, alt_rows=True):
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("FONTNAME",      (0,0), (-1,0),   "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1),  7.5),
        ("LEADING",       (0,0), (-1,-1),  10),
        ("TOPPADDING",    (0,0), (-1,-1),  3),
        ("BOTTOMPADDING", (0,0), (-1,-1),  3),
        ("LEFTPADDING",   (0,0), (-1,-1),  4),
        ("RIGHTPADDING",  (0,0), (-1,-1),  4),
        ("LINEBELOW",     (0,0), (-1,0),   1.0, INK),
        ("LINEABOVE",     (0,-1),(-1,-1),  0.5, RULE_HEAVY),
        ("LINEBELOW",     (0,1), (-1,-2),  0.3, RULE),
        ("ALIGN",         (1,0), (-1,-1),  "RIGHT"),
        ("ALIGN",         (0,0), (0,-1),   "LEFT"),
        ("VALIGN",        (0,0), (-1,-1),  "MIDDLE"),
    ]
    if alt_rows:
        for i in range(2, len(rows), 2):
            cmds.append(("BACKGROUND", (0,i), (-1,i), ACCENT_LIGHT))
    tbl.setStyle(TableStyle(cmds))
    return tbl

def generate_report(data: dict, output_path: str) -> str:
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=MARGIN, bottomMargin=MARGIN,
        leftMargin=MARGIN, rightMargin=MARGIN,
        title=f"{data.get('company_name','Report')} — Equity Research",
    )

    story = []

    company  = data.get("company_name") or "Company Name"
    sector   = data.get("sector") or ""
    rep_date = data.get("report_date") or ""
    rating   = (data.get("rating") or "N/A").upper()
    target   = data.get("target_price")
    cmp_val  = data.get("cmp")
    ret_val  = data.get("return_pct")
    nse      = data.get("nse_code") or "—"
    bse      = data.get("bse_code") or "—"
    stk_type = data.get("stock_type") or "—"
    timeframe= data.get("time_frame") or "12 Months"

    rc = _rating_color(rating)

    left_inner = [
        [Paragraph("EQUITY RESEARCH  ·  INDIA", STYLES["eyebrow"])],
        [Paragraph(company, STYLES["co_name"])],
        [Paragraph(f"{sector}  ·  {rep_date}  ·  NSE: {nse}  ·  BSE: {bse}", STYLES["body_muted"])],
    ]
    left_tbl = Table(left_inner, colWidths=[COL_W * 0.62])
    left_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),1),
        ("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1),0),
    ]))

    sign = "+" if (ret_val or 0) > 0 else ""
    metrics_rows = [
        [Paragraph("TARGET", STYLES["badge_sub"]), Paragraph(f"Rs. {_cr(target)}", STYLES["badge"])],
        [Paragraph("CMP",    STYLES["badge_sub"]), Paragraph(f"Rs. {_cr(cmp_val)}", STYLES["badge"])],
        [Paragraph("RETURN", STYLES["badge_sub"]), Paragraph(f"{sign}{_pct(ret_val)}", STYLES["badge"])],
    ]
    metrics_tbl = Table(metrics_rows, colWidths=[COL_W*0.12, COL_W*0.22])
    metrics_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), rc),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LINEBELOW",     (0,0),(-1,-2), 0.5, colors.HexColor("#FFFFFF44")),
    ]))

    rating_label = Table([
        [Paragraph(rating, ParagraphStyle("RatingBig", fontName="Times-Bold",
                    fontSize=16, leading=20, textColor=WHITE, alignment=TA_CENTER))],
    ], colWidths=[COL_W*0.34])
    rating_label.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), rc),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
    ]))

    right_inner = [[rating_label], [metrics_tbl]]
    right_tbl = Table(right_inner, colWidths=[COL_W*0.34])
    right_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))

    banner = Table([[left_tbl, right_tbl]], colWidths=[COL_W*0.64, COL_W*0.36])
    banner.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(banner)
    story.append(Spacer(1, 4))

    story.append(HRFlowable(width=COL_W, thickness=2, color=ACCENT, spaceAfter=0))
    story.append(HRFlowable(width=COL_W, thickness=0.4, color=RULE, spaceAfter=8))

    meta_cells = [
        [Paragraph("STOCK TYPE", STYLES["eyebrow"]),
         Paragraph("NSE CODE",   STYLES["eyebrow"]),
         Paragraph("BSE CODE",   STYLES["eyebrow"]),
         Paragraph("TIME FRAME", STYLES["eyebrow"])],
        [Paragraph(stk_type, STYLES["body_bold"]),
         Paragraph(nse,       STYLES["body_bold"]),
         Paragraph(bse,       STYLES["body_bold"]),
         Paragraph(timeframe, STYLES["body_bold"])],
    ]
    meta_tbl = Table(meta_cells, colWidths=[COL_W/4]*4)
    meta_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("LINEBELOW",     (0,-1),(-1,-1), 0.5, RULE),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 10))

    cd = data.get("company_data") or {}

    cd_rows = [
        [Paragraph("Metric", STYLES["tbl_hdr"]),    Paragraph("Value", STYLES["tbl_hdr"])],
        ["Market Cap (cr)",                          _cr(cd.get("market_cap"))],
        ["52-Wk High / Low",
         f"{_cr(cd.get('week_52_high'))} / {_cr(cd.get('week_52_low'))}"],
        ["Enterprise Value (cr)",                   _cr(cd.get("enterprise_value"))],
        ["Shares Outstanding (cr)",                 _cr(cd.get("outstanding_shares"))],
        ["Free Float",                               _pct(cd.get("free_float_pct"))],
        ["Face Value (Rs.)",                         _v(cd.get("face_value"), 1)],
        ["Beta",                                     _v(cd.get("beta"), 2)],
        ["Dividend Yield",                           _pct(cd.get("dividend_yield"))],
    ]
    cd_tbl = _data_table(cd_rows, [COL_W*0.22, COL_W*0.18])

    highlights = data.get("key_highlights") or []
    hl_items   = [Paragraph(f"<b>—</b>  {h}", STYLES["bullet"]) for h in highlights[:7]]
    if not hl_items:
        hl_items = [Paragraph("No highlights extracted.", STYLES["body_muted"])]

    hl_section = _section("Key Highlights") + hl_items

    left_block  = _section("Company Data") + [cd_tbl]
    right_block = hl_section

    two_col = Table([[left_block, right_block]], colWidths=[COL_W*0.42, COL_W*0.58])
    two_col.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ("LEFTPADDING",   (1,0),(1,-1),  12),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 12))

    story += _section("Quarterly Financial Summary")
    qf  = data.get("quarterly_financials") or {}
    cq  = qf.get("current_quarter",    "Current Q")
    pyq = qf.get("prior_year_quarter", "Prior Year Q")

    q_rows = [
        [Paragraph("Rs. cr",     STYLES["tbl_hdr"]),
         Paragraph(cq,           STYLES["tbl_hdr"]),
         Paragraph(pyq,          STYLES["tbl_hdr"]),
         Paragraph("YoY Δ",      STYLES["tbl_hdr"])],
        ["Revenue",   _cr(qf.get("sales_current")),  _cr(qf.get("sales_prior_year")),  _pct(qf.get("sales_yoy_growth"))],
        ["EBITDA",    _cr(qf.get("ebitda_current")), _cr(qf.get("ebitda_prior_year")), _pct(qf.get("ebitda_yoy_growth"))],
        ["Margin",    _pct(qf.get("ebitda_margin_current")), _pct(qf.get("ebitda_margin_prior_year")), "—"],
        ["PAT",       _cr(qf.get("pat_current")),    _cr(qf.get("pat_prior_year")),    _pct(qf.get("pat_yoy_growth"))],
        ["EPS (Rs.)", _v(qf.get("eps_current"),2),   _v(qf.get("eps_prior_year"),2),   "—"],
    ]
    story.append(_data_table(q_rows, [COL_W*0.22, COL_W*0.26, COL_W*0.26, COL_W*0.26]))
    story.append(Spacer(1, 12))

    ae = data.get("annual_estimates") or []
    if ae:
        story += _section("Annual Estimates")
        years = [r.get("year","") for r in ae]
        n = len(years)
        year_w = (COL_W * 0.72) / max(n, 1)

        ae_rows = [
            [Paragraph("Y/E Mar (cr)", STYLES["tbl_hdr"])] +
            [Paragraph(y, STYLES["tbl_hdr"]) for y in years],

            ["Revenue"]       + [_cr(r.get("sales"))              for r in ae],
            ["Growth %"]      + [_pct(r.get("sales_growth_pct"))  for r in ae],
            ["EBITDA"]        + [_cr(r.get("ebitda"))             for r in ae],
            ["EBITDA Margin"] + [_pct(r.get("ebitda_margin_pct")) for r in ae],
            ["PAT"]           + [_cr(r.get("pat"))                for r in ae],
            ["PAT Growth %"]  + [_pct(r.get("pat_growth_pct"))   for r in ae],
            ["EPS (Rs.)"]     + [_v(r.get("eps"), 2)              for r in ae],
            ["P/E (x)"]       + [_v(r.get("pe"), 1)              for r in ae],
            ["EV/EBITDA (x)"] + [_v(r.get("ev_ebitda"), 1)       for r in ae],
            ["ROE %"]         + [_pct(r.get("roe_pct"))           for r in ae],
        ]
        story.append(_data_table(ae_rows, [COL_W*0.28] + [year_w]*n))
        story.append(Spacer(1, 12))

    story += _section("Outlook & Valuation")
    outlook = data.get("outlook_valuation") or "No outlook information extracted."
    story.append(Paragraph(outlook, STYLES["body_serif"]))
    story.append(Spacer(1, 12))

    story += _section("Financial Trends")
    imgs = [img for img in [build_revenue_chart(data),
                             build_ebitda_chart(data),
                             build_pat_chart(data)] if img]
    if imgs:
        n = len(imgs)
        cw = COL_W / n
        chart_row = Table([imgs], colWidths=[cw]*n)
        chart_row.setStyle(TableStyle([
            ("ALIGN",  (0,0),(-1,-1), "CENTER"),
            ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0),(-1,-1), 4),
        ]))
        story.append(chart_row)
    story.append(Spacer(1, 14))

    story.append(HRFlowable(width=COL_W, thickness=0.5, color=RULE_HEAVY, spaceAfter=4))
    story.append(Paragraph(
        "Generated by Bull AI · For informational purposes only · "
        "This is not investment advice · Please read all scheme-related documents carefully before investing.",
        STYLES["footer"]
    ))

    doc.build(story)
    return output_path