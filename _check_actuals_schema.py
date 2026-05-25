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

for table in ['FE_BASIC_ACT_QF', 'FE_BASIC_ACT_AF']:
    print(f'=== {table} columns ===')
    cur.execute(f"SELECT * FROM FACTSET.FE_V4.{table} LIMIT 1")
    print([d[0] for d in cur.description])
    print(cur.fetchone())

print('\n=== AAPL items in actual quarter table ===')
cur.execute("""
SELECT DISTINCT FE_ITEM
FROM FACTSET.FE_V4.FE_BASIC_ACT_QF q
JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr ON tr.FSYM_ID = q.FSYM_ID
WHERE tr.TICKER_REGION = 'AAPL-US'
ORDER BY FE_ITEM
""")
print([r[0] for r in cur.fetchall()])

print('\n=== AAPL items in actual annual table ===')
cur.execute("""
SELECT DISTINCT FE_ITEM
FROM FACTSET.FE_V4.FE_BASIC_ACT_AF a
JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr ON tr.FSYM_ID = a.FSYM_ID
WHERE tr.TICKER_REGION = 'AAPL-US'
ORDER BY FE_ITEM
""")
print([r[0] for r in cur.fetchall()])

conn.close()
