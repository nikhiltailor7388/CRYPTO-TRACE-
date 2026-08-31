"""
VASP Address Database Module (M3 - VASP/Data Engineer)

Provides SQLite-backed VASP dataset management:
- Add verified VASP addresses to database
- Query VASP by address and chain
- List all VASP addresses
- Update VASP records
- Delete VASP records
- Bulk import from JSON

The VASP_addresses table stores:
- address: blockchain address (normalized to lowercase)
- chain: ETH, TRON, etc.
- entity: Exchange/VASP name
- type: exchange, wallet, service, bridge, mixer, etc.
- confidence: HIGH, MEDIUM, LOW, UNKNOWN
- source: where the data came from
- source_url: verification URL
- source_date: when verified (YYYY-MM-DD)
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from backend.db_init import get_connection


class VASPDatabase:
    """SQLite-backed VASP dataset manager."""
    
    def __init__(self):
        self.db_path = Path(__file__).resolve().parent / "data" / "cryptotrace.db"
    
    def add_vasp(
        self,
        address: str,
        chain: str,
        entity: str,
        type_: str = "exchange",
        confidence: str = "UNKNOWN",
        source: Optional[str] = None,
        source_url: Optional[str] = None,
        source_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add or update a VASP record in the database.
        
        Args:
            address: Blockchain address (will be normalized to lowercase)
            chain: Blockchain (ETH, TRON, etc.)
            entity: Exchange/VASP name
            type_: Address type (exchange, wallet, bridge, etc.)
            confidence: HIGH, MEDIUM, LOW, UNKNOWN
            source: Source documentation
            source_url: URL to verification
            source_date: Date verified (YYYY-MM-DD)
            
        Returns:
            Dict with inserted/updated record
        """
        conn = get_connection()
        address_normalized = address.lower().strip()
        
        try:
            cursor = conn.execute(
                """
                INSERT INTO vasp_addresses 
                (address, chain, entity, type, confidence, source, source_url, source_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(address, chain) DO UPDATE SET
                    entity = excluded.entity,
                    type = excluded.type,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    source_url = excluded.source_url,
                    source_date = excluded.source_date,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (address_normalized, chain, entity, type_, confidence, source, source_url, source_date),
            )
            conn.commit()
            
            # Fetch and return the record
            row = conn.execute(
                "SELECT * FROM vasp_addresses WHERE address = ? AND chain = ?",
                (address_normalized, chain),
            ).fetchone()
            
            return dict(row) if row else {}
        
        finally:
            conn.close()
    
    def get_vasp(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Get VASP record by address and chain.
        
        Args:
            address: Blockchain address
            chain: Blockchain (ETH, TRON, etc.)
            
        Returns:
            Dict with VASP record or None if not found
        """
        conn = get_connection()
        address_normalized = address.lower().strip()
        
        try:
            row = conn.execute(
                "SELECT * FROM vasp_addresses WHERE address = ? AND chain = ?",
                (address_normalized, chain),
            ).fetchone()
            
            return dict(row) if row else None
        
        finally:
            conn.close()
    
    def get_vasp_by_chain(self, chain: str) -> List[Dict[str, Any]]:
        """
        Get all VASP records for a specific chain.
        
        Args:
            chain: Blockchain (ETH, TRON, etc.)
            
        Returns:
            List of VASP records
        """
        conn = get_connection()
        
        try:
            rows = conn.execute(
                "SELECT * FROM vasp_addresses WHERE chain = ? ORDER BY entity",
                (chain,),
            ).fetchall()
            
            return [dict(row) for row in rows]
        
        finally:
            conn.close()
    
    def list_all_vasp(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get all VASP records.
        
        Args:
            limit: Maximum records to return
            
        Returns:
            List of VASP records
        """
        conn = get_connection()
        
        try:
            rows = conn.execute(
                "SELECT * FROM vasp_addresses ORDER BY entity, chain LIMIT ?",
                (limit,),
            ).fetchall()
            
            return [dict(row) for row in rows]
        
        finally:
            conn.close()
    
    def delete_vasp(self, address: str, chain: str) -> bool:
        """
        Delete a VASP record.
        
        Args:
            address: Blockchain address
            chain: Blockchain
            
        Returns:
            True if deleted, False if not found
        """
        conn = get_connection()
        address_normalized = address.lower().strip()
        
        try:
            cursor = conn.execute(
                "DELETE FROM vasp_addresses WHERE address = ? AND chain = ?",
                (address_normalized, chain),
            )
            conn.commit()
            
            return cursor.rowcount > 0
        
        finally:
            conn.close()
    
    def bulk_import_json(self, json_path: Path) -> Dict[str, Any]:
        """
        Bulk import VASP records from JSON file.
        
        Expected JSON format:
        - List of objects with address, chain, entity, type, confidence, source, source_url, source_date
        - OR Dict with lowercase addresses as keys
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Dict with import stats
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Normalize data to list of dicts
        if isinstance(data, dict):
            records = list(data.values())
        elif isinstance(data, list):
            records = data
        else:
            return {"success": False, "message": "Invalid JSON format"}
        
        added = 0
        updated = 0
        errors = []
        
        for record in records:
            try:
                if not isinstance(record, dict):
                    errors.append(f"Invalid record: {record}")
                    continue
                
                address = record.get("address", "").lower().strip()
                chain = record.get("chain", "").upper().strip()
                
                if not address or not chain:
                    errors.append(f"Missing address or chain: {record}")
                    continue
                
                # Check if exists
                existing = self.get_vasp(address, chain)
                
                result = self.add_vasp(
                    address=address,
                    chain=chain,
                    entity=record.get("entity", "UNKNOWN"),
                    type_=record.get("type", "exchange"),
                    confidence=record.get("confidence", "UNKNOWN"),
                    source=record.get("source"),
                    source_url=record.get("source_url"),
                    source_date=record.get("source_date"),
                )
                
                if existing:
                    updated += 1
                else:
                    added += 1
            
            except Exception as e:
                errors.append(f"Error processing record {record}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "added": added,
            "updated": updated,
            "errors": errors,
            "total_processed": added + updated + len(errors),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = get_connection()
        
        try:
            total = conn.execute("SELECT COUNT(*) as count FROM vasp_addresses").fetchone()
            by_chain = conn.execute(
                "SELECT chain, COUNT(*) as count FROM vasp_addresses GROUP BY chain"
            ).fetchall()
            by_confidence = conn.execute(
                "SELECT confidence, COUNT(*) as count FROM vasp_addresses GROUP BY confidence"
            ).fetchall()
            
            return {
                "total_records": total["count"],
                "by_chain": {row["chain"]: row["count"] for row in by_chain},
                "by_confidence": {row["confidence"]: row["count"] for row in by_confidence},
            }
        
        finally:
            conn.close()


# Singleton instance
_vasp_db = None


def get_vasp_db() -> VASPDatabase:
    """Get or create the VASP database instance."""
    global _vasp_db
    if _vasp_db is None:
        _vasp_db = VASPDatabase()
    return _vasp_db


if __name__ == "__main__":
    # Demo usage
    db = get_vasp_db()
    
    print("\n📊 VASP Database Stats:")
    stats = db.get_stats()
    print(f"  Total records: {stats['total_records']}")
    print(f"  By chain: {stats['by_chain']}")
    print(f"  By confidence: {stats['by_confidence']}")
