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

# 1) StreetAccount news - parse headline from XML
print("=== StreetAccount news mentioning Apple ===")
cur.execute("""
SELECT REPORT_ID, PUBLISH_TIME,
       XMLGET(PARSE_XML(RAW_XML), 'headline'):"$"::STRING as HEADLINE
FROM FACTSET.STREETACCOUNT.STREETACCOUNT
WHERE RAW_XML ILIKE '%Apple Inc%'
ORDER BY PUBLISH_TIME DESC
LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[1]}  |  {r[2][:120] if r[2] else 'no headline'}")

# 2) Transcripts for AAPL - need to check XML for ticker
print("\n=== Transcripts mentioning Apple ===")
cur.execute("""
SELECT ID, DATE, TRANSCRIPT_TYPE,
       XMLGET(PARSE_XML(RAW_XML), 'companyName'):"$"::STRING as COMPANY
FROM FACTSET.TRANSCRIPTS.TRANSCRIPTS
WHERE RAW_XML ILIKE '%Apple Inc%'
ORDER BY DATE DESC
LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[1]}  |  {r[2]}  |  {r[3][:80] if r[3] else 'no company'}")

# 3) SEC filings for Apple
print("\n=== SEC filings for Apple ===")
cur.execute("""
SELECT COMPANY_NAME, FILED_DATE, FORM_TYPE, ADSH
FROM SEC_FILINGS.CYBERSYN.SEC_REPORT_INDEX
WHERE COMPANY_NAME ILIKE '%Apple Inc%'
ORDER BY FILED_DATE DESC
LIMIT 15
""")
for r in cur.fetchall():
    print(f"  {r[1]}  |  {r[2]:10s}  |  {r[0][:40]}")

# 4) Check SEC_REPORT_TEXT_ATTRIBUTES for actual filing content
print("\n=== SEC_REPORT_TEXT_ATTRIBUTES columns ===")
cur.execute("SELECT * FROM SEC_FILINGS.CYBERSYN.SEC_REPORT_TEXT_ATTRIBUTES LIMIT 1")
print([d[0] for d in cur.description])
r = cur.fetchone()
if r:
    for i, d in enumerate(cur.description):
        val = str(r[i])[:150] if r[i] else 'NULL'
        print(f"  {d[0]}: {val}")

conn.close()
