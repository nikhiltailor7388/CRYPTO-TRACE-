# CryptoTrace I4C — Shared Project Context for AI Coding Agents

**Project:** CryptoTrace I4C  
**SIH Problem Statement:** SIH26183  
**Purpose:** Give every team member's AI coding agent the same project
context, while each agent implements only its assigned module.

## 1. Project Overview

CryptoTrace I4C is an investigator-focused blockchain fund-flow tracing
prototype.

It starts **after an investigator has a suspect cryptocurrency wallet
address** obtained through an appropriate complaint/investigation
process.

Core workflow:

``` text
Victim complaint / investigation
→ Suspect crypto wallet obtained
→ React frontend
→ Python + FastAPI
→ Etherscan / TronScan
→ Raw transaction data
→ Normalization
→ NetworkX graph
→ Controlled 2–3 hop tracing
→ VASP / exchange address matching
→ Confidence + source + deterministic risk indicators
→ Evidence
→ ReportLab PDF
→ Investigator's legal/compliance next step
```

### Problem

Investigators may need to manually inspect explorers, follow
wallet-to-wallet transfers, check destination addresses, verify
exchange/VASP labels and document evidence.

### Focused innovation

Do not claim blockchain tracing itself is new.

> **Reported wallet → automated bounded fund-flow trace → supported VASP
> attribution → source/confidence explanation → evidence → structured
> report.**

Existing explorers and commercial analytics already solve parts of this
problem. Our contribution is a narrow, transparent investigator
workflow.

## 2. Important Boundaries

CryptoTrace does **not** access:

- Paytm internal systems
- Private bank records
- UPI/NPCI private routing or dispute data
- Private exchange KYC
- NCRP/I4C government databases
- Government-only APIs

It does not automatically freeze funds, identify a real person,
prosecute anyone, or prove ownership of an unknown wallet.

A VASP match identifies a **service endpoint**, not the customer's
identity. Obtaining customer identity is an off-chain legal/compliance
process.

## 3. Real-World Starting Point

``` text
Victim notices fraud
→ reports through the appropriate channel
→ relevant transaction/reference details are investigated
→ if cryptocurrency is involved and a suspect wallet is obtained
→ CryptoTrace starts
```

Do not claim that every Paytm/UPI fraud automatically freezes money
within 24 hours. Outcomes depend on transaction type, institutions and
applicable procedures.

## 4. Prototype Scope

### Primary MVP

- Ethereum
- TRON / TRC-20
- 2–3 hop tracing
- Small source-labelled VASP dataset
- Interactive graph
- Evidence panel
- PDF report
- Cached demo case

### Only after the core works

- BNB Smart Chain
- Additional heuristics or batch improvements

### Do not build for the 3-day MVP

- Arbitrary full cross-chain tracing
- Mixer de-anonymization
- Real-person identity attribution
- Real NCRP/I4C integration
- Private bank/UPI integration
- Commercial-scale entity intelligence
- 20+ chain support
- Permanent live monitoring infrastructure

## 5. Technology Stack

| Layer       | Technology            | Role                               |
|-------------|-----------------------|------------------------------------|
| Frontend    | React.js              | Investigator dashboard             |
| Graph UI    | Cytoscape.js          | Interactive graph                  |
| Backend     | Python + FastAPI      | API and orchestration              |
| Data models | Pydantic              | Shared schemas                     |
| Blockchain  | Etherscan API         | Ethereum data                      |
| Blockchain  | TronScan API          | TRON/TRC-20 data                   |
| Graph       | NetworkX              | Nodes, edges, BFS/DFS              |
| VASP store  | JSON                  | MVP address labels                 |
| Optional DB | SQLite                | Local structured storage if needed |
| PDF         | ReportLab             | Evidence report                    |
| Styling     | Simple CSS / Tailwind | Fast UI development                |
| Optional AI | Any suitable LLM      | Verified-data narration only       |

Keep the stack simple. Do not add frameworks just to make the
architecture look advanced.

## 6. Common Transaction Schema

All blockchain adapters must normalize their provider-specific responses
into:

