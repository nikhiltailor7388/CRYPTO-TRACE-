import os
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.graph.analytics import summarize_graph
from backend.services.address_validator import is_valid_address, normalize_address
from backend.services.attribution import apply_fifo_attribution
from backend.services.auth import decode_token, get_bearer_token
from backend.services.fetcher import fetch_transactions
from backend.services.fraud_detector import (
    build_graph_hash,
    build_wallet_clusters,
    calculate_multilayer_probability,
    compute_evidence_checksum,
    identify_suspicious_path,
)
from backend.services.graph_utils import bfs_subgraph_from_graph, build_graph_from_txs, build_graph_payload
from backend.services.normalizer import normalize_etherscan_raw
from backend.services.vasp_matcher import load_vasp_labels, match_vasp_for_address

router = APIRouter()


class TraceRequest(BaseModel):
    case_id: Optional[str] = None
    case_name: Optional[str] = None
    chain: str = Field("ETH")
    wallets: List[str] = Field(default_factory=list)
    source_wallet: Optional[str] = None
    target_wallet: Optional[str] = None
    address: Optional[str] = None
    tx_hash: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    max_hops: int = Field(3, ge=1, le=5)
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

        chain_name = str(req.chain or "ETH").upper().replace(" ", "_")
        invalid = [w for w in wallet_targets if w and not is_valid_address(w, chain_name)]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid wallet address for {req.chain}: {invalid[0]}")

        all_normalized = []
        seen_hashes = set()
        rate_limit_fallback = False
        partial_reasons = []
        trace_started = time.monotonic()
        is_tron = chain_name in {"TRON", "TRX"}
        use_eth = os.getenv("USE_ETHERSCAN", str(settings.use_etherscan)).lower() in ["1", "true", "yes", "on"]
        api_key = (os.getenv("TRONSCAN_API_KEY", getattr(settings, "tronscan_api_key", "")) if is_tron else os.getenv("ETHERSCAN_API_KEY", settings.etherscan_api_key)) or None
        demo_mode = os.getenv("DEMO_MODE", str(settings.demo_mode)).lower() in ["1", "true", "yes", "on"]
        use_live_data = use_eth and not demo_mode
        if use_live_data and not api_key:
            provider_key = "TRONSCAN_API_KEY" if is_tron else "ETHERSCAN_API_KEY"
            raise HTTPException(status_code=503, detail=f"Live retrieval requires {provider_key}. Configure it, or explicitly enable DEMO_MODE=true.")
        if not use_live_data and not demo_mode:
            raise HTTPException(status_code=503, detail="Live retrieval is not configured. Set USE_ETHERSCAN=true and ETHERSCAN_API_KEY, or explicitly enable DEMO_MODE=true.")

        pending = [(wallet, 0) for wallet in wallet_targets]
        fetched_wallets = set()
        while pending:
            if time.monotonic() - trace_started >= settings.trace_timeout_seconds:
                partial_reasons.append("trace_time_limit_reached")
                break
            if len(fetched_wallets) >= settings.max_trace_wallets:
                partial_reasons.append("wallet_limit_reached")
                break
            if len(all_normalized) >= settings.max_trace_transactions:
                partial_reasons.append("transaction_limit_reached")
                break
            w, depth = pending.pop(0)
            wallet_key = normalize_address(w, chain_name)
            if wallet_key in fetched_wallets or depth >= req.max_hops:
                continue
            fetched_wallets.add(wallet_key)
            try:
                raw = fetch_transactions(
                    w,
                    use_cache=(not use_live_data),
                    api_key=api_key,
                    chain=chain_name,
                    tx_hash=req.tx_hash if depth == 0 and wallet_key == normalize_address(wallet_targets[0], chain_name) else None,
                )
            except RuntimeError as exc:
                if str(exc).startswith("TRONSCAN_RATE_LIMIT"):
                    retry_after = str(exc).partition("retry after ")[2].removesuffix("s")
                    headers = {"Retry-After": retry_after} if retry_after.isdigit() else None
                    raise HTTPException(status_code=429, detail="TronScan rate limit reached. Retry later.", headers=headers)
                if str(exc) != "RATE_LIMIT" or not use_live_data or is_tron:
                    raise HTTPException(status_code=502, detail=f"Blockchain provider error: {exc}")
                rate_limit_fallback = True
                use_live_data = False
                raw = fetch_transactions(
                    w,
                    use_cache=True,
                    chain=chain_name,
                    tx_hash=req.tx_hash if depth == 0 and wallet_key == normalize_address(wallet_targets[0], chain_name) else None,
                )
            normalized = normalize_etherscan_raw(raw)
            for tx in normalized:
                if len(all_normalized) >= settings.max_trace_transactions:
                    partial_reasons.append("transaction_limit_reached")
                    break
                transaction_hash = str(tx.get("tx_hash") or "").lower()
                if not transaction_hash or transaction_hash in seen_hashes:
                    continue
                # This is a FROM-wallet investigation: provider history can
                # include unrelated inbound activity. It must not consume the
                # trace budget or become evidence for the outbound flow.
                if normalize_address(tx.get("from"), tx.get("source_chain") or tx.get("chain") or chain_name) != wallet_key:
                    continue
                timestamp = str(tx.get("timestamp") or "")
                if req.start_date and (not timestamp or timestamp[:10] < req.start_date):
                    continue
                if req.end_date and (not timestamp or timestamp[:10] > req.end_date):
                    continue
                seen_hashes.add(transaction_hash)
                all_normalized.append(tx)
                if (
                    normalize_address(tx.get("from"), tx.get("source_chain") or tx.get("chain") or chain_name) == wallet_key
                    and tx.get("to")
                    and not tx.get("cross_chain_boundary")
                ):
                    pending.append((tx["to"], depth + 1))

        partial_reasons = list(dict.fromkeys(partial_reasons))

        if req.tx_hash and use_live_data and not any(
            str(tx.get("tx_hash") or "").lower() == str(req.tx_hash).lower()
            for tx in all_normalized
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Transaction ID was not found in the live {chain_name} data for the provided wallet(s).",
            )

        if not all_normalized:
            if use_live_data:
                raise HTTPException(
                    status_code=404,
                    detail="Unable to retrieve real transaction data for this address — please check the address or try again.",
                )
            raise HTTPException(
                status_code=404,
                detail="Synthetic demo path is enabled, but no labelled demo transaction data was available for this address.",
            )

        G = build_graph_from_txs(all_normalized)
        generated_case_id = req.case_id or f"CASE-{int(time.time())}-{str(uuid.uuid4())[:8]}"

        seed_addresses = list(wallet_targets)
        seed_tx = None
        if req.tx_hash:
            for tx in all_normalized:
                if str(tx.get("tx_hash")).lower() == str(req.tx_hash).lower():
                    seed_tx = tx
                    break
            if not seed_tx:
                raise HTTPException(
                    status_code=404,
                    detail="Transaction ID was not found in the fetched data for the provided wallet(s).",
                )
            if use_live_data:
                seed_parties = {
                    normalize_address(seed_tx.get("from"), seed_tx.get("source_chain") or seed_tx.get("chain") or chain_name),
                }
                if not seed_parties.intersection(normalize_address(wallet, chain_name) for wallet in wallet_targets):
                    raise HTTPException(
                        status_code=400,
                        detail="The supplied transaction is not an outgoing transaction from the provided wallet(s).",
                    )
            seed_addresses = list(wallet_targets)
            if req.currency and str(seed_tx.get("asset") or "").upper() != str(req.currency).upper():
                raise HTTPException(status_code=400, detail="The supplied transaction asset does not match the requested currency.")
            if req.amount is not None and abs(float(seed_tx.get("amount") or 0) - req.amount) > 1e-12:
                raise HTTPException(status_code=400, detail="The supplied transaction amount does not match the requested amount.")

        nodes, edges = bfs_subgraph_from_graph(G, seed_addresses, req.max_hops)
        evidence, _ = apply_fifo_attribution(all_normalized, seed_addresses, chain=chain_name)
        traced_hashes = {str(edge[2] or "").lower() for edge in edges if edge[2]}
        evidence = [
            item for item in evidence
            if str(item.get("tx_hash") or "").lower() in traced_hashes
        ]
        cross_chain_boundaries = [item for item in evidence if item.get("cross_chain_boundary")]
        for item in cross_chain_boundaries:
            item["continuation_status"] = "unsupported_cross_chain"

        recipient_sums = {}
        for ev in evidence:
            to = ev.get("to")
            amt = float(ev.get("amount") or 0)
            if not to:
                continue
            recipient_sums[to] = recipient_sums.get(to, 0.0) + amt
        destination_wallets = [addr for addr, _ in sorted(recipient_sums.items(), key=lambda x: x[1], reverse=True)[:5]]

        wallet_cluster = list(nodes)
        wallet_clusters = build_wallet_clusters(evidence, wallet_targets, chain=chain_name)
        cluster_members = []
        for cluster in wallet_clusters:
            cluster_members.extend(cluster.get("members", []))
        wallet_cluster = sorted(set(wallet_cluster + cluster_members))
        graph_payload = build_graph_payload(nodes, edges, evidence, wallet_targets, wallet_clusters)

        node_roles = {}
        for n in wallet_cluster:
            incoming = sum(float(ev.get("amount") or 0) for ev in evidence if ev.get("to") == n)
            outgoing = sum(float(ev.get("amount") or 0) for ev in evidence if ev.get("from") == n)
            node_roles[n] = {
                "address": n,
                "role": "suspect" if n in wallet_targets else ("destination" if n in destination_wallets else "intermediate"),
                "incoming_total": round(incoming, 6),
                "outgoing_total": round(outgoing, 6),
                "tx_count_in": sum(1 for ev in evidence if ev.get("to") == n),
                "tx_count_out": sum(1 for ev in evidence if ev.get("from") == n),
            }

        vasp_labels = load_vasp_labels()
        price_cache = {}
        price_lookup_count = 0
        for e in evidence:
            match = match_vasp_for_address(
                str(e.get("to") or ""),
                vasp_labels,
                chain=e.get("destination_chain") or chain_name,
            )
            e["vasp"] = match.get("entity") if match else "UNKNOWN"
            e["confidence"] = match.get("confidence") if match else "UNKNOWN"
            e["explorer_url"] = e.get("source_url") or (f"https://etherscan.io/tx/{e.get('tx_hash')}" if e.get("tx_hash") else "")
            e["source"] = match.get("source") if match else "public blockchain"
            e["source_date"] = match.get("source_date") if match else None
            e["asset"] = e.get("asset") or req.currency or "ETH"
            e["risk_rule"] = "suspicious_flow" if float(e.get("amount") or 0) > 0 else "unknown"
            e["historical_value_usd"] = "historical price unavailable"
            try:
                ts = str(e.get("timestamp") or "")
                if ts:
                    date_part = ts.split("T")[0].replace("-", "")
                    asset_key = str(e.get("asset") or "ETH").upper()
                    if asset_key not in price_cache:
                        price_cache[asset_key] = {}
                    # Do not value TRX with Ethereum's price history. Historical
                    # pricing for unsupported assets remains explicitly absent.
                    coin_id = {"ETH": "ethereum", "ETHEREUM": "ethereum"}.get(asset_key)
                    if coin_id and date_part not in price_cache[asset_key] and price_lookup_count < settings.max_historical_price_lookups:
                        import requests
                        price_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history?date={date_part}&localization=false"
                        price_resp = requests.get(price_url, timeout=10)
                        price_y = None
                        if price_resp.ok:
                            price_y = price_resp.json().get("market_data", {}).get("current_price", {}).get("usd")
                        price_cache[asset_key][date_part] = price_y
                        price_lookup_count += 1
                    price_y = price_cache[asset_key].get(date_part)
                    if price_y is not None:
                        e["historical_value_usd"] = f"${float(e.get('amount') or 0) * float(price_y):,.2f} (Value at time of transaction, source: CoinGecko)"
            except Exception:
                e["historical_value_usd"] = "historical price unavailable"

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
        risk_score = round(min(99, max(15, (unclassified_value / total_value) * 100))) if total_value > 0 else 0
        risk_profile = calculate_multilayer_probability(evidence, wallet_targets, chain=chain_name)
        graph_hash = build_graph_hash(generated_case_id, wallet_targets, evidence)
        graph_metrics = summarize_graph(G, wallet_targets)

        evidence_checksum = compute_evidence_checksum(evidence, risk_profile, wallet_clusters)
        legal_notice = (
            "This report identifies the likely exchange endpoint and supporting evidence for a legal request. "
            "It does not identify a real person — that requires the exchange's own KYC process, which is outside this system's scope."
        )

        response = {
            "case_id": generated_case_id,
            "status": "partial" if partial_reasons else "complete",
            "wallets": [{"address": w, "role": "suspect"} for w in wallet_targets],
            "source_wallet": req.source_wallet or (req.address if req.address else None),
            "target_wallet": req.target_wallet,
            "chain": chain_name,
            "provider": "TronScan" if is_tron else "Etherscan",
            "seed_tx": seed_tx or None,
            "requested_amount": req.amount,
            "requested_currency": req.currency,
            "summary": {
                "total_transactions": len(all_normalized),
                "hops_traced": req.max_hops,
                "total_value": round(total_value, 3),
                "traceable_value": round(traceable_value, 3),
                "unclassified_value": round(unclassified_value, 3),
                "vasp_matches": len(unique_vasp),
                "risk_score": risk_score,
                "fraud_probability": risk_profile.get("overall_probability", risk_score),
                "chain": chain_name,
                "partial": bool(partial_reasons),
                "partial_reasons": partial_reasons,
                "limits": {
                    "max_wallets": settings.max_trace_wallets,
                    "max_transactions": settings.max_trace_transactions,
                    "trace_timeout_seconds": settings.trace_timeout_seconds,
                },
            },
            "risk_profile": {
                "overall_probability": risk_profile.get("overall_probability", risk_score),
                "confidence": risk_profile.get("confidence", "low"),
                "fraudster_candidate": risk_profile.get("fraudster_candidate"),
                "risk_factors": risk_profile.get("risk_factors", []),
                "suspicious_path": identify_suspicious_path(evidence, wallet_targets, chain=chain_name),
            },
            "graph": graph_payload,
            "graph_metrics": graph_metrics,
            "graph_hash": graph_hash,
            "vasp_matches": list(unique_vasp.values()),
            "evidence": evidence,
            "destination_wallets": destination_wallets,
            "wallet_cluster": wallet_cluster,
            "wallet_clusters": wallet_clusters,
            "cross_chain_boundaries": cross_chain_boundaries,
            "node_roles": node_roles,
            "report_url": f"/reports/{generated_case_id}.pdf",
            "csv_report_url": f"/reports/{generated_case_id}.csv",
                "data_source": "live" if use_live_data else ("synthetic demo data" if demo_mode or rate_limit_fallback else "cached"),
            "fallback_used": rate_limit_fallback,
            "evidence_checksum": evidence_checksum,
            "legal_notice": legal_notice,
            "audit_log": [{
                "case_id": generated_case_id,
                "who": request.headers.get("x-user-email") or "investigator",
                "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "wallet": wallet_targets[0] if wallet_targets else None,
                "parameters": {"tx_hash": req.tx_hash, "amount": req.amount, "currency": req.currency, "max_hops": req.max_hops, "chain": chain_name},
            }],
        }

        from backend.services.persistence import save_case
        try:
            save_case(generated_case_id, response, user_id=user_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Trace completed but case persistence failed: {exc}")
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
