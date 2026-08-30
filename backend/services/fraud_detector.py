import hashlib
import json
from typing import Any, Dict, List


def build_graph_hash(case_id: str, wallets: List[str], evidence: List[Dict[str, Any]]) -> str:
    payload = {
        "case_id": case_id,
        "wallets": sorted((w or '').lower().strip() for w in wallets if w),
        "transactions": [
            {
                "from": (item.get("from") or '').lower(),
                "to": (item.get("to") or '').lower(),
                "amount": float(item.get("amount") or 0),
                "tx_hash": item.get("tx_hash") or "",
            }
            for item in evidence
        ],
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:32]


def calculate_multilayer_probability(evidence: List[Dict[str, Any]], wallets: List[str]) -> Dict[str, Any]:
    if not evidence:
        return {
            "overall_probability": 0,
            "confidence": "low",
            "risk_factors": [],
            "fraudster_candidate": None,
        }

    total_value = sum(float(item.get("amount") or 0) for item in evidence)
    traceable_value = sum(float(item.get("traceable_amount") or 0) for item in evidence)
    unclassified_value = sum(float(item.get("unclassified_amount") or 0) for item in evidence)
    vasp_hits = sum(1 for item in evidence if (item.get("vasp") or "UNKNOWN") != "UNKNOWN")
    unique_addresses = {str(item.get("from") or '').lower() for item in evidence} | {str(item.get("to") or '').lower() for item in evidence}
    cluster_size = len(unique_addresses)
    wallet_set = {str(w or '').lower() for w in wallets if w}

    direct_exposure = min(35.0, (traceable_value / total_value * 35.0) if total_value else 0.0)
    vasp_factor = min(25.0, vasp_hits * 12.5)
    unclassified_factor = min(25.0, (unclassified_value / total_value * 25.0) if total_value else 0.0)
    propagation_factor = min(15.0, cluster_size * 2.0)
    wallet_binding = 10.0 if wallet_set and any(addr not in wallet_set for addr in unique_addresses if addr) else 0.0

    overall_probability = round(min(99.0, direct_exposure + vasp_factor + unclassified_factor + propagation_factor + wallet_binding))
    if overall_probability >= 70:
        confidence = "high"
    elif overall_probability >= 40:
        confidence = "medium"
    else:
        confidence = "low"

    risk_factors = [
        {
            "name": "Direct exposure",
            "score": round(direct_exposure),
            "rule": "direct_exposure",
            "confidence": "medium" if direct_exposure >= 10 else "low",
            "explanation": "The traced wallet shows meaningful downstream value movement that is directly tied to the case flow.",
        },
        {
            "name": "VASP linkage",
            "score": round(vasp_factor),
            "rule": "vasp_linkage",
            "confidence": "medium" if vasp_hits else "low",
            "explanation": "Known VASP or exchange labels appear in the trace; this indicates a potential destination or off-ramp pattern.",
        },
        {
            "name": "Unclassified flow",
            "score": round(unclassified_factor),
            "rule": "unclassified_flow",
            "confidence": "medium" if unclassified_value > 0 else "low",
            "explanation": "A non-trivial portion of the funds cannot be cleanly assigned to a known wallet or exchange path.",
        },
        {
            "name": "Propagation depth",
            "score": round(propagation_factor),
            "rule": "propagation_depth",
            "confidence": "medium" if cluster_size > 3 else "low",
            "explanation": "The flow spreads through multiple addresses, increasing the chance of layering or obfuscation.",
        },
    ]

    candidate_map: Dict[str, float] = {}
    for item in evidence:
        frm = str(item.get("from") or '').lower()
        to = str(item.get("to") or '').lower()
        amt = float(item.get("amount") or 0)
        if frm and frm not in wallet_set:
            candidate_map[frm] = candidate_map.get(frm, 0.0) + amt
        if to and to not in wallet_set:
            candidate_map[to] = candidate_map.get(to, 0.0) + amt * 1.15
        if (item.get("vasp") or "UNKNOWN") != "UNKNOWN":
            candidate_map[to] = candidate_map.get(to, 0.0) + 2.0

    candidate = None
    if candidate_map:
        candidate = max(candidate_map.items(), key=lambda pair: pair[1])[0]

    return {
        "overall_probability": overall_probability,
        "confidence": confidence,
        "risk_factors": risk_factors,
        "fraudster_candidate": candidate,
    }


def identify_suspicious_path(evidence: List[Dict[str, Any]], wallets: List[str]) -> List[str]:
    wallet_set = {str(w or '').lower() for w in wallets if w}
    current = None
    path = []
    for item in evidence:
        frm = str(item.get("from") or '').lower()
        to = str(item.get("to") or '').lower()
        if not frm or not to:
            continue
        if frm in wallet_set or to in wallet_set:
            if frm not in path:
                path.append(frm)
            if to not in path:
                path.append(to)
            current = to
    if current is None and evidence:
        path = [str(evidence[0].get("from") or '').lower(), str(evidence[0].get("to") or '').lower()]
    return path
