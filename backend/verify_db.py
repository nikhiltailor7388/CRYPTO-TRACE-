"""Quick verification script for SQLite database"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "data" / "cryptotrace.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("\n[TABLES IN DATABASE]")
for table_name in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name[0]}")
    count = cursor.fetchone()[0]
    print(f"  - {table_name[0]:<20} ({count} records)")

print("\n[VASP_ADDRESSES TABLE SCHEMA]")
cursor.execute("PRAGMA table_info(vasp_addresses)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]:<20} {col[2]:<10}")

print(f"\nTotal tables: {len(tables)}")
print(f"Database file: {db_path}")
print(f"Database size: {db_path.stat().st_size} bytes")

conn.close()
