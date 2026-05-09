"""
apps/reports/services.py

PDF generation via ReportLab.
Excel generation via openpyxl.

PDF reports:
  generate_bookings_pdf(start, end)   — бронирования за период
  generate_clients_pdf(filters)       — список клиентов
  generate_occupancy_pdf(start, end)  — загрузка номеров

Design:
  - Dark header (#1a1a2e) with gold accent (#c9a84c)
  - Alternating row colors
  - Summary block at top
  - Page numbers in footer
  - Cyrillic via built-in Helvetica (ASCII transliteration fallback)
    OR via registered TTF if available
"""

import io
from datetime import date
from decimal import Decimal

from django.http import HttpResponse


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Brand colors
DARK   = "#1a1a2e"
GOLD   = "#c9a84c"
LIGHT  = "#f8f7f4"
WHITE  = "#ffffff"
GRAY1  = "#f0ede8"   # odd rows
GRAY2  = "#ffffff"   # even rows
TEXT   = "#1a1a2e"
MUTED  = "#6b7280"
GREEN  = "#16a34a"
RED    = "#dc2626"
BLUE   = "#2563eb"


def _hex(h: str):
    """Convert #rrggbb to ReportLab HexColor."""
    from reportlab.lib.colors import HexColor
    return HexColor(h)


def _register_fonts():
    """
    Register fonts with Cyrillic support.
    Priority: DejaVu Sans > Arial > Helvetica (fallback)
    """
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os
        
        # Try to find and register DejaVu Sans (best Cyrillic support)
        dejavu_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/DejaVuSans.ttf",
            "/usr/local/share/fonts/DejaVuSans.ttf",
        ]
        
        for path in dejavu_candidates:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                    # Try to register bold variant
                    bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
                        return "DejaVuSans"
                    else:
                        return "DejaVuSans"
                except Exception:
                    continue
        
        # Try Arial (Windows)
        arial_candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/Arial.ttf",
        ]
        
        for path in arial_candidates:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont("Arial", path))
                    bold_path = path.replace("arial.ttf", "arialbd.ttf").replace("Arial.ttf", "Arialbd.ttf")
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont("Arial-Bold", bold_path))
                    return "Arial"
                except Exception:
                    continue
                    
    except Exception:
        pass
    
    # Fallback to Helvetica (Latin only)
    return "Helvetica"


FONT = _register_fonts()
def _safe_text(text: str) -> str:
    """
    Ensure text can be displayed in PDF.
    If font doesn't support Cyrillic, transliterate to Latin.
    """
    if not text:
        return ""
    
    # If we have a good font, return as-is
    if FONT in ["DejaVuSans", "Arial"]:
        return text
    
    # Fallback: simple transliteration for Helvetica
    cyrillic_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    
    result = ""
    for char in text:
        result += cyrillic_map.get(char, char)
    
    return result


FONT_BOLD = FONT + "-Bold" if FONT in ["Helvetica", "DejaVuSans", "Arial"] else FONT


def _make_doc(buffer, title: str, landscape_mode: bool = False):
    """Create a SimpleDocTemplate with standard margins."""
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.pagesizes import A4, landscape

    pagesize = landscape(A4) if landscape_mode else A4
    return SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=1.5 * 28.35,   # 1.5 cm
        leftMargin=1.5 * 28.35,
        topMargin=2 * 28.35,
        bottomMargin=2 * 28.35,
        title=title,
        author="Зори Ваха",
    )


def _header_paragraph(text: str, styles):
    """Gold-colored section header paragraph."""
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=9,
        textColor=_hex(GOLD),
        spaceAfter=4,
        spaceBefore=12,
        leading=12,
    )
    return Paragraph(_safe_text(text), style)


def _summary_table(rows: list[tuple[str, str]]):
    """
    Two-column summary block: label | value.
    rows = [("Период", "01.01.2025 — 31.01.2025"), ...]
    """
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.units import cm

    data = [[_safe_text(label), _safe_text(value)] for label, value in rows]
    t = Table(data, colWidths=[5 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME",    (1, 0), (1, -1), FONT),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (0, -1), _hex(MUTED)),
        ("TEXTCOLOR",   (1, 0), (1, -1), _hex(TEXT)),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW",   (0, -1), (-1, -1), 0.5, _hex("#e5e7eb")),
    ]))
    return t


