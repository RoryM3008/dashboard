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

# Verify the working join path
print("=== SYM_ENTITY columns ===")
cur.execute("SELECT * FROM FACTSET.SYM_V1.SYM_ENTITY LIMIT 1")
print([d[0] for d in cur.description])

print("\n=== Test: Consumer Staples via SYM_ENTITY ===")
cur.execute("""
    SELECT DISTINCT tr.TICKER_REGION, sc.PROPER_NAME
    FROM FACTSET.SYM_V1.SYM_ENTITY_SECTOR es
    JOIN FACTSET.SYM_V1.SYM_ENTITY ent
        ON ent.FACTSET_ENTITY_ID = es.FACTSET_ENTITY_ID
    JOIN FACTSET.SYM_V1.SYM_COVERAGE sc
        ON sc.PROPER_NAME = ent.ENTITY_PROPER_NAME
        AND sc.UNIVERSE_TYPE = 'EQ'
    JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr
        ON tr.FSYM_ID = sc.FSYM_ID
    WHERE es.SECTOR_CODE IN ('2400', '3250')
      AND tr.TICKER_REGION LIKE '%-US'
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r}")

# Simpler approach - use SYM_ENTITY directly  
print("\n=== SYM_ENTITY join approach ===")
cur.execute("""
    SELECT ent.FACTSET_ENTITY_ID, ent.ENTITY_PROPER_NAME,
           sc.FSYM_ID, sc.FSYM_PRIMARY_EQUITY_ID
    FROM FACTSET.SYM_V1.SYM_ENTITY ent
    JOIN FACTSET.SYM_V1.SYM_COVERAGE sc
        ON sc.FSYM_ID = ent.ENTITY_PROPER_NAME  -- wrong, just checking columns
    LIMIT 1
""")
# That won't work, just checking SYM_ENTITY columns
cur.execute("SELECT * FROM FACTSET.SYM_V1.SYM_ENTITY LIMIT 1")
print("SYM_ENTITY cols:", [d[0] for d in cur.description])
row = cur.fetchone()
print("Sample:", row)

# The real fix - use SYM_ENTITY to get FSYM_ID then join to coverage
cur.execute("""
    SELECT DISTINCT tr.TICKER_REGION, sc.PROPER_NAME
    FROM FACTSET.SYM_V1.SYM_ENTITY_SECTOR es
    JOIN FACTSET.SYM_V1.SYM_ENTITY ent
        ON ent.FACTSET_ENTITY_ID = es.FACTSET_ENTITY_ID
    JOIN FACTSET.SYM_V1.SYM_COVERAGE sc
        ON sc.FSYM_PRIMARY_EQUITY_ID = ent.FSYM_PRIMARY_EQUITY_ID
    JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr
        ON tr.FSYM_ID = sc.FSYM_ID
    WHERE es.SECTOR_CODE IN ('2400', '3250')
      AND sc.UNIVERSE_TYPE = 'EQ'
      AND tr.TICKER_REGION LIKE '%-US'
    LIMIT 10
""")
print("\n=== Consumer Staples via SYM_ENTITY.FSYM_PRIMARY_EQUITY_ID ===")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
