"""Display all VASP records in the database"""
from backend.services.vasp_db import get_vasp_db

db = get_vasp_db()
vasps = db.list_all_vasp()

print(f"\n[VASP DATABASE CONTENTS ({len(vasps)} records)]\n")
print(f"{'Entity':<20} | {'Chain':<6} | {'Address':<42} | {'Confidence':<10}")
print("-" * 90)

for v in vasps:
    print(f"{v['entity']:<20} | {v['chain']:<6} | {v['address']:<42} | {v['confidence']:<10}")

print()
