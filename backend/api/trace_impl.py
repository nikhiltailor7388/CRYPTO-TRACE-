import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.address_validator import is_valid_eth_address
from backend.services.attribution import apply_fifo_attribution
from backend.graph.analytics import summarize_graph
from backend.services.auth import decode_token, get_bearer_token
from backend.services.fetcher import fetch_transactions
from backend.services.fraud_detector import (
    build_graph_hash,
    calculate_multilayer_probability,
    identify_suspicious_path,
)
from backend.services.graph_utils import bfs_subgraph_from_graph, build_graph_from_txs
from backend.services.normalizer import normalize_etherscan_raw
from backend.services.vasp_matcher import load_vasp_labels, match_vasp_for_address

router = APIRouter()


class TraceRequest(BaseModel):
    case_id: str = Field(...)
    case_name: Optional[str] = None
    chain: str = Field("ETH")
    wallets: List[str] = Field(default_factory=list)
    source_wallet: Optional[str] = None
    target_wallet: Optional[str] = None
    address: Optional[str] = None
    max_hops: int = Field(3, le=3)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/trace")
def trace(req: TraceRequest, request: Request):
    try:
        user_id = None
        auth_header = request.headers.get("authorization")
        if auth_header:
            try:
                user_id = int(decode_token(get_bearer_token(auth_header))["sub"])
            except Exception:
                user_id = None
        wallet_targets = [w for w in (req.wallets or []) if w]
        if req.address and req.address not in wallet_targets:
            wallet_targets.insert(0, req.address)
        if req.source_wallet and req.source_wallet not in wallet_targets:
            wallet_targets.insert(0, req.source_wallet)
        if req.target_wallet and req.target_wallet not in wallet_targets:
            wallet_targets.append(req.target_wallet)

        if not wallet_targets:
            raise HTTPException(status_code=400, detail="Provide at least one wallet address to trace.")

        invalid = [w for w in wallet_targets if w and not is_valid_eth_address(w)]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid wallet address for {req.chain}: {invalid[0]}")

        chain_name = str(req.chain or "ETH").upper().replace(" ", "_")
        all_normalized = []
        seen_hashes = set()
        use_eth = os.getenv("USE_ETHERSCAN", str(settings.use_etherscan)).lower() in ["1", "true", "yes"]
        api_key = os.getenv("ETHERSCAN_API_KEY", settings.etherscan_api_key) or None
        demo_mode = os.getenv("DEMO_MODE", str(settings.demo_mode)).lower() in ["1", "true", "yes"]

        for w in wallet_targets:
            raw = fetch_transactions(w, use_cache=demo_mode or (not use_eth), api_key=api_key, chain=chain_name)
            normalized = normalize_etherscan_raw(raw)
            for tx in normalized:
                tx_hash = tx.get("tx_hash")
                if not tx_hash or tx_hash in seen_hashes:
                    continue
                seen_hashes.add(tx_hash)
                all_normalized.append(tx)

        if not all_normalized:
            raise HTTPException(status_code=404, detail="No transaction data found for the provided wallet(s).")

        G = build_graph_from_txs(all_normalized)
        nodes, edges = bfs_subgraph_from_graph(G, wallet_targets, req.max_hops)
        evidence, annotated = apply_fifo_attribution(all_normalized, wallet_targets)

        vasp_labels = load_vasp_labels()
        for e in evidence:
            match = match_vasp_for_address(e["to"], vasp_labels)
            e["vasp"] = match.get("entity") if match else "UNKNOWN"
            e["confidence"] = match.get("confidence") if match else "UNKNOWN"
            e["explorer_url"] = f"https://etherscan.io/tx/{e.get('tx_hash')}"
            e["source"] = match.get("source") if match else "public blockchain"
            e["source_date"] = match.get("source_date") if match else None

        unique_vasp = {}
        for item in evidence:
            entity = (item.get("vasp") or "UNKNOWN").strip()
            if entity == "UNKNOWN":
                continue
            if entity not in unique_vasp:
                unique_vasp[entity] = {"entity": entity, "confidence": item.get("confidence", "UNKNOWN"), "matches": 0, "amount": 0.0}
            unique_vasp[entity]["matches"] += 1
            unique_vasp[entity]["amount"] += float(item.get("traceable_amount", 0) or 0)

        total_value = sum(float(item.get("amount", 0) or 0) for item in evidence)
        traceable_value = sum(float(item.get("traceable_amount", 0) or 0) for item in evidence)
        unclassified_value = sum(float(item.get("unclassified_amount", 0) or 0) for item in evidence)
        known_vasp_count = len(unique_vasp)
        risk_score = 0
        if total_value > 0:
            risk_score = round(min(99, max(15, (unclassified_value / total_value) * 100)))

        risk_profile = calculate_multilayer_probability(evidence, wallet_targets)
        graph_hash = build_graph_hash(req.case_id, wallet_targets, evidence)
        graph_metrics = summarize_graph(G, wallet_targets)

        response = {
            "case_id": req.case_id,
            "status": "complete",
            "wallets": [{"address": w, "role": "suspect"} for w in wallet_targets],
            "source_wallet": req.source_wallet or (req.address if req.address else None),
            "target_wallet": req.target_wallet,
            "chain": chain_name,
            "summary": {
                "total_transactions": len(all_normalized),
                "hops_traced": req.max_hops,
                "total_value": round(total_value, 3),
                "traceable_value": round(traceable_value, 3),
                "unclassified_value": round(unclassified_value, 3),
                "vasp_matches": known_vasp_count,
                "risk_score": risk_score,
                "fraud_probability": risk_profile.get("overall_probability", risk_score),
            },
            "risk_profile": {
                "overall_probability": risk_profile.get("overall_probability", risk_score),
                "confidence": risk_profile.get("confidence", "low"),
                "fraudster_candidate": risk_profile.get("fraudster_candidate"),
                "risk_factors": risk_profile.get("risk_factors", []),
                "suspicious_path": identify_suspicious_path(evidence, wallet_targets),
            },
            "graph": {"nodes": list(nodes), "edges": list(edges)},
            "graph_metrics": graph_metrics,
            "graph_hash": graph_hash,
            "vasp_matches": list(unique_vasp.values()),
            "evidence": evidence,
            "report_url": f"/reports/{req.case_id}.pdf",
            "csv_report_url": f"/reports/{req.case_id}.csv",
            "data_source": "live" if use_eth and not demo_mode else "cached",
            "fallback_used": demo_mode and (not use_eth or not api_key),
        }

        try:
            from backend.services.persistence import save_case
            save_case(req.case_id, response, user_id=user_id)
        except Exception:
            pass
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