``` python
class NormalisedTransaction(BaseModel):
    chain: str
    tx_hash: str
    from_addr: str
    to_addr: str
    asset: str
    amount: float
    timestamp: str
    block: int
    source_url: str
```

Only the blockchain adapters should know Etherscan/TronScan-specific
field names.

All downstream modules use the normalized schema.

## 7. Common Evidence Object

All modules should work toward one shared evidence structure:

``` json
{
  "case": {
    "case_id": "optional",
    "start_address": "...",
    "chain": "ETH"
  },
  "transactions": [],
  "graph": {
    "nodes": [],
    "edges": []
  },
  "trace": {
    "path": [],
    "hop_count": 0
  },
  "vasp_matches": [],
  "heuristic_flags": [],
  "sources": [],
  "limitations": []
}
```

Do not change this contract independently. Discuss integration changes
with the team.

## 8. Multi-Hop Tracing

Example:

``` text
Wallet A → Wallet B → Wallet C → VASP
   Hop 1      Hop 2      Hop 3
```

- Wallet = graph node
- Transaction = directed edge
- BFS/DFS = bounded traversal
- Maximum depth = 2–3 for MVP
- Stop at maximum depth
- Stop/flag known mixer boundaries
- Stop/flag bridge boundaries
- Stop when a supported VASP endpoint is reached
- Stop at dead ends

If a wallet has many outgoing transactions, keep the graph manageable
using the team's agreed top-N filtering rule and record that filtering
in evidence.

## 9. Fund-Flow Clarity

A wallet can contain legitimate funds and potentially fraud-related
funds.

Do **not** treat its entire balance as fraud money.

CryptoTrace follows the **specific observed transaction/path** and
records:

- transaction hash
- amount
- timestamp
- from
- to
- asset
- explorer source

The output is an investigative lead/path, not proof that the entire
wallet balance is fraud money or that the wallet owner is guilty.

## 10. VASP Identification

Primary method:

``` text
Discovered address
→ exact lookup in source-labelled VASP dataset
→ entity + source + date + confidence
```

Confidence:

- **HIGH:** exact match to trustworthy/current labelled address
- **MEDIUM:** reliable public explorer/community label
- **LOW:** behavioral heuristic only
- **UNKNOWN:** insufficient evidence

Never silently guess.

Preferred wording:

> “The destination address matched our source-labelled VASP database.”

Not:

> “AI identified Binance.”

## 11. VASP Record

``` json
{
  "address": "...",
  "chain": "ETH",
  "entity": "Example Exchange",
  "type": "exchange",
  "source": "public label",
  "source_url": "...",
  "source_date": "YYYY-MM-DD",
  "confidence": "HIGH"
}
```

Every real record used in the demo must be independently verified.

## 12. Heuristics

Heuristics are deterministic investigative signals, not AI fraud
detection.

Possible MVP rules:

- rapid forwarding
- consolidation
- limited prior activity
- known mixer interaction
- bridge interaction
- source-linked risk

Every flag must show the rule and its limitation.

## 13. AI Position

The core system is deterministic.

AI is **not required** for:

- transaction retrieval
- graph construction
- BFS/DFS
- exact VASP matching
- confidence calculation
- heuristic evaluation
- evidence generation
- PDF generation

Optional AI can receive verified evidence JSON and produce a
plain-English summary.

It must never invent:

- wallet addresses
- transaction hashes
- amounts
- entities
- identities
- evidence

## 14. API Integration

Minimum endpoints:

``` http
POST /trace
GET /health
POST /report
```

Example `/trace` input:

``` json
{
  "address": "0x...",
  "chain": "ETH",
  "depth": 2,
  "case_id": "optional"
}
```

`/trace` returns the common evidence JSON.

`/report` receives verified evidence JSON and returns a PDF.

Frontend should consume backend evidence JSON rather than raw blockchain
API responses.

## 15. Judge Demo Flow

``` text
Wallet input
→ Trace
→ public blockchain data
→ normalization
→ graph
→ 1–2+ verified hops
→ VASP match or UNKNOWN
→ source + confidence
→ transaction evidence
→ PDF report
```

Use real public data for the main demo whenever possible.

