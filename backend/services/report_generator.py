import csv
import json
from pathlib import Path

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _historical_value_at_timestamp(asset: str, amount: float, timestamp: str):
    if not timestamp or amount in (None, 0):
        return "historical price unavailable"
    try:
        if asset.upper() in {"ETH", "ETHEREUM"}:
            asset_id = "ethereum"
        elif asset.upper() in {"USDT", "TETHER"}:
            asset_id = "tether"
        elif asset.upper() in {"USDC", "USDCOIN"}:
            asset_id = "usd-coin"
        else:
            return "historical price unavailable"
        dt = str(timestamp).split("T")[0].replace("-", "")
        url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/history?date={dt}&localization=false"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data.get("market_data", {}).get("current_price", {}).get("usd")
        if price is None:
            return "historical price unavailable"
        return f"${amount * float(price):,.2f} (Value at time of transaction, source: CoinGecko)"
    except Exception:
        return "historical price unavailable"


def generate_csv(case_id: str, evidence_list, out_path: str = None, summary: dict = None, graph_hash: str = None):
    if out_path is None:
        out_path = REPORT_DIR / f"report_{case_id}.csv"
    else:
        out_path = Path(out_path)

    summary = summary or {}
    fieldnames = [
        "tx_hash", "from", "to", "amount", "asset", "value_at_tx_time_usd", "timestamp",
        "vasp", "confidence", "explorer_url", "risk_rule", "chain", "source_chain", "destination_chain", "continuation_status"
    ]
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
                "value_at_tx_time_usd": e.get("historical_value_usd", "historical price unavailable"),
                "timestamp": e.get("timestamp", ""),
                "vasp": e.get("vasp", ""),
                "confidence": e.get("confidence", ""),
                "explorer_url": e.get("explorer_url", ""),
                "risk_rule": e.get("risk_rule", ""),
                "chain": e.get("chain", summary.get("chain", "ETH")),
                "source_chain": e.get("source_chain", e.get("chain", summary.get("chain", "ETH"))),
                "destination_chain": e.get("destination_chain", e.get("chain", summary.get("chain", "ETH"))),
                "continuation_status": e.get("continuation_status", ""),
            })
    return str(out_path)


