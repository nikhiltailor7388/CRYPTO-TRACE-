from typing import Dict, List


def evaluate_rapid_forwarding(evidence: List[dict]) -> Dict[str, object]:
    if not evidence:
        return {"rule": "rapid_forwarding", "fired": False, "confidence": "LOW", "explanation": "No transactions were received for a rapid forwarding check."}
    t1 = evidence[0]
    t2 = evidence[1] if len(evidence) > 1 else None
    if t2 and t1.get("to") == t2.get("from"):
        return {
            "rule": "rapid_forwarding",
            "fired": True,
            "confidence": "MEDIUM",
            "explanation": "Funds were received and forwarded in a short sequence, which often indicates a rapid movement pattern.",
        }
    return {"rule": "rapid_forwarding", "fired": False, "confidence": "LOW", "explanation": "No rapid forwarding pattern was detected in the traced flow."}


def evaluate_consolidation_pattern(evidence: List[dict]) -> Dict[str, object]:
    if not evidence:
        return {"rule": "consolidation_pattern", "fired": False, "confidence": "LOW", "explanation": "No account consolidation pattern was present."}
    unique_targets = {item.get("to") for item in evidence if item.get("to")}
    if len(unique_targets) <= 1:
        return {
            "rule": "consolidation_pattern",
            "fired": True,
            "confidence": "MEDIUM",
            "explanation": "Multiple incoming funds appear to consolidate into a single downstream address, a typical layering signal.",
        }
    return {"rule": "consolidation_pattern", "fired": False, "confidence": "LOW", "explanation": "No strong consolidation pattern was observed."}


def evaluate_known_mixer_hit(evidence: List[dict]) -> Dict[str, object]:
    hits = [item for item in evidence if str(item.get("to", "")).lower() in {"0xabc0000000000000000000000000000000000000"}]
    if hits:
        return {
            "rule": "known_mixer_address",
            "fired": True,
            "confidence": "HIGH",
            "explanation": "The trace reached a known mixer-style contract or address; this requires probabilistic follow-up rather than direct attribution.",
        }
    return {"rule": "known_mixer_address", "fired": False, "confidence": "LOW", "explanation": "No mixer-style address was encountered in the traced path."}


def evaluate_bridge_boundary(evidence: List[dict]) -> Dict[str, object]:
    if any(item.get("chain") == "ETH" for item in evidence):
        return {
            "rule": "bridge_boundary",
            "fired": True,
            "confidence": "MEDIUM",
            "explanation": "Cross-chain or bridge-adjacent activity was flagged; the system treats it as a boundary event and does not continue the trace arbitrarily.",
        }
    return {"rule": "bridge_boundary", "fired": False, "confidence": "LOW", "explanation": "No bridge boundary was identified in this trace."}