If synthetic content is used, visibly label it:

> SYNTHETIC DEMO DATA

Never fabricate a real complaint ID, victim identity, government record,
transaction hash or wallet address.

## 16. Real / Synthetic / Unavailable

### LIVE / REAL

- Public blockchain retrieval
- Normalization
- Supported multi-hop tracing
- VASP lookup
- Explorer evidence
- Report generation

### SYNTHETIC

Only controlled UI/testing data where real ground truth is unavailable.

### UNAVAILABLE

- Bank records
- Paytm internal data
- UPI/NPCI private data
- Exchange KYC
- NCRP/I4C private data
- Government-only APIs
- Real-person identity

## 17. Team Roles

### Member 1 — Backend / Blockchain API

Build:

- FastAPI
- address validation
- chain selection/detection
- Etherscan adapter
- TronScan adapter/stub
- error handling
- normalized transaction output

**Input:** wallet + chain  
**Output:** `NormalisedTransaction[]`

### Member 2 — Graph / Analytics

Build:

- NetworkX graph
- BFS/DFS bounded traversal
- path logic
- hop counting
- graph nodes/edges
- deterministic heuristics if assigned

**Input:** `NormalisedTransaction[]`  
**Output:** graph + traced path + flags

### Member 3 — VASP / Data

Build:

- source-labelled VASP dataset
- source verification log
- exact address matching
- confidence metadata
- demo case verification

**Input:** destination addresses  
**Output:** VASP match + source + date + confidence

### Member 4 — Frontend

Build:

- React dashboard
- wallet input
- chain/depth controls
- loading/error states
- Cytoscape graph
- path highlighting
- VASP/confidence panel
- evidence panel
- report button

**Input:** evidence JSON  
**Output:** investigator UI

### Member 5 — Report / Integration

Build:

- evidence-object integration
- ReportLab PDF
- `/report`
- cache/fallback
- end-to-end integration

**Input:** verified evidence JSON  
**Output:** PDF + integrated flow

### Member 6 — Demo / Documentation / Validation

Own:

- demo case documentation
- tests
- screenshots
- backup fixture
- measured timings
- README
- demo flow
- judge Q&A coordination

This member should understand the complete system.

## 18. Three-Day Build

### Day 0

- repository
- Python/Node environment
- API access
- verified public demo case
- VASP seed data
- common schema
- project folders

### Day 1

``` text
Wallet → API → normalized transactions → graph
```

### Day 2

``` text
Graph → 2–3 hop traversal → VASP matching → frontend integration
```

### Day 3

``` text
Evidence → PDF → cache/fallback → testing → final demo
```

Freeze new features before rehearsal.

## 19. Shared Coding-Agent Rule

Every member should first give their AI agent this project context.

Then add their own role:

``` text
MY ASSIGNED ROLE:
[Member role]

MY TASK:
[Specific task]

Understand the complete project context, but implement ONLY my assigned role.

Do not:
- redesign the architecture
- implement another member's feature
- add unnecessary frameworks
- invent blockchain/VASP data
- change the shared schema without discussion
- add AI where deterministic logic is required

Before coding:
1. Identify files to create/change.
2. Explain how this module connects to the next module.
3. Follow the shared schema/API contract.
4. Keep the implementation simple and debuggable.

After coding:
1. Explain what was implemented.
2. List files changed.
3. Explain inputs and outputs.
4. Give exact run/test commands.
5. State integration dependencies.
```

## 20. Final Definition of Done

The team can reliably demonstrate:

``` text
Public wallet
→ blockchain data
→ normalized transactions
→ graph
→ bounded multi-hop trace
→ VASP match OR UNKNOWN
→ source + confidence
→ transaction evidence
→ PDF report
```

Every member should understand:

- where CryptoTrace starts
- where data comes from
- what each module does
- what each module consumes/produces
- how modules connect
- why VASP attribution is source-backed
- why UNKNOWN is valid
- why an entire wallet balance is not automatically treated as fraud
- what is real, synthetic and unavailable
- what belongs in the 3-day MVP
- what is future scope

**Core principle:** Build a small system that actually works, can be
verified, and can be explained by every team member.
