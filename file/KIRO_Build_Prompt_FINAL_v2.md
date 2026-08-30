# AGENT BUILD BRIEF — CryptoTrace (SIH26183)

You are an autonomous senior full-stack engineer building a complete, demo-ready hackathon
prototype in one continuous session. Build **everything** described in this document without
stopping to ask clarifying questions. If something is ambiguous, choose the option most
consistent with the Non-Negotiable Design Principles in Section 1 — never guess toward a
bigger or more impressive-sounding claim. Follow the Build Order in Section 7 in sequence.
Do not summarise this brief back to me — start building. At the end, run the Definition of
Done checklist in Section 8 yourself and fix anything that fails before you stop.

---

## 0. Project & Problem

**PROJECT:** CryptoTrace — Automated Blockchain Fund-Flow Tracing & VASP Identification.
Prototype for Smart India Hackathon 2026, Problem Statement **SIH26183**, sponsored by the
Ministry of Home Affairs / I4C (Indian Cyber Crime Coordination Centre). Theme: Blockchain &
Cybersecurity.

**PROBLEM:** A cybercrime victim reports a fraudster's crypto wallet address. Investigators
currently trace where funds went manually, one transaction at a time, across multiple
blockchain-explorer tabs — slow and error-prone. Build a system that automates this: given a
wallet address, trace the fund flow, identify which exchange (VASP) the funds likely ended up
at, flag suspicious patterns, and produce an investigator-ready evidence report.

---

## 1. Non-Negotiable Design Principles (apply to every feature you build)

1. Every VASP/exchange attribution must show its confidence level (`HIGH`/`MEDIUM`/`LOW`/
   `UNKNOWN`) and its source (which dataset, and when it was recorded). Never present a match
   as certain fact. If no match exists, show `UNKNOWN` — never guess or infer an entity from
   behaviour alone and present it as a real match.
2. All risk/heuristic flags must show the exact rule that fired and its confidence — they are
   investigative leads, never proof, and never described as "AI fraud detection."
3. The core evidence pipeline (fetching transactions, building the graph, traversal, VASP
   matching, heuristics) must be fully deterministic — no LLM in the core logic. An LLM may
   ONLY be used optionally, at the very end, to turn already-verified structured JSON into
   plain-language narration — it must never invent addresses, hashes, amounts, or entities.
4. Never claim: real-person identification, guaranteed attribution of unknown wallets,
   complete cross-chain tracing, full mixer de-anonymisation, or automatic freezing of funds.
   The system produces evidence for a human investigator's next legal step — it does not act
   autonomously.
5. Use only free/public data sources (public blockchain APIs, public address label datasets).
   Do not assume access to private bank, UPI, NPCI, exchange KYC, or government
   complaint-system data.
6. Keep the architecture as small as it can be while still proving the concept. Do not add
   technology just to look advanced.
7. **The Etherscan integration must use the current V2 API.** Base URL
   `https://api.etherscan.io/v2/api`, and every request MUST include a `chainid` parameter
   (`1` = Ethereum mainnet). The old V1 endpoint
   (`https://api.etherscan.io/api` with no `chainid`) has been fully deprecated since 15
   August 2025 and returns an error — it must never appear anywhere in this codebase.
8. Never invent performance numbers ("90% accuracy," "under 60 seconds," etc.) in code
   comments, UI copy, or the README. Any metric shown must be computed live from real
   measurements, or the field must say "not yet measured."
9. Never fabricate a real complaint ID, victim identity, or claim of government/API access
   the system does not have. The demo wallet must be a real, publicly verifiable address (see
   Section 6).

---

## 2. Scope — Build in This Priority Order

### TIER 1 — Must work end to end first

- Wallet address input with format validation (detect Ethereum vs TRON address format
  automatically, with manual override).
- Fetch public transactions for a given wallet from the **Etherscan V2 API** (Ethereum) and
  the **TronScan API** (TRON/TRC-20, since USDT-TRC20 is the most fraud-relevant asset in
  this context). See Section 4.1 for the exact required request pattern.
