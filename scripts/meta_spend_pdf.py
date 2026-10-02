"""Build the monthly Meta ad spend PDF.

Usage: python3 scripts/meta_spend_pdf.py data.json out.pdf
data.json: {"account_name": str, "account_id": str, "year": int, "month": int,
            "rows": [{"date": "YYYY-MM-DD", "campaign": str, "spend": "12.34"}, ...]}
Rows come from ads_get_ad_entities (level=campaign, time_increment="1").
Days with no rows are shown as $0.00. Prints the grand total.
"""
import calendar, json, sys
from collections import defaultdict
from datetime import date
from decimal import Decimal as D
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

src, out = sys.argv[1], sys.argv[2]
cfg = json.load(open(src))
y, mo = cfg["year"], cfg["month"]
ndays = calendar.monthrange(y, mo)[1]
month_name = date(y, mo, 1).strftime("%B %Y")

spend = defaultdict(D)  # (day, campaign) -> spend
camp_tot = defaultdict(D)
for r in cfg["rows"]:
    d = date.fromisoformat(r["date"])
    v = D(str(r["spend"]))
    spend[(d.day, r["campaign"])] += v
    camp_tot[r["campaign"]] += v
camps = sorted(camp_tot, key=lambda c: -camp_tot[c])
grand = sum(camp_tot.values(), D(0))
m = lambda v: f"${v:,.2f}"

ss = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, spaceAfter=4, alignment=0)
sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=10, textColor=colors.HexColor("#555555"))
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6)
note = ParagraphStyle("note", parent=ss["Normal"], fontSize=8.5, textColor=colors.HexColor("#666666"), leading=11)
cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=9.5, textColor=colors.white, fontName="Helvetica-Bold", alignment=2)
grey, dark = colors.HexColor("#eeeeee"), colors.HexColor("#222222")


def styled(t):
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("BACKGROUND", (0, 0), (-1, 0), dark),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("BACKGROUND", (0, -1), (-1, -1), grey),
        ("LINEABOVE", (0, -1), (-1, -1), 1, dark)]))
    return t


doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                        title=f"Meta Ad Spend - {month_name}", author="Iron Sanctuary")
el = [Paragraph(f"Meta Ad Spend Report — {month_name}", h1),
      Paragraph(f"Ad account: {cfg['account_name']} &nbsp;·&nbsp; ID {cfg['account_id']}<br/>"
                f"Period: {date(y, mo, 1):%b} 1 – {ndays}, {y} &nbsp;·&nbsp; Currency: USD"
                f" &nbsp;·&nbsp; Generated: {date.today():%b %d, %Y}", sub),
      Paragraph("Summary", h2)]
el.append(styled(Table([["Campaign", "Amount spent"]] + [[c, m(camp_tot[c])] for c in camps]
                       + [[f"TOTAL — {month_name}", m(grand)]], colWidths=[4.5 * inch, 2.5 * inch])))

el.append(Paragraph("Daily breakdown", h2))
total_w = 7.0 * inch
date_w = 1.5 * inch
cw = (total_w - date_w) / (len(camps) + 1)
header = ["Date"] + [Paragraph(c, cell) for c in camps] + ["Day total"]
data, zero_rows = [header], []
for day in range(1, ndays + 1):
    vals = [spend[(day, c)] for c in camps]
    tot = sum(vals, D(0))
    if tot == 0:
        zero_rows.append(len(data))
    data.append([date(y, mo, day).strftime("%a, %b %d")] + [m(v) for v in vals] + [m(tot)])
data.append(["TOTAL"] + [m(camp_tot[c]) for c in camps] + [m(grand)])
tbl = styled(Table(data, colWidths=[date_w] + [cw] * (len(camps) + 1), repeatRows=1))
for i in zero_rows:
    tbl.setStyle(TableStyle([("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#999999"))]))
el += [tbl, Spacer(1, 12), Paragraph(
    "Note: Amounts are ad spend as reported by Meta Ads (by day the ads ran). This is not Meta's official "
    "invoice or receipt. Actual card charges may be grouped differently and may include taxes. For official "
    "billing documents, see Meta Billing &amp; Payments (business.facebook.com/billing_hub).", note)]
doc.build(el)
print(f"{grand:.2f}")
