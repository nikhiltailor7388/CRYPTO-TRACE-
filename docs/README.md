# CryptoTrace

CryptoTrace is a blockchain investigation platform for tracing wallet movement, identifying likely downstream VASP exposure, and producing investigation-ready evidence.

## Run locally

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173

## Environment

Set required values in `backend/.env`:

```env
ETHERSCAN_API_KEY=your_key_here
USE_ETHERSCAN=true
DEMO_MODE=false
```

## Investigation flow

- Enter a case ID and a valid wallet address.
- Submit to `/trace`.
- Review the traced path, VASP label, and risk layer output.
- Download the generated PDF report.

## Demo and validation

Follow [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) for the reproducible ETH, TRON,
multi-wallet, and report walkthrough using the existing real fixtures.

Current validation:

- Backend suite: 21 tests passed; one existing TRON datetime deprecation warning.
- Frontend production build: passed with `npm run build`.
- ETH and TRON `/trace`: verified with non-zero real fixture values.
- PDF and CSV report endpoints: verified with HTTP 200 responses.
- Cross-chain bridge tracing: not implemented by the current backend.
- Separate backup demo case: not available; no fabricated or duplicated case is used.

## Scope

This is an investigative evidence prototype built for public blockchain analysis. It does not claim private KYC access or definitive criminal attribution.
