# /// script
# requires-python = ">=3.11"
# dependencies = ["reportlab==4.2.5"]
# ///
"""Build the synthetic proposal PDF used in the CampusCue demo.

    uv run docs/demo/make_proposal_pdf.py            # writes docs/demo/robotics-demo-day-proposal.pdf

Everything in it is fictional: the club, the sponsor, the people and every figure. It matches the
seeded campus (Synthetic Robotics Club, Synthetic Main Auditorium, the Projector Kit and PA
System) and the planned event (24 November 2026, 15:00 to 17:00), so what the assistant proposes,
what the organizer uploads and what the assistant later answers from all agree.

Layout notes for the RAG parser: the first line of each page is in capitals, which the parser
reads as the page's section title, so the banner and footer are drawn after the content (they
would otherwise be the first line). Each page holds one topic in under 180 words, so each page
becomes exactly one chunk and a citation can say "page 3: budget".
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).with_name("robotics-demo-day-proposal.pdf")
TITLE = "Synthetic Robotics Demo Day 2026: Event Proposal"
PAGES = 7

styles = getSampleStyleSheet()
H = ParagraphStyle("H", parent=styles["Heading1"], fontSize=15, spaceAfter=6, textColor=colors.HexColor("#14365c"))
SUB = ParagraphStyle("SUB", parent=styles["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=2)
P = ParagraphStyle("P", parent=styles["BodyText"], fontSize=10, leading=14, spaceAfter=4)
NOTE = ParagraphStyle("NOTE", parent=P, fontSize=8.5, textColor=colors.HexColor("#8a1f1f"))


def table(rows: list[list[str]], widths: list[float], header: bool = True) -> Table:
    t = Table(rows, colWidths=[w * mm for w in widths])
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4ecf5")),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ]
    t.setStyle(TableStyle(style))
    return t


def banner(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#8a1f1f"))
    canvas.drawString(18 * mm, 287 * mm, "SYNTHETIC DEMO DOCUMENT - fictional club, people and figures; not institutional data")
    canvas.setFillColor(colors.HexColor("#5b6b7b"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, 10 * mm, f"{TITLE}  |  Submitted by the Synthetic Robotics Club  |  Page {doc.page} of {PAGES}")
    canvas.restoreState()


def story() -> list:
    s: list = []

    # ---- page 1 ------------------------------------------------------------------------------
    s.append(Paragraph("1. EVENT SUMMARY", H))
    s.append(table(
        [
            ["Organizing club", "Synthetic Robotics Club (faculty advisor: Dr. A. Example, fictional)"],
            ["Event", "Synthetic Robotics Demo Day 2026, an open demo afternoon for student robotics teams"],
            ["Date and time", "Tuesday 24 November 2026, 15:00 to 17:00 IST (doors open at 14:45)"],
            ["Venue", "Synthetic Main Auditorium (capacity 450)"],
            ["Expected attendance", "200 students and 12 faculty guests"],
            ["Submitted", "2 November 2026, which is 22 days (over three weeks) before the event"],
        ],
        [42, 128], header=False,
    ))
    s.append(Spacer(1, 4 * mm))
    s.append(Paragraph("Purpose", SUB))
    s.append(Paragraph(
        "Eight student teams demonstrate a working robot for seven minutes each to an audience of "
        "peers and faculty, followed by a supervised indoor drone flight and an awards ceremony. "
        "The goal is to recruit first-year students into the club and to give teams practice "
        "presenting engineering work to a general audience.", P))
    s.append(PageBreak())

    # ---- page 2 ------------------------------------------------------------------------------
    s.append(Paragraph("2. VENUE, TIMING AND SUPPORT REQUESTED", H))
    s.append(Paragraph("Why this slot", SUB))
    s.append(Paragraph(
        "The auditorium has no confirmed booking on 24 November 2026, and the event ends at least two "
        "hours before the next campus event, which respects the planning rule of 120 minutes between "
        "campus events. Venue and equipment requests were sent to Student Affairs more than two weeks "
        "ahead, as the handbook asks, but are not yet confirmed in writing. This proposal is a plan, not "
        "a booking.", P))
    s.append(Paragraph("Equipment and support requested", SUB))
    s.append(Paragraph(
        "One Synthetic Projector Kit, the Synthetic PA System with two wireless microphones, and Synthetic "
        "AV Support (two technicians from 14:00 to 17:30). Stage power: one dedicated three-phase supply "
        "for the demonstration arena.", P))
    s.append(PageBreak())

    # ---- page 3 ------------------------------------------------------------------------------
    s.append(Paragraph("3. BUDGET", H))
    s.append(Paragraph("The total budget for the Synthetic Robotics Demo Day 2026 is Rs. 1,45,000.", P))
    s.append(table(
        [
            ["Line item", "Detail", "Amount (Rs.)"],
            ["Stage and AV hire", "Staging, lighting and cabling beyond the requested support", "48,000"],
            ["Safety netting", "Barriers and netting for the drone flight arena", "22,000"],
            ["Refreshments", "Snacks and water for 200 attendees at Rs. 180 each", "36,000"],
            ["Prizes", "Three team prizes and one audience-choice prize", "20,000"],
            ["Printing and signage", "Posters, programmes and entrance signs", "9,500"],
            ["Contingency", "Held back for unforeseen costs, about 6.5 percent", "9,500"],
            ["Total", "", "1,45,000"],
        ],
        [40, 100, 30],
    ))
    s.append(PageBreak())

    # ---- page 4 ------------------------------------------------------------------------------
    s.append(Paragraph("4. FUNDING AND APPROVALS", H))
    s.append(Paragraph("Funding sources", SUB))
    s.append(Paragraph(
        "Rs. 80,000 comes from the Synthetic Robotics Club's annual allocation. Rs. 65,000 comes from a "
        "sponsorship by Synthetic Tech Partners, a fictional company, which receives its logo on the "
        "programme and one banner at the entrance. No ticket revenue is planned; entry is free for "
        "students.", P))
    s.append(Paragraph("Approvals and reimbursements", SUB))
    s.append(Paragraph(
        "No money is spent before Student Affairs confirms the venue in writing. Purchases above "
        "Rs. 10,000 need a faculty advisor signature, and every reimbursement claim is filed within "
        "seven days of the event with original receipts.", P))
    s.append(PageBreak())

    # ---- page 5 ------------------------------------------------------------------------------
    s.append(Paragraph("5. RUN OF SHOW", H))
    s.append(table(
        [
            ["Time (IST)", "Activity"],
            ["14:45", "Doors open; registration desk and demo-table setup finished"],
            ["15:00", "Welcome and introduction by the club president"],
            ["15:15", "Eight team demonstrations, seven minutes each, with two minutes between teams"],
            ["16:20", "Supervised drone flight demonstration inside the netted arena"],
            ["16:40", "Awards ceremony and audience-choice vote"],
            ["17:00", "Close; teardown, and the room handed back by 17:30"],
        ],
        [28, 142],
    ))
    s.append(PageBreak())

    # ---- page 6 ------------------------------------------------------------------------------
    s.append(Paragraph("6. SAFETY PLAN", H))
    s.append(Paragraph(
        "Drones fly only inside the netted arena, at most two at a time and below three metres, with a "
        "licensed faculty supervisor holding the emergency stop. Lithium batteries are stored in "
        "fireproof bags and are never charged in the auditorium. Two fire marshals and a first-aid desk "
        "staffed by two trained volunteers are present throughout. All emergency exits stay clear and "
        "marked, and attendance is capped at 300 even though the room holds 450.", P))
    s.append(PageBreak())

    # ---- page 7 ------------------------------------------------------------------------------
    s.append(Paragraph("7. VOLUNTEERS", H))
    s.append(Paragraph(
        "Twenty-four student volunteers work in four teams of six: registration, stage and demo tables, "
        "safety and crowd flow, and hospitality. A briefing is held on 23 November at 18:00, and every "
        "volunteer carries a printed copy of the safety plan.", P))
    s.append(Spacer(1, 6 * mm))
    s.append(Paragraph(
        "This document is a synthetic example prepared for a product demonstration. Names, companies, "
        "amounts and dates are invented.", NOTE))
    return s


def main() -> None:
    doc = BaseDocTemplate(
        str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm, title=TITLE,
        author="Synthetic Robotics Club (fictional)", subject="Synthetic demo proposal",
        invariant=True,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    # onPageEnd, not onPage: the banner is then the last text on the page, not the first.
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPageEnd=banner)])
    doc.build(story())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
