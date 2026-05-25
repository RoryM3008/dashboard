from snowflake_data import _get_connection, SF_WAREHOUSE
conn = _get_connection()
cur = conn.cursor()
cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

# Search for MSCI indices
searches = ['%MSCI%USA%', '%MSCI%WORLD%', '%MSCI%EUROPE%', '%MSCI%EMERG%',
            '%MSCI%ACWI%', '%MSCI%EAFE%', '%MSCI%JAPAN%', '%MSCI%UK%',
            '%S&P 500%INDEX%', '%STOXX%600%', '%FTSE%100%', '%EURO STOXX%']

for s in searches:
    cur.execute(f"""
        SELECT t.TICKER_REGION, s.PROPER_NAME,
               (SELECT COUNT(*) FROM FACTSET.FP_V2.FP_BASIC_PRICES p WHERE p.FSYM_ID = t.FSYM_ID) as CNT
        FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
        JOIN FACTSET.SYM_V1.SYM_COVERAGE s ON t.FSYM_ID = s.FSYM_ID
        WHERE UPPER(s.PROPER_NAME) LIKE '{s}'
        ORDER BY CNT DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"{r[0]:<20} {r[2]:>6} prices  {r[1]}")
        print()

# Also check MSCI database directly
print("=== MSCI INDEX SCHEMAS ===")
cur.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM MSCI.INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA LIKE '%INDEX%' LIMIT 20")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}")

# Check if there's index return data
print("\n=== MSCI INDEX tables ===")
cur.execute("SELECT TABLE_NAME FROM MSCI.INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = 'INDEX' AND (TABLE_NAME LIKE '%RETURN%' OR TABLE_NAME LIKE '%PRICE%' OR TABLE_NAME LIKE '%PERF%' OR TABLE_NAME LIKE '%LEVEL%') LIMIT 20")
for r in cur.fetchall():
    print(f"  {r[0]}")
