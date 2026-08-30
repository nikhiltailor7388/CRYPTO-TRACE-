import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    etherscan_api_key: str = os.getenv("ETHERSCAN_API_KEY", "")
    use_etherscan: bool = os.getenv("USE_ETHERSCAN", "false").lower() in {"1", "true", "yes", "on"}
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes", "on"}
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    backoff_seconds: int = int(os.getenv("BACKOFF_SECONDS", "2"))


settings = Settings()