def generate_victim_friendly_pdf(case_id: str, investigation: dict, out_path: str = None):
    """Create a plain-language companion report from an already saved case.

    This function intentionally performs no tracing, scoring, attribution, or
    valuation. Every case-specific fact is read directly from the canonical
    saved investigation response.
    """
    if out_path is None:
        out_path = REPORT_DIR / f"victim_report_{case_id}.pdf"
    else:
        out_path = Path(out_path)

    summary = investigation.get("summary") or {}
    profile = investigation.get("risk_profile") or {}
    evidence = investigation.get("evidence") or []
    chain = investigation.get("chain") or summary.get("chain") or "Unknown network"
    source_wallet = investigation.get("source_wallet") or ((investigation.get("wallets") or [{}])[0].get("address"))
    destination_wallets = investigation.get("destination_wallets") or []
    candidate = profile.get("fraudster_candidate")
    risk_score = summary.get("risk_score")
    risk_level = summary.get("risk_level") or profile.get("risk_level") or "UNKNOWN"
    asset = next((item.get("asset") for item in evidence if item.get("asset")), chain)

    def short_wallet(value):
        text = str(value or "")
        return f"{text[:7]}...{text[-6:]}" if len(text) > 16 else (text or "Not available")

    doc = SimpleDocTemplate(str(out_path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#123047")
    styles["Title"].fontSize = 22
    styles["Title"].leading = 26
    body = styles["BodyText"]
    body.leading = 15
    body.textColor = colors.HexColor("#263746")
    heading = ParagraphStyle("VictimHeading", parent=styles["Heading2"], textColor=colors.HexColor("#123047"), fontSize=14, leading=18, spaceBefore=13, spaceAfter=7)
    small = ParagraphStyle("VictimSmall", parent=body, textColor=colors.HexColor("#526777"), fontSize=8, leading=10)
    centered = ParagraphStyle("VictimCentered", parent=body, alignment=TA_CENTER)
    story = [Paragraph("CryptoTrace — Victim-Friendly Report", styles["Title"]), Spacer(1, 10)]
    story.append(Paragraph(f"Case reference: {case_id} | Network: {chain}", body))
    story.append(Spacer(1, 10))

    card_label = ParagraphStyle("VictimCardLabel", parent=small, alignment=TA_CENTER)
    card_value = ParagraphStyle("VictimCardValue", parent=centered, textColor=colors.HexColor("#123047"), fontSize=12, leading=15)
    summary_cards = [[
        Paragraph("AMOUNT IN TRACE", card_label), Paragraph("TRANSACTIONS", card_label), Paragraph("HOPS REVIEWED", card_label), Paragraph("TRACE CONFIDENCE", card_label),
    ], [
        Paragraph(f"{float(summary.get('total_value') or 0):,.8f} {asset}", card_value),
        Paragraph(str(summary.get("total_transactions", len(evidence))), card_value),
        Paragraph(f"{summary.get('trace_depth_reached', 0)} / {summary.get('max_hops', summary.get('hops_traced', 'N/A'))}", card_value),
        Paragraph(str(summary.get("trace_confidence", "unknown")).title(), card_value),
    ]]
    card_table = Table(summary_cards, colWidths=[44 * mm] * 4)
    card_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF5F8")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E3E9")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E3E9")), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(card_table)
    story.append(Spacer(1, 10))

    # This status panel is presentation-only: it reads the saved score and
    # saved risk level and does not perform a second calculation.
    level_colour = {"LOW": "#2E7D5B", "MEDIUM": "#A66B00", "HIGH": "#C24E4E", "CRITICAL": "#8A2540"}.get(str(risk_level).upper(), "#526777")
    score_value = f"{risk_score}/100" if risk_score is not None else "N/A"
    top_risk = Table([[
        Paragraph("RISK STATUS", card_label),
        Paragraph(score_value, ParagraphStyle("VictimTopScore", parent=centered, textColor=colors.HexColor(level_colour), fontSize=25, leading=28)),
        Paragraph(str(risk_level).upper(), ParagraphStyle("VictimTopLevel", parent=card_value, textColor=colors.HexColor(level_colour), fontSize=16)),
    ]], colWidths=[42 * mm, 58 * mm, 76 * mm])
    top_risk.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9F4EE")), ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(level_colour)), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([top_risk, Spacer(1, 4), Paragraph("This status reflects the saved investigation result. Trace confidence is shown separately in the summary above.", small)])

    story.append(Paragraph("What happened?", heading))
    if evidence:
        story.append(Paragraph(
            f"This automated review found {len(evidence)} recorded transaction(s) connected to the supplied wallet on {chain}. "
            f"The total amount represented in this trace is {float(summary.get('total_value') or 0):,.8f} {asset}.", body
        ))
    else:
        story.append(Paragraph("No transaction evidence was available in the saved investigation result.", body))

    story.append(Paragraph("Observed money movement", heading))
    if source_wallet:
        story.append(Paragraph(f"<b>Starting wallet:</b> {short_wallet(source_wallet)}", body))
    if destination_wallets:
        story.append(Paragraph("<b>Observed downstream wallet(s):</b> " + "; ".join(short_wallet(wallet) for wallet in destination_wallets), body))
    elif evidence:
        story.append(Paragraph("The saved trace did not identify a separate downstream destination list.", body))
    else:
        story.append(Paragraph("No movement path was available.", body))

    # Build a compact diagram only from direct saved evidence links. A wallet
    # is never placed in the diagram merely because it is an investigative lead.
    links = {}
    for item in evidence:
        frm, to = str(item.get("from") or ""), str(item.get("to") or "")
        if frm and to and frm not in links:
            links[frm] = to
    flow = [str(source_wallet)] if source_wallet else []
    while flow and len(flow) < 4 and links.get(flow[-1]) and links[flow[-1]] not in flow:
        flow.append(links[flow[-1]])
    if len(flow) > 1:
        cells = []
        for index, wallet in enumerate(flow):
            if index:
                cells.append(Paragraph("&rarr;", centered))
            role = "Starting wallet" if index == 0 else ("Investigative lead" if str(wallet) == str(candidate or "") else "Observed wallet")
            cells.append(Paragraph(f"<b>{role}</b><br/>{short_wallet(wallet)}", ParagraphStyle("VictimFlow", parent=small, alignment=TA_CENTER, textColor=colors.HexColor("#123047"))))
        widths = [(176 * mm - 12 * mm * (len(flow) - 1)) / len(flow) if index % 2 == 0 else 12 * mm for index in range(len(cells))]
        flow_table = Table([cells], colWidths=widths)
        flow_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF5F8")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E3E9")), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        story.append(flow_table)
        story.append(Paragraph("Each arrow represents a recorded transaction in the saved investigation. No unsupported links are shown.", small))

    story.append(Paragraph("Key transactions", heading))
    if evidence:
        transaction_rows = [[
            Paragraph("STEP", card_label), Paragraph("FROM", card_label), Paragraph("TO", card_label), Paragraph("AMOUNT", card_label), Paragraph("ASSET", card_label), Paragraph("STATUS", card_label),
        ]]
        for step, item in enumerate(evidence[:10], start=1):
            transaction_rows.append([
                Paragraph(str(step), centered),
                Paragraph(short_wallet(item.get("from")), small),
                Paragraph(short_wallet(item.get("to")), small),
                Paragraph(f"{float(item.get('amount') or 0):,.8f}", centered),
                Paragraph(str(item.get("asset") or asset), centered),
                Paragraph(str(item.get("continuation_status") or "Observed"), small),
            ])
        transaction_table = Table(transaction_rows, repeatRows=1, colWidths=[13 * mm, 34 * mm, 34 * mm, 32 * mm, 18 * mm, 43 * mm])
        transaction_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123047")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7FAFB")), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5E3E9")), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(transaction_table)
        if len(evidence) > 10:
            story.append(Paragraph(f"Showing the first 10 of {len(evidence)} saved transaction records. Full hashes and evidence remain in the detailed investigator report.", small))
    else:
        story.append(Paragraph("No saved transaction records are available for this section.", body))

    story.append(Paragraph("Investigative lead", heading))
    if candidate:
        lead_table = Table([
            [Paragraph("AUTOMATED INVESTIGATIVE LEAD", card_label)],
            [Paragraph(short_wallet(candidate), ParagraphStyle("VictimLead", parent=centered, textColor=colors.HexColor("#8A2540"), fontSize=11, leading=13))],
            [Paragraph("This is NOT proof that this wallet belongs to a fraudster or to any particular person. It is an automated lead based only on saved investigation data.", small)],
        ], colWidths=[176 * mm])
        lead_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBEFF1")), ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#C24E4E")), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(lead_table)
    else:
        story.append(Paragraph("No wallet was highlighted as an investigative lead in this result.", body))

    level_colour = {"LOW": "#2E7D5B", "MEDIUM": "#A66B00", "HIGH": "#C24E4E", "CRITICAL": "#8A2540"}.get(str(risk_level).upper(), "#526777")
    score_value = f"{risk_score}/100" if risk_score is not None else "N/A"
    risk_table = Table([[
        Paragraph("RISK SCORE", card_label),
        Paragraph(score_value, ParagraphStyle("VictimScore", parent=centered, textColor=colors.HexColor(level_colour), fontSize=24, leading=27)),
        Paragraph(str(risk_level).upper(), ParagraphStyle("VictimLevel", parent=card_value, textColor=colors.HexColor(level_colour), fontSize=16)),
    ]], colWidths=[42 * mm, 58 * mm, 76 * mm])
    risk_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9F4EE")), ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(level_colour)), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(Paragraph("Why was it flagged?", heading))
    observed_factors = [factor for factor in profile.get("risk_factors", []) if factor.get("observed") and factor.get("score", 0) > 0]
    if observed_factors:
        factor_table = Table(
            [[Paragraph(str(factor.get("name", "Observed indicator")), body), Paragraph(str(factor.get("explanation", "")), small)] for factor in observed_factors],
            colWidths=[52 * mm, 124 * mm],
        )
        factor_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFB")), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5E3E9")), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
        story.append(factor_table)
        for factor in []:
            story.append(Paragraph(f"• {factor.get('explanation', factor.get('name', 'Observed pattern'))}", body))
    else:
        story.append(Paragraph("No strong behavioural risk pattern was recorded in the saved analysis. Unknown wallets, missing attribution, and exchange labels are not treated as proof of fraud.", body))

    story.append(Paragraph("What should you do now?", heading))
    for step in (
        "Save this report and the original transaction confirmation, messages, screenshots, and payment records.",
        "Contact your bank, exchange, or payment provider as soon as possible and provide the transaction reference.",
        "Report the incident to the appropriate local cybercrime or law-enforcement authority.",
        "Do not send additional money or share recovery codes with anyone claiming they can reverse the transaction.",
    ):
        story.append(Paragraph(f"• {step}", body))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Technical details", heading))
    technical = [
        ["Case ID", case_id], ["Network", chain], ["Provider", investigation.get("provider") or "not recorded"],
        ["Data source", investigation.get("data_source") or "not recorded"], ["Trace status", summary.get("trace_status") or investigation.get("status") or "not recorded"],
        ["Starting wallet", source_wallet or "not recorded"], ["Investigative lead", candidate or "not recorded"],
        ["Graph reference", investigation.get("graph_hash") or "not recorded"], ["Evidence checksum", investigation.get("evidence_checksum") or "not recorded"],
    ]
    technical_table = Table([[Paragraph(str(label), small), Paragraph(str(value), small)] for label, value in technical], colWidths=[44 * mm, 132 * mm])
    technical_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF5F8")), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5E3E9")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(technical_table)
    story.append(Paragraph("Important legal and automated-analysis disclaimer", heading))
    story.append(Paragraph(
        "This is an automated analysis of public blockchain data. It is an investigative lead, not proof that any wallet belongs to a particular person or that a person committed a crime. Identity information requires appropriate legal and KYC processes.",
        body,
    ))
    def victim_footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D5E3E9"))
        canvas.line(16 * mm, 11 * mm, A4[0] - 16 * mm, 11 * mm)
        canvas.setFillColor(colors.HexColor("#526777"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(16 * mm, 7 * mm, f"CryptoTrace victim-friendly report | Case {case_id}")
        canvas.drawRightString(A4[0] - 16 * mm, 7 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=victim_footer, onLaterPages=victim_footer)
    return str(out_path)


def generate_pdf(case_id: str, evidence_list, out_path: str = None, summary: dict = None, graph_hash: str = None, wallet_clusters: list = None, legal_notice: str = None, evidence_checksum: str = None):
    """Generate a readable PDF report with core evidence and investigator-scope notice."""
    if out_path is None:
        out_path = REPORT_DIR / f"report_{case_id}.pdf"
    else:
        out_path = Path(out_path)

    doc = SimpleDocTemplate(str(out_path), pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = []

    summary = summary or {}
    graph_hash = graph_hash or "N/A"
    total_value = summary.get('total_value', 0)
    traceable_value = summary.get('traceable_value', 0)
    unclassified_value = summary.get('unclassified_value', 0)
    risk_score = summary.get('risk_score')
    legal_notice = legal_notice or (
        "This report identifies the likely exchange endpoint and supporting evidence for a legal request. It does not identify a real person — that requires the exchange's own KYC process, which is outside this system's scope."
    )

    story.append(Paragraph(f"CryptoTrace - Investigation Report: {case_id}", styles['Title']))
    story.append(Spacer(1, 6))
    risk_text = f"{risk_score}%" if risk_score is not None else "Insufficient evidence for a numeric score"
    story.append(Paragraph(f"Risk score: {risk_text} | Risk evidence: {summary.get('risk_evidence_state', 'unknown')} | Trace confidence: {summary.get('trace_confidence', 'unknown')}", styles['Normal']))
    story.append(Paragraph(f"Network: {summary.get('chain', 'unknown')} | Provider: {summary.get('provider', 'unknown')} | Data source: {summary.get('data_source', 'unknown')} | Investigation time: {summary.get('investigation_timestamp') or 'not recorded'}", styles['Normal']))
    story.append(Paragraph(f"Source wallet: {summary.get('source_wallet') or 'not supplied'} | Target wallet: {summary.get('target_wallet') or 'not supplied'} | Hops: {summary.get('trace_depth_reached', 0)}/{summary.get('max_hops', 'unknown')} | Transactions: {summary.get('total_transactions', len(evidence_list))}", styles['Normal']))
    if summary.get("seed_tx"):
        story.append(Paragraph(f"Seed transaction: {summary['seed_tx'].get('tx_hash', 'unknown')}", styles['Normal']))
    story.append(Paragraph(f"Graph hash: {graph_hash}", styles['Normal']))
    asset = summary.get("chain", "ETH")
    story.append(Paragraph(f"Total value: {total_value} {asset} | Traceable: {traceable_value} {asset} | Unclassified: {unclassified_value} {asset}", styles['Normal']))
    story.append(Paragraph(legal_notice, styles['Normal']))
    story.append(Spacer(1, 10))

    if summary.get("partial"):
        reasons = "; ".join(detail.get("message", detail.get("code", "")) for detail in summary.get("partial_reason_details", []))
        story.append(Paragraph(f"PARTIAL TRACE: {reasons or 'Traversal was incomplete. Results must not be treated as a complete flow.'}", styles['Normal']))
        story.append(Spacer(1, 6))

    cell_style = styles['BodyText']
    cell_style.fontSize = 6
    cell_style.leading = 7
    data = [["From", "To", "Transaction hash", "Amount", "Asset", "Timestamp", "USD at tx time", "VASP"]]
    for e in evidence_list:
        tx_hash = e.get("tx_hash") or ""
        data.append([
            Paragraph(str(e.get("from") or ""), cell_style),
            Paragraph(str(e.get("to") or ""), cell_style),
            Paragraph(str(tx_hash), cell_style),
            Paragraph(f"{float(e.get('amount') or 0):,.8f}", cell_style),
            Paragraph(str(e.get("asset") or ""), cell_style),
            Paragraph(str(e.get("timestamp") or "unavailable"), cell_style),
            Paragraph(str(e.get("historical_value_usd") or "unavailable"), cell_style),
            Paragraph(str(e.get("vasp") or "UNKNOWN"), cell_style),
        ])
    table = Table(data, repeatRows=1, colWidths=[30*mm, 30*mm, 40*mm, 20*mm, 14*mm, 32*mm, 38*mm, 25*mm], splitByRow=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E6DA4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("VASP/entity attribution", styles['Heading3']))
    vasp_matches = summary.get("vasp_matches") or []
    if vasp_matches:
        for match in vasp_matches:
            story.append(Paragraph(f"{match.get('entity', 'UNKNOWN')} — confidence: {match.get('confidence', 'UNKNOWN')}; matches: {match.get('matches', 0)}; traced amount: {match.get('amount', 0)}. Attribution is context, not an allegation.", styles['Normal']))
    else:
        story.append(Paragraph("No reliable public VASP/entity attribution was available.", styles['Normal']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Wallet clusters", styles['Heading3']))
    cluster_records = wallet_clusters or []
    if cluster_records:
        for cluster in cluster_records:
            story.append(Paragraph(
                f"- {cluster.get('id', 'cluster')}: members={cluster.get('members', [])}; heuristic={cluster.get('heuristic', 'unknown')}; confidence={cluster.get('confidence', 'unknown')}; reason={cluster.get('reason', 'No reason given')}",
                styles['Normal'],
            ))
    else:
        story.append(Paragraph("No wallet clusters were inferred from the available evidence.", styles['Normal']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Risk flags", styles['Heading3']))
    risk_flags = summary.get("risk_factors") or summary.get("risk_profile", {}).get("risk_factors", [])
    if risk_flags:
        for flag in risk_flags:
            story.append(Paragraph(f"- {flag.get('name', 'Risk flag')}: {flag.get('rule', 'unknown')} | observed: {flag.get('observed', False)} | score contribution: {flag.get('score', 0)} | confidence: {flag.get('confidence', 'unknown')}. {flag.get('explanation', '')}", styles['Normal']))
    else:
        story.append(Paragraph("No risk flags fired for this case.", styles['Normal']))
    story.append(Spacer(1, 8))

    if evidence_checksum:
        story.append(Paragraph("Checksum (evidence integrity): " + evidence_checksum, styles['Normal']))
        story.append(Paragraph("This checksum lets an investigator verify this evidence record has not been altered since it was generated.", styles['Normal']))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Limitations:", styles['Heading3']))
    story.append(Paragraph("This is an investigative lead based on public blockchain data. VASP matches and cluster heuristics are probabilistic and should support, not replace, legal/compliance review.", styles['Normal']))
    def page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(landscape(A4)[0] - 12 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    return str(out_path)
