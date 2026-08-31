# SQLite Setup Guide for CryptoTrace I4C

Complete guide to set up and use SQLite with VS Code.

## 1. Prerequisites

Make sure you have Python installed:

```bash
python --version
# Should be 3.8 or higher
```

SQLite is built into Python, so no separate installation needed!

---

## 2. Database Initialization

### Step 1: Initialize the database

From the project root directory:

```bash
cd backend
python db_init.py
```

Or from Python:

```python
from backend.db_init import init_all
init_all()
```

This creates the database file at: `backend/data/cryptotrace.db`

**Expected output:**
```
✅ users table created/verified
✅ cases table created/verified
✅ vasp_addresses table created/verified
✅ transactions table created/verified
✅ graph_nodes table created/verified
✅ graph_edges table created/verified

✅ All tables created successfully!
```

---

## 3. VS Code SQLite Extension Setup

### Step 1: Install SQLite Extension

1. Open VS Code
2. Click on **Extensions** (Ctrl+Shift+X)
3. Search for: **"SQLite"**
4. Install **"SQLite"** by alexcvzz (official extension)

### Step 2: Open Database in VS Code

1. Press **Ctrl+Shift+P** (Command Palette)
2. Type: **SQLite: Open Database**
3. Select: `backend/data/cryptotrace.db`

### Step 3: View Database Structure

In the VS Code Explorer sidebar, you should see:

```
SQLITE EXPLORER
└── cryptotrace.db
    ├── users
    ├── cases
    ├── vasp_addresses        ← M3 VASP dataset table
    ├── transactions
    ├── graph_nodes
    └── graph_edges
```

---

## 4. Database Tables Reference

### 4.1 Users Table (Authentication)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Usage:**
- Store user credentials
- Used by auth module

---

### 4.2 Cases Table (Investigation Cases)
```sql
CREATE TABLE cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT UNIQUE NOT NULL,
    user_id INTEGER,
    payload TEXT NOT NULL,        -- JSON with full evidence
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

**Usage:**
- Store complete investigation cases
- `payload` contains full evidence JSON
- Can be loaded/saved by M5 report module

---

### 4.3 VASP Addresses Table (M3 - Your Responsibility!)
```sql
CREATE TABLE vasp_addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,              -- Blockchain address (lowercase)
    chain TEXT NOT NULL,                -- ETH, TRON, etc.
    entity TEXT NOT NULL,               -- Exchange/VASP name
    type TEXT DEFAULT 'exchange',       -- exchange, wallet, bridge, etc.
    confidence TEXT DEFAULT 'UNKNOWN',  -- HIGH, MEDIUM, LOW, UNKNOWN
    source TEXT,                        -- Where data came from
    source_url TEXT,                    -- Verification URL
    source_date TEXT,                   -- Date verified (YYYY-MM-DD)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(address, chain)
);
```

**Indexes:**
```sql
idx_vasp_address          -- Fast lookup by address
idx_vasp_chain            -- Fast lookup by chain
idx_vasp_address_chain    -- Fast lookup by address + chain (composite)
```

**Usage (M3 VASP Module):**
```python
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()

# Add a VASP address
db.add_vasp(
    address="0x3f5ce5fbfe3e9af3971dd820d28b22f08",
    chain="ETH",
    entity="Binance",
    type_="exchange",
    confidence="HIGH",
    source="Etherscan official label",
    source_url="https://etherscan.io/accounts/label/binance",
    source_date="2024-01-15"
)

# Lookup VASP
match = db.get_vasp("0x3f5ce5fbfe3e9af3971dd820d28b22f08", "ETH")
if match:
    print(f"Found: {match['entity']} (confidence: {match['confidence']})")
else:
    print("UNKNOWN address")

# List all VASP for a chain
eth_vasps = db.get_vasp_by_chain("ETH")
```

---

### 4.4 Transactions Table (Transaction Cache)
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    tx_hash TEXT UNIQUE NOT NULL,
    chain TEXT NOT NULL,
    from_addr TEXT NOT NULL,
    to_addr TEXT NOT NULL,
    asset TEXT,
    amount REAL,
    timestamp TEXT,
    block INTEGER,
    source_url TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(case_id)
);
```

**Usage:**
- M1 caches normalized transactions here
- Avoid repeated API calls
- Integrates with M2 graph tracing

---

### 4.5 Graph Nodes Table (Graph Cache)
```sql
CREATE TABLE graph_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    address TEXT NOT NULL,
    chain TEXT NOT NULL,
    node_type TEXT,
    metadata TEXT,                  -- JSON with additional data
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(case_id, address, chain),
    FOREIGN KEY(case_id) REFERENCES cases(case_id)
);
```

**Usage:**
- M2 caches graph nodes
- Avoids re-tracing

---

### 4.6 Graph Edges Table (Graph Cache)
```sql
CREATE TABLE graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    from_addr TEXT NOT NULL,
    to_addr TEXT NOT NULL,
    chain TEXT NOT NULL,
    tx_count INTEGER DEFAULT 1,
    total_amount REAL DEFAULT 0,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(case_id, from_addr, to_addr, chain),
    FOREIGN KEY(case_id) REFERENCES cases(case_id)
);
```

**Usage:**
- M2 caches edges (transactions between addresses)
- Aggregates multiple transactions between same pair

---

## 5. Querying VASP Data in VS Code

### Method 1: Using SQLite Extension

1. In VS Code, open the SQLite Explorer
2. Right-click on `vasp_addresses` table
3. Click **Run Query**
4. Enter SQL, e.g.:

```sql
-- See all VASP addresses
SELECT * FROM vasp_addresses;

-- See all ETH exchanges
SELECT * FROM vasp_addresses WHERE chain = 'ETH';

-- Search for address
SELECT * FROM vasp_addresses WHERE address = '0x3f5ce5fbfe3e9af3971dd820d28b22f08';

-- See statistics
SELECT confidence, COUNT(*) as count FROM vasp_addresses GROUP BY confidence;
SELECT chain, COUNT(*) as count FROM vasp_addresses GROUP BY chain;
```

### Method 2: Using Python

```python
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()

# Get statistics
stats = db.get_stats()
print(stats)

# List all VASP
all_vasp = db.list_all_vasp()
for v in all_vasp:
    print(f"{v['entity']}: {v['address']} ({v['chain']})")
```

---

## 6. Importing VASP Data from JSON

If you have a JSON file with VASP addresses:

```json
[
  {
    "address": "0x3f5ce5fbfe3e9af3971dd820d28b22f08",
    "chain": "ETH",
    "entity": "Binance",
    "type": "exchange",
    "confidence": "HIGH",
    "source": "Etherscan official label",
    "source_url": "https://etherscan.io/accounts/label/binance",
    "source_date": "2024-01-15"
  },
  ...
]
```

Then import it:

```python
from pathlib import Path
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()
result = db.bulk_import_json(Path("backend/data/vasp_labels.json"))

print(f"✅ Added: {result['added']}")
print(f"📝 Updated: {result['updated']}")
if result['errors']:
    print(f"❌ Errors: {result['errors']}")
```

---

## 7. Connection from FastAPI

Use the existing connection in your FastAPI routes:

```python
from backend.db_init import get_connection
from backend.services.vasp_db import get_vasp_db

# In your endpoint
@app.post("/vasp-lookup")
async def vasp_lookup(address: str, chain: str):
    db = get_vasp_db()
    match = db.get_vasp(address, chain)
    
    if match:
        return {
            "found": True,
            "entity": match["entity"],
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
            "source": None,
            "source_url": None,
            "source_date": None,
        }
```

---

## 8. Common SQL Queries

### Insert VASP Address
```sql
INSERT INTO vasp_addresses 
(address, chain, entity, type, confidence, source, source_url, source_date)
VALUES (
  '0x3f5ce5fbfe3e9af3971dd820d28b22f08',
  'ETH',
  'Binance',
  'exchange',
  'HIGH',
  'Etherscan label',
  'https://etherscan.io/accounts/label/binance',
  '2024-01-15'
);
```

### Lookup VASP
```sql
SELECT * FROM vasp_addresses 
WHERE address = '0x3f5ce5fbfe3e9af3971dd820d28b22f08' 
AND chain = 'ETH';
```

### Update VASP
```sql
UPDATE vasp_addresses 
SET confidence = 'MEDIUM', updated_at = CURRENT_TIMESTAMP
WHERE address = '0x3f5ce5fbfe3e9af3971dd820d28b22f08';
```

### Delete VASP
```sql
DELETE FROM vasp_addresses 
WHERE address = '0x3f5ce5fbfe3e9af3971dd820d28b22f08' 
AND chain = 'ETH';
```

### Statistics
```sql
-- Total records
SELECT COUNT(*) FROM vasp_addresses;

-- By confidence level
SELECT confidence, COUNT(*) as count 
FROM vasp_addresses 
GROUP BY confidence 
ORDER BY count DESC;

-- By chain
SELECT chain, COUNT(*) as count 
FROM vasp_addresses 
GROUP BY chain 
ORDER BY count DESC;

-- By entity
SELECT entity, chain, COUNT(*) as count 
FROM vasp_addresses 
GROUP BY entity, chain 
ORDER BY entity;
```

---

## 9. Testing VASP Database

Run the test suite:

```bash
cd backend
pytest tests/test_vasp_db.py -v
```

Or manually:

```python
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()

# Add test address
db.add_vasp(
    address="0xtest123",
    chain="ETH",
    entity="Test Exchange",
    confidence="HIGH",
    source="Test",
    source_url="https://test.com",
    source_date="2024-01-01"
)

# Lookup
result = db.get_vasp("0xtest123", "ETH")
assert result is not None
assert result["entity"] == "Test Exchange"
print("✅ Test passed!")

# Cleanup
db.delete_vasp("0xtest123", "ETH")
```

---

## 10. Troubleshooting

### Problem: Database file not created
**Solution:** Run `python backend/db_init.py` explicitly to initialize

### Problem: "No such table" error
**Solution:** Call `init_all()` or run `db_init.py` to create tables

### Problem: Address queries return nothing
**Solution:** Make sure addresses are lowercase. Use:
```python
address = "0x1234ABC".lower()  # → "0x1234abc"
```

### Problem: SQLite locked error
**Solution:** Ensure you're not using the database file in multiple processes simultaneously

---

## 11. Database File Location

```
project-root/
└── backend/
    └── data/
        └── cryptotrace.db    ← This is your SQLite database file
```

File size: ~1-5 MB (small, portable, no external DB needed!)

---

## 12. Backup & Reset

### Backup database
```bash
cp backend/data/cryptotrace.db backend/data/cryptotrace.db.backup
```

### Reset database
```bash
rm backend/data/cryptotrace.db
python backend/db_init.py
```

---

**✅ You're ready to use SQLite with CryptoTrace!**

For M3 VASP module: Use `backend.services.vasp_db` module
For general queries: Use `backend.db_init.get_connection()`
For VS Code: Use SQLite Explorer (Ctrl+Shift+P → SQLite: Open Database)