def _page_footer(canvas, doc):
    """Draw page number + brand name in footer."""
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor(_hex(MUTED))
    page_num = _safe_text(f"Страница {doc.page}")
    brand_text = _safe_text("Зори Ваха — Система управления гостиницей")
    canvas.drawString(doc.leftMargin, 14, brand_text)
    canvas.drawRightString(doc.width + doc.leftMargin, 14, page_num)
    # Gold top border on first page
    if doc.page == 1:
        canvas.setStrokeColor(_hex(GOLD))
        canvas.setLineWidth(3)
        canvas.line(doc.leftMargin, doc.height + doc.topMargin + 10,
                    doc.width + doc.leftMargin, doc.height + doc.topMargin + 10)
    canvas.restoreState()


def _build_title_block(title: str, subtitle: str, styles):
    """Dark header block with gold accent line."""
    from reportlab.platypus import Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=18,
        textColor=_hex(WHITE),
        leading=22,
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName=FONT,
        fontSize=10,
        textColor=_hex(GOLD),
        leading=14,
        spaceAfter=0,
    )

    from reportlab.platypus import Table, TableStyle
    # Title block as a table with dark background
    inner = [[Paragraph(_safe_text(title), title_style)], [Paragraph(_safe_text(subtitle), sub_style)]]
    t = Table(inner, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _hex(DARK)),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("ROUNDEDCORNERS", [6]),
    ]))

    return [
        t,
        HRFlowable(width="100%", thickness=3, color=_hex(GOLD), spaceAfter=12),
    ]


def _data_table(headers: list, rows: list, col_widths=None, align_right_cols: list = None):
    """
    Styled data table with dark header row and alternating body rows.
    align_right_cols: list of column indices (0-based) to right-align.
    """
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.units import cm

    # Apply safe text conversion to all data
    safe_headers = [_safe_text(str(h)) for h in headers]
    safe_rows = []
    for row in rows:
        safe_row = [_safe_text(str(cell)) for cell in row]
        safe_rows.append(safe_row)

    data = [safe_headers] + safe_rows
    t = Table(data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), _hex(DARK)),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _hex(WHITE)),
        ("FONTNAME",      (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        # Body
        ("FONTNAME",      (0, 1), (-1, -1), FONT),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TEXTCOLOR",     (0, 1), (-1, -1), _hex(TEXT)),
        # Grid
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, _hex("#e5e7eb")),
        ("LINEAFTER",     (0, 0), (-1, -1), 0.3, _hex("#e5e7eb")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]

    # Alternating row colors
    for i in range(1, len(data)):
        bg = GRAY1 if i % 2 == 1 else GRAY2
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), _hex(bg)))

    # Right-align specified columns
    for col in (align_right_cols or []):
        style_cmds.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))

    t.setStyle(TableStyle(style_cmds))
    return t


# ---------------------------------------------------------------------------
# 1. Bookings PDF
# ---------------------------------------------------------------------------

def generate_bookings_pdf(start: date, end: date) -> HttpResponse:
    """
    PDF report: bookings for the given period.
    Landscape A4, full booking table + summary block.
    """
    from reportlab.platypus import Spacer, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    from .selectors import get_bookings_report_data, get_bookings_summary

    bookings = get_bookings_report_data(start, end)
    summary  = get_bookings_summary(start, end)

    buffer = io.BytesIO()
    doc    = _make_doc(buffer, f"Бронирования {start}–{end}", landscape_mode=True)
    styles = getSampleStyleSheet()
    elems  = []

    # ── Title ──
    elems += _build_title_block(
        "Отчёт по бронированиям",
        f"Период: {start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}",
        styles,
    )

    # ── Summary ──
    elems.append(_header_paragraph("Сводка", styles))
    revenue = summary.get("revenue") or Decimal("0")
    avg_n   = summary.get("avg_nights")
    avg_nights_str = f"{float(avg_n):.1f}" if avg_n else "—"
    elems.append(_summary_table([
        ("Всего бронирований:",    str(summary.get("total", 0))),
        ("Подтверждённых:",        str(summary.get("confirmed", 0))),
        ("Отменённых:",            str(summary.get("cancelled", 0))),
        ("Общая выручка:",         f"{float(revenue):,.0f} ₽"),
        ("Средний срок (ночей):",  avg_nights_str),
    ]))
    elems.append(Spacer(1, 0.4 * cm))

    # ── Table ──
    elems.append(_header_paragraph("Список бронирований", styles))

    if bookings:
        headers = ["№ брони", "Гость", "Телефон", "Категория", "Заезд", "Выезд", "Ночей", "Статус", "Сумма, ₽"]
        rows = []
        for b in bookings:
            rows.append([
                b.confirmation_number,
                b.guest_full_name[:28],
                b.guest_phone,
                b.room_category.name[:20],
                b.check_in.strftime("%d.%m.%Y"),
                b.check_out.strftime("%d.%m.%Y"),
                str(b.nights),
                b.get_status_display(),
                f"{float(b.total_price):,.0f}",
            ])

        col_w = [2.8*cm, 4.5*cm, 3*cm, 3.5*cm, 2.5*cm, 2.5*cm, 1.5*cm, 2.8*cm, 2.5*cm]
        elems.append(_data_table(headers, rows, col_widths=col_w, align_right_cols=[6, 8]))
    else:
        elems.append(Paragraph("Нет данных за выбранный период.", styles["Normal"]))

    doc.build(elems, onFirstPage=_page_footer, onLaterPages=_page_footer)
    buffer.seek(0)

    resp = HttpResponse(buffer, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="bookings_{start}_{end}.pdf"'
    )
    return resp


