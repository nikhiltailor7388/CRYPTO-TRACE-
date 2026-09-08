from pathlib import Path

from backend.services.report_generator import generate_pdf, generate_victim_friendly_pdf


def test_pdf_uses_authoritative_risk_and_partial_warning(tmp_path):
    output = tmp_path / "report.pdf"
    generate_pdf(
        "CASE-PDF",
        [{"tx_hash": "0x" + "a" * 64, "from": "0x1", "to": "0x2", "amount": 1.25, "asset": "ETH", "timestamp": "2024-01-01T00:00:00Z", "historical_value_usd": "unavailable", "vasp": "UNKNOWN"}],
        out_path=output,
        summary={"risk_score": 42, "risk_evidence_state": "sufficient", "trace_confidence": "low", "chain": "ETH", "provider": "Etherscan", "partial": True, "partial_reason_details": [{"message": "Safety limit reached"}]},
    )
    assert output.exists()
    assert output.stat().st_size > 0


def test_victim_friendly_pdf_uses_saved_investigation_data_without_recalculation(tmp_path):
    output = tmp_path / "victim-report.pdf"
    result = generate_victim_friendly_pdf(
        "CASE-VICTIM",
        {
            "chain": "ETH",
            "source_wallet": "0xsource",
            "destination_wallets": ["0xdestination"],
            "summary": {"risk_score": 42, "risk_level": "MEDIUM", "trace_confidence": "medium", "total_value": 1.25},
            "risk_profile": {"fraudster_candidate": "0xlead", "risk_factors": [{"observed": True, "score": 7, "explanation": "One observed rapid forwarding pattern."}]},
            "evidence": [{"asset": "ETH"}],
        },
        out_path=output,
    )
    assert result == str(output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_victim_report_route_removes_presentation_suffix_before_loading_case(monkeypatch, tmp_path):
    from backend.api import reports

    loaded_case_ids = []
    output = tmp_path / "victim.pdf"
    monkeypatch.setattr(reports, "load_case", lambda case_id: loaded_case_ids.append(case_id) or {"summary": {}, "evidence": []})
    monkeypatch.setattr(reports, "generate_victim_friendly_pdf", lambda case_id, case: str(output))
    response = reports.get_victim_friendly_report("CASE-123.victim")
    assert loaded_case_ids == ["CASE-123"]
    assert response.filename == "victim_report_CASE-123.pdf"
