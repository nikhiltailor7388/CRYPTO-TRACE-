# CryptoTrace Demo Script

This script demonstrates the existing public-data workflow without adding
sample transactions or changing the application state intentionally.

## Start the stack

### Backend

```powershell
cd C:\Users\Divyanshu\CRYPTO-TRACE-
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend

In a second terminal:

```powershell
cd C:\Users\Divyanshu\CRYPTO-TRACE-\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173>.

## ETH demonstration

1. Select `ETH`.
2. Enter this existing public fixture wallet as the reported wallet:
   `0x899Ac98d90CD60Eda9aF2b4690307Db784D03871`
3. Set max hops to `3` and select **Trace wallet**.
4. Confirm the response shows:
   - `ETH` as the asset;
   - a non-zero transfer such as `0.0000666 ETH`;
   - an ordered bounded path;
   - matching graph nodes and edges;
   - evidence with an Etherscan link;
   - risk output and honest `UNKNOWN` VASP status where no label exists.
5. Expand **Technical details and reports** only when the graph hash,
   metrics, PDF, or CSV are needed.

## TRON demonstration

1. Select `TRON`.
2. Enter this existing public fixture wallet as the reported wallet:
   `TMtWegFY9czQEMqupk4dCrdWqpG77MPJnz`
3. Set max hops to `3` and select **Trace wallet**.
4. Confirm the response shows `TRX`, a non-zero transfer, an ordered
   bounded path, Tronscan evidence links, risk output, and honest VASP
   attribution.

## Multi-wallet demonstration

Use the optional **Additional wallets** field for the existing ETH fixture
addresses:

```text
0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
0xb8aEccC3ab76a0a1FB807244205B1E3f88C86B89
```

The backend remains authoritative for the resulting path and evidence. The
frontend must not infer or fabricate relationships.

## Reports

Use the existing report links after a trace:

- `/reports/{case_id}.pdf`
- `/reports/{case_id}.csv`

The PDF contains the investigation summary, bounded path, VASP findings,
transaction evidence, and limitations. The CSV contains the evidence rows
and preserves the chain/asset values.

## Validation commands

```powershell
python -m pytest backend/tests -q
cd frontend
npm run build
```

The current frontend has no separate automated test runner.

## Boundaries and limitations

- Live retrieval depends on configured provider access; demo mode uses the
  existing real historical fixtures.
- `UNKNOWN` means that no source-backed label matched the bounded evidence.
- The backend does not implement arbitrary cross-chain bridge tracing.
- No real-person identity, private KYC, government, bank, or telecom data is
  accessed.
- No independently verified second backup case is currently available.
  Do not create one from fabricated or duplicated transactions.