# ---------------------------------------------------------------------------
# 2. Clients PDF
# ---------------------------------------------------------------------------

def generate_clients_pdf(
    search: str = "",
    loyalty_tier: str = "",
    status: str = "",
) -> HttpResponse:
    """
    PDF report: client list with loyalty stats.
    Portrait A4.
    """
    from reportlab.platypus import Spacer, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    from .selectors import get_clients_report_data, get_clients_summary

    clients = get_clients_report_data(search=search, loyalty_tier=loyalty_tier, status=status)
    summary = get_clients_summary()

    buffer = io.BytesIO()
    doc    = _make_doc(buffer, "Список клиентов", landscape_mode=False)
    styles = getSampleStyleSheet()
    elems  = []

    # ── Title ──
    from django.utils import timezone
    today = timezone.localdate()
    elems += _build_title_block(
        "Список клиентов",
        f"Сформирован: {today.strftime('%d.%m.%Y')}  |  Записей: {len(clients)}",
        styles,
    )

    # ── Summary ──
    elems.append(_header_paragraph("Сводка по клиентской базе", styles))
    total_rev = summary.get("total_revenue") or Decimal("0")
    avg_stays = summary.get("avg_stays")
    elems.append(_summary_table([
        ("Всего клиентов:",     str(summary.get("total", 0))),
        ("VIP клиентов:",       str(summary.get("vip", 0))),
        ("Чёрный список:",      str(summary.get("blacklisted", 0))),
        ("Суммарная выручка:",  f"{float(total_rev):,.0f} ₽"),
        ("Среднее заездов:",    f"{float(avg_stays or 0):.1f}"),
    ]))
    elems.append(Spacer(1, 0.4 * cm))

    # ── Table ──
    elems.append(_header_paragraph("Клиенты", styles))

    if clients:
        headers = ["ФИО", "Email", "Тип", "Лояльность", "Заездов", "Ночей", "Потрачено, ₽", "Статус"]
        rows = []
        for p in clients:
            rows.append([
                p.user.get_full_name()[:30] or p.user.email[:30],
                p.user.email[:28],
                p.get_client_type_display(),
                p.get_loyalty_tier_display(),
                str(p.total_stays),
                str(p.total_nights),
                f"{float(p.total_spent):,.0f}",
                p.get_status_display(),
            ])

        col_w = [4*cm, 4.5*cm, 2.5*cm, 2.5*cm, 1.8*cm, 1.8*cm, 3*cm, 2.5*cm]
        elems.append(_data_table(headers, rows, col_widths=col_w, align_right_cols=[4, 5, 6]))
    else:
        elems.append(Paragraph("Нет данных.", styles["Normal"]))

    doc.build(elems, onFirstPage=_page_footer, onLaterPages=_page_footer)
    buffer.seek(0)

    resp = HttpResponse(buffer, content_type="application/pdf")
    resp["Content-Disposition"] = 'attachment; filename="clients.pdf"'
    return resp


# ---------------------------------------------------------------------------
# 3. Room Occupancy PDF
# ---------------------------------------------------------------------------

