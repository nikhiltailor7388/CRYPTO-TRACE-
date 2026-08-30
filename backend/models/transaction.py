from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizedTransaction:
    chain: str
    tx_hash: str
    from_addr: str
    to_addr: str
    asset: str
    amount: float
    timestamp: Optional[str]
    block: Optional[int]
    source_url: Optional[str] = None
