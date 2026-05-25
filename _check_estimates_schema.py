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

print('=== FE_BASIC_CONH_QF columns ===')
cur.execute("SELECT * FROM FACTSET.FE_V4.FE_BASIC_CONH_QF LIMIT 1")
print([d[0] for d in cur.description])
print(cur.fetchone())

print('\n=== FE items for AAPL-US ===')
cur.execute("""
SELECT DISTINCT FE_ITEM
FROM FACTSET.FE_V4.FE_BASIC_CONH_QF q
JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr ON tr.FSYM_ID = q.FSYM_ID
WHERE tr.TICKER_REGION = 'AAPL-US'
ORDER BY FE_ITEM
LIMIT 100
""")
print([r[0] for r in cur.fetchall()])

print('\n=== Annual FE items for AAPL-US ===')
cur.execute("""
SELECT DISTINCT FE_ITEM
FROM FACTSET.FE_V4.FE_BASIC_CONH_AF a
JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr ON tr.FSYM_ID = a.FSYM_ID
WHERE tr.TICKER_REGION = 'AAPL-US'
ORDER BY FE_ITEM
LIMIT 100
""")
print([r[0] for r in cur.fetchall()])

conn.close()