def generate_occupancy_pdf(start: date, end: date) -> HttpResponse:
    """
    PDF report: room occupancy for the given period.
    Portrait A4 with per-room stats + occupancy bar.
    """
    from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics import renderPDF

    from .selectors import get_room_occupancy_report, get_occupancy_summary

    rooms   = get_room_occupancy_report(start, end)
    summary = get_occupancy_summary(start, end)

    buffer = io.BytesIO()
    doc    = _make_doc(buffer, f"Загрузка номеров {start}–{end}", landscape_mode=True)
    styles = getSampleStyleSheet()
    elems  = []

    # ── Title ──
    elems += _build_title_block(
        "Загрузка номерного фонда",
        f"Период: {start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}  |  Дней: {summary['total_days']}",
        styles,
    )

    # ── Summary ──
    elems.append(_header_paragraph("Сводка", styles))
    total_rev = summary.get("total_revenue") or Decimal("0")
    elems.append(_summary_table([
        ("Всего номеров:",         str(summary["total_rooms"])),
        ("Всего бронирований:",    str(summary["total_bookings"])),
        ("Ночей продано:",         str(summary["total_nights"])),
        ("Средняя загрузка:",      f"{summary['avg_occupancy']}%"),
        ("Выручка за период:",     f"{float(total_rev):,.0f} ₽"),
    ]))
    elems.append(Spacer(1, 0.4 * cm))

    # ── Table ──
    elems.append(_header_paragraph("Детализация по номерам", styles))

    if rooms:
        headers = ["Номер", "Этаж", "Категория", "Статус", "Броней", "Ночей", "Загрузка %", "Выручка, ₽"]
        rows = []
        for r in rooms:
            # Color-code occupancy
            occ = r["occupancy"]
            occ_str = f"{occ:.1f}%"
            rows.append([
                r["number"],
                str(r["floor"]),
                r["category"][:22],
                r["status"],
                str(r["bookings"]),
                str(r["nights"]),
                occ_str,
                f"{r['revenue']:,.0f}",
            ])

        col_w = [2*cm, 1.5*cm, 5*cm, 3.5*cm, 2*cm, 2*cm, 2.5*cm, 3*cm]
        t = _data_table(headers, rows, col_widths=col_w, align_right_cols=[4, 5, 6, 7])

        # Color-code occupancy column (index 6) in body rows
        from reportlab.platypus import TableStyle
        extra_styles = []
        for i, r in enumerate(rooms, start=1):
            occ = r["occupancy"]
            if occ >= 80:
                color = _hex(GREEN)
            elif occ >= 50:
                color = _hex(GOLD)
            else:
                color = _hex(MUTED)
            extra_styles.append(("TEXTCOLOR", (6, i), (6, i), color))
            extra_styles.append(("FONTNAME",  (6, i), (6, i), FONT_BOLD))

        # Apply additional styles
        if extra_styles:
            t.setStyle(TableStyle(extra_styles))
        
        elems.append(t)
    else:
        elems.append(Paragraph("Нет данных за выбранный период.", styles["Normal"]))

    doc.build(elems, onFirstPage=_page_footer, onLaterPages=_page_footer)
    buffer.seek(0)

    resp = HttpResponse(buffer, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="occupancy_{start}_{end}.pdf"'
    )
    return resp


# ---------------------------------------------------------------------------
# Excel (existing, kept for compatibility)
# ---------------------------------------------------------------------------

def generate_bookings_excel(start: date, end: date) -> HttpResponse:
    """Generate an Excel report of bookings for the given period."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    from .selectors import get_bookings_report_data

    bookings = get_bookings_report_data(start, end)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Бронирования"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", fgColor="1A1A2E")
    center = Alignment(horizontal="center", vertical="center")
    thin   = Side(style="thin", color="DEE2E6")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = [
        "№ брони", "Гость", "Email", "Телефон", "Категория", "Номер",
        "Заезд", "Выезд", "Ночей", "Взрослых", "Детей",
        "Статус", "Оплата", "Сумма (₽)",
    ]
    ws.append(headers)
    for col_num, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = center
        cell.border    = border

    for b in bookings:
        ws.append([
            b.confirmation_number,
            b.guest_full_name,
            b.guest_email,
            b.guest_phone,
            b.room_category.name,
            b.room.number if b.room else "—",
            b.check_in,
            b.check_out,
            b.nights,
            b.adults,
            b.children,
            b.get_status_display(),
            b.get_payment_status_display(),
            float(b.total_price),
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

    ws.freeze_panes = "A2"

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    resp = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="bookings_{start}_{end}.xlsx"'
    return resp
