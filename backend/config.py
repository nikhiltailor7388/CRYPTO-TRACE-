import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    etherscan_api_key: str = os.getenv("ETHERSCAN_API_KEY", "")
    tronscan_api_key: str = os.getenv("TRONSCAN_API_KEY", "")
    use_etherscan: bool = os.getenv("USE_ETHERSCAN", "true").lower() in {"1", "true", "yes", "on"}
    # Live retrieval is the default when it has been configured. Demo data is
    # opt-in so a missing provider configuration cannot silently look live.
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes", "on"}
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    backoff_seconds: int = int(os.getenv("BACKOFF_SECONDS", "2"))
    max_trace_wallets: int = int(os.getenv("MAX_TRACE_WALLETS", "25"))
    max_trace_transactions: int = int(os.getenv("MAX_TRACE_TRANSACTIONS", "500"))
    trace_timeout_seconds: int = int(os.getenv("TRACE_TIMEOUT_SECONDS", "45"))
    max_historical_price_lookups: int = int(os.getenv("MAX_HISTORICAL_PRICE_LOOKUPS", "10"))
    tronscan_page_size: int = int(os.getenv("TRONSCAN_PAGE_SIZE", "100"))


settings = Settings()
