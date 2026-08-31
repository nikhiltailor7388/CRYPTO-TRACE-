# CryptoTrace live demo verification

## A. Real wallet used for the end-to-end live run

Address: `0x28C6c06298d514Db089934071355E5743bf21d60`
Source: public Etherscan account history for this address, independently verifiable at https://etherscan.io/address/0x28C6c06298d514Db089934071355E5743bf21d60
This was selected because it is a real, published public Ethereum address with genuine activity and non-trivial on-chain history.

## B. Actual flow result

Live API call used:
- POST `http://127.0.0.1:8000/trace`
- Authenticated user: `nikhiltailor7388@gmail.com`
- Payload:
  ```json
  {
    "case_id": "CASE-DEMO-REAL",
    "case_name": "Case DEMO REAL",
    "address": "0x28C6c06298d514Db089934071355E5743bf21d60",
    "chain": "ETH",
    "max_hops": 3
  }
  ```

Actual raw response saved at: `demo_verification/real_case_trace.json`
Actual full graph payload saved at: `demo_verification/live_graph_payload.json`

Actual graph payload from the live response (full node/edge objects, not counts):
```json
{
  "nodes": [
    {
      "id": "0x0cf0ee63788a0849fe5297f3407f701e122cc023",
      "label": "Cluster Member",
      "type": "cluster_member",
      "cluster_id": "cluster-1",
      "total_in": 0.0,
      "total_out": 0
    },
    {
      "id": "0x103c3a209da59d3e7c4a89307e66521e081cfdf0",
      "label": "Intermediate Wallet - Hop 2",
      "type": "intermediate",
      "cluster_id": null,
      "total_in": 0.0,
      "total_out": 0
    },
    {
      "id": "0x28c6c06298d514db089934071355e5743bf21d60",
      "label": "Victim Wallet (Source)",
      "type": "victim",
      "cluster_id": "cluster-1",
      "total_in": 11.0,
      "total_out": 0.0
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "0x28c6c06298d514db089934071355e5743bf21d60",
      "target": "0x0cf0ee63788a0849fe5297f3407f701e122cc023",
      "tx_hash": "0xd770a1efe27aac576d2b4fa1857dea5c172cd1fe7ff3d6a6ae115c79df3db071",
      "amount": 0.0,
      "asset": "ETH",
      "timestamp": "2021-04-29T16:46:28Z",
      "edge_type": "direct",
      "confidence": null
    }
  ]
}
```

The live response contains 17 nodes and 16 edges. The exact payload was saved to `demo_verification/live_graph_payload.json`.

Actual values from the response:
```json
{
  "case_id": "CASE-DEMO-REAL",
  "status": "complete",
  "data_source": "live",
  "summary": {
    "total_transactions": 1000,
    "hops_traced": 3,
    "total_value": 11.0,
    "traceable_value": 0.0,
    "unclassified_value": 11.0,
    "vasp_matches": 0,
    "risk_score": 99,
    "fraud_probability": 50
  },
  "wallet_clusters": [
    {
      "id": "cluster-1",
      "members": [
        "0x28c6c06298d514db089934071355e5743bf21d60",
        "0x0cf0ee63788a0849fe5297f3407f701e122cc023",
        "0xd7efb00d12c2c13131fd319336fdf952525da2af",
        "0x4156d3342d5c385a87d264f90653733592000581",
        "0x99ea4db9ee77acd40b119bd1dc4e33e1c070b80d"
      ],
      "confidence": 0.7,
      "heuristic": "common-input-ownership",
      "reason": "Grouped because 16 addresses were observed as downstream recipients from the same origin wallet across txs ... this is a probabilistic grouping and not definitive proof of shared control."
    }
  ],
  "vasp_matches": [],
  "risk_profile": {
    "overall_probability": 50,
    "risk_factors": [
      {"name": "Direct exposure", "score": 0, "rule": "direct_exposure", "confidence": "low"},
      {"name": "VASP linkage", "score": 0, "rule": "vasp_linkage", "confidence": "low"},
      {"name": "Unclassified flow", "score": 25, "rule": "unclassified_flow", "confidence": "medium"},
      {"name": "Propagation depth", "score": 15, "rule": "propagation_depth", "confidence": "medium"}
    ]
  },
  "evidence_checksum": "d10720aaec0d51df85b2fc3c933587b25dc5f34f881c76fcc81439e845555f03",
  "legal_notice": "This report identifies the likely exchange endpoint and supporting evidence for a legal request. It does not identify a real person — that requires the exchange's own KYC process, which is outside this system's scope."
}
```

## C. Frontend graph / legend

The app was run locally and the rendered result was captured from the live frontend at http://127.0.0.1:5173.
The graph view is populated with real transaction data and the legend includes the expected classes for wallet nodes, direct transactions, probable continuations, and clustered wallet groups.
Saved live UI screenshot is in the local session output and the live front-end is available to rerun locally.

## D. PDF and CSV exports

Generated files:
- `demo_verification/CASE-DEMO-REAL.pdf`
- `demo_verification/CASE-DEMO-REAL.csv`

The PDF report includes the evidence table, cluster reasoning, checksum, legal notice, and summary output produced by the live case.

## E. Failure-path verification (explicit real-data-only error)

Test address used: `0x97a45d69e96a9bfd140b2ca53ce3ed5977bd7aa2`
This address has no real transaction history on Etherscan, and the API correctly returned the guardrail error instead of synthetic results.
Actual response:
```json
{
  "detail": "Unable to retrieve real transaction data for this address — please check the address or try again."
}
```
HTTP status: 404

## F. File inventory

- `demo_verification/real_case_trace.json` — raw live API response
- `demo_verification/CASE-DEMO-REAL.pdf` — generated PDF report
- `demo_verification/CASE-DEMO-REAL.csv` — generated CSV export
- `DEMO_VERIFICATION.md` — summary of the verification case
