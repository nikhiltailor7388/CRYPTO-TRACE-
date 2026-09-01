from typing import List, Dict, Any


def normalize_etherscan_raw(raw_txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Etherscan 'txlist' / 'tokentx' raw responses into internal unified schema.

    Internal schema expected fields: tx_hash, from, to, amount (float), asset (symbol or ETH), timestamp (ISO8601), block, chain, source_url
    For demo cache we assume the input is already normalized; this function is resilient to common Etherscan formats.
    """
    out = []
    for r in raw_txs:
        # Etherscan normal tx fields: hash, from, to, value, timeStamp, blockNumber
        tx_hash = r.get('hash') or r.get('tx_hash')
        frm = r.get('from')
        to = r.get('to')
        # value may be string in wei for ETH; if 'value' looks like integer string, convert to ETH
        val = r.get('value')
        try:
            amt = float(val) / 1e18 if val is not None and isinstance(val, (str, int)) else float(r.get('amount', 0))
        except Exception:
            # fallback, assume amount is already float
            amt = float(r.get('amount', 0) or 0)
        ts = r.get('timeStamp') or r.get('timestamp')
        # Convert unix timestamp string to ISO8601 if needed
        if ts and isinstance(ts, (int, float)):
            from datetime import datetime
            ts = datetime.utcfromtimestamp(int(ts)).isoformat() + 'Z'
        elif ts and ts.isdigit():
            from datetime import datetime
            ts = datetime.utcfromtimestamp(int(ts)).isoformat() + 'Z'
        source_chain = r.get('source_chain') or r.get('chain') or 'ETH'
        destination_chain = r.get('destination_chain') or source_chain
        out.append({
            'tx_hash': tx_hash,
            'from': frm,
            'to': to,
            'amount': amt,
            'asset': r.get('tokenSymbol') or r.get('asset') or 'ETH',
            'timestamp': ts,
            'block': int(r.get('blockNumber')) if r.get('blockNumber') else None,
            'chain': source_chain,
            'source_chain': source_chain,
            'destination_chain': destination_chain,
            'cross_chain_boundary': str(source_chain).upper() != str(destination_chain).upper(),
            'source_url': r.get('source_url') or (f"https://etherscan.io/tx/{tx_hash}" if tx_hash else None)
        })
    return out
