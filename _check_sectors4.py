import snowflake.connector
conn = snowflake.connector.connect(
    account='ja91996.west-europe.privatelink',
    user='RORY.MCMULLAN@MEDIOLANUM.IE',
    warehouse='PROD_EDW_LOAD',
    role='PROD_MED_BUSINESS_ANALYST',
    authenticator='externalbrowser'
)
cur = conn.cursor()
cur.execute("USE WAREHOUSE PROD_EDW_LOAD")

# Check FP_SEC_ENTITY columns
print("=== FP_SEC_ENTITY columns ===")
cur.execute("SELECT * FROM FACTSET.FP_V2.FP_SEC_ENTITY LIMIT 1")
print([d[0] for d in cur.description])
print(cur.fetchone())

# Check SYM_COVERAGE columns
print("\n=== SYM_COVERAGE columns ===")
cur.execute("SELECT * FROM FACTSET.SYM_V1.SYM_COVERAGE LIMIT 1")
print([d[0] for d in cur.description])

# Test the full join using FP_SEC_ENTITY
print("\n=== Consumer Staples via FP_SEC_ENTITY ===")
cur.execute("""
    SELECT DISTINCT tr.TICKER_REGION, sc.PROPER_NAME
    FROM FACTSET.SYM_V1.SYM_ENTITY_SECTOR es
    JOIN FACTSET.FP_V2.FP_SEC_ENTITY fse
        ON fse.FACTSET_ENTITY_ID = es.FACTSET_ENTITY_ID
    JOIN FACTSET.SYM_V1.SYM_COVERAGE sc
        ON sc.FSYM_PRIMARY_EQUITY_ID = fse.FSYM_ID
    JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr
        ON tr.FSYM_ID = sc.FSYM_ID
    WHERE es.SECTOR_CODE IN ('2400', '3250')
      AND sc.UNIVERSE_TYPE = 'EQ'
      AND tr.TICKER_REGION LIKE '%-US'
    LIMIT 10
""")
rows = cur.fetchall()
print(f"Got {len(rows)} rows")
for r in rows:
    print(f"  {r}")

conn.close()
print("\nDone.")
