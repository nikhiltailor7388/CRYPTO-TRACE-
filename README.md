# CryptoTrace 

Automated blockchain fund-flow tracing and VASP identification for cybercrime investigators. Given a victim-reported crypto wallet address, CryptoTrace automatically retrieves public blockchain transactions, traces the fund flow across a bounded number of hops, matches destination addresses against a curated VASP/exchange label dataset with explicit confidence levels, flags explainable risk patterns, and generates a structured investigation report — replacing hours of manual explorer-hopping with a single input.

Built for Smart India Hackathon 2026 — Problem Statement SIH26183, Ministry of Home Affairs / I4C, Theme: Blockchain & Cybersecurity.

> This is a hackathon prototype, not an official government tool. It does not identify real-world identities, freeze funds, or replace legal process — it generates investigative leads from public blockchain data only.

## Project structure
- backend/: FastAPI service with transaction retrieval, graph analysis, VASP matching, risk heuristics, PDF report generation, and test coverage
- frontend/: React + Vite interface for wallet tracing and investigation review
- docs/: project notes and quick-reference material
- file/: supporting hackathon artifacts and build materials

## Quick local run (Windows PowerShell)

1) Backend
  cd D:\OneDrive\Documents\CRYPTO-TRACE\backend
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8000

2) Frontend
  cd D:\OneDrive\Documents\CRYPTO-TRACE\frontend
  npm install
  npm run dev -- --host 127.0.0.1 --port 5173

3) Investigate
- Open http://127.0.0.1:5173
- Enter a case ID and any valid Ethereum wallet address
- Use live Etherscan retrieval by setting the backend environment variables
- If live access is unavailable, the backend falls back to the cache instead of crashing

## Configuration notes
- Real live fetch requires `ETHERSCAN_API_KEY` and `USE_ETHERSCAN=true` in `backend/.env`
- The project is designed to work safely in local/demo mode when no live API key is configured

## Current scope
- Persistent case storage and authentication are included in the local-first workflow
- Multi-chain-aware tracing and richer graph analytics are supported as part of the investigation engine
- Risk scoring and report exports are included for investigation workflow usage

## Limitations
- This remains an investigative prototype and is not a production-grade money-laundering enforcement system or a private-bank/KYC integration

## Next recommended work
- Add stronger multi-user case management and analytic workflows
- Expand multi-chain adapters and richer entity intelligence
- Add warehouse-grade VASP and mixer correlation workflows

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
