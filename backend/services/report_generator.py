import csv
import json
from pathlib import Path

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
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
        "vasp", "confidence", "explorer_url", "risk_rule", "chain"
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
            })
    return str(out_path)


def generate_pdf(case_id: str, evidence_list, out_path: str = None, summary: dict = None, graph_hash: str = None, wallet_clusters: list = None, legal_notice: str = None, evidence_checksum: str = None):
    """Generate a readable PDF report with core evidence and investigator-scope notice."""
    if out_path is None:
        out_path = REPORT_DIR / f"report_{case_id}.pdf"
    else:
        out_path = Path(out_path)

    doc = SimpleDocTemplate(str(out_path), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    summary = summary or {}
    graph_hash = graph_hash or "N/A"
    total_value = summary.get('total_value', 0)
    traceable_value = summary.get('traceable_value', 0)
    unclassified_value = summary.get('unclassified_value', 0)
    fraud_probability = summary.get('fraud_probability', summary.get('risk_score', 0))
    legal_notice = legal_notice or (
        "This report identifies the likely exchange endpoint and supporting evidence for a legal request. It does not identify a real person — that requires the exchange's own KYC process, which is outside this system's scope."
    )

    story.append(Paragraph(f"CryptoTrace - Investigation Report: {case_id}", styles['Title']))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Fraud probability: {fraud_probability}% | Graph hash: {graph_hash}", styles['Normal']))
    story.append(Paragraph(f"Total value: {total_value} ETH | Traceable: {traceable_value} ETH | Unclassified: {unclassified_value} ETH", styles['Normal']))
    story.append(Paragraph("This report identifies the likely exchange endpoint and supporting evidence for a legal request. It does not identify a real person — that requires the exchange's own KYC process, which is outside this system's scope.", styles['Normal']))
    story.append(Spacer(1, 10))

    data = [["Source wallet", "Destination wallet", "Tx hash", "Amount", "Asset", "Timestamp", "Value at tx time (USD)", "VASP", "Explorer"]]
    for e in evidence_list:
        short_hash = (e.get("tx_hash") or "")[:18]
        data.append([
            e.get("from") or "",
            e.get("to") or "",
            short_hash,
            str(e.get("amount") or ""),
            e.get("asset") or "",
            str(e.get("timestamp") or ""),
            e.get("historical_value_usd") or "historical price unavailable",
            e.get("vasp") or "UNKNOWN",
            e.get("explorer_url") or "",
        ])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E6DA4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

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
            story.append(Paragraph(f"- {flag.get('name', 'Risk flag')}: {flag.get('rule', 'unknown')} (confidence: {flag.get('confidence', 'unknown')})", styles['Normal']))
    else:
        story.append(Paragraph("No risk flags fired for this case.", styles['Normal']))
    story.append(Spacer(1, 8))

    if evidence_checksum:
        story.append(Paragraph("Checksum (evidence integrity): " + evidence_checksum, styles['Normal']))
        story.append(Paragraph("This checksum lets an investigator verify this evidence record has not been altered since it was generated.", styles['Normal']))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Limitations:", styles['Heading3']))
    story.append(Paragraph("This is an investigative lead based on public blockchain data. VASP matches and cluster heuristics are probabilistic and should support, not replace, legal/compliance review.", styles['Normal']))
    doc.build(story)
    return str(out_path)
