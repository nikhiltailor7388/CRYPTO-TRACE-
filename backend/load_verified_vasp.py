"""
Load verified VASP data from Etherscan and other official sources into SQLite
"""

from pathlib import Path
from backend.services.vasp_db import get_vasp_db


def load_verified_vasp():
    """Load verified VASP addresses from multiple sources into database."""
    
    db = get_vasp_db()
    
    # Load from verified_vasp_sources.json
    vasp_file = Path(__file__).resolve().parent / "data" / "verified_vasp_sources.json"
    
    if not vasp_file.exists():
        print(f"[ERROR] File not found: {vasp_file}")
        return
    
    print(f"\n[LOADING] Importing verified VASP sources from: {vasp_file.name}\n")
    
    result = db.bulk_import_json(vasp_file)
    
    print(f"[RESULTS]")
    print(f"  Added: {result['added']} records")
    print(f"  Updated: {result['updated']} records")
    print(f"  Total processed: {result['total_processed']}")
    
    if result['errors']:
        print(f"\n[ERRORS] ({len(result['errors'])})")
        for error in result['errors']:
            print(f"  - {error}")
    
    # Show database stats
    stats = db.get_stats()
    print(f"\n[DATABASE STATS]")
    print(f"  Total VASP records: {stats['total_records']}")
    print(f"  By chain: {stats['by_chain']}")
    print(f"  By confidence: {stats['by_confidence']}")
    
    print(f"\n[SUCCESS] Verified VASP data loaded!\n")


if __name__ == "__main__":
    load_verified_vasp()
