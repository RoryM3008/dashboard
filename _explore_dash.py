"""Quick VIX check."""
import sys
sys.path.insert(0, ".")
from snowflake_data import _get_connection, SF_WAREHOUSE
conn = _get_connection()
cur = conn.cursor()
cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
cur.execute("SELECT TICKER_REGION, FSYM_ID FROM FACTSET.SYM_V1.SYM_TICKER_REGION WHERE TICKER_REGION LIKE 'VIX%' LIMIT 10")
for r in cur.fetchall():
    print(r)
# Also check VIXY (VIX ETF)
cur.execute("SELECT TICKER_REGION, FSYM_ID FROM FACTSET.SYM_V1.SYM_TICKER_REGION WHERE TICKER_REGION IN ('VIXY-US','UVXY-US','VXX-US')")
for r in cur.fetchall():
    print("ETF:", r)

