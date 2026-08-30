from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from backend.services.graph_builder import build_graph, bfs_subgraph
from backend.services.attribution import apply_fifo_attribution
from backend.services.vasp_matcher import load_vasp_labels, match_vasp_for_address

router = APIRouter()

class TraceRequest(BaseModel):
    case_id: str = Field(...)
    case_name: Optional[str] = None
    chain: str = Field("ETH")
    wallets: List[str] = Field(default_factory=list)
    source_wallet: Optional[str] = None
    target_wallet: Optional[str] = None
    max_hops: int = Field(3, le=3)
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@router.get("/schema")
def schema():
    """Return the agreed /trace request/response schema for frontend mocking and integration."""
    return {
        "request_example": {
            "case_id": "CASE-001",
            "case_name": "Demo Case 001",
            "chain": "ETH",
            "wallets": ["0xvictim", "0xaaa111aaa111aaa111aaa111aaa111aaa111aaa1"],
            "source_wallet": "0xvictim",
            "target_wallet": "0xccc333ccc333ccc333ccc333ccc333ccc333ccc3",
            "max_hops": 3
        },
        "response_example": {
            "case_id": "CASE-001",
            "status": "complete",
            "wallets": [{"address":"0xvictim","role":"suspect"}],
            "summary": {"total_transactions": 3, "hops_traced": 3, "fraud_probability": 57},
            "risk_profile": {"overall_probability": 57, "confidence": "medium", "fraudster_candidate": "0xbbb...", "suspicious_path": ["0xvictim", "0xaaa...", "0xbbb...", "0xccc..."]},
            "graph_hash": "f2f8a7d26bb8d0a6fc59249328b83c8c",
            "graph": {"nodes": ["0xaaa...","0xbbb...","0xccc..."], "edges": [["0xaaa...","0xbbb...","txhash"]]},
            "evidence": [{"hop":1, "from":"0xaaa...","to":"0xbbb...","amount":20.0,"traceable_amount":10.0,"unclassified_amount":10.0,"tx_hash":"0x123...","timestamp":"2024-06-01T10:00:00Z","block":19000002,"vasp":"UNKNOWN","confidence":"UNKNOWN","explorer_url":"https://etherscan.io/tx/0x123..."}],
            "report_url":"/reports/CASE-001.pdf",
            "data_source":"cached"
        }
    }
