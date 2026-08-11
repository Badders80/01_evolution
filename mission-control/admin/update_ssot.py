import sqlite3
from pathlib import Path
from datetime import datetime, timezone

db_path = Path(__file__).parent / "ssot_local.db"
print("Updating Mission Control SQLite DB:", db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

now = datetime.now(timezone.utc).isoformat()

# Update HLT-001, HLT-002, HLT-003 status to fully_subscribed
target_ids = ["HLT-001", "HLT-002", "HLT-003"]
for hlt_id in target_ids:
    cursor.execute("""
        UPDATE hlts
        SET status = 'fully_subscribed', updated_at = ?
        WHERE id = ?
    """, (now, hlt_id))
    print(f"  Updated {hlt_id} -> status: fully_subscribed (rows affected: {cursor.rowcount})")

# Also update associated leases status to 'complete' if applicable
cursor.execute("""
    UPDATE leases
    SET lease_status = 'complete', updated_at = ?
    WHERE lease_id IN (SELECT lease_id FROM hlts WHERE id IN ('HLT-001', 'HLT-002', 'HLT-003'))
""", (now,))
print(f"  Updated leases for HLT-001, HLT-002, HLT-003 -> lease_status: complete (rows affected: {cursor.rowcount})")

conn.commit()
conn.close()
print("✅ Mission Control SQLite DB successfully updated and committed!")
