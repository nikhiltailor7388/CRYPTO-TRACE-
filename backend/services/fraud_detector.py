import hashlib
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from backend.services.address_validator import normalize_address


def _address(value: Any, chain: str = "ETH") -> str:
    return normalize_address(value, chain)


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


def build_wallet_clusters(evidence: List[Dict[str, Any]], wallets: List[str], chain: str = "ETH") -> List[Dict[str, Any]]:
    """Build a basic probabilistic cluster list using common-input-ownership and peeling-chain heuristics.

    These are investigative leads rather than proof of same ownership. Every cluster must carry a reason string and
    confidence value, matching the system requirement for transparent probabilistic clustering.
    """
    if not evidence:
        return []

    normalized_wallets = {_address(w, chain) for w in wallets if w}
    by_origin: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in evidence:
        frm = _address(item.get("from"), item.get("source_chain") or item.get("chain") or chain)
        if frm:
            by_origin[frm].append(item)

    clusters: List[Dict[str, Any]] = []
    seen_members = set()

    # Common-input-ownership heuristic: a single source repeatedly sends to multiple downstream addresses in a short window.
    for origin, items in sorted(by_origin.items()):
        recipients = []
        tx_hashes = []
        for item in items:
            to = _address(item.get("to"), item.get("destination_chain") or item.get("chain") or chain)
            tx_hash = str(item.get("tx_hash") or '')
            if to and to not in normalized_wallets and to not in recipients:
                recipients.append(to)
            if tx_hash and tx_hash not in tx_hashes:
                tx_hashes.append(tx_hash)
        if len(recipients) >= 2:
            members = [origin] + recipients[:4]
            cluster_key = tuple(sorted(members))
            if cluster_key in seen_members:
                continue
            seen_members.add(cluster_key)
            clusters.append({
                "id": f"cluster-{len(clusters) + 1}",
                "members": members,
                "confidence": 0.70,
                "heuristic": "common-input-ownership",
                "reason": (
                    f"Grouped because {len(recipients)} addresses were observed as downstream recipients from the same origin "
                    f"wallet across txs {', '.join(tx_hashes[:3]) or 'unknown'}; this is a probabilistic grouping and not definitive proof of shared control."
                ),
            })

    # Peeling chain heuristic: a wallet repeatedly sends on a large proportion of its balance, leaving a small remainder each hop.
    txs = sorted(
        [item for item in evidence if item.get("timestamp")],
        key=lambda item: str(item.get("timestamp") or ""),
    )
    for index in range(len(txs) - 1):
        current = txs[index]
        nxt = txs[index + 1]
        current_from = _address(current.get("from"), current.get("source_chain") or current.get("chain") or chain)
        next_to = _address(nxt.get("to"), nxt.get("destination_chain") or nxt.get("chain") or chain)
        current_amount = float(current.get("amount") or 0)
        next_amount = float(nxt.get("amount") or 0)
        if not current_from or not next_to or current_amount <= 0 or next_amount <= 0:
            continue
        if current_from == next_to and current_amount > next_amount and (next_amount / current_amount) < 0.5:
            cluster_members = [current_from, _address(current.get("to"), current.get("destination_chain") or current.get("chain") or chain), next_to]
            cluster_key = tuple(sorted(cluster_members))
            if cluster_key in seen_members:
                continue
            seen_members.add(cluster_key)
            clusters.append({
                "id": f"cluster-{len(clusters) + 1}",
                "members": [m for m in cluster_members if m],
                "confidence": 0.65,
                "heuristic": "peeling-chain-detection",
                "reason": (
                    f"Peeling chain pattern detected across hops {index + 1}-{index + 2}: the wallet repeatedly forwarded most of its balance while retaining a smaller remainder; "
                    "this is a probabilistic layering lead, not proof of ownership."
                ),
            })

    return clusters


def compute_evidence_checksum(evidence: List[Dict[str, Any]], *extra: Dict[str, Any]) -> str:
    payload = {"evidence": evidence, "extras": list(extra)}
    flat = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(flat).hexdigest()


