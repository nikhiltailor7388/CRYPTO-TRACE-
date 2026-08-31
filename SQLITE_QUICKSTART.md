# SQLite Setup - Quick Reference for VS Code

## Status ✅

- [x] SQLite database created: `backend/data/cryptotrace.db`
- [x] All 7 tables initialized
- [x] VASP addresses table ready (M3)
- [x] Sample data loaded (5 records)
- [x] Python connection modules working

---

## 1. Open Database in VS Code

### Step 1: Install SQLite Extension
- Press `Ctrl+Shift+X` (Extensions)
- Search for **"SQLite"** by alexcvzz
- Click Install

### Step 2: Open Database
- Press `Ctrl+Shift+P` (Command Palette)
- Type: **SQLite: Open Database**
- Select: `backend/data/cryptotrace.db`

### Step 3: View Tables
In VS Code Explorer sidebar, you'll see:
```
SQLite Explorer
└── cryptotrace.db
    ├── users
    ├── cases
    ├── vasp_addresses         ← Your VASP data!
    ├── transactions
    ├── graph_nodes
    └── graph_edges
```

---

## 2. Query VASP Data in VS Code

### Right-click on `vasp_addresses` table → Run Query

**Example queries:**

```sql
-- See all VASP addresses
SELECT * FROM vasp_addresses;

-- Find a specific address
SELECT * FROM vasp_addresses 
WHERE address = '0x3f5ce5fbfe3e9af3971dd820d28b22f08';

-- Get Binance addresses
SELECT * FROM vasp_addresses 
WHERE entity = 'Binance';

-- Statistics
SELECT chain, confidence, COUNT(*) 
FROM vasp_addresses 
GROUP BY chain, confidence;
```

---

## 3. Use VASP Database in Python

### Example 1: Look up an address

```python
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()

# Lookup
match = db.get_vasp("0x3f5ce5fbfe3e9af3971dd820d28b22f08", "ETH")

if match:
    print(f"Found: {match['entity']}")
    print(f"Confidence: {match['confidence']}")
    print(f"Source: {match['source']}")
else:
    print("UNKNOWN address")
```

### Example 2: Add new VASP

```python
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()

db.add_vasp(
    address="0x...",
    chain="ETH",
    entity="Your Exchange",
    type_="exchange",
    confidence="HIGH",
    source="Your source",
    source_url="https://...",
    source_date="2024-01-20"
)
```

### Example 3: Get all for a chain

```python
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()

eth_vasps = db.get_vasp_by_chain("ETH")
for v in eth_vasps:
    print(f"{v['entity']}: {v['address']}")
```

### Example 4: Get database stats

```python
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()
stats = db.get_stats()

print(f"Total records: {stats['total_records']}")
print(f"By chain: {stats['by_chain']}")
print(f"By confidence: {stats['by_confidence']}")
```

---

## 4. Use in FastAPI Endpoints

```python
from fastapi import FastAPI
from backend.services.vasp_db import get_vasp_db

app = FastAPI()

@app.post("/vasp-lookup")
async def vasp_lookup(address: str, chain: str):
    """Look up VASP address"""
    db = get_vasp_db()
    match = db.get_vasp(address, chain)
    
    if match:
        return {
            "found": True,
            "entity": match["entity"],
            "type": match["type"],
            "confidence": match["confidence"],
            "source": match["source"],
            "source_url": match["source_url"],
            "source_date": match["source_date"],
        }
    else:
        return {
            "found": False,
            "entity": "UNKNOWN",
            "confidence": "UNKNOWN",
        }
```

---

## 5. Database Commands

### View all VASP records
```bash
cd backend && python list_vasp.py
```

### Initialize database (create tables)
```bash
cd backend && python db_init.py
```

### Load sample data
```bash
cd .. && python -m backend.load_sample_vasp
```

### Verify database
```bash
cd backend && python verify_db.py
```

---

## 6. Database Schema Reference

### VASP Addresses Table
| Column | Type | Purpose |
|--------|------|---------|
| id | INTEGER PK | Auto-increment ID |
| address | TEXT | Blockchain address (lowercase) |
| chain | TEXT | ETH, TRON, etc. |
| entity | TEXT | Exchange/VASP name |
| type | TEXT | exchange, wallet, bridge, etc. |
| confidence | TEXT | HIGH, MEDIUM, LOW, UNKNOWN |
| source | TEXT | Where data came from |
| source_url | TEXT | Verification URL |
| source_date | TEXT | Date verified (YYYY-MM-DD) |
| created_at | TEXT | Timestamp |
| updated_at | TEXT | Timestamp |

### Unique Constraint
- `(address, chain)` — No duplicate address+chain combinations

### Indexes
- `idx_vasp_address` — Fast lookup by address
- `idx_vasp_chain` — Fast lookup by chain
- `idx_vasp_address_chain` — Fast lookup by both

---

## 7. File Locations

```
project-root/
├── backend/
│   ├── data/
│   │   └── cryptotrace.db             ← SQLite database file
│   ├── db_init.py                     ← Initialize DB
│   ├── services/
│   │   ├── vasp_db.py                 ← VASP database module
│   │   └── vasp_matcher.py            ← Address matching (existing)
│   ├── list_vasp.py                   ← List VASP records
│   ├── verify_db.py                   ← Verify DB structure
│   └── load_sample_vasp.py            ← Load sample data
├── SQLITE_SETUP.md                    ← Full setup guide
└── SQLITE_QUICKSTART.md               ← This file
```

---

## 8. Data Validation

### Address Format
- Always store as **lowercase**
- `0x3F5CE5FBFe3E9af3971dD820d28b22F08` → `0x3f5ce5fbfe3e9af3971dd820d28b22f08`

### Confidence Levels
- `HIGH` — Verified public source (Etherscan label, official exchange)
- `MEDIUM` — Reliable community consensus
- `LOW` — Behavioral heuristic only
- `UNKNOWN` — No match or insufficient evidence

### Chain Abbreviations
- `ETH` — Ethereum
- `TRON` — TRON network
- Add others as needed

---

## 9. Testing

Run tests:
```bash
cd backend && pytest tests/test_vasp_matcher.py -v
```

---

## 10. Common Tasks

### Add new VASP address
```python
db.add_vasp(
    address="0x...",
    chain="ETH",
    entity="New Exchange",
    confidence="HIGH",
    source="Your source",
    source_url="https://...",
    source_date="2024-01-20"
)
```

### Update existing VASP
```python
# add_vasp with same address+chain updates it
db.add_vasp(address="...", chain="...", confidence="MEDIUM", ...)
```

### Delete VASP
```python
db.delete_vasp("0x...", "ETH")
```

### Import from JSON
```python
db.bulk_import_json(Path("data/vasp_labels.json"))
```

---

## 11. Troubleshooting

| Problem | Solution |
|---------|----------|
| Database file not found | Run `python backend/db_init.py` |
| "No such table" | Run `python backend/db_init.py` to initialize |
| Address lookup returns None | Make sure address is lowercase |
| Import doesn't work | Ensure JSON format has required fields |
| SQLite extension not showing in VS Code | Reload VS Code, reinstall extension |

---

## ✅ You're Ready!

- Database: **Created and initialized**
- Sample data: **Loaded**
- VS Code integration: **Ready**
- Python modules: **Working**

Start querying and building! 🚀
