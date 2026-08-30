# CryptoTrace Quick Reference

## Main endpoints
- GET /health
- POST /trace
- GET /reports/{case_id}.pdf

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

## Known constraints
- This is a public-data forensic prototype.
- VASP matching is deterministic and exact-match based.
- Risk scores are investigative leads, not proof of criminality.
