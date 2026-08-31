import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def generate_csv(case_id: str, evidence_list, out_path: str = None, summary: dict = None, graph_hash: str = None, chain: str = "ETH"):
    if out_path is None:
        out_path = REPORT_DIR / f"report_{case_id}.csv"
    else:
        out_path = Path(out_path)

    summary = summary or {}
    fieldnames = ["tx_hash", "from", "to", "amount", "asset", "traceable_amount", "unclassified_amount", "timestamp", "vasp", "confidence", "chain"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in evidence_list:
            writer.writerow({
                "tx_hash": e.get("tx_hash", ""),
                "from": e.get("from", ""),
                "to": e.get("to", ""),
                "amount": e.get("amount", ""),
                "asset": e.get("asset", ""),
                "traceable_amount": e.get("traceable_amount", ""),
                "unclassified_amount": e.get("unclassified_amount", ""),
                "timestamp": e.get("timestamp", ""),
                "vasp": e.get("vasp", ""),
                "confidence": e.get("confidence", ""),
                "chain": e.get("chain", summary.get("chain", chain)),
            })
    return str(out_path)


def generate_pdf(case_id: str, evidence_list, out_path: str = None, summary: dict = None, graph_hash: str = None, case: dict = None):
    """Generate a readable PDF report from evidence_list. Returns path to PDF file."""
    if out_path is None:
        out_path = REPORT_DIR / f"report_{case_id}.pdf"
    else:
        out_path = Path(out_path)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6))
    story = []

    summary = summary or {}
    case = case or {}
    graph_hash = graph_hash or "N/A"
    asset = (evidence_list[0].get("asset") if evidence_list else None) or ("TRX" if str(case.get("chain", "")).upper().startswith("TRON") else "ETH")
    total_value = summary.get('total_value', 0)
    traceable_value = summary.get('traceable_value', 0)
    unclassified_value = summary.get('unclassified_value', 0)
    fraud_probability = summary.get('fraud_probability', summary.get('risk_score', 0))
    trace = case.get("trace", {})
    path = trace.get("path", [])

    story.append(Paragraph("CryptoTrace Investigation Report", styles["Title"]))
    story.append(Paragraph(f"Case {case_id} · {case.get('chain', 'ETH')} / {asset}", styles["Heading3"]))
    story.append(Spacer(1, 6))
    summary_data = [
        ["Risk indicator", "Fraud probability", "Total value", "Traceable", "Unclassified"],
        ["Assessment", f"{fraud_probability}%", f"{total_value} {asset}", f"{traceable_value} {asset}", f"{unclassified_value} {asset}"],
    ]
    summary_table = Table(summary_data, colWidths=[31 * mm, 30 * mm, 33 * mm, 33 * mm, 33 * mm], repeatRows=1)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EAF2F8")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C7D9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, 1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Generated from public blockchain evidence. This report is an investigative lead and does not identify real persons or access private KYC data.", styles["Small"]))
    story.append(Spacer(1, 12))

    if path:
        story.append(Paragraph("Bounded Trace Path", styles["Section"]))
        story.append(Paragraph(" → ".join(str(address)[:10] + "…" + str(address)[-8:] for address in path), styles["Small"]))
        story.append(Spacer(1, 6))

    vasp_matches = case.get("vasp_matches", [])
    story.append(Paragraph("VASP Findings", styles["Section"]))
    if vasp_matches:
        vasp_data = [["Entity", "Confidence", "Matches", "Amount", "Source"]]
        for match in vasp_matches:
            matched_evidence = next((item for item in evidence_list if item.get("vasp") == match.get("entity")), {})
            source = matched_evidence.get("source") or "Not provided"
            source_date = matched_evidence.get("source_date")
            if source_date:
                source = f"{source} ({source_date})"
            vasp_data.append([
                match.get("entity", "UNKNOWN"),
                match.get("confidence", "UNKNOWN"),
                str(match.get("matches", 0)),
                f"{match.get('amount', 0)} {asset}",
                Paragraph(source, styles["Small"]),
            ])
        vasp_table = Table(vasp_data, colWidths=[48 * mm, 28 * mm, 20 * mm, 32 * mm, 52 * mm], repeatRows=1)
        vasp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E6DA4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C7D9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(vasp_table)
    else:
        story.append(Paragraph("No verified VASP match was returned for the bounded evidence.", styles["Small"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Transaction Evidence", styles["Section"]))
    data = [["Transaction", "From", "To", "Amount", "Traceable", "Timestamp"]]
    for e in evidence_list:
        data.append([
            Paragraph((e.get("tx_hash") or "")[:16] + "…", styles["Small"]),
            Paragraph((e.get("from") or "")[:10] + "…", styles["Small"]),
            Paragraph((e.get("to") or "")[:10] + "…", styles["Small"]),
            f"{e.get('amount', '')} {e.get('asset', asset)}",
            f"{e.get('traceable_amount', '')} {e.get('asset', asset)}",
            Paragraph(str(e.get("timestamp", "")), styles["Small"]),
        ])

    table = Table(data, colWidths=[30 * mm, 30 * mm, 30 * mm, 25 * mm, 25 * mm, 42 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E6DA4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C7D9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1,12))

    story.append(Paragraph("Assessment and Limitations", styles["Section"]))
    story.append(Paragraph(
        "The flow shows multi-layer evidence: traceable routing, unclassified movement, and VASP-linked destination addresses. "
        "This should be treated as a prioritized investigation lead rather than legal proof of identity or criminality.",
        styles["Small"]
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Attribution uses a conservative FIFO heuristic and curated address matching. UNKNOWN means no labelled match was found, not that an address is safe. Tracing is bounded and follows the largest-value outbound edge; this output is not legal proof of identity or guilt.", styles["Small"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Technical reference: graph hash {graph_hash}", styles["Small"]))

    doc.build(story)
    return str(out_path)
