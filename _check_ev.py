import sys
sys.path.insert(0, r'c:\Users\rory.mcmullan\OneDrive - Mediolanum International Funds\MIA\4 - Quant\Dashboard')
from snowflake_data import _get_connection, SF_WAREHOUSE

conn = _get_connection()
cur = conn.cursor()
cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

# Search all FF_V3 tables for any column containing EV
cur.execute("""
    SELECT TABLE_NAME, COLUMN_NAME
    FROM FACTSET.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'FF_V3'
      AND (COLUMN_NAME ILIKE '%EV%' OR COLUMN_NAME ILIKE '%ENTRPR%')
    ORDER BY TABLE_NAME, COLUMN_NAME
""")
rows = cur.fetchall()
print(f"=== All EV/Enterprise Value columns in FF_V3 ({len(rows)}) ===")
for r in rows:
    print(f"  {r[0]}.{r[1]}")

# Also check if there's a dedicated EV table
print()
cur.execute("""
    SELECT TABLE_NAME FROM FACTSET.INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'FF_V3'
    ORDER BY TABLE_NAME
""")
rows = cur.fetchall()
print(f"=== All FF_V3 tables ({len(rows)}) ===")
for r in rows: print(f"  {r[0]}")

cur.close(); conn.close()
