from snowflake_data import _get_connection, SF_WAREHOUSE
conn = _get_connection()
cur = conn.cursor()
cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

# What variant types exist?
cur.execute("SELECT DISTINCT INDEX_VARIANT_TYPE FROM MSCI.INDEX.INDEX_LEVELS LIMIT 20")
print("Variant types:", [r[0] for r in cur.fetchall()])

# What currencies?
cur.execute("SELECT DISTINCT ISO_CURRENCY_SYMBOL FROM MSCI.INDEX.INDEX_LEVELS LIMIT 20")
print("Currencies:", [r[0] for r in cur.fetchall()])

# Latest date
cur.execute("SELECT MAX(CALC_DATE) FROM MSCI.INDEX.INDEX_LEVELS")
print("Latest date:", cur.fetchone()[0])

# Just get a sample of index names
cur.execute("""
    SELECT DISTINCT MSCI_INDEX_CODE, INDEX_NAME, INDEX_VARIANT_TYPE, ISO_CURRENCY_SYMBOL
    FROM MSCI.INDEX.INDEX_LEVELS
    WHERE CALC_DATE >= DATEADD(day, -5, CURRENT_DATE())
    ORDER BY INDEX_NAME
    LIMIT 50
""")
print(f"\n{'Code':>10}  {'Variant':<12} {'CCY':<5} {'Index Name'}")
print("-" * 90)
for r in cur.fetchall():
    print(f"{r[0]:>10}  {r[2]:<12} {r[3]:<5} {r[1]}")
