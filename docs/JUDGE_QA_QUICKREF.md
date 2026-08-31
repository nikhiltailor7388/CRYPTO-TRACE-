# CryptoTrace Quick Reference

## Main endpoints
- GET /health
- POST /trace
- GET /reports/{case_id}.pdf
- GET /reports/{case_id}.csv

## Live API configuration
- Set `ETHERSCAN_API_KEY` in `backend/.env`.
- Keep `USE_ETHERSCAN=true` for live fetches.
- If the API is unavailable, the backend falls back to the cached demo fixture automatically.

## Demo validation
1. Start backend and frontend.
2. Enter `CASE-001` and the sample wallet.
3. Click Trace wallet.
4. Verify the risk panel, suspicious path, graph, and evidence table render.
5. Download the PDF report.

## What the demo proves

- The same normalized transaction data drives the bounded path, graph,
  evidence, risk result, VASP lookup, and report output.
- ETH values are shown in ETH and TRON values in TRX.
- VASP `UNKNOWN` is an honest result when no source-backed label matches.
- Report links use the existing PDF/CSV endpoints; there is no duplicate
  report system.

## Known constraints
- This is a public-data forensic prototype.
- VASP matching is deterministic and exact-match based.
- Risk scores are investigative leads, not proof of criminality.
- Arbitrary cross-chain bridge tracing is outside the current backend scope.
