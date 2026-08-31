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
        out.append({
            'tx_hash': tx_hash,
            'from': frm,
            'to': to,
            'amount': amt,
            'asset': r.get('tokenSymbol') or 'ETH',
            'timestamp': ts,
            'block': int(r.get('blockNumber')) if r.get('blockNumber') else None,
            'chain': 'ETH',
            'source_url': f"https://etherscan.io/tx/{tx_hash}" if tx_hash else None
        })
    return out


def normalize_tron_raw(raw_txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert TronScan raw responses into the same internal schema used by tracing."""
    out = []
    for r in raw_txs:
        tx_hash = r.get('hash') or r.get('tx_hash')
        frm = r.get('ownerAddress') or r.get('from')
        raw_to = r.get('toAddress') or r.get('to')
        if isinstance(r.get('toAddressList'), list) and r.get('toAddressList'):
            first_to = r['toAddressList'][0]
            if isinstance(first_to, dict):
                raw_to = first_to.get('address') or raw_to
        to = raw_to
        val = r.get('amount')
        try:
            if val is not None and isinstance(val, (str, int, float)):
                # Cached fixtures already use the internal unit; TronScan raw
                # records use integer base units alongside ownerAddress.
                amt = float(val) if 'from' in r or 'tx_hash' in r else float(val) / 1_000_000
            else:
                amt = float(r.get('amount', 0) or 0) / 1_000_000
        except Exception:
            amt = 0.0
        ts = r.get('timestamp') or r.get('timeStamp')
        if ts and isinstance(ts, (int, float)):
            from datetime import datetime
            ts_value = int(ts)
            if ts_value > 1_000_000_000_000:
                ts_value = ts_value // 1000
            ts = datetime.utcfromtimestamp(ts_value).isoformat() + 'Z'
        elif ts and str(ts).isdigit():
            from datetime import datetime
            ts_value = int(str(ts))
            if ts_value > 1_000_000_000_000:
                ts_value = ts_value // 1000
            ts = datetime.utcfromtimestamp(ts_value).isoformat() + 'Z'
        asset = (r.get('tokenInfo') or {}).get('symbol') or r.get('tokenSymbol') or 'TRX'
        out.append({
            'tx_hash': tx_hash,
            'from': frm,
            'to': to,
            'amount': amt,
            'asset': asset,
            'timestamp': ts,
            'block': int(r.get('block')) if r.get('block') is not None else None,
            'chain': 'TRON',
            'source_url': f"https://tronscan.org/#/transaction/{tx_hash}" if tx_hash else None
        })
    return out