- Normalise every chain's response into one common internal schema:
  `{ chain, tx_hash, from_addr, to_addr, asset, amount, timestamp, block, source_url }`. Only
  the chain-specific adapter modules should know about raw Etherscan/TronScan field names —
  everything downstream uses only this normalised schema.
- Build a directed transaction graph (wallets = nodes, transactions = edges) using NetworkX,
  and perform a BOUNDED traversal (configurable, default 2–3 hops) following the largest
  outgoing transfer at each step. Do not traverse indefinitely.
- A small, source-labelled VASP/exchange address dataset (JSON is fine — no heavy database
  needed). Each entry must record: `address, chain, entity, type, source, source_date,
  confidence`. Seed it with 10–30 addresses you can genuinely verify against a public source
  (e.g. a known exchange's publicly tagged deposit address on a block explorer) — do not
  fabricate entries.
- Exact-match VASP lookup: when a traced path reaches an address in this dataset, report it
  with `HIGH` confidence and its source. If not found, report `UNKNOWN` — never guess.
- Deterministic risk heuristics, each returning the rule name, whether it fired, its
  confidence, and a plain-language explanation:
  - rapid forwarding (funds received and forwarded on quickly)
  - consolidation pattern (many inputs into one output)
  - limited prior activity / burner-like wallet
  - known mixer address interaction (see Tier 2 for what to do beyond simply flagging this)
  - known bridge contract interaction (flag as a cross-chain boundary, do not attempt to
    continue the trace onto another chain)
- A FastAPI backend exposing at minimum:
  ```
  POST /trace   { address, chain?, depth? } -> evidence JSON
  POST /report  { evidence JSON }           -> PDF file
  GET  /health                              -> { status: "ok" }
  ```
- A React frontend with: address input form, an interactive graph view (Cytoscape.js)
  showing the traced path, a VASP confidence badge, a risk-flag panel showing each rule and
  its explanation, an evidence panel with clickable public-explorer links for every
  transaction hash, and a "Generate Report" button that downloads a PDF (built with
  ReportLab) containing the case summary, path, VASP match with confidence/source, and all
  risk flags.
- Response caching for a chosen demo wallet so the live demo does not depend on an external
  API being available at presentation time (add a `DEMO_MODE` toggle).

### TIER 2 — The differentiator layer (build after Tier 1 is fully stable)

- **Mixer-aware probabilistic correlation:** when the trace reaches a known mixing-service
  contract address (hard-code one well-documented example, e.g. a specific Tornado Cash pool,
  for the initial version), do NOT stop silently. Instead:
  1. Record the deposit's amount, token, and block number.
  2. Query the same pool/contract for withdrawal events within a configurable time window
     (e.g. a few hours).
  3. Score each candidate withdrawal by **(i)** time proximity, **(ii)** how closely the
     amount matches after accounting for any fee, and **(iii)** pool liquidity depth (thinner
     pools = higher confidence in a match, since fewer participants could coincidentally
     match).
  4. Present the result explicitly as a ranked, confidence-scored "probable continuation" —
     visually distinct (e.g. a dashed graph edge) from a certain, directly-observed transfer.
     Never claim this de-anonymises the mixer; frame it as the same statistical reasoning
     real forensic investigators use, not cryptographic de-anonymisation.
- Apply the same probabilistic time/amount-correlation technique to known DEX/AMM
  liquidity-pool swaps (e.g. a Uniswap V2 pool) if time allows — same three-factor scoring,
  same explicit "probable, not certain" framing. Source swap events from a public subgraph or
  the relevant block explorer's event logs (free, no special access needed).

### TIER 3 — Nice to have, only if Tier 1 and 2 are fully stable

- BNB Smart Chain support (only after ETH+TRON are rock solid) — note that with the V2
  Etherscan API this only requires adding `chainid=56` to existing adapter calls, no new
  integration.
- Optional LLM narration of the finished evidence JSON into a plain-language summary,
  strictly following the safe-LLM contract in Principle 3 above.
- A basic OCR step (e.g. Tesseract) that extracts a candidate wallet address from an uploaded
  complaint screenshot or pasted text, with checksum validation before feeding it into the
  trace pipeline.

### DO NOT BUILD (explicitly out of scope)

- Full arbitrary cross-chain bridge tracing.
- Complete mixer de-anonymisation (only probabilistic correlation as above).
- Real-world identity attribution of any kind.
- Any integration with private government/bank/exchange systems.
- Support for more than 2–3 blockchains.
- A commercial-scale entity-label database.
- Any "network-level"/multi-wallet syndicate-clustering feature — out of scope for this
  build; do not add it even if it seems like a natural extension.

---

## 3. Tech Stack

- **Frontend:** React (Vite), Cytoscape.js (via `react-cytoscapejs`), axios.
- **Backend:** Python 3.10+, FastAPI, NetworkX, Pydantic (+ `pydantic-settings`), ReportLab,
  requests.
- **Data:** Etherscan V2 API, TronScan API, JSON for the VASP label store.
- **Security:** `python-dotenv`/`pydantic-settings` for API keys (never hard-coded);
  `.gitignore` for `.env`, `venv/`, `node_modules/`, `cache/*.json` (except committed demo
  fixtures); strict address-format input validation on both frontend and backend; CORS
  restricted to the actual frontend origin (never a wildcard); try/except with retry/backoff
  around every external API call (Section 4.2), with graceful, non-crashing error responses.
- **Testing:** pytest for the backend (Section 4.6).
- **Deployment:** Docker + docker-compose for a reproducible local/demo environment
  (Section 4.7).

---

## 4. Backend Build Details

### 4.1 Etherscan adapter — mandatory V2 pattern

```python
# adapters/etherscan_adapter.py
import requests
from config import settings
from models.transaction import NormalisedTransaction

BASE_URL = "https://api.etherscan.io/v2/api"

def fetch_eth_transactions(address: str, chainid: int = 1):
    params = {
        "chainid": chainid, "module": "account", "action": "txlist",
        "address": address, "sort": "asc", "apikey": settings.etherscan_api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=settings.request_timeout)
    data = resp.json()
    if data.get("status") == "0" and "rate limit" in str(data.get("result", "")).lower():
        raise RuntimeError("RATE_LIMIT")
    raw = data.get("result", [])
    if not isinstance(raw, list):
        return []
    return [NormalisedTransaction(
        chain="ETH", tx_hash=tx["hash"], from_addr=tx["from"], to_addr=tx["to"],
        asset="ETH", amount=int(tx["value"]) / 1e18, timestamp=tx["timeStamp"],
        block=int(tx["blockNumber"]), source_url=f"https://etherscan.io/tx/{tx['hash']}",
    ) for tx in raw]
```

Implement `adapters/tronscan_adapter.py` analogously against
`https://apilist.tronscanapi.com/api/transaction`, normalising `block_ts` (milliseconds) to
ISO 8601 UTC and mapping `tokenInfo.tokenAbbr` to `asset`.

### 4.2 Resilient retry wrapper (required — the live demo depends on this)

```python
# adapters/resilient.py
import time, logging

logger = logging.getLogger("cryptotrace")

def call_with_retry(fn, *args, max_attempts=3, backoff_seconds=2, **kwargs):
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except RuntimeError as e:
            if str(e) == "RATE_LIMIT" and attempt < max_attempts:
                wait = backoff_seconds * attempt
                logger.warning(f"Rate limited, retry {attempt} in {wait}s")
                time.sleep(wait)
                continue
            raise
```

`main.py`'s `/trace` handler must call adapters through this wrapper, and on final failure
(after retries are exhausted, or on any other adapter exception) must fall back to the cached
`DEMO_MODE` fixture (Section 6) rather than returning a 500 with no recovery path.

### 4.3 Mixer/DEX correlation modules (Tier 2)

```python
# graph/mixer_correlation.py
def score_mixer_candidate(deposit, candidate_withdrawal, pool_liquidity_depth):
    """
    Returns {confidence_pct, breakdown} for one candidate withdrawal, given a
    recorded mixer deposit. Never call this a de-anonymisation — always a
    probabilistic, ranked lead.
    """
    breakdown = {}

    # (i) Time proximity — closer withdrawal after deposit scores higher
    delay_minutes = (candidate_withdrawal.timestamp - deposit.timestamp).total_seconds() / 60
    breakdown["time_proximity"] = (
        40 if delay_minutes <= 30 else 25 if delay_minutes <= 120 else 10 if delay_minutes <= 360 else 0
    )

    # (ii) Amount match, accounting for a mixer/relayer fee tolerance
    expected = deposit.amount * 0.99
    diff_pct = abs(candidate_withdrawal.amount - expected) / expected
    breakdown["amount_match"] = 35 if diff_pct < 0.02 else 20 if diff_pct < 0.05 else 0

    # (iii) Pool depth — thinner pools narrow the candidate set, raising confidence
    breakdown["pool_depth_factor"] = 25 if pool_liquidity_depth < 50 else 15 if pool_liquidity_depth < 200 else 5

    return {"confidence_pct": min(sum(breakdown.values()), 100), "breakdown": breakdown}
```

Implement `graph/dex_correlation.py` with the same three-factor structure (time proximity,
amount match, pool-depth-equivalent liquidity factor) applied to AMM swap events instead of
mixer withdrawal events. Both modules must return a `breakdown` dict so the UI/report can
show *why* a score was given, never a bare number.

In the graph/UI, render every mixer/DEX-correlation edge as visually distinct (e.g. dashed,
labelled "probable, N% confidence") from a directly-observed, certain transaction edge.

### 4.4 VASP matcher

```python
# vasp/vasp_matcher.py
import json

def load_vasp_labels(path="vasp/vasp_labels.json"):
    with open(path) as f:
        return json.load(f)

def match_vasp(address, labels):
    for entry in labels:
        if entry["address"].lower() == address.lower():
            return entry
    return None  # caller renders this as UNKNOWN — never guess
```

### 4.5 Structured logging

Configure Python `logging` at INFO level in `main.py`; log every `/trace` request (address,
chain, elapsed time), every retry/fallback event, and every error with enough context to
debug live during judging.

### 4.6 Tests (required — do not skip)

Write real pytest tests, not placeholders, covering at minimum:
- `graph/trace_engine.py`: graph construction from transactions; bounded traversal stops at
  `max_hops`; traversal follows the largest-amount edge at each step.
- `vasp/vasp_matcher.py`: exact match (case-insensitive) returns the right entry; no match
  returns `None`.
- `graph/mixer_correlation.py`: confidence score decreases as time delay increases; score
  drops when amount mismatch grows beyond tolerance.
- `adapters/resilient.py`: retries on `RuntimeError("RATE_LIMIT")` up to `max_attempts`, then
  re-raises.

Run `pytest tests/ -v` and it must pass with zero failures before you consider the backend
done.

### 4.7 Docker

Add a `backend/Dockerfile` (`python:3.11-slim`, install `requirements.txt`, run with
`uvicorn main:app --host 0.0.0.0 --port 8000`), a `frontend/Dockerfile` (Node build stage →
nginx serve stage), and a root `docker-compose.yml` wiring both together with the backend's
`.env` mounted. `docker compose up --build` must produce a fully working system from a clean
checkout.

---

## 5. Folder Structure — create exactly this layout

```
cryptotrace-i4c/
  backend/
    main.py
    config.py
    .env.example
    requirements.txt
    adapters/    (etherscan_adapter.py, tronscan_adapter.py, resilient.py)
    models/      (transaction.py)
    graph/       (trace_engine.py, mixer_correlation.py, dex_correlation.py)
    vasp/        (vasp_labels.json, vasp_matcher.py)
    risk/        (heuristics.py)
    reports/     (report_generator.py)
    cache/       (demo_case.json, demo_case_backup.json)
    tests/       (test_trace_engine.py, test_vasp_matcher.py,
                  test_mixer_correlation.py, test_resilient.py)
    Dockerfile
  frontend/
    src/
      components/ (WalletInput.jsx, GraphView.jsx, EvidencePanel.jsx,
                    RiskPanel.jsx, VaspBadge.jsx, ReportButton.jsx,
                    ErrorBanner.jsx, LoadingState.jsx)
      App.jsx, api.js
    Dockerfile
  docker-compose.yml
  docs/
    README.md
    JUDGE_QA_QUICKREF.md
    DEMO_SCRIPT.md
  .gitignore
```

---

## 6. Demo Data You Must Prepare

1. Choose one **publicly documented, independently verifiable** Ethereum or TRON address
   (e.g. from a public scam-address tracker or a published on-chain investigation write-up —
   never a fabricated address, never a real private complaint's address).
2. Call the real API for it, save the raw + normalised response as
   `backend/cache/demo_case.json`. This is what `DEMO_MODE` / the retry-fallback path
   (Section 4.2) serves when the live API is unavailable.
3. Manually verify at least 1–2 real hops from that address on the public explorer, and
   record whether any destination matches a `vasp_labels.json` entry, with a real source and
   date.
4. Prepare a second, independent **backup case** the same way, saved as
   `backend/cache/demo_case_backup.json`.
5. Write `docs/DEMO_SCRIPT.md` with this flow (adapt only the literal address/screenshots):
   - "This is the wallet reported by the victim" → paste the demo wallet, click **Trace**.
   - Show chain detection + retrieval (live, or graceful fallback to cache).
   - Graph appears; highlight the reported wallet and traced path.
   - Click a node → show amount, time, tx hash, explorer link.
   - Show the VASP badge: entity, confidence tier, source, date — or `UNKNOWN` if genuinely
     unmatched.
   - Show the risk panel: each fired rule with its explanation.
   - If the path crosses the hard-coded mixer example: show the dashed "probable
     continuation" edge and its confidence breakdown, explicitly stating out loud that this
     is probabilistic correlation, not de-anonymisation.
   - Click **Generate Report** → open the PDF.
   - Close with a one-line summary of what was just proven end to end.

---

## 7. Build Order (execute in this sequence; do not skip ahead)

1. Scaffold the full repository from Section 5, including `.gitignore` and `.env.example`.
2. Backend — `config.py`, `models/transaction.py`, both adapters using the **V2 Etherscan
   pattern** (Section 4.1), `adapters/resilient.py` (Section 4.2). Manually verify `/trace`
   returns real, normalised transactions end to end for a live address.
3. Backend — `graph/trace_engine.py` (bounded traversal), `vasp/vasp_matcher.py` + seeded
   `vasp_labels.json`, `risk/heuristics.py`. Verify `/trace` now returns path + VASP match +
   risk flags together.
4. Backend — `reports/report_generator.py`, `/report` endpoint, structured logging, `/health`.
5. Backend — Tier 2: `graph/mixer_correlation.py` with the hard-coded example pool, wired
   into the trace flow so a mixer hit produces ranked candidates instead of a dead end. Then
   `graph/dex_correlation.py` if time allows.
6. Backend — write and pass all tests in `backend/tests/` (Section 4.6).
7. Frontend — scaffold, `WalletInput`, `GraphView` (including dashed "probable" edges for
   Tier 2 results), wired to `/trace`, with `LoadingState`/`ErrorBanner`.
8. Frontend — `EvidencePanel`, `VaspBadge`, `RiskPanel`, `ReportButton`.
9. Prepare demo data (Section 6) and confirm the full demo flow works end to end, live, at
   least three times in a row without manual intervention; confirm the retry/cache fallback
   works by simulating a failed API call.
10. Docker — build both Dockerfiles + `docker-compose.yml`; confirm `docker compose up
    --build` produces a working system from a clean checkout.
11. Documentation — write `docs/README.md` and `docs/JUDGE_QA_QUICKREF.md` (Section 9).
12. Run the Definition of Done checklist (Section 8) and fix anything failing.
13. Only if Tiers 1–2 are fully stable and time remains: attempt Tier 3 items in the order
    listed in Section 2.

---

## 8. Definition of Done — verify every line before stopping

- [ ] No occurrence of the deprecated Etherscan V1 endpoint anywhere in the repo; every
      Etherscan call includes `chainid`.
- [ ] `pytest backend/tests/ -v` passes with zero failures.
- [ ] `/trace` on the prepared demo address returns a real path, a VASP match (or honest
      `UNKNOWN`), and risk flags with rule + confidence — verified by actually running it.
- [ ] If the live API is disconnected or rate-limited, `/trace` falls back to the cached demo
      case instead of crashing (test this by temporarily breaking the API key).
- [ ] A mixer hit on the demo path (or a manually-triggered test case) produces a ranked,
      confidence-scored candidate list rendered as visually distinct (dashed) edges — never
      presented as a certain match.
- [ ] PDF report opens correctly and includes source/date/confidence for the VASP match and
      every risk flag.
- [ ] `docker compose up --build` runs the full stack from a clean clone.
- [ ] No hard-coded accuracy/speed claims anywhere in code, UI copy, or docs.
- [ ] No real complaint ID, real victim data, or claim of government/bank/telecom access
      appears anywhere.
- [ ] `docs/README.md` and `docs/JUDGE_QA_QUICKREF.md` exist and are complete (Section 9).
- [ ] Nothing from the "DO NOT BUILD" list in Section 2 has been added.

---

## 9. Documentation to Generate

**`docs/README.md`** must include: a one-paragraph project summary; setup instructions (venv,
`.env` from `.env.example`, `npm install`, how to run backend + frontend, how to run via
Docker); the Definition of Done checklist copied in as a status section with boxes checked as
you complete them; and a boundary statement, stated plainly: *"CryptoTrace generates
investigative intelligence from public blockchain data. It does not identify real-world
identities, automatically freeze funds, prosecute anyone, guarantee attribution of unknown
wallets, or de-anonymise mixers — mixer/DEX correlation is explicitly probabilistic and
labelled as such everywhere it appears."*

**`docs/JUDGE_QA_QUICKREF.md`** must include, verbatim, these Q&As (add more if useful, never
soften these):

- **Q: Isn't this just Etherscan/TronScan?** A: No. Those are data/explorer layers. Our value
  is the automated investigation workflow: retrieve → bounded trace → VASP match → explain
  evidence/confidence → report.
- **Q: Doesn't Chainalysis already do this?** A: Professional platforms already provide
  powerful analytics. We do not claim to replace them. Our focus is a transparent, narrow
  workflow for the stated Indian cybercrime use case.
- **Q: How do you know a wallet belongs to an exchange?** A: Only when source-backed
  address/entity evidence supports it. Exact labelled matches are `HIGH` confidence;
  behavioural heuristics are shown separately as leads, never as proof.
- **Q: Can you identify the fraudster?** A: Not from public blockchain data alone. The system
  attributes supported entities and produces evidence for the authorised VASP/legal process to
  obtain KYC when applicable.
- **Q: Do you de-anonymise mixers?** A: No. When a trace hits a known mixer, we score
  candidate withdrawals by time proximity, amount match, and pool depth, and present them as
  ranked, confidence-scored probable continuations — the same statistical reasoning real
  forensic investigators use, never a cryptographic or certain de-anonymisation.
- **Q: What happens if the VASP is unknown?** A: We show `UNKNOWN` explicitly and expose the
  path and risk flags we do have — we never fabricate an attribution.

---

Build the entire system now, in the order given in Section 7, and do not stop until every box
in Section 8 is checked.
