from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.api.cases import current_user_or_none
from backend.services.case_access import require_case_access
from fastapi.responses import FileResponse

from backend.services.persistence import load_case
from backend.services.report_generator import generate_csv, generate_pdf, generate_victim_friendly_pdf

router = APIRouter()


@router.get("/reports/{case_id}.victim.pdf")
def get_victim_friendly_report(case_id: str, user: Optional[Dict[str, Any]] = Depends(current_user_or_none)):
    """Generate a separate plain-language report from the saved case only."""
    try:
        # Some Starlette route orders can let the generic `.pdf` matcher pass
        # the suffix through as part of the path parameter. The saved case ID
        # never includes this presentation-only suffix.
        canonical_case_id = case_id.removesuffix(".victim")
        # FastAPI resolves this dependency during HTTP requests. Keeping the
        # direct-call path usable preserves the existing generator unit test.
        if isinstance(user, dict) or user is None:
            require_case_access(canonical_case_id, user)
        case = load_case(canonical_case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {canonical_case_id} not found. Run /trace first.")
        pdf_path = generate_victim_friendly_pdf(canonical_case_id, case)
        return FileResponse(path=pdf_path, filename=f"victim_report_{canonical_case_id}.pdf", media_type="application/pdf")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/reports/{case_id}.pdf")
def get_report(case_id: str, user: Optional[Dict[str, Any]] = Depends(current_user_or_none)):
    """Generate a PDF for a previously run case."""
    # Compatibility guard for an already-running application whose generic
    # route is evaluated before the newly-added victim route. Ordinary
    # investigator report requests never enter this branch.
    if case_id.endswith(".victim"):
        return get_victim_friendly_report(case_id, user)
    try:
        if isinstance(user, dict) or user is None:
            require_case_access(case_id, user)
        case = load_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found. Run /trace first.")
        evidence = case.get('evidence', [])
        summary = case.get('summary', {})
        graph_hash = case.get('graph_hash')
        report_summary = dict(summary)
        report_summary["chain"] = case.get("chain", report_summary.get("chain", "ETH"))
        report_summary["risk_factors"] = case.get("risk_profile", {}).get("risk_factors", [])
        report_summary["provider"] = case.get("provider", "Unknown provider")
        report_summary["investigation_timestamp"] = (case.get("audit_log") or [{}])[0].get("when")
        report_summary["source_wallet"] = case.get("source_wallet") or ((case.get("wallets") or [{}])[0].get("address"))
        report_summary["target_wallet"] = case.get("target_wallet")
        report_summary["seed_tx"] = case.get("seed_tx")
        report_summary["data_source"] = case.get("data_source")
        report_summary["vasp_matches"] = case.get("vasp_matches", [])
        report_summary["suspicious_path"] = case.get("risk_profile", {}).get("suspicious_path", [])
        pdf_path = generate_pdf(
            case_id,
            evidence,
            summary=report_summary,
            graph_hash=graph_hash,
            wallet_clusters=case.get('wallet_clusters', []),
            legal_notice=case.get('legal_notice'),
            evidence_checksum=case.get('evidence_checksum'),
        )
        return FileResponse(path=pdf_path, filename=f"report_{case_id}.pdf", media_type='application/pdf')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{case_id}.csv")
def get_report_csv(case_id: str, user: Optional[Dict[str, Any]] = Depends(current_user_or_none)):
    try:
        if isinstance(user, dict) or user is None:
            require_case_access(case_id, user)
        case = load_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found. Run /trace first.")
        summary = dict(case.get('summary', {}))
        summary["chain"] = case.get("chain", summary.get("chain", "ETH"))
        csv_path = generate_csv(case_id, case.get('evidence', []), summary=summary, graph_hash=case.get('graph_hash'))
        return FileResponse(path=csv_path, filename=f"report_{case_id}.csv", media_type='text/csv')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