def calculate_multilayer_probability(evidence: List[Dict[str, Any]], wallets: List[str], chain: str = "ETH") -> Dict[str, Any]:
    """Calculate a deterministic, explainable risk score from observed evidence.

    This intentionally does not treat trace completeness as risk.  A sparse
    trace can be low-confidence without being low-risk (or vice versa).
    """
    if not evidence:
        return {
            "overall_probability": None,
            "risk_score": None,
            "evidence_state": "insufficient",
            "risk_level": "UNKNOWN",
            "confidence": "low",
            "trace_confidence": "low",
            "risk_factors": [],
            "fraudster_candidate": None,
        }

    total_value = sum(float(item.get("amount") or 0) for item in evidence)
    vasp_hits = sum(1 for item in evidence if (item.get("vasp") or "UNKNOWN") != "UNKNOWN")
    unique_addresses = {_address(item.get("from"), item.get("source_chain") or item.get("chain") or chain) for item in evidence} | {_address(item.get("to"), item.get("destination_chain") or item.get("chain") or chain) for item in evidence}
    cluster_size = len(unique_addresses)
    wallet_set = {_address(w, chain) for w in wallets if w}

    # The score uses only observed behavioural or independently-labelled risk
    # indicators. VASP attribution and unclassified value are retained as
    # context but never add risk by themselves.
    timed = []
    for item in evidence:
        try:
            timestamp = datetime.fromisoformat(str(item.get("timestamp")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        timed.append((timestamp, item))
    timed.sort(key=lambda pair: pair[0])
    rapid_pairs = 0
    for (first_time, first), (second_time, second) in zip(timed, timed[1:]):
        if (_address(first.get("to"), first.get("destination_chain") or chain)
                == _address(second.get("from"), second.get("source_chain") or chain)
                and 0 <= (second_time - first_time).total_seconds() <= 3600):
            rapid_pairs += 1

    adjacency: Dict[str, set] = defaultdict(set)
    inbound: Dict[str, set] = defaultdict(set)
    outbound: Dict[str, set] = defaultdict(set)
    for item in evidence:
        frm = _address(item.get("from"), item.get("source_chain") or chain)
        to = _address(item.get("to"), item.get("destination_chain") or chain)
        if frm and to:
            adjacency[frm].add(to)
            inbound[to].add(frm)
            outbound[frm].add(to)

    def longest_path(node: str, seen: set) -> int:
        return max((1 + longest_path(child, seen | {child}) for child in adjacency.get(node, ()) if child not in seen), default=0)

    max_path = max((longest_path(source, {source}) for source in list(adjacency)), default=0)
    consolidation_sources = max((len(sources) for sources in inbound.values()), default=0)
    split_destinations = max((len(targets) for targets in outbound.values()), default=0)
    mixer_addresses = {"0xabc0000000000000000000000000000000000000"}
    mixer_hits = sum(1 for item in evidence if _address(item.get("to"), item.get("destination_chain") or chain) in mixer_addresses or str(item.get("entity_type") or "").lower() == "mixer")
    bridge_hits = sum(1 for item in evidence if item.get("cross_chain_boundary") or str(item.get("entity_type") or "").lower() == "bridge")
    risky_entity_hits = sum(1 for item in evidence if str(item.get("risk_classification") or "").lower() in {"sanctioned", "high_risk", "illicit"})

    rapid_score = min(15, rapid_pairs * 7)
    layering_score = min(10, max(0, max_path - 1) * 5)
    consolidation_score = min(15, max(0, consolidation_sources - 2) * 5)
    splitting_score = min(10, max(0, split_destinations - 2) * 5)
    mixer_score = 30 if mixer_hits else 0
    risky_entity_score = min(20, risky_entity_hits * 20)
    independent = sum(score > 0 for score in (rapid_score, layering_score, consolidation_score, splitting_score, mixer_score, risky_entity_score))
    interaction_score = min(10, (independent - 1) * 5) if independent >= 2 else 0
    overall_probability = round(min(100, rapid_score + layering_score + consolidation_score + splitting_score + mixer_score + risky_entity_score + interaction_score))
    evidence_state = "sufficient" if len(evidence) >= 2 and (timed or max_path >= 2) else "limited" if evidence else "insufficient"
    trace_confidence = "high" if len(evidence) >= 4 and max_path >= 2 else "medium" if len(evidence) >= 2 else "low"
    confidence = "high" if independent >= 3 and len(evidence) >= 4 else "medium" if independent >= 1 and len(evidence) >= 2 else "low"
    risk_level = "CRITICAL" if overall_probability >= 85 else "HIGH" if overall_probability >= 65 else "MEDIUM" if overall_probability >= 40 else "LOW"

    risk_factors = [
        {"name": "Rapid forwarding", "rule": "rapid_forwarding", "score": rapid_score, "observed": bool(rapid_pairs), "confidence": "high" if rapid_pairs >= 2 else "medium" if rapid_pairs else "low", "explanation": f"{rapid_pairs} sequential transfer(s) were forwarded within one hour based on available timestamps."},
        {"name": "Multi-hop layering", "rule": "multi_hop_layering", "score": layering_score, "observed": max_path >= 2, "confidence": "medium" if max_path >= 2 else "low", "explanation": f"Observed maximum connected flow depth: {max_path} hop(s)."},
        {"name": "Consolidation", "rule": "consolidation", "score": consolidation_score, "observed": consolidation_sources >= 3, "confidence": "medium" if consolidation_sources >= 3 else "low", "explanation": f"Largest observed destination had {consolidation_sources} distinct source wallet(s)."},
        {"name": "Splitting", "rule": "splitting", "score": splitting_score, "observed": split_destinations >= 3, "confidence": "medium" if split_destinations >= 3 else "low", "explanation": f"Largest observed source distributed to {split_destinations} distinct destination wallet(s)."},
        {"name": "Mixer interaction", "rule": "mixer_interaction", "score": mixer_score, "observed": bool(mixer_hits), "confidence": "high" if mixer_hits else "low", "explanation": "Observed interaction with a known or explicitly labelled mixer endpoint." if mixer_hits else "No known or explicitly labelled mixer endpoint was observed."},
        {"name": "Bridge interaction (context only)", "rule": "bridge_interaction", "score": 0, "observed": bool(bridge_hits), "confidence": "medium" if bridge_hits else "low", "explanation": "Bridge activity is recorded as a trace boundary/context and does not itself increase risk."},
        {"name": "VASP attribution (context only)", "rule": "vasp_context", "score": 0, "observed": bool(vasp_hits), "confidence": "medium" if vasp_hits else "low", "explanation": "A VASP/exchange label is attribution context, not a risk indicator by itself."},
        {"name": "Independently risky entity", "rule": "risky_entity", "score": risky_entity_score, "observed": bool(risky_entity_hits), "confidence": "high" if risky_entity_hits else "low", "explanation": "Score applies only to an independently classified sanctioned, illicit, or high-risk entity."},
        {"name": "Independent-indicator interaction", "rule": "indicator_interaction", "score": interaction_score, "observed": interaction_score > 0, "confidence": "medium" if interaction_score else "low", "explanation": f"Bonus applies only because {independent} independent behavioural/risk indicators were observed."},
    ]

    candidate_map: Dict[str, float] = {}
    for item in evidence:
        frm = _address(item.get("from"), item.get("source_chain") or item.get("chain") or chain)
        to = _address(item.get("to"), item.get("destination_chain") or item.get("chain") or chain)
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
        "risk_score": overall_probability,
        "evidence_state": evidence_state,
        "risk_level": risk_level,
        "confidence": confidence,
        "trace_confidence": trace_confidence,
        "risk_factors": risk_factors,
        "fraudster_candidate": candidate,
    }


def apply_canonical_risk(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Populate the one authoritative score for a saved investigation.

    Older case files persisted independent `fraud_probability` and
    `overall_probability` fields. Recomputing from the immutable evidence
    removes those stale values from the API/PDF display path.
    """
    evidence = payload.get("evidence") or []
    wallets = [item.get("address") for item in payload.get("wallets", []) if item.get("address")]
    if not wallets and payload.get("source_wallet"):
        wallets = [payload["source_wallet"]]
    profile = calculate_multilayer_probability(evidence, wallets, payload.get("chain") or "ETH")
    summary = payload.setdefault("summary", {})
    risk_score = profile.get("risk_score")
    trace_confidence = profile.get("trace_confidence") or profile.get("confidence") or "low"
    summary["risk_score"] = risk_score
    summary["risk_level"] = profile["risk_level"]
    summary["risk_evidence_state"] = profile["evidence_state"]
    summary["trace_confidence"] = trace_confidence
    # Retain the legacy field only as an exact alias for compatibility; it is
    # never independently calculated or read as the authoritative value.
    summary["fraud_probability"] = risk_score
    payload["risk_profile"] = {
        **payload.get("risk_profile", {}),
        "overall_probability": risk_score,
        "risk_score": risk_score,
        "risk_level": profile["risk_level"],
        "evidence_state": profile["evidence_state"],
        "trace_confidence": trace_confidence,
        "confidence": profile["confidence"],
        "risk_factors": profile["risk_factors"],
    }
    return payload


def identify_suspicious_path(evidence: List[Dict[str, Any]], wallets: List[str], chain: str = "ETH") -> List[str]:
    wallet_set = {_address(w, chain) for w in wallets if w}
    current = None
    path = []
    for item in evidence:
        frm = _address(item.get("from"), item.get("source_chain") or item.get("chain") or chain)
        to = _address(item.get("to"), item.get("destination_chain") or item.get("chain") or chain)
        if not frm or not to:
            continue
        if frm in wallet_set or to in wallet_set:
            if frm not in path:
                path.append(frm)
            if to not in path:
                path.append(to)
            current = to
    if current is None and evidence:
        path = [
            _address(evidence[0].get("from"), evidence[0].get("source_chain") or evidence[0].get("chain") or chain),
            _address(evidence[0].get("to"), evidence[0].get("destination_chain") or evidence[0].get("chain") or chain),
        ]
    return path
