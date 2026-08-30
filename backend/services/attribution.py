from typing import List, Dict, Any


def apply_fifo_attribution(txs: List[Dict[str, Any]], suspect_wallets: List[str]):
    """Apply the FIFO attribution from the build doc.

    txs: list of normalized transactions sorted by timestamp asc.
    Each tx is a dict with keys: tx_hash, from, to, amount

    Returns (evidence_list, annotated_tx_list)
    evidence_list: list of dicts describing transactions and traceable amounts
    """
    # Normalize addresses
    initial_suspects = set([s.lower() for s in suspect_wallets])
    suspected_balance: Dict[str, float] = {}
    annotated = []
    evidence = []

    # Ensure timestamps order; if missing, assume incoming order
    sorted_txs = sorted(txs, key=lambda x: x.get("timestamp", ""))

    for tx in sorted_txs:
        frm = (tx.get("from") or "").lower()
        to = (tx.get("to") or "").lower()
        try:
            amt = float(tx.get("amount", 0.0))
        except Exception:
            amt = 0.0

        # Incoming side: mark `to` suspected if source is a suspect, source has suspected_balance,
        # or the receiver is a known initial suspect and this is the first incoming being treated as suspected
        if (frm in initial_suspects) or (suspected_balance.get(frm, 0.0) > 0) or (to in initial_suspects and suspected_balance.get(to, 0.0) == 0.0):
            suspected_balance[to] = suspected_balance.get(to, 0.0) + amt
        else:
            # non-suspected incoming: no change to suspected_balance (keep previous suspected amount if any)
            suspected_balance[to] = suspected_balance.get(to, 0.0)

        # Outgoing processing: compute traceable on outgoing for 'frm' using FIFO conservative rule
        traceable = min(suspected_balance.get(frm, 0.0), amt)
        unclassified = amt - traceable
        # reduce suspected balance on the sender
        suspected_balance[frm] = max(0.0, suspected_balance.get(frm, 0.0) - traceable)

        annotated_tx = dict(tx)
        annotated_tx["traceable_amount"] = traceable
        annotated_tx["unclassified_amount"] = unclassified
        annotated.append(annotated_tx)

        evidence.append({
            "hop": None,
            "from": frm,
            "to": to,
            "amount": amt,
            "asset": tx.get("asset", "ETH"),
            "traceable_amount": traceable,
            "unclassified_amount": unclassified,
            "tx_hash": tx.get("tx_hash"),
            "timestamp": tx.get("timestamp"),
            "block": tx.get("block")
        })

    return evidence, annotated
