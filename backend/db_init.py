"""
SQLite Database Initialization for CryptoTrace I4C

This script initializes the SQLite database with all required tables:
- users (authentication)
- cases (investigation cases)
- vasp_addresses (VASP dataset - M3 responsibility)
- transactions (cached transactions)
- graph_nodes (graph data for caching)

Usage:
    python -m backend.db_init
    or from Python:
    from backend.db_init import init_all
    init_all()
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path(__file__).resolve().parent / "data" / "cryptotrace.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Get SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def create_users_table(conn):
    """Create users table for authentication."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create index on email for faster lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    conn.commit()
    print("[OK] users table created/verified")


def create_cases_table(conn):
    """Create cases table for storing investigation cases."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            payload TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_case_id ON cases(case_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_user_id ON cases(user_id)")
    conn.commit()
    print("[OK] cases table created/verified")


def create_vasp_addresses_table(conn):
    """
    Create VASP addresses table for M3 VASP dataset.
    
    This table stores verified VASP/exchange addresses with:
    - address: blockchain address
    - chain: ETH, TRON, etc.
    - entity: exchange/VASP name
    - type: exchange, wallet, service, etc.
    - confidence: HIGH, MEDIUM, LOW, UNKNOWN
    - source: where the data came from
    - source_url: URL to verification source
    - source_date: date the source was verified
    - created_at: when this record was added to DB
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vasp_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL,
            chain TEXT NOT NULL,
            entity TEXT NOT NULL,
            type TEXT DEFAULT 'exchange',
            confidence TEXT DEFAULT 'UNKNOWN',
            source TEXT,
            source_url TEXT,
            source_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(address, chain)
        )
    """)
    # Create indexes for fast lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vasp_address ON vasp_addresses(address)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vasp_chain ON vasp_addresses(chain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vasp_address_chain ON vasp_addresses(address, chain)")
    conn.commit()
    print("[OK] vasp_addresses table created/verified")


def create_transactions_table(conn):
    """Create transactions cache table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_case_id ON transactions(case_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_hash ON transactions(tx_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_addr)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_to ON transactions(to_addr)")
    conn.commit()
    print("[OK] transactions table created/verified")


def create_graph_nodes_table(conn):
    """Create graph nodes cache table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            address TEXT NOT NULL,
            chain TEXT NOT NULL,
            node_type TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(case_id, address, chain),
            FOREIGN KEY(case_id) REFERENCES cases(case_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_case_id ON graph_nodes(case_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_address ON graph_nodes(address)")
    conn.commit()
    print("[OK] graph_nodes table created/verified")


def create_graph_edges_table(conn):
    """Create graph edges cache table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS graph_edges (
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_case_id ON graph_edges(case_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON graph_edges(from_addr)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON graph_edges(to_addr)")
    conn.commit()
    print("[OK] graph_edges table created/verified")


def init_all():
    """Initialize all tables."""
    print(f"\n[SETUP] Initializing SQLite database at: {DB_PATH}\n")
    
    conn = get_connection()
    try:
        create_users_table(conn)
        create_cases_table(conn)
        create_vasp_addresses_table(conn)
        create_transactions_table(conn)
        create_graph_nodes_table(conn)
        create_graph_edges_table(conn)
        
        print("\n[SUCCESS] All tables created successfully!")
        print(f"[DB] Database location: {DB_PATH}")
        print(f"[DB] Database size: {DB_PATH.stat().st_size if DB_PATH.exists() else 0} bytes\n")
        
    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_all()
