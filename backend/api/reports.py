from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services.persistence import load_case
from backend.services.report_generator import generate_csv, generate_pdf

router = APIRouter()


@router.get("/reports/{case_id}.pdf")
def get_report(case_id: str):
    """Generate a PDF for a previously run case."""
    try:
        case = load_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found. Run /trace first.")
        evidence = case.get('evidence', [])
        summary = case.get('summary', {})
        graph_hash = case.get('graph_hash')
        pdf_path = generate_pdf(
            case_id,
            evidence,
            summary=summary,
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
def get_report_csv(case_id: str):
    try:
        case = load_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found. Run /trace first.")
        csv_path = generate_csv(case_id, case.get('evidence', []), summary=case.get('summary', {}), graph_hash=case.get('graph_hash'))
        return FileResponse(path=csv_path, filename=f"report_{case_id}.csv", media_type='text/csv')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
