"""Explore available benchmarks in Snowflake."""
import sys
sys.path.insert(0, ".")
from snowflake_data import _get_connection, SF_WAREHOUSE

conn = _get_connection()
cur = conn.cursor()
cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

# 1. MSCI indices — unique index names
print("=" * 80)
print("MSCI INDICES (from INDEX_LEVELS)")
print("=" * 80)
cur.execute("""
    SELECT DISTINCT INDEX_NAME, MSCI_INDEX_CODE, INDEX_VARIANT_TYPE, ISO_CURRENCY_SYMBOL
    FROM MSCI.INDEX.INDEX_LEVELS
    WHERE CALC_DATE >= '2026-01-01'
    ORDER BY INDEX_NAME
""")
rows = cur.fetchall()
print(f"Total unique MSCI indices: {len(rows)}")
print()
for r in rows[:100]:
    print(f"  {r[0]:60s}  code={r[1]}  variant={r[2]}  ccy={r[3]}")
if len(rows) > 100:
    print(f"  ... and {len(rows)-100} more")

# 2. Check common ETF benchmarks in FactSet
print()
print("=" * 80)
print("COMMON ETF BENCHMARKS (FactSet prices)")
print("=" * 80)
etfs = [
    ("SPY", "S&P 500"), ("QQQ", "NASDAQ 100"), ("DIA", "Dow Jones"),
    ("IWM", "Russell 2000"), ("IWB", "Russell 1000"), ("IWN", "Russell 2000 Value"),
    ("EFA", "MSCI EAFE"), ("EEM", "MSCI EM"), ("VGK", "FTSE Europe"),
    ("VWO", "FTSE EM"), ("ACWI", "MSCI ACWI"), ("VT", "Total World"),
    ("AGG", "US Agg Bond"), ("BND", "Total Bond"), ("TLT", "US 20Y+ Treasury"),
    ("LQD", "IG Corporate"), ("HYG", "HY Corporate"), ("EMB", "EM Bonds"),
    ("GLD", "Gold"), ("SLV", "Silver"), ("USO", "Crude Oil"),
    ("VNQ", "US REITs"), ("VNQI", "Intl REITs"),
    ("XLK", "Tech"), ("XLV", "Healthcare"), ("XLF", "Financials"),
    ("XLE", "Energy"), ("XLI", "Industrials"), ("XLP", "Cons Staples"),
    ("XLY", "Cons Disc"), ("XLB", "Materials"), ("XLU", "Utilities"),
    ("XLRE", "Real Estate"), ("XLC", "Comm Svcs"),
    ("ARKK", "ARK Innovation"), ("MTUM", "Momentum"), ("QUAL", "Quality"),
    ("VLUE", "Value"), ("SIZE", "Size"), ("USMV", "Min Vol"),
]
tickers = [e[0] for e in etfs]
ph = ",".join("'" + t + "-US'" for t in tickers)
cur.execute(f"""
    SELECT DISTINCT t.TICKER_REGION
    FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
    JOIN FACTSET.FP_V2.FP_BASIC_PRICES p ON t.FSYM_ID = p.FSYM_ID
    WHERE t.TICKER_REGION IN ({ph})
    AND p.P_DATE >= '2026-04-01'
""")
available = {r[0].replace("-US", "") for r in cur.fetchall()}
print()
for ticker, name in etfs:
    status = "✅" if ticker in available else "❌"
    print(f"  {status} {ticker:6s}  {name}")

# 3. MSCI index variant types
print()
print("=" * 80)
print("MSCI INDEX VARIANT TYPES")
print("=" * 80)
cur.execute("""
    SELECT DISTINCT INDEX_VARIANT_TYPE, COUNT(*) as cnt
    FROM MSCI.INDEX.INDEX_LEVELS
    WHERE CALC_DATE >= '2026-01-01'
    GROUP BY INDEX_VARIANT_TYPE
    ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]:30s}  ({r[1]} rows)")
