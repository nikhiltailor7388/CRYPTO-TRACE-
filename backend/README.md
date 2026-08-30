CryptoTrace - Backend Skeleton

This skeleton provides a minimal FastAPI backend, NetworkX graph builder, FIFO attribution implementation, sample cached transactions, and a unit test.

Quick start (PowerShell, Windows):

1. Create and activate venv
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install requirements
   pip install -r requirements.txt

3. Run the app (from backend folder)
   uvicorn main:app --reload --port 8000

4. Run tests
   pytest -q

Files created:
- main.py (FastAPI app)
- api/routes.py (POST /trace reading cached data)
- services/graph_builder.py (build graph from data/eth_cache.json)
- services/attribution.py (FIFO attribution & annotation)
- services/vasp_matcher.py (simple JSON lookup)
- data/eth_cache.json (sample transactions)
- data/vasp_labels.json (sample VASP record)
- tests/test_attribution.py (unit test for FIFO worked example)

Next recommended steps:
- Expand fetcher + normaliser to call Etherscan when needed (with rate limit + cache fallback)
- Implement evidence assembly and ReportLab PDF stub
- Build React frontend against the /trace schema (mock data already matches shape)
