"""
Snowflake / FactSet data layer
================================
Drop-in replacements for yfinance price-fetching functions, pulling from
FactSet tables in Snowflake instead.

FactSet tables used
-------------------
- FACTSET.SYM_V1.SYM_TICKER_REGION   — maps TICKER_REGION → FSYM_ID
- FACTSET.FP_V2.FP_BASIC_PRICES      — daily OHLCV prices keyed by FSYM_ID

Ticker convention
-----------------
The dashboard uses Yahoo-style tickers (AAPL, MSFT, ^GSPC).
FactSet uses TICKER_REGION format  (AAPL-US, MSFT-US).
This module handles the mapping automatically.

Connection
----------
Uses SSO (externalbrowser) so a browser popup appears on first query.
The connection is cached for the session to avoid repeated logins.
"""

import datetime
import pandas as pd
import numpy as np
import logging

log = logging.getLogger(__name__)

# ── Snowflake connection parameters ──────────────────────────────────────────
SF_ACCOUNT   = "ja91996.west-europe.privatelink"
SF_USER      = "RORY.MCMULLAN@MEDIOLANUM.IE"
SF_WAREHOUSE = "PROD_EDW_LOAD"
SF_ROLE      = "PROD_MED_BUSINESS_ANALYST"

# Module-level cached connection
_conn = None

# Set to True once a successful Snowflake connection is established.
# Checked by the dashboard to decide whether SF-only pages are available.
SF_AVAILABLE: bool = False


def _get_connection():
    """Return a cached Snowflake connection (SSO login once per session)."""
    global _conn, SF_AVAILABLE
    if _conn is not None:
        try:
            _conn.cursor().execute("SELECT 1")
            return _conn
        except Exception:
            _conn = None

    import snowflake.connector
    _conn = snowflake.connector.connect(
        account=SF_ACCOUNT,
        user=SF_USER,
        warehouse=SF_WAREHOUSE,
        role=SF_ROLE,
        authenticator="externalbrowser",
    )
    SF_AVAILABLE = True
    log.info("Snowflake connection established (SSO)")
    return _conn


# ── Ticker mapping ───────────────────────────────────────────────────────────

# Yahoo tickers that don't follow the simple TICKER-US convention
_TICKER_MAP = {
    # Indices — FactSet uses different identifiers
    "^GSPC":   "SP50",       # S&P 500
    "^DJI":    "DJIA",       # Dow Jones
    "^IXIC":   "COMP",       # NASDAQ Composite
    "^FTSE":   "FTSE100",    # FTSE 100
    "^STOXX50E": "SX5E",     # Euro Stoxx 50
    "^VIX":    "VIX",
    # Special tickers with dashes that are NOT region suffixes
    "BRK-B":   "BRK.B-US",
    "BF-B":    "BF.B-US",
    "BT.A-GB": "BT.A-GB",
}

# Default region suffix if none specified
_DEFAULT_REGION = "US"

# ── FactSet sector code mapping to SPDR/GICS sector names ───────────────────
# FactSet codes from FACTSET_SECTOR_MAP, grouped to match SPDR ETF sectors
SECTOR_CODE_MAP = {
    "Technology":        ["1300", "3300"],   # Electronic Technology + Technology Services
    "Healthcare":        ["2300", "3350"],   # Health Technology + Health Services
    "Financials":        ["4800"],           # Finance
    "Energy":            ["2100"],           # Energy Minerals
    "Consumer Disc.":    ["1400", "3400", "3500"],  # Consumer Durables + Consumer Services + Retail Trade
    "Consumer Staples":  ["2400", "3250"],   # Consumer Non-Durables + Distribution Services
    "Industrials":       ["1200", "3100", "4600"],  # Producer Manufacturing + Industrial Services + Transportation
    "Materials":         ["1100", "2200"],   # Non-Energy Minerals + Process Industries
    "Utilities":         ["4700"],           # Utilities
    "Real Estate":       ["6000"],           # Miscellaneous (closest proxy)
    "Comm. Services":    ["4900"],           # Communications
}


def search_tickers(query, limit=15):
    """Search for tickers/company names matching a query string.

    Returns list of dicts: {ticker, name, exchange, region}.
    """
    if not query or len(query) < 2:
        return []
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    safe_q = query.replace("'", "''").upper()
    cur.execute(f"""
        SELECT tr.TICKER_REGION, sc.PROPER_NAME,
               sc.FREF_LISTING_EXCHANGE, sc.UNIVERSE_TYPE
        FROM FACTSET.SYM_V1.SYM_TICKER_REGION tr
        JOIN FACTSET.SYM_V1.SYM_COVERAGE sc ON tr.FSYM_ID = sc.FSYM_ID
        WHERE sc.UNIVERSE_TYPE = 'EQ'
          AND sc.REGIONAL_FLAG = TRUE
          AND sc.FREF_SECURITY_TYPE NOT IN ('WARRANT','STRUCT','MF_O','MF_C','ETF_ETF','ETF_UVI','ETF_NAV','RIGHT','UNIT','TEMP')
          AND (UPPER(tr.TICKER_REGION) LIKE '%{safe_q}%'
               OR UPPER(sc.PROPER_NAME) LIKE '%{safe_q}%')
        ORDER BY CASE WHEN UPPER(tr.TICKER_REGION) LIKE '{safe_q}%' THEN 0
                      WHEN UPPER(sc.PROPER_NAME) LIKE '{safe_q}%' THEN 1
                      ELSE 2 END,
                 sc.PROPER_NAME
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    results = []
    for r in rows:
        tr = r[0]  # e.g. "AAPL-US"
        ticker = tr.split("-")[0] if "-" in tr else tr
        region = tr.split("-")[1] if "-" in tr else ""
        results.append({
            "ticker": ticker,
            "ticker_region": tr,
            "name": r[1] or "",
            "exchange": r[2] or "",
            "region": region,
        })
    return results


def _to_factset_ticker(yahoo_ticker: str) -> str:
    """Convert a Yahoo-style ticker to FactSet TICKER_REGION format.

    Yahoo uses dot-suffixes for exchanges (e.g. CSPX.L = London, DSY.PA = Paris).
    FactSet uses hyphen-region (e.g. CSPX-GB, DSY-FR).
    """
    t = yahoo_ticker.strip().upper()
    if t in _TICKER_MAP:
        return _TICKER_MAP[t]
    # Already has a FactSet region suffix like "VOD-GB"?
    if "-" in t:
        return t
    # Handle Yahoo exchange dot-suffixes → FactSet region codes
    _YAHOO_EXCHANGE_MAP = {
        ".L":   "GB",   # London Stock Exchange
        ".PA":  "FR",   # Euronext Paris
        ".DE":  "DE",   # Frankfurt / XETRA
        ".AS":  "NL",   # Euronext Amsterdam
        ".MC":  "ES",   # Bolsa Madrid
        ".MI":  "IT",   # Borsa Italiana
        ".BR":  "BE",   # Euronext Brussels
        ".SW":  "CH",   # SIX Swiss Exchange
        ".HK":  "HK",   # Hong Kong
        ".T":   "JP",   # Tokyo
        ".AX":  "AU",   # ASX Australia
        ".TO":  "CA",   # Toronto
        ".V":   "CA",   # TSX Venture
        ".SI":  "SG",   # Singapore
        ".KS":  "KR",   # Korea
        ".SS":  "CN",   # Shanghai
        ".SZ":  "CN",   # Shenzhen
    }
    for suffix, region in _YAHOO_EXCHANGE_MAP.items():
        if t.endswith(suffix):
            base = t[: -len(suffix)]
            return f"{base}-{region}"
    return f"{t}-{_DEFAULT_REGION}"


def _from_factset_ticker(fs_ticker: str, original: str) -> str:
    """Convert back from FactSet TICKER_REGION to the original Yahoo label."""
    # If we have a reverse mapping, use it
    for yahoo, fs in _TICKER_MAP.items():
        if fs == fs_ticker:
            return yahoo
    return original


def fetch_msci_constituents(msci_code, gics_sector=None):
    """
    Fetch current constituents of an MSCI index by numeric code.
    Returns a list of FactSet-style TICKER_REGION strings (e.g. 'AAPL-US').

    Parameters
    ----------
    msci_code : int
        MSCI index code (e.g. 990100 for MSCI World).
    gics_sector : int or None
        If provided, filter constituents to this GICS sector code
        (e.g. 30 = Consumer Staples). Used for sector indices that are not
        stored as separate codes in the database.
    """
    sector_filter = ""
    if gics_sector is not None:
        sector_filter = f"AND sec.SECTOR = {int(gics_sector)}"

    sql = f"""
    SELECT DISTINCT tr.TICKER_REGION
    FROM MSCI.INDEX.INDEX_CONSTITUENTS ic
    JOIN MSCI.INDEX.SECURITY sec
        ON sec.MSCI_SECURITY_CODE = ic.MSCI_SECURITY_CODE
        AND sec.CALC_DATE = ic.CALC_DATE
    JOIN FACTSET.SYM_V1.SYM_ISIN si ON si.ISIN = sec.ISIN
    JOIN FACTSET.SYM_V1.SYM_COVERAGE cov
        ON cov.FSYM_SECURITY_ID = si.FSYM_ID
        AND cov.SECURITY_FLAG = TRUE
    JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr ON tr.FSYM_ID = cov.FSYM_REGIONAL_ID
    WHERE ic.MSCI_INDEX_CODE = {int(msci_code)}
      AND ic.CALC_DATE = (
          SELECT MAX(CALC_DATE)
          FROM MSCI.INDEX.INDEX_CONSTITUENTS
          WHERE MSCI_INDEX_CODE = {int(msci_code)}
      )
      AND sec.ISIN IS NOT NULL
      AND tr.TICKER_REGION IS NOT NULL
      AND cov.FSYM_REGIONAL_ID IS NOT NULL
      {sector_filter}
    ORDER BY tr.TICKER_REGION
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
        cur.execute(sql)
        rows = cur.fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception:
        return []


# ── MSCI index helpers ────────────────────────────────────────────────────────

def download_msci_index(code, start=None, end=None, period=None,
                        variant="STRD", currency="USD"):
    """
    Download MSCI index level history from Snowflake.

    Parameters
    ----------
    code : int or str
        MSCI numeric index code, e.g. 990200 for North America.
    start, end, period : same semantics as download_prices.
    variant : str
        INDEX_VARIANT_TYPE: 'STRD' (price), 'NETR' (net TR), 'GRTR' (gross TR).
    currency : str
        ISO currency for the level, default 'USD'.

    Returns
    -------
    pd.Series
        Index = datetime dates, values = index level, name = index name.
    """
    if start is None and period:
        start = _period_to_start(period)
    elif start is None:
        start = _period_to_start("1y")
    if end is None:
        end = datetime.date.today()
    if isinstance(start, str):
        start = pd.Timestamp(start).date()
    if isinstance(end, str):
        end = pd.Timestamp(end).date()

    sql = f"""
    SELECT CALC_DATE, INDEX_NAME, LEVEL
    FROM MSCI.INDEX.INDEX_LEVELS
    WHERE MSCI_INDEX_CODE = {int(code)}
      AND INDEX_VARIANT_TYPE = '{variant}'
      AND ISO_CURRENCY_SYMBOL = '{currency}'
      AND LEVEL IS NOT NULL
      AND CALC_DATE BETWEEN '{start}' AND '{end}'
    ORDER BY CALC_DATE
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(sql)
    rows = cur.fetchall()
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows, columns=["date", "name", "level"])
    name = df["name"].iloc[0]
    s = pd.Series(df["level"].astype(float).values,
                  index=pd.to_datetime(df["date"]),
                  name=f"MSCI {name}")
    return s


# ── Core price functions ─────────────────────────────────────────────────────

def download_prices(tickers, start=None, end=None, period=None):
    """
    Download daily close prices from FactSet via Snowflake.

    Parameters
    ----------
    tickers : list[str]
        Yahoo-style tickers, e.g. ["AAPL", "MSFT"]
    start : str or datetime, optional
        Start date. If None, uses `period`.
    end : str or datetime, optional
        End date. Defaults to today.
    period : str, optional
        yfinance-style period string: "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"

    Returns
    -------
    pd.DataFrame
        Columns = ticker names, index = dates, values = closing prices.
    """
    if not tickers:
        return pd.DataFrame()

    # Resolve period → start date
    if start is None and period:
        start = _period_to_start(period)
    elif start is None:
        start = _period_to_start("1y")

    if end is None:
        end = datetime.date.today()

    if isinstance(start, str):
        start = pd.Timestamp(start).date()
    if isinstance(end, str):
        end = pd.Timestamp(end).date()

    # Build FactSet ticker list
    fs_tickers = [_to_factset_ticker(t) for t in tickers]
    ticker_lookup = dict(zip(fs_tickers, tickers))  # FactSet → Yahoo label

    placeholders = ", ".join(f"'{t}'" for t in fs_tickers)

    sql = f"""
    SELECT
        p.P_DATE,
        t.TICKER_REGION,
        p.P_PRICE
    FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
    JOIN FACTSET.FP_V2.FP_BASIC_PRICES p
        ON t.FSYM_ID = p.FSYM_ID
    WHERE t.TICKER_REGION IN ({placeholders})
      AND p.P_DATE BETWEEN '{start}' AND '{end}'
    ORDER BY p.P_DATE
    """

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)

    if df.empty:
        return pd.DataFrame(columns=tickers)

    # Pivot: rows=date, cols=ticker
    df["P_DATE"] = pd.to_datetime(df["P_DATE"])
    # Map FactSet tickers back to Yahoo labels
    df["LABEL"] = df["TICKER_REGION"].map(ticker_lookup)
    result = df.pivot(index="P_DATE", columns="LABEL", values="P_PRICE")
    result.index.name = "Date"
    result = result.sort_index()

    # Ensure column order matches input
    result = result.reindex(columns=[t for t in tickers if t in result.columns])
    return result


def download_ohlcv(ticker, start=None, end=None, period=None):
    """
    Download daily OHLCV data for a single ticker.

    Returns
    -------
    pd.DataFrame with columns: Open, High, Low, Close, Volume
    """
    t = ticker.strip().upper()
    fs_ticker = _to_factset_ticker(t)

    if start is None and period:
        start = _period_to_start(period)
    elif start is None:
        start = _period_to_start("6mo")
    if end is None:
        end = datetime.date.today()
    if isinstance(start, str):
        start = pd.Timestamp(start).date()
    if isinstance(end, str):
        end = pd.Timestamp(end).date()

    sql = f"""
    SELECT
        p.P_DATE  AS "Date",
        p.P_PRICE_OPEN  AS "Open",
        p.P_PRICE_HIGH  AS "High",
        p.P_PRICE_LOW   AS "Low",
        p.P_PRICE       AS "Close",
        p.P_VOLUME      AS "Volume"
    FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
    JOIN FACTSET.FP_V2.FP_BASIC_PRICES p
        ON t.FSYM_ID = p.FSYM_ID
    WHERE t.TICKER_REGION = '{fs_ticker}'
      AND p.P_DATE BETWEEN '{start}' AND '{end}'
    ORDER BY p.P_DATE
    """

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)

    if df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


def fetch_last_price(ticker):
    """Return the most recent closing price for a ticker."""
    fs_ticker = _to_factset_ticker(ticker.strip().upper())

    sql = f"""
    SELECT p.P_PRICE
    FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
    JOIN FACTSET.FP_V2.FP_BASIC_PRICES p
        ON t.FSYM_ID = p.FSYM_ID
    WHERE t.TICKER_REGION = '{fs_ticker}'
    ORDER BY p.P_DATE DESC
    LIMIT 1
    """

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    row = cur.fetchone()
    return float(row[0]) if row else None


def fetch_last_n_prices(ticker, n=10):
    """Return the last N closing prices as a DataFrame (Date, Close)."""
    fs_ticker = _to_factset_ticker(ticker.strip().upper())

    sql = f"""
    SELECT p.P_DATE AS "Date", p.P_PRICE AS "Close"
    FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
    JOIN FACTSET.FP_V2.FP_BASIC_PRICES p
        ON t.FSYM_ID = p.FSYM_ID
    WHERE t.TICKER_REGION = '{fs_ticker}'
    ORDER BY p.P_DATE DESC
    LIMIT {n}
    """

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").set_index("Date")
    return df


# ── Helpers ──────────────────────────────────────────────────────────────────

def _period_to_start(period: str) -> datetime.date:
    """Convert a yfinance-style period string to a start date."""
    today = datetime.date.today()
    mapping = {
        "1d":  1,
        "5d":  5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 182,
        "1y":  365,
        "2y":  730,
        "5y":  1826,
        "10y": 3652,
        "max": 365 * 30,
    }
    days = mapping.get(period, 365)
    return today - datetime.timedelta(days=days)


# ── Single Stock Analysis functions ──────────────────────────────────────────

def _resolve_ids(ticker):
    """Resolve ticker to FSYM_ID (regional), FSYM_SECURITY_ID (-S), and FACTSET_ENTITY_ID.

    Returns dict with keys: fsym_id, security_id, entity_id, name, currency, exchange, country.
    """
    fs_ticker = _to_factset_ticker(ticker)
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    # Get FSYM_ID and coverage info
    cur.execute(f"""
        SELECT FSYM_ID, CURRENCY, PROPER_NAME, FSYM_PRIMARY_EQUITY_ID,
               FREF_LISTING_EXCHANGE, UNIVERSE_TYPE
        FROM FACTSET.SYM_V1.SYM_COVERAGE
        WHERE FSYM_ID = (
            SELECT FSYM_ID FROM FACTSET.SYM_V1.SYM_TICKER_REGION
            WHERE TICKER_REGION = '{fs_ticker}'
        )
    """)
    row = cur.fetchone()
    if not row:
        return None

    fsym_id, currency, name, sec_id, exchange, _ = row

    # Get entity ID via security ID
    entity_id = None
    country = None
    if sec_id:
        cur.execute(f"SELECT FACTSET_ENTITY_ID FROM FACTSET.FP_V2.FP_SEC_ENTITY WHERE FSYM_ID = '{sec_id}'")
        ent_row = cur.fetchone()
        if ent_row:
            entity_id = ent_row[0]
            cur.execute(f"SELECT ISO_COUNTRY FROM FACTSET.SYM_V1.SYM_ENTITY WHERE FACTSET_ENTITY_ID = '{entity_id}'")
            c_row = cur.fetchone()
            if c_row:
                country = c_row[0]

    return {
        "fsym_id": fsym_id,
        "security_id": sec_id,
        "entity_id": entity_id,
        "name": name,
        "currency": currency,
        "exchange": exchange,
        "country": country,
    }


def fetch_company_profile(entity_id):
    """Return company description, sector, industry for an entity."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    profile = {}

    # Description
    cur.execute(f"""
        SELECT ENTITY_PROFILE FROM FACTSET.FF_V3.FF_ENTITY_PROFILES
        WHERE FACTSET_ENTITY_ID = '{entity_id}' AND ENTITY_PROFILE_TYPE = 'PRD'
    """)
    row = cur.fetchone()
    profile["description"] = row[0] if row else "N/A"

    # Sector codes
    cur.execute(f"""
        SELECT SECTOR_CODE, INDUSTRY_CODE, PRIMARY_SIC_CODE
        FROM FACTSET.SYM_V1.SYM_ENTITY_SECTOR
        WHERE FACTSET_ENTITY_ID = '{entity_id}'
    """)
    row = cur.fetchone()
    if row:
        profile["sector_code"] = row[0]
        profile["industry_code"] = row[1]
        profile["sic_code"] = row[2]
    else:
        profile["sector_code"] = profile["industry_code"] = profile["sic_code"] = None

    # Resolve sector/industry names from REF_V2
    if profile.get("sector_code"):
        cur.execute(f"""
            SELECT FACTSET_SECTOR_DESC FROM FACTSET.REF_V2.FACTSET_SECTOR_MAP
            WHERE FACTSET_SECTOR_CODE = '{profile["sector_code"]}'
        """)
        row = cur.fetchone()
        profile["sector"] = row[0] if row else profile["sector_code"]

        cur.execute(f"""
            SELECT FACTSET_INDUSTRY_DESC FROM FACTSET.REF_V2.FACTSET_INDUSTRY_MAP
            WHERE FACTSET_INDUSTRY_CODE = '{profile["industry_code"]}'
        """)
        row = cur.fetchone()
        profile["industry"] = row[0] if row else profile["industry_code"]
    else:
        profile["sector"] = "N/A"
        profile["industry"] = "N/A"

    return profile


def fetch_key_ratios(fsym_id):
    """Return latest LTM financial ratios as a dict."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    cur.execute(f"""
        SELECT DATE, FF_PE, FF_MKT_VAL, FF_GROSS_MGN, FF_NET_MGN, FF_OPER_MGN,
               FF_EPS_DIL, FF_EBITDA_OPER, FF_FREE_CF_FCFE, FF_PAY_OUT_RATIO,
               FF_PSALES, FF_PCF
        FROM FACTSET.FF_V3.FF_BASIC_DER_LTM
        WHERE FSYM_ID = '{fsym_id}'
        ORDER BY DATE DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        return {}

    result = {
        "date": row[0],
        "pe": row[1],
        "mkt_cap": row[2],
        "gross_margin": row[3],
        "net_margin": row[4],
        "oper_margin": row[5],
        "eps_diluted": row[6],
        "ebitda": row[7],
        "free_cf": row[8],
        "payout_ratio": row[9],
        "ps": row[10],
        "pcf": row[11],
    }

    # ── Fallback for market cap: try QTR table ─────────────────────────
    if not result.get("mkt_cap"):
        try:
            cur.execute(f"""
                SELECT FF_MKT_VAL
                FROM FACTSET.FF_V3.FF_BASIC_DER_QTR
                WHERE FSYM_ID = '{fsym_id}' AND FF_MKT_VAL IS NOT NULL AND FF_MKT_VAL > 0
                ORDER BY DATE DESC LIMIT 1
            """)
            qtr = cur.fetchone()
            if qtr and qtr[0]:
                result["mkt_cap"] = qtr[0]
        except Exception:
            pass

    # ── Fallback for FCF: try QTR table ────────────────────────────────
    if not result.get("free_cf"):
        try:
            cur.execute(f"""
                SELECT FF_FREE_CF_FCFE
                FROM FACTSET.FF_V3.FF_BASIC_DER_QTR
                WHERE FSYM_ID = '{fsym_id}' AND FF_FREE_CF_FCFE IS NOT NULL AND FF_FREE_CF_FCFE != 0
                ORDER BY DATE DESC LIMIT 1
            """)
            qtr = cur.fetchone()
            if qtr and qtr[0]:
                result["free_cf"] = qtr[0]
        except Exception:
            pass

    return result


def fetch_ratio_history(fsym_id):
    """Return quarterly LTM ratios going back 3 years as a DataFrame."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(f"""
        SELECT DATE, FF_PE, FF_MKT_VAL, FF_GROSS_MGN, FF_NET_MGN, FF_OPER_MGN,
               FF_EPS_DIL, FF_EBITDA_OPER, FF_FREE_CF_FCFE, FF_PSALES, FF_PCF
        FROM FACTSET.FF_V3.FF_BASIC_DER_LTM
        WHERE FSYM_ID = '{fsym_id}'
          AND DATE >= DATEADD(year, -3, CURRENT_DATE())
        ORDER BY DATE DESC
    """)
    rows = cur.fetchall()
    cols = ["Date", "P/E", "Mkt Cap (M)", "Gross Mgn %", "Net Mgn %", "Oper Mgn %",
            "EPS (Dil)", "EBITDA (M)", "FCF (M)", "P/Sales", "P/CF"]
    return pd.DataFrame(rows, columns=cols)


def fetch_valuation_history(fsym_id, years=10):
    """Return LTM valuation metrics as a DataFrame indexed by date.

    Pulls from both FF_BASIC_DER_LTM (core multiples + margins) and
    FF_ADVANCED_DER_LTM (yields, growth, advanced margins) joined on DATE.
    All columns confirmed present via INFORMATION_SCHEMA catalog query.
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    since = f"DATEADD(year, -{int(years)}, CURRENT_DATE())"

    sql = f"""
        SELECT
            b.DATE,
            -- Valuation multiples
            b.FF_PE           AS "P/E",
            b.FF_PSALES       AS "P/S",
            -- NOTE: FF_*_DER_LTM tables used here do not expose enterprise value
            -- or net debt fields, so EV-based ratios are approximated using market
            -- value as denominator/numerator proxy for historical continuity.
            b.FF_PSALES       AS "EV/S",
            CASE WHEN b.FF_EBITDA_OPER <> 0
                 THEN b.FF_MKT_VAL / b.FF_EBITDA_OPER
            END               AS "EV/EBITDA",
            CASE WHEN b.FF_EBIT_OPER <> 0
                 THEN b.FF_MKT_VAL / b.FF_EBIT_OPER
            END               AS "EV/EBIT",
            b.FF_PCF          AS "P/CF",
            b.FF_PAY_OUT_RATIO AS "Payout Ratio %",
            -- Margin metrics (LTM)
            b.FF_GROSS_MGN    AS "Gross Margin %",
            b.FF_OPER_MGN     AS "Oper Margin %",
            b.FF_NET_MGN      AS "Net Margin %",
            b.FF_PTX_MGN      AS "PreTax Margin %",
            -- Advanced metrics (joined from ADVANCED_DER_LTM)
            a.FF_DIV_YLD          AS "Div Yield %",
            a.FF_FCF_YLD          AS "FCF Yield %",
            a.FF_EBITDA_OPER_MGN  AS "EBITDA Margin %",
            a.FF_EBIT_OPER_MGN    AS "EBIT Margin %",
            a.FF_SGA_SALES        AS "SGA % Sales",
            a.FF_RD_SALES         AS "RD % Sales",
            a.FF_SALES_GR         AS "Sales Growth %",
            a.FF_OPER_INC_GR      AS "Oper Inc Growth %",
            a.FF_NET_INC_BEF_XORD_GR AS "Net Inc Growth %",
            a.FF_EPS_BASIC_GR     AS "EPS Growth %",
            a.FF_DPS_GR           AS "DPS Growth %",
            b.FF_CAPEX_SALES      AS "Capex % Sales",
            a.FF_CF_SALES         AS "CF % Sales",
            a.FF_TAX_RATE         AS "Tax Rate %",
            CASE WHEN b.FF_MKT_VAL <> 0
                 THEN b.FF_OPER_CF / b.FF_MKT_VAL * 100
            END               AS "CFO/EV %",
            CASE WHEN b.FF_MKT_VAL <> 0
                 THEN (b.FF_OPER_CF - ABS(b.FF_CAPEX)) / b.FF_MKT_VAL * 100
            END               AS "FCFF/EV %"
        FROM FACTSET.FF_V3.FF_BASIC_DER_LTM b
        LEFT JOIN FACTSET.FF_V3.FF_ADVANCED_DER_LTM a
            ON b.FSYM_ID = a.FSYM_ID AND b.DATE = a.DATE
        WHERE b.FSYM_ID = '{fsym_id}'
          AND b.DATE >= {since}
          AND b.DATE <= CURRENT_DATE()
        ORDER BY b.DATE ASC
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.set_index("DATE")
    df.index.name = "Date"
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def fetch_annual_margins(fsym_id, years=25):
    """Return annual metrics from FF_BASIC_DER_AF joined with FF_ADVANCED_DER_AF
    and FF_BASIC_AF (fiscal year end rows).

    Includes: margins, SG&A % Sales, FCF margin (computed), returns,
    leverage ratios, P/Book. Also aliased as fetch_annual_metrics.
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    since = f"DATEADD(year, -{int(years)}, CURRENT_DATE())"

    cur.execute(f"""
        SELECT
            b.DATE,
            b.FF_FYR                                           AS "FY",
            b.FF_GROSS_MGN                                    AS "Gross Margin %",
            a.FF_SGA_SALES                                    AS "SGA % Sales",
            b.FF_OPER_MGN                                     AS "Oper Margin %",
            b.FF_PTX_MGN                                      AS "PreTax Margin %",
            b.FF_NET_MGN                                      AS "Net Margin %",
            CASE WHEN bas.FF_SALES <> 0
                 THEN (b.FF_OPER_CF - ABS(b.FF_CAPEX)) / bas.FF_SALES * 100
            END                                               AS "FCF Margin %",
            b.FF_ROE                                          AS "ROE %",
            b.FF_ROA                                          AS "ROA %",
            b.FF_ROTC                                         AS "ROTC %",
            b.FF_PBK                                          AS "P/Book",
            b.FF_DEBT_EBITDA_OPER                             AS "Net Debt/EBITDA",
            b.FF_DEBT_ASSETS                                  AS "Debt/Assets %",
            b.FF_CURR_RATIO                                   AS "Current Ratio",
            b.FF_QUICK_RATIO                                  AS "Quick Ratio"
        FROM FACTSET.FF_V3.FF_BASIC_DER_AF b
        JOIN FACTSET.FF_V3.FF_ADVANCED_DER_AF a
            ON b.FSYM_ID = a.FSYM_ID AND b.DATE = a.DATE
        JOIN FACTSET.FF_V3.FF_BASIC_AF bas
            ON b.FSYM_ID = bas.FSYM_ID AND b.DATE = bas.DATE
        WHERE b.FSYM_ID = '{fsym_id}'
          AND b.DATE >= {since}
          AND b.DATE <= CURRENT_DATE()
        ORDER BY b.DATE ASC
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["DATE"] = pd.to_datetime(df["DATE"])
        df = df.set_index("DATE")
        df.index.name = "Date"
        for c in df.columns:
            if c != "FY":
                df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# Alias
fetch_annual_metrics = fetch_annual_margins


def fetch_annual_fundamentals(fsym_id, year_from=2000, year_to=None):
    """Comprehensive annual fundamental analysis — full CTE covering:
    Profitability, Valuation, Per Share, Asset Analysis, DuPont,
    Operating Efficiency, Liquidity, Coverage, Leverage.

    Source tables: FF_BASIC_AF, FF_BASIC_DER_AF, FF_ADVANCED_DER_AF, FF_ADVANCED_AF
    Returns a DataFrame indexed by PERIOD_END_DATE with FISCAL_YEAR as a column.
    """
    import datetime
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    if year_to is None:
        year_to = datetime.date.today().year

    sql = f"""
    WITH base AS (
        SELECT
            b.FSYM_ID,
            b.FF_FYR                                              AS FISCAL_YEAR,
            b.DATE                                                AS PERIOD_END_DATE,
            b.CURRENCY,

            -- PROFITABILITY
            bd.FF_GROSS_MGN                                       AS GROSS_MARGIN,
            ad.FF_SGA_SALES                                       AS SGA_TO_SALES,
            bd.FF_OPER_MGN                                        AS OPERATING_MARGIN,
            bd.FF_PTX_MGN                                         AS PRETAX_MARGIN,
            bd.FF_NET_MGN                                         AS NET_MARGIN,
            CASE WHEN b.FF_SALES <> 0
                 THEN (bd.FF_OPER_CF - ABS(bd.FF_CAPEX)) / b.FF_SALES * 100
            END                                                   AS FREE_CASH_FLOW_MARGIN,
            CASE WHEN bd.FF_NET_INC <> 0
                 THEN bd.FF_FREE_CF_FCFE / bd.FF_NET_INC
            END                                                   AS FCF_CONVERSION_RATIO,
            bd.FF_CAPEX_SALES                                     AS CAPEX_TO_SALES,
            bd.FF_ROA                                             AS RETURN_ON_ASSETS,
            bd.FF_ROE                                             AS RETURN_ON_EQUITY,
            ad.FF_ROCE                                            AS RETURN_ON_COMMON_EQUITY,
            bd.FF_ROTC                                            AS RETURN_ON_TOTAL_CAPITAL,
            ad.FF_ROIC                                            AS RETURN_ON_INVESTED_CAPITAL,
            ad.FF_CF_ROIC                                         AS CASH_FLOW_ROIC,

            -- VALUATION
            bd.FF_PSALES                                          AS PRICE_TO_SALES,
            bd.FF_PE                                              AS PRICE_TO_EARNINGS,
            bd.FF_PBK                                             AS PRICE_TO_BOOK,
            ad.FF_PBK_TANG                                        AS PRICE_TO_TANGIBLE_BOOK,
            bd.FF_PCF                                             AS PRICE_TO_CASH_FLOW,
            ad.FF_PFCF                                            AS PRICE_TO_FREE_CASH_FLOW,
            ad.FF_DIV_YLD                                         AS DIVIDEND_YIELD_PCT,
            ad.FF_ENTRPR_VAL_EBIT_OPER                            AS EV_TO_EBIT,
            ad.FF_ENTRPR_VAL_EBITDA_OPER                          AS EV_TO_EBITDA,
            ad.FF_ENTRPR_VAL_SALES                                AS EV_TO_SALES,
            ad.FF_DEBT_ENTRPR_VAL                                 AS TOTAL_DEBT_TO_EV,

            -- PER SHARE
            bd.FF_SALES_PS                                        AS SALES_PER_SHARE,
            b.FF_EBIT_OPER_PS                                     AS EBIT_PER_SHARE,
            bd.FF_EPS_DIL_BEF_UNUSUAL                             AS EPS_RECURRING,
            b.FF_EPS_BASIC                                        AS EPS_BASIC,
            bd.FF_EPS_DIL                                         AS EPS_DILUTED,
            b.FF_DPS                                              AS DIVIDENDS_PER_SHARE,
            bd.FF_PAY_OUT_RATIO                                   AS DIVIDEND_PAYOUT_RATIO,
            b.FF_BPS                                              AS BOOK_VALUE_PER_SHARE,
            bd.FF_BPS_TANG                                        AS TANGIBLE_BV_PER_SHARE,
            ad.FF_OPER_PS_NET_CF                                  AS CASH_FLOW_PER_SHARE,
            ad.FF_FREE_PS_CF_FCF                                  AS FREE_CASH_FLOW_PER_SHARE,
            b.FF_COM_SHS_OUT_EPS_DIL  / 1e6                      AS DILUTED_SHARES_M,
            b.FF_COM_SHS_OUT_EPS_BASIC / 1e6                     AS BASIC_SHARES_M,
            b.FF_COM_SHS_OUT / 1e6                               AS TOTAL_SHARES_M,

            -- ASSET ANALYSIS
            CASE WHEN b.FF_ASSETS <> 0 THEN b.FF_CASH_ST / b.FF_ASSETS * 100 END
                                                                  AS CASH_ST_INV_PCT_ASSETS,
            CASE WHEN b.FF_ASSETS <> 0 THEN b.FF_RECEIV_ST / b.FF_ASSETS * 100 END
                                                                  AS RECEIVABLES_PCT_ASSETS,
            CASE WHEN b.FF_ASSETS <> 0 THEN b.FF_INVEN / b.FF_ASSETS * 100 END
                                                                  AS INVENTORIES_PCT_ASSETS,
            CASE WHEN b.FF_ASSETS <> 0 THEN b.FF_ASSETS_CURR / b.FF_ASSETS * 100 END
                                                                  AS CURRENT_ASSETS_PCT_ASSETS,
            CASE WHEN b.FF_ASSETS <> 0 THEN b.FF_PPE_NET / b.FF_ASSETS * 100 END
                                                                  AS FIXED_ASSETS_PCT_ASSETS,
            b.FF_ASSETS                                           AS TOTAL_ASSETS,

            -- DUPONT
            bd.FF_ASSET_TURN                                      AS ASSET_TURNOVER,
            ad.FF_ROA_PTX                                         AS PRETAX_ROA,
            ad.FF_TAX_RATE                                        AS TAX_RATE,
            (1 - ad.FF_TAX_RATE / 100)                           AS TAX_RATE_COMPLEMENT,
            CASE WHEN b.FF_COM_EQ <> 0
                 THEN b.FF_ASSETS / b.FF_COM_EQ
            END                                                   AS EQUITY_MULTIPLIER,
            CASE WHEN bd.FF_PAY_OUT_RATIO IS NOT NULL
                 THEN (1 - bd.FF_PAY_OUT_RATIO / 100)
            END                                                   AS EARNINGS_RETENTION,
            ad.FF_REINVEST_RATE                                   AS REINVESTMENT_RATE,
            ad.FF_EBIT_OPER_ROA                                   AS EBIT_ROA,

            -- OPERATING EFFICIENCY
            ad.FF_SALES_PER_EMP                                   AS REVENUE_PER_EMPLOYEE,
            ad.FF_NET_INC_PER_EMP                                 AS NET_INCOME_PER_EMPLOYEE,
            ad.FF_ASSETS_PER_EMP                                  AS ASSETS_PER_EMPLOYEE,
            ad.FF_RECEIV_TURN                                     AS RECEIVABLES_TURNOVER,
            ad.FF_INVEN_TURN                                      AS INVENTORY_TURNOVER,
            ad.FF_PAY_ACCT_SALES                                  AS PAYABLES_TURNOVER_PROXY,
            ad.FF_SALES_WKCAP                                     AS WORKING_CAPITAL_TURNOVER,

            -- OPERATING CYCLE (days)
            ad.FF_INVEN_DAYS                                      AS DAYS_INVENTORY_ON_HAND,
            ad.FF_RECEIV_TURN_DAYS                                AS DAYS_SALES_OUTSTANDING,
            ad.FF_INVEN_DAYS + ad.FF_RECEIV_TURN_DAYS            AS OPERATING_CYCLE,
            ad.FF_PAY_TURN_DAYS                                   AS DAYS_PAYABLES_OUTSTANDING,
            ad.FF_INVEN_DAYS + ad.FF_RECEIV_TURN_DAYS - ad.FF_PAY_TURN_DAYS
                                                                  AS NET_OPERATING_CYCLE,

            -- LIQUIDITY
            bd.FF_CURR_RATIO                                      AS CURRENT_RATIO,
            bd.FF_QUICK_RATIO                                     AS QUICK_RATIO,
            CASE WHEN b.FF_LIABS_CURR <> 0
                 THEN b.FF_CASH_ST / b.FF_LIABS_CURR
            END                                                   AS CASH_RATIO,
            ad.FF_CASH_CURR_ASSETS                                AS CASH_ST_INV_PCT_CURR_ASSETS,
            CASE WHEN b.FF_LIABS_CURR <> 0
                 THEN bd.FF_OPER_CF / b.FF_LIABS_CURR
            END                                                   AS CFO_TO_CURRENT_LIABILITIES,

            -- COVERAGE
            bd.FF_DEBT_EBITDA_OPER                                AS NET_DEBT_TO_EBITDA,
            CASE WHEN (bd.FF_EBITDA_OPER - ABS(bd.FF_CAPEX)) <> 0
                 THEN bd.FF_NET_DEBT / (bd.FF_EBITDA_OPER - ABS(bd.FF_CAPEX))
            END                                                   AS NET_DEBT_TO_EBITDA_MINUS_CAPEX,
            CASE WHEN bd.FF_EBITDA_OPER <> 0
                 THEN b.FF_DEBT / bd.FF_EBITDA_OPER
            END                                                   AS TOTAL_DEBT_TO_EBITDA,
            ad.FF_EBIT_OPER_INT_COVG                              AS EBIT_INTEREST_COVERAGE,
            CASE WHEN bd.FF_INT_EXP_NET <> 0
                 THEN bd.FF_EBITDA_OPER / ABS(bd.FF_INT_EXP_NET)
            END                                                   AS EBITDA_INTEREST_COVERAGE,
            ad.FF_EBIT_OPER_FIX_CHRG_COVG                        AS FIXED_CHARGE_COVERAGE,
            CASE WHEN bd.FF_INT_EXP_NET <> 0
                 THEN bd.FF_OPER_CF / ABS(bd.FF_INT_EXP_NET)
            END                                                   AS CFO_INTEREST_COVERAGE,
            ad.FF_CASH_DIV_COVG_RATIO                             AS CASH_DIVIDEND_COVERAGE,
            CASE WHEN bd.FF_EBITDA_OPER <> 0
                 THEN b.FF_DEBT_LT / bd.FF_EBITDA_OPER
            END                                                   AS LT_DEBT_TO_EBITDA,
            CASE WHEN bd.FF_OPER_CF <> 0
                 THEN bd.FF_NET_DEBT / bd.FF_OPER_CF
            END                                                   AS NET_DEBT_TO_FFO,
            CASE WHEN bd.FF_OPER_CF <> 0
                 THEN b.FF_DEBT_LT / bd.FF_OPER_CF
            END                                                   AS LT_DEBT_TO_FFO,
            CASE WHEN b.FF_DEBT <> 0
                 THEN bd.FF_FREE_CF_FCFE / b.FF_DEBT
            END                                                   AS FCF_TO_TOTAL_DEBT,
            ad.FF_NET_CF_DEBT                                     AS CFO_TO_TOTAL_DEBT,
            CASE WHEN bd.FF_EBIT_OPER <> 0
                 THEN b.FF_DEBT / bd.FF_EBIT_OPER
            END                                                   AS TOTAL_DEBT_TO_EBIT,
            CASE WHEN bd.FF_EBIT_OPER <> 0
                 THEN bd.FF_NET_DEBT / bd.FF_EBIT_OPER
            END                                                   AS NET_DEBT_TO_EBIT,
            CASE WHEN bd.FF_INT_EXP_NET <> 0
                 THEN (bd.FF_EBITDA_OPER - ABS(bd.FF_CAPEX)) / ABS(bd.FF_INT_EXP_NET)
            END                                                   AS EBITDA_MINUS_CAPEX_INT_COVERAGE,

            -- LEVERAGE
            ad.FF_LTD_COM_EQ                                      AS LT_DEBT_TO_EQUITY,
            ad.FF_LTD_TCAP                                        AS LT_DEBT_TO_TOTAL_CAPITAL,
            CASE WHEN b.FF_ASSETS <> 0
                 THEN b.FF_DEBT_LT / b.FF_ASSETS * 100
            END                                                   AS LT_DEBT_TO_TOTAL_ASSETS,
            bd.FF_DEBT_ASSETS                                     AS TOTAL_DEBT_TO_ASSETS,
            CASE WHEN b.FF_EQ_TOT <> 0
                 THEN bd.FF_NET_DEBT / b.FF_EQ_TOT * 100
            END                                                   AS NET_DEBT_TO_EQUITY,
            ad.FF_DEBT_EQ                                         AS TOTAL_DEBT_TO_EQUITY,
            CASE WHEN bd.FF_TCAP <> 0
                 THEN bd.FF_NET_DEBT / bd.FF_TCAP * 100
            END                                                   AS NET_DEBT_TO_TOTAL_CAPITAL,
            ad.FF_TOT_DEBT_TCAP_STD                               AS TOTAL_DEBT_TO_TOTAL_CAPITAL

        FROM FACTSET.FF_V3.FF_BASIC_AF b
        JOIN FACTSET.FF_V3.FF_BASIC_DER_AF bd
            ON b.FSYM_ID = bd.FSYM_ID AND b.DATE = bd.DATE
        JOIN FACTSET.FF_V3.FF_ADVANCED_DER_AF ad
            ON b.FSYM_ID = ad.FSYM_ID AND b.DATE = ad.DATE
        WHERE b.FSYM_ID = '{fsym_id}'
          AND b.FF_FYR BETWEEN {int(year_from)} AND {int(year_to)}
    )
    SELECT * FROM base ORDER BY FISCAL_YEAR
    """
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["PERIOD_END_DATE"] = pd.to_datetime(df["PERIOD_END_DATE"])
        df = df.set_index("PERIOD_END_DATE")
        df.index.name = "Date"
        for c in df.columns:
            if c not in ("FSYM_ID", "CURRENCY", "FISCAL_YEAR"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def fetch_forward_estimates(fsym_id):
    """Return forward consensus EPS, Sales, DPS for upcoming fiscal years."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    results = []
    for item in ["EPS", "SALES", "DPS", "CFPS"]:
        cur.execute(f"""
            SELECT FE_FP_END, FE_MEAN, FE_MEDIAN, FE_HIGH, FE_LOW, FE_NUM_EST
            FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
            WHERE FSYM_ID = '{fsym_id}' AND FE_ITEM = '{item}'
              AND FE_FP_END >= CURRENT_DATE()
              AND CONS_END_DATE IS NULL
            ORDER BY FE_FP_END
        """)
        for row in cur.fetchall():
            results.append({"Item": item, "FY End": row[0], "Mean": row[1],
                            "Median": row[2], "High": row[3], "Low": row[4],
                            "# Est": row[5]})
    return pd.DataFrame(results)


def fetch_estimate_actuals(fsym_id, item="EPS", periodicity="quarterly", limit=24):
    """Return actual estimate values for the selected item/frequency."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    table = "FE_BASIC_ACT_QF" if periodicity == "quarterly" else "FE_BASIC_ACT_AF"
    cur.execute(f"""
        SELECT FE_FP_END, REPORT_DATE, ACTUAL_VALUE, CURRENCY
        FROM FACTSET.FE_V4.{table}
        WHERE FSYM_ID = '{fsym_id}'
          AND FE_ITEM = '{item}'
          AND REPORT_DATE <= CURRENT_DATE()
          AND ACTUAL_VALUE IS NOT NULL
        ORDER BY FE_FP_END DESC
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    cols = ["FE_FP_END", "REPORT_DATE", "ACTUAL_VALUE", "CURRENCY"]
    return pd.DataFrame(rows, columns=cols)


def fetch_consensus_estimates(fsym_id, item="EPS", periodicity="quarterly", limit=12):
    """Return latest active consensus estimates for the selected item/frequency."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    table = "FE_BASIC_CONH_QF" if periodicity == "quarterly" else "FE_BASIC_CONH_AF"
    cur.execute(f"""
        SELECT FE_FP_END, FE_MEAN, FE_MEDIAN, FE_HIGH, FE_LOW, FE_NUM_EST, CURRENCY
        FROM FACTSET.FE_V4.{table}
        WHERE FSYM_ID = '{fsym_id}'
          AND FE_ITEM = '{item}'
          AND FE_FP_END >= DATEADD(year, -4, CURRENT_DATE())
          AND CONS_END_DATE IS NULL
        ORDER BY FE_FP_END
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    cols = ["FE_FP_END", "FE_MEAN", "FE_MEDIAN", "FE_HIGH", "FE_LOW", "FE_NUM_EST", "CURRENCY"]
    return pd.DataFrame(rows, columns=cols)


def fetch_latest_price(fsym_id):
    """Return latest closing price and currency."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(f"""
        SELECT P_DATE, P_PRICE, CURRENCY
        FROM FACTSET.FP_V2.FP_BASIC_PRICES
        WHERE FSYM_ID = '{fsym_id}'
        ORDER BY P_DATE DESC LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        return None, None
    return row[1], row[2]


def fetch_eps_consensus(fsym_id, item="EPS"):
    """Return EPS consensus revision history as a DataFrame.

    Columns: FE_FP_END (fiscal year end), CONS_END_DATE (snapshot date),
             FE_MEAN, FE_MEDIAN, FE_NUM_EST, FE_HIGH, FE_LOW
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    cur.execute(f"""
        SELECT FE_FP_END, CONS_END_DATE, FE_MEAN, FE_MEDIAN, FE_NUM_EST, FE_HIGH, FE_LOW
        FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
        WHERE FSYM_ID = '{fsym_id}' AND FE_ITEM = '{item}'
          AND CONS_END_DATE IS NOT NULL
          AND CONS_END_DATE >= DATEADD(year, -2, CURRENT_DATE())
        ORDER BY FE_FP_END, CONS_END_DATE
    """)
    rows = cur.fetchall()
    cols = ["FE_FP_END", "CONS_END_DATE", "FE_MEAN", "FE_MEDIAN", "FE_NUM_EST", "FE_HIGH", "FE_LOW"]
    df = pd.DataFrame(rows, columns=cols)
    return df


def fetch_recommendations(fsym_id):
    """Return analyst recommendation history as a DataFrame.

    Columns: CONS_END_DATE, FE_BUY, FE_OVER, FE_HOLD, FE_UNDER, FE_SELL, FE_TOTAL
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    cur.execute(f"""
        SELECT CONS_END_DATE, FE_BUY, FE_OVER, FE_HOLD, FE_UNDER, FE_SELL, FE_TOTAL
        FROM FACTSET.FE_V4.FE_BASIC_CONH_REC
        WHERE FSYM_ID = '{fsym_id}' AND FE_ITEM = 'REC'
          AND CONS_END_DATE IS NOT NULL
        ORDER BY CONS_END_DATE DESC
        LIMIT 12
    """)
    rows = cur.fetchall()
    cols = ["CONS_END_DATE", "FE_BUY", "FE_OVER", "FE_HOLD", "FE_UNDER", "FE_SELL", "FE_TOTAL"]
    df = pd.DataFrame(rows, columns=cols)
    return df


def fetch_earnings_actuals(fsym_id, item="EPS"):
    """Return quarterly actual EPS values as a DataFrame.

    Columns: FE_FP_END, REPORT_DATE, ACTUAL_VALUE
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    cur.execute(f"""
        SELECT FE_FP_END, REPORT_DATE, ACTUAL_VALUE
        FROM FACTSET.FE_V4.FE_BASIC_ACT_QF
        WHERE FSYM_ID = '{fsym_id}' AND FE_ITEM = '{item}'
        ORDER BY FE_FP_END DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    cols = ["FE_FP_END", "REPORT_DATE", "ACTUAL_VALUE"]
    df = pd.DataFrame(rows, columns=cols)
    return df


def fetch_shares_outstanding(fsym_id):
    """Return current shares outstanding."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    # Try with the -R ID first, then the -S from coverage
    cur.execute(f"""
        SELECT P_COM_SHS_OUT FROM FACTSET.FP_V2.FP_BASIC_SHARES_CURRENT
        WHERE FSYM_ID = '{fsym_id}'
    """)
    row = cur.fetchone()
    return float(row[0]) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard widget functions  (replacing yfinance equivalents in data.py)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_earnings_package(fsym_id: str, item: str = "EPS") -> dict:
    """Return everything needed for the Earnings & Revisions page in one call.

    Returns dict with keys:
      actuals_q    – quarterly actuals (FE_FP_END, REPORT_DATE, ACTUAL_VALUE, CURRENCY)
      actuals_a    – annual actuals (same cols)
      surprise_q   – quarterly beat/miss: actuals joined to the consensus mean that
                     was active just before REPORT_DATE
      consensus_fwd– forward annual consensus (FE_FP_END, FE_MEAN, FE_HIGH, FE_LOW,
                     FE_MEDIAN, FE_NUM_EST, CURRENCY) – future fiscal years only
      revisions    – annual consensus revision history for up to 4 forward FYs
                     (FE_FP_END, CONS_END_DATE, FE_MEAN, FE_NUM_EST)
      recommendations – latest monthly recommendation splits
                     (CONS_END_DATE, FE_BUY, FE_OVER, FE_HOLD, FE_UNDER, FE_SELL, FE_TOTAL)
      forward_items– multi-item forward table (EPS, SALES, EBITDA, EBIT, DPS)
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    fid = fsym_id
    it  = item

    # ── 1. Quarterly actuals ─────────────────────────────────────────────
    cur.execute(f"""
        SELECT FE_FP_END, REPORT_DATE, ACTUAL_VALUE, CURRENCY
        FROM FACTSET.FE_V4.FE_BASIC_ACT_QF
        WHERE FSYM_ID = '{fid}' AND FE_ITEM = '{it}'
          AND ACTUAL_VALUE IS NOT NULL
        ORDER BY FE_FP_END DESC
        LIMIT 32
    """)
    actuals_q = pd.DataFrame(cur.fetchall(),
                             columns=["FE_FP_END", "REPORT_DATE", "ACTUAL_VALUE", "CURRENCY"])

    # ── 2. Annual actuals ────────────────────────────────────────────────
    cur.execute(f"""
        SELECT FE_FP_END, REPORT_DATE, ACTUAL_VALUE, CURRENCY
        FROM FACTSET.FE_V4.FE_BASIC_ACT_AF
        WHERE FSYM_ID = '{fid}' AND FE_ITEM = '{it}'
          AND ACTUAL_VALUE IS NOT NULL
        ORDER BY FE_FP_END DESC
        LIMIT 15
    """)
    actuals_a = pd.DataFrame(cur.fetchall(),
                             columns=["FE_FP_END", "REPORT_DATE", "ACTUAL_VALUE", "CURRENCY"])

    # ── 3. Beat/Miss: quarterly actuals vs consensus just before report ──
    cur.execute(f"""
        WITH latest_cons AS (
            SELECT a.FE_FP_END,
                   a.REPORT_DATE,
                   a.ACTUAL_VALUE,
                   a.CURRENCY,
                   c.FE_MEAN   AS CONS_MEAN,
                   c.FE_MEDIAN AS CONS_MEDIAN,
                   c.FE_NUM_EST,
                   ROW_NUMBER() OVER (
                       PARTITION BY a.FE_FP_END
                       ORDER BY c.CONS_END_DATE DESC
                   ) AS rn
            FROM FACTSET.FE_V4.FE_BASIC_ACT_QF a
            JOIN FACTSET.FE_V4.FE_BASIC_CONH_QF c
              ON c.FSYM_ID = a.FSYM_ID
             AND c.FE_ITEM = a.FE_ITEM
             AND c.FE_FP_END = a.FE_FP_END
             AND c.CONS_END_DATE < a.REPORT_DATE
             AND c.CONS_END_DATE >= DATEADD(day, -30, a.REPORT_DATE)
            WHERE a.FSYM_ID = '{fid}' AND a.FE_ITEM = '{it}'
              AND a.ACTUAL_VALUE IS NOT NULL
        )
        SELECT FE_FP_END, REPORT_DATE, ACTUAL_VALUE, CURRENCY,
               CONS_MEAN, CONS_MEDIAN, FE_NUM_EST
        FROM latest_cons
        WHERE rn = 1
        ORDER BY FE_FP_END DESC
        LIMIT 32
    """)
    surprise_q = pd.DataFrame(cur.fetchall(),
                              columns=["FE_FP_END", "REPORT_DATE", "ACTUAL_VALUE", "CURRENCY",
                                       "CONS_MEAN", "CONS_MEDIAN", "FE_NUM_EST"])

    # ── 4. Forward annual consensus ──────────────────────────────────────
    cur.execute(f"""
        SELECT FE_FP_END, FE_MEAN, FE_HIGH, FE_LOW, FE_MEDIAN, FE_NUM_EST, CURRENCY
        FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
        WHERE FSYM_ID = '{fid}' AND FE_ITEM = '{it}'
          AND FE_FP_END >= CURRENT_DATE()
          AND CONS_END_DATE IS NULL
        ORDER BY FE_FP_END
        LIMIT 5
    """)
    consensus_fwd = pd.DataFrame(cur.fetchall(),
                                 columns=["FE_FP_END", "FE_MEAN", "FE_HIGH", "FE_LOW",
                                          "FE_MEDIAN", "FE_NUM_EST", "CURRENCY"])

    # ── 5. Revision history for next 3 FYs ──────────────────────────────
    cur.execute(f"""
        WITH fwd_ends AS (
            SELECT DISTINCT FE_FP_END
            FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
            WHERE FSYM_ID = '{fid}' AND FE_ITEM = '{it}'
              AND FE_FP_END >= CURRENT_DATE()
              AND CONS_END_DATE IS NULL
            ORDER BY FE_FP_END
            LIMIT 3
        )
        SELECT c.FE_FP_END, c.CONS_END_DATE, c.FE_MEAN, c.FE_NUM_EST
        FROM FACTSET.FE_V4.FE_BASIC_CONH_AF c
        JOIN fwd_ends f ON f.FE_FP_END = c.FE_FP_END
        WHERE c.FSYM_ID = '{fid}' AND c.FE_ITEM = '{it}'
          AND c.CONS_END_DATE IS NOT NULL
          AND c.CONS_END_DATE >= DATEADD(year, -3, CURRENT_DATE())
        ORDER BY c.FE_FP_END, c.CONS_END_DATE
    """)
    revisions = pd.DataFrame(cur.fetchall(),
                             columns=["FE_FP_END", "CONS_END_DATE", "FE_MEAN", "FE_NUM_EST"])

    # ── 6. Analyst recommendations ───────────────────────────────────────
    cur.execute(f"""
        SELECT CONS_END_DATE, FE_BUY, FE_OVER, FE_HOLD, FE_UNDER, FE_SELL, FE_TOTAL
        FROM FACTSET.FE_V4.FE_BASIC_CONH_REC
        WHERE FSYM_ID = '{fid}' AND FE_ITEM = 'REC'
          AND CONS_END_DATE IS NOT NULL
        ORDER BY CONS_END_DATE DESC
        LIMIT 24
    """)
    recs = pd.DataFrame(cur.fetchall(),
                        columns=["CONS_END_DATE", "FE_BUY", "FE_OVER", "FE_HOLD",
                                 "FE_UNDER", "FE_SELL", "FE_TOTAL"])

    # ── 7. Multi-item forward table (EPS, SALES, EBITDA, EBIT, DPS) ──────
    cur.execute(f"""
        SELECT FE_ITEM, FE_FP_END, FE_MEAN, FE_HIGH, FE_LOW, FE_NUM_EST, CURRENCY
        FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
        WHERE FSYM_ID = '{fid}'
          AND FE_ITEM IN ('EPS','SALES','EBITDA','EBIT','DPS','CFPS')
          AND FE_FP_END >= CURRENT_DATE()
          AND CONS_END_DATE IS NULL
        ORDER BY FE_ITEM, FE_FP_END
    """)
    fwd_items = pd.DataFrame(cur.fetchall(),
                             columns=["FE_ITEM", "FE_FP_END", "FE_MEAN", "FE_HIGH",
                                      "FE_LOW", "FE_NUM_EST", "CURRENCY"])

    # ── 8. Price target consensus history (last 3 years) ─────────────────
    cur.execute(f"""
        SELECT CONS_END_DATE, FE_MEAN, FE_HIGH, FE_LOW, FE_NUM_EST, CURRENCY
        FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
        WHERE FSYM_ID = '{fid}' AND FE_ITEM = 'TP'
          AND CONS_END_DATE IS NOT NULL
          AND CONS_END_DATE >= DATEADD(year, -3, CURRENT_DATE())
        ORDER BY CONS_END_DATE
    """)
    price_target_hist = pd.DataFrame(cur.fetchall(),
                                     columns=["CONS_END_DATE", "FE_MEAN", "FE_HIGH",
                                              "FE_LOW", "FE_NUM_EST", "CURRENCY"])

    # ── 9. Latest stock price (for upside calculation) ────────────────────
    cur.execute(f"""
        SELECT P_DATE, P_PRICE, CURRENCY
        FROM FACTSET.FP_V2.FP_BASIC_PRICES
        WHERE FSYM_ID = '{fid}'
        ORDER BY P_DATE DESC
        LIMIT 1
    """)
    _price_row = cur.fetchone()
    current_price = {
        "date":     _price_row[0] if _price_row else None,
        "price":    float(_price_row[1]) if _price_row and _price_row[1] else None,
        "currency": _price_row[2] if _price_row else None,
    }

    # ── 10. Monthly price history for 3 years (NTM P/E chart) ────────────
    cur.execute(f"""
        WITH monthly AS (
            SELECT DATE_TRUNC('month', P_DATE) AS MONTH,
                   MAX(P_DATE)                 AS LAST_DATE
            FROM FACTSET.FP_V2.FP_BASIC_PRICES
            WHERE FSYM_ID = '{fid}'
              AND P_DATE >= DATEADD(year, -3, CURRENT_DATE())
            GROUP BY DATE_TRUNC('month', P_DATE)
        )
        SELECT p.P_DATE, p.P_PRICE
        FROM FACTSET.FP_V2.FP_BASIC_PRICES p
        JOIN monthly m ON p.P_DATE = m.LAST_DATE AND p.FSYM_ID = '{fid}'
        ORDER BY p.P_DATE
    """)
    price_hist = pd.DataFrame(cur.fetchall(), columns=["P_DATE", "P_PRICE"])

    # ── 11. Prices ±5 days around each earnings report date ──────────────
    cur.execute(f"""
        WITH report_dates AS (
            SELECT DISTINCT REPORT_DATE
            FROM FACTSET.FE_V4.FE_BASIC_ACT_QF
            WHERE FSYM_ID = '{fid}' AND FE_ITEM = '{it}'
              AND ACTUAL_VALUE IS NOT NULL
              AND REPORT_DATE IS NOT NULL
        )
        SELECT p.P_DATE, p.P_PRICE
        FROM FACTSET.FP_V2.FP_BASIC_PRICES p
        WHERE p.FSYM_ID = '{fid}'
          AND EXISTS (
              SELECT 1 FROM report_dates r
              WHERE p.P_DATE BETWEEN DATEADD(day, -5, r.REPORT_DATE)
                                 AND DATEADD(day,  2, r.REPORT_DATE)
          )
        ORDER BY p.P_DATE
    """)
    price_reaction_prices = pd.DataFrame(cur.fetchall(), columns=["P_DATE", "P_PRICE"])

    # ── Coerce numeric columns ────────────────────────────────────────────
    for df, num_cols in [
        (actuals_q,             ["ACTUAL_VALUE"]),
        (actuals_a,             ["ACTUAL_VALUE"]),
        (surprise_q,            ["ACTUAL_VALUE", "CONS_MEAN", "CONS_MEDIAN", "FE_NUM_EST"]),
        (consensus_fwd,         ["FE_MEAN", "FE_HIGH", "FE_LOW", "FE_MEDIAN", "FE_NUM_EST"]),
        (revisions,             ["FE_MEAN", "FE_NUM_EST"]),
        (recs,                  ["FE_BUY", "FE_OVER", "FE_HOLD", "FE_UNDER", "FE_SELL", "FE_TOTAL"]),
        (fwd_items,             ["FE_MEAN", "FE_HIGH", "FE_LOW", "FE_NUM_EST"]),
        (price_target_hist,     ["FE_MEAN", "FE_HIGH", "FE_LOW", "FE_NUM_EST"]),
        (price_hist,            ["P_PRICE"]),
        (price_reaction_prices, ["P_PRICE"]),
    ]:
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return {
        "actuals_q":             actuals_q,
        "actuals_a":             actuals_a,
        "surprise_q":            surprise_q,
        "consensus_fwd":         consensus_fwd,
        "revisions":             revisions,
        "recommendations":       recs,
        "forward_items":         fwd_items,
        "price_target_hist":     price_target_hist,
        "current_price":         current_price,
        "price_hist":            price_hist,
        "price_reaction_prices": price_reaction_prices,
    }


def fetch_quote_table_sf(pairs_dict):
    """
    Fetch latest price + daily change for a dict of {label: factset_ticker}.
    Returns list of dicts: [{name, symbol, price, chg, pct}, ...].
    """
    if not pairs_dict:
        return []
    tickers = list(pairs_dict.values())
    labels = list(pairs_dict.keys())
    fs_tickers = [_to_factset_ticker(t) for t in tickers]
    ticker_to_label = dict(zip(fs_tickers, labels))
    ticker_to_sym = dict(zip(fs_tickers, tickers))

    ph = ",".join("'" + t + "'" for t in fs_tickers)
    sql = f"""
    SELECT t.TICKER_REGION, p.P_DATE, p.P_PRICE
    FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
    JOIN FACTSET.FP_V2.FP_BASIC_PRICES p ON t.FSYM_ID = p.FSYM_ID
    WHERE t.TICKER_REGION IN ({ph})
      AND p.P_DATE >= DATEADD(day, -10, CURRENT_DATE())
    ORDER BY t.TICKER_REGION, p.P_DATE DESC
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(sql)
    rows = cur.fetchall()

    # Group by ticker: last 2 prices → today + prev
    from collections import defaultdict
    by_ticker = defaultdict(list)
    for tr, dt, px in rows:
        by_ticker[tr].append((dt, px))

    results = []
    for fs_t in fs_tickers:
        label = ticker_to_label.get(fs_t, fs_t)
        sym = ticker_to_sym.get(fs_t, fs_t)
        prices = by_ticker.get(fs_t, [])
        if len(prices) >= 2:
            p, prev = float(prices[0][1]), float(prices[1][1])
            chg = p - prev
            pct = (chg / prev * 100) if prev else 0
        elif len(prices) == 1:
            p = float(prices[0][1])
            chg, pct = 0, 0
        else:
            p, chg, pct = None, 0, 0
        results.append({"name": label, "symbol": sym, "price": p, "chg": chg, "pct": pct})
    return results


def fetch_fx_rates():
    """
    Fetch FX spot rates from MSCI CURRENCY_EXCHANGE_RATES.
    Returns list of dicts: [{name, symbol, price, chg, pct}, ...].

    MSCI stores rates as "foreign currency units per 1 USD".
    We convert to standard market convention:
    - EUR/USD, GBP/USD, AUD/USD, NZD/USD → invert (1/rate)
    - USD/JPY, USD/CHF, USD/CAD           → keep as-is
    """
    # Define pairs: (display_name, MSCI currency code, invert?)
    pairs = [
        ("EUR/USD", "EUR", True),
        ("GBP/USD", "GBP", True),
        ("USD/JPY", "JPY", False),
        ("USD/CHF", "CHF", False),
        ("AUD/USD", "AUD", True),
        ("USD/CAD", "CAD", False),
        ("NZD/USD", "NZD", True),
    ]
    ccy_codes = list(set(p[1] for p in pairs))
    # Also need EUR and GBP for the EUR/GBP cross rate
    if "EUR" not in ccy_codes:
        ccy_codes.append("EUR")
    if "GBP" not in ccy_codes:
        ccy_codes.append("GBP")
    ph = ",".join("'" + c + "'" for c in ccy_codes)

    sql = f"""
    SELECT CALC_DATE, ISO_CURRENCY_SYMBOL, SPOT_FX_EOD00D
    FROM MSCI.INDEX.CURRENCY_EXCHANGE_RATES
    WHERE ISO_CURRENCY_SYMBOL IN ({ph})
      AND CALC_DATE >= DATEADD(day, -10, CURRENT_DATE())
    ORDER BY CALC_DATE DESC
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(sql)
    rows = cur.fetchall()

    # Group by currency: {ccy: [(date, rate), ...]} sorted newest first
    from collections import defaultdict
    by_ccy = defaultdict(list)
    for dt, ccy, rate in rows:
        if rate is not None:
            by_ccy[ccy].append((dt, float(rate)))

    results = []
    for name, ccy, invert in pairs:
        rates = by_ccy.get(ccy, [])
        if len(rates) >= 2:
            today_rate, prev_rate = rates[0][1], rates[1][1]
            if invert:
                p = 1.0 / today_rate if today_rate else None
                prev_p = 1.0 / prev_rate if prev_rate else None
            else:
                p = today_rate
                prev_p = prev_rate
            if p and prev_p:
                chg = p - prev_p
                pct = (chg / prev_p * 100)
            else:
                chg, pct = 0, 0
        elif len(rates) == 1:
            p = (1.0 / rates[0][1]) if invert else rates[0][1]
            chg, pct = 0, 0
        else:
            p, chg, pct = None, 0, 0
        results.append({"name": name, "symbol": name, "price": p, "chg": chg, "pct": pct})

    # EUR/GBP cross rate: EUR/GBP = (EUR/USD) / (GBP/USD) = GBP_rate / EUR_rate
    eur_rates = by_ccy.get("EUR", [])
    gbp_rates = by_ccy.get("GBP", [])
    if len(eur_rates) >= 2 and len(gbp_rates) >= 2:
        # Both are "per 1 USD", so EUR/GBP = GBP_rate / EUR_rate
        eurgbp_today = gbp_rates[0][1] / eur_rates[0][1] if eur_rates[0][1] else None
        eurgbp_prev = gbp_rates[1][1] / eur_rates[1][1] if eur_rates[1][1] else None
        if eurgbp_today and eurgbp_prev:
            chg = eurgbp_today - eurgbp_prev
            pct = (chg / eurgbp_prev * 100)
        else:
            chg, pct = 0, 0
        results.append({"name": "EUR/GBP", "symbol": "EUR/GBP",
                        "price": eurgbp_today, "chg": chg, "pct": pct})

    return results


def fetch_movers_sf(ticker_list, n=10, prefix="$"):
    """
    Fetch top gainers/losers from a list of FactSet-style tickers.
    Returns (gainers_df, losers_df).
    """
    if not ticker_list:
        return pd.DataFrame(), pd.DataFrame()

    fs_tickers = [_to_factset_ticker(t) for t in ticker_list]
    fs_to_orig = dict(zip(fs_tickers, ticker_list))
    ph = ",".join("'" + t + "'" for t in fs_tickers)

    sql = f"""
    SELECT t.TICKER_REGION, p.P_DATE, p.P_PRICE
    FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
    JOIN FACTSET.FP_V2.FP_BASIC_PRICES p ON t.FSYM_ID = p.FSYM_ID
    WHERE t.TICKER_REGION IN ({ph})
      AND p.P_DATE >= DATEADD(day, -10, CURRENT_DATE())
    ORDER BY t.TICKER_REGION, p.P_DATE DESC
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(sql)
    rows_raw = cur.fetchall()

    from collections import defaultdict
    by_ticker = defaultdict(list)
    for tr, dt, px in rows_raw:
        by_ticker[tr].append((dt, float(px)))

    rows = []
    for fs_t in fs_tickers:
        orig = fs_to_orig.get(fs_t, fs_t)
        prices = by_ticker.get(fs_t, [])
        if len(prices) < 2:
            continue
        live, prev = prices[0][1], prices[1][1]
        if prev == 0:
            continue
        pct = (live / prev - 1) * 100
        sign = "+" if pct >= 0 else ""
        # Strip region suffix for display (AZN-GB → AZN)
        display = orig.split("-")[0] if "-" in orig else orig
        rows.append({
            "Ticker": display,
            "Price": f"{prefix}{live:,.2f}",
            "Chg %": f"{sign}{pct:.2f}%",
            "_chg": pct,
        })

    if not rows:
        return pd.DataFrame(), pd.DataFrame()
    result = pd.DataFrame(rows).sort_values("_chg", ascending=False)
    # Ensure gainers/losers are non-overlapping. If n is too large relative
    # to universe size, cap each side at floor(N/2).
    n_each = min(int(n), len(result) // 2)
    if n_each <= 0:
        n_each = min(int(n), len(result))
    gainers = result.head(n_each).reset_index(drop=True)
    losers = result.tail(n_each).sort_values("_chg").reset_index(drop=True)
    return gainers, losers


# ── News, Filings & Transcripts ──────────────────────────────────────────────

def fetch_sec_filings(company_name, limit=20):
    """
    Fetch recent SEC filings (10-K, 10-Q, 8-K, etc.) for a company.
    Returns a list of dicts with keys: filed_date, form_type, company, adsh, url.
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    # Clean the name for matching — use first significant word
    safe = company_name.replace("'", "''")
    cur.execute(f"""
        SELECT COMPANY_NAME, FILED_DATE, FORM_TYPE, ADSH, CIK
        FROM SEC_FILINGS.CYBERSYN.SEC_REPORT_INDEX
        WHERE COMPANY_NAME ILIKE '%{safe}%'
        ORDER BY FILED_DATE DESC
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    results = []
    for r in rows:
        cik = str(r[4]).lstrip("0") if r[4] else ""
        adsh = str(r[3]).replace("-", "") if r[3] else ""
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh}/{r[3]}-index.htm" if cik and r[3] else ""
        results.append({
            "filed_date": r[1],
            "form_type": r[2],
            "company": r[0],
            "adsh": r[3],
            "url": url,
        })
    return results


def fetch_news_headlines(company_name, limit=25):
    """
    Fetch recent StreetAccount news headlines mentioning a company.
    Returns list of dicts: publish_time, headline.
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    safe = company_name.replace("'", "''")
    cur.execute(f"""
        SELECT PUBLISH_TIME,
               XMLGET(PARSE_XML(RAW_XML), 'headline'):"$"::STRING AS HEADLINE
        FROM FACTSET.STREETACCOUNT.STREETACCOUNT
        WHERE RAW_XML ILIKE '%{safe}%'
        ORDER BY PUBLISH_TIME DESC
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    return [{"publish_time": r[0], "headline": r[1]} for r in rows if r[1]]


def fetch_transcripts_list(company_name, limit=15):
    """
    Fetch list of available earnings call transcripts for a company.
    Returns list of dicts: date, transcript_type, id.
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    safe = company_name.replace("'", "''")
    cur.execute(f"""
        SELECT ID, DATE, TRANSCRIPT_TYPE
        FROM FACTSET.TRANSCRIPTS.TRANSCRIPTS
        WHERE RAW_XML ILIKE '%{safe}%'
          AND TRANSCRIPT_TYPE = 'CorrectedTranscript'
        ORDER BY DATE DESC
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    return [{"id": r[0], "date": r[1], "type": r[2]} for r in rows]


# ── Financial Statements (Income Statement, Balance Sheet, Cash Flow) ────

# Column mappings for each statement
_IS_COLS = {
    "FF_SALES": "Revenue",
    "FF_GROSS_INC": "Gross Profit",
    "FF_OPER_EXP_TOT": "Total Operating Expenses",
    "FF_OPER_INC": "Operating Income",
    "FF_INT_EXP_TOT": "Interest Expense",
    "FF_PTX_INC": "Pretax Income",
    "FF_INC_TAX": "Income Tax",
    "FF_NET_INCOME": "Net Income",
    "FF_EPS_BASIC": "EPS (Basic)",
    "FF_EPS_REPORTED": "EPS (Diluted)",
    "FF_DPS": "Dividends Per Share",
    "FF_COM_SHS_OUT": "Shares Outstanding",
}

_BS_COLS = {
    "FF_CASH_ST": "Cash & Short-Term Investments",
    "FF_RECEIV_ST": "Receivables",
    "FF_INVEN": "Inventories",
    "FF_ASSETS_CURR": "Total Current Assets",
    "FF_PPE_NET": "Property, Plant & Equipment",
    "FF_INTANG": "Intangible Assets",
    "FF_ASSETS": "Total Assets",
    "FF_PAY_ACCT": "Accounts Payable",
    "FF_DEBT_ST": "Short-Term Debt",
    "FF_LIABS_CURR": "Total Current Liabilities",
    "FF_DEBT_LT": "Long-Term Debt",
    "FF_DEBT": "Total Debt",
    "FF_SHLDRS_EQ": "Total Shareholders' Equity",
    "FF_LIABS_SHLDRS_EQ": "Total Liabilities & Equity",
}

_CF_COLS = {
    "FF_NET_INC_CF": "Net Income",
    "FF_DEP_EXP_CF": "Depreciation & Amortisation",
    "FF_DFD_TAX_CF": "Deferred Income Tax",
    "FF_NON_CASH": "Non-Cash Items",
    "FF_WKCAP_CHG": "Changes in Working Capital",
    "FF_FUNDS_OPER_GROSS": "Cash from Operations",
    "FF_INVEST_ACTIV_CF": "Cash from Investing",
    "FF_ACQ_BUS_CF": "Acquisitions",
    "FF_DIV_CF": "Dividends Paid",
    "FF_CHG_CASH_CF": "Net Change in Cash",
}


def _resolve_ff_company_id(security_id):
    """Map a FactSet security FSYM_ID (-S) to FF company FSYM_ID via FF_SEC_MAP."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(f"""
        SELECT FSYM_COMPANY_ID
        FROM FACTSET.FF_V3.FF_SEC_MAP
        WHERE FSYM_ID = '{security_id}'
    """)
    row = cur.fetchone()
    return row[0] if row else None


def fetch_financial_statements(security_id, freq="annual", years=5):
    """
    Fetch Income Statement, Balance Sheet, and Cash Flow data.

    Parameters
    ----------
    security_id : str
        FactSet FSYM_ID ending in -S (security level).
    freq : str
        'annual' or 'quarterly'.
    years : int
        Number of years of data (annual) or equivalent quarters.

    Returns
    -------
    dict with keys 'income_statement', 'balance_sheet', 'cash_flow'.
    Each is a list of dicts with 'label' and period-date keys.
    """
    company_id = _resolve_ff_company_id(security_id)
    if not company_id:
        return {"income_statement": [], "balance_sheet": [], "cash_flow": []}

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    table = "FF_BASIC_AF" if freq == "annual" else "FF_BASIC_QF"
    limit = years if freq == "annual" else years * 4

    all_cols = list(_IS_COLS.keys()) + list(_BS_COLS.keys()) + list(_CF_COLS.keys())
    # Remove duplicates while preserving order
    seen = set()
    unique_cols = []
    for c in all_cols:
        if c not in seen:
            seen.add(c)
            unique_cols.append(c)

    col_str = ", ".join(unique_cols)
    cur.execute(f"""
        SELECT FF_FISCAL_DATE, CURRENCY, {col_str}
        FROM FACTSET.FF_V3.{table}
        WHERE FSYM_ID = '{company_id}'
        ORDER BY FF_FISCAL_DATE DESC
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    if not rows:
        return {"income_statement": [], "balance_sheet": [], "cash_flow": []}

    desc = [d[0] for d in cur.description]

    # Build a dict per column: {FF_COL: {date: value, ...}}
    dates = []
    col_data = {c: {} for c in unique_cols}
    currency = None
    for row in rows:
        d = dict(zip(desc, row))
        dt = str(d["FF_FISCAL_DATE"])
        dates.append(dt)
        if not currency:
            currency = d.get("CURRENCY", "")
        for c in unique_cols:
            col_data[c][dt] = d.get(c)

    def _build_statement(col_map):
        result = []
        for ff_col, label in col_map.items():
            entry = {"label": label}
            for dt in dates:
                entry[dt] = col_data.get(ff_col, {}).get(dt)
            result.append(entry)
        return result

    return {
        "income_statement": _build_statement(_IS_COLS),
        "balance_sheet": _build_statement(_BS_COLS),
        "cash_flow": _build_statement(_CF_COLS),
        "dates": dates,
        "currency": currency or "",
    }


def fetch_sector_stocks_1d(sector_name, region="US", limit=80):
    """
    Fetch stocks belonging to a given sector with their 1-day % change.

    Parameters
    ----------
    sector_name : str
        One of the keys in SECTOR_CODE_MAP (e.g. "Consumer Staples").
    region : str
        Region suffix, default "US". Use "GB" for UK, "FR" for France, etc.
    limit : int
        Max number of stocks to return (sorted by abs % change desc).

    Returns
    -------
    list of dicts: {ticker, name, price, pct_chg}
    """
    codes = SECTOR_CODE_MAP.get(sector_name)
    if not codes:
        return []

    codes_str = ", ".join(f"'{c}'" for c in codes)
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    today = datetime.date.today()
    # Look back 5 days to ensure we get at least 2 trading days
    start = today - datetime.timedelta(days=7)

    cur.execute(f"""
        WITH sector_tickers AS (
            -- Carry FSYM_ID (the listing-level ID) through to avoid re-joining later
            SELECT DISTINCT tr.FSYM_ID, tr.TICKER_REGION, sc.PROPER_NAME
            FROM FACTSET.SYM_V1.SYM_ENTITY_SECTOR es
            JOIN FACTSET.FP_V2.FP_SEC_ENTITY fse
                ON fse.FACTSET_ENTITY_ID = es.FACTSET_ENTITY_ID
            JOIN FACTSET.SYM_V1.SYM_COVERAGE sc
                ON sc.FSYM_PRIMARY_EQUITY_ID = fse.FSYM_ID
            JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr
                ON tr.FSYM_ID = sc.FSYM_ID
            WHERE es.SECTOR_CODE IN ({codes_str})
              AND sc.UNIVERSE_TYPE = 'EQ'
              AND tr.TICKER_REGION LIKE '%-{region}'
        ),
        latest_prices AS (
            SELECT
                t.TICKER_REGION,
                t.PROPER_NAME,
                p.P_DATE,
                p.P_PRICE,
                -- Partition by FSYM_ID to ensure one price series per listing
                ROW_NUMBER() OVER (PARTITION BY t.FSYM_ID ORDER BY p.P_DATE DESC) AS rn
            FROM sector_tickers t
            JOIN FACTSET.FP_V2.FP_BASIC_PRICES p ON p.FSYM_ID = t.FSYM_ID
            WHERE p.P_DATE >= '{start}'
        ),
        last_two AS (
            SELECT TICKER_REGION, PROPER_NAME, P_DATE, P_PRICE, rn
            FROM latest_prices
            WHERE rn <= 2
        ),
        pivoted AS (
            -- Group by TICKER_REGION (now 1:1 with FSYM_ID after the fix above)
            SELECT
                TICKER_REGION,
                MAX(PROPER_NAME) AS PROPER_NAME,
                MAX(CASE WHEN rn = 1 THEN P_PRICE END) AS price_today,
                MAX(CASE WHEN rn = 2 THEN P_PRICE END) AS price_prev
            FROM last_two
            GROUP BY TICKER_REGION
        )
        SELECT
            TICKER_REGION,
            PROPER_NAME,
            price_today,
            CASE WHEN price_prev > 0
                 THEN (price_today - price_prev) / price_prev * 100
                 ELSE NULL END AS pct_chg
        FROM pivoted
        WHERE price_today IS NOT NULL
          AND price_prev IS NOT NULL
        ORDER BY ABS(pct_chg) DESC NULLS LAST
        LIMIT {int(limit)}
    """)
    rows = cur.fetchall()
    results = []
    for r in rows:
        tr = r[0]
        ticker = tr.split("-")[0] if "-" in tr else tr
        results.append({
            "ticker": ticker,
            "ticker_region": tr,
            "name": r[1] or ticker,
            "price": r[2],
            "pct_chg": round(float(r[3]), 2) if r[3] is not None else 0.0,
        })
    return results


def fetch_peer_comparison(entity_id, region=None, limit=12):
    """Return refined RBICS peers for an entity with valuation metrics.

    Method:
    - same RBICS L2 industry bucket
    - global primary regional listings (not restricted to the same country/region)
    - exclude ADR/DR/GDR/NVDR/ALIEN style instruments
    - ranked by similarity to target on valuation + margins
    """
    if not entity_id:
        return []

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    region_clause = f"AND tr.TICKER_REGION LIKE '%-{region}'" if region else ""

    cur.execute(f"""
        WITH latest_der AS (
            SELECT
                FSYM_ID,
                DATE,
                FF_MKT_VAL,
                FF_PE,
                FF_PSALES,
                FF_PCF,
                FF_GROSS_MGN,
                FF_OPER_MGN,
                FF_NET_MGN,
                FF_EBITDA_OPER,
                FF_FREE_CF_FCFE,
                ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_BASIC_DER_LTM
        ),
        base AS (
            SELECT DISTINCT
                rb.L2_ID,
                tr.TICKER_REGION AS target_ticker_region,
                sc.FSYM_ID AS target_fsym_id,
                ld.FF_PE AS target_pe,
                ld.FF_PSALES AS target_ps,
                ld.FF_PCF AS target_pcf,
                ld.FF_GROSS_MGN AS target_gross_mgn,
                ld.FF_OPER_MGN AS target_oper_mgn,
                ld.FF_NET_MGN AS target_net_mgn
            FROM FACTSET.SYM_V1.SYM_ENTITY_SECTOR_RBICS rb
            JOIN FACTSET.SYM_V1.SYM_ENTITY ent
                ON ent.FACTSET_ENTITY_ID = rb.FACTSET_ENTITY_ID
            JOIN FACTSET.FP_V2.FP_SEC_ENTITY fse
                ON fse.FACTSET_ENTITY_ID = rb.FACTSET_ENTITY_ID
            JOIN FACTSET.SYM_V1.SYM_COVERAGE sc
                ON sc.FSYM_PRIMARY_EQUITY_ID = fse.FSYM_ID
               AND sc.UNIVERSE_TYPE = 'EQ'
               AND sc.REGIONAL_FLAG = TRUE
                             AND COALESCE(sc.FREF_SECURITY_TYPE, 'SHARE') NOT IN ('ADR', 'DR', 'GDR', 'NVDR', 'ALIEN')
            JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr
                ON tr.FSYM_ID = sc.FSYM_ID
            LEFT JOIN latest_der ld
                ON ld.FSYM_ID = sc.FSYM_ID
               AND ld.rn = 1
            WHERE rb.FACTSET_ENTITY_ID = '{entity_id}'
              AND rb.FOCUS_FLAG = TRUE
                            {region_clause}
            LIMIT 1
        ),
        peer_set AS (
            SELECT
                CASE WHEN rb.FACTSET_ENTITY_ID = '{entity_id}' THEN 1 ELSE 0 END AS is_target,
                tr.TICKER_REGION,
                sc.PROPER_NAME,
                ent.ISO_COUNTRY,
                ld.FF_MKT_VAL,
                ld.FF_PE,
                ld.FF_PSALES,
                ld.FF_PCF,
                ld.FF_GROSS_MGN,
                ld.FF_OPER_MGN,
                ld.FF_NET_MGN,
                ld.FF_EBITDA_OPER,
                ld.FF_FREE_CF_FCFE,
                (
                    0.70 * COALESCE(ABS(ld.FF_PSALES - b.target_ps), 4)
                    + 0.30 * COALESCE(ABS(ld.FF_PCF - b.target_pcf), 4)
                    + 0.20 * COALESCE(ABS(ld.FF_PE - b.target_pe) / 10, 2)
                    + 0.35 * COALESCE(ABS(ld.FF_GROSS_MGN - b.target_gross_mgn) / 10, 2)
                    + 0.35 * COALESCE(ABS(ld.FF_OPER_MGN - b.target_oper_mgn) / 10, 2)
                    + 0.20 * COALESCE(ABS(ld.FF_NET_MGN - b.target_net_mgn) / 10, 2)
                ) AS peer_score
            FROM base b
            JOIN FACTSET.SYM_V1.SYM_ENTITY_SECTOR_RBICS rb
                ON rb.L2_ID = b.L2_ID
               AND rb.FOCUS_FLAG = TRUE
            JOIN FACTSET.SYM_V1.SYM_ENTITY ent
                ON ent.FACTSET_ENTITY_ID = rb.FACTSET_ENTITY_ID
            JOIN FACTSET.FP_V2.FP_SEC_ENTITY fse
                ON fse.FACTSET_ENTITY_ID = rb.FACTSET_ENTITY_ID
            JOIN FACTSET.SYM_V1.SYM_COVERAGE sc
                ON sc.FSYM_PRIMARY_EQUITY_ID = fse.FSYM_ID
               AND sc.UNIVERSE_TYPE = 'EQ'
               AND sc.REGIONAL_FLAG = TRUE
                             AND COALESCE(sc.FREF_SECURITY_TYPE, 'SHARE') NOT IN ('ADR', 'DR', 'GDR', 'NVDR', 'ALIEN')
            JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr
                ON tr.FSYM_ID = sc.FSYM_ID
            LEFT JOIN latest_der ld
                ON ld.FSYM_ID = sc.FSYM_ID
               AND ld.rn = 1
                        WHERE 1=1
                            {region_clause}
        )
        SELECT DISTINCT
            is_target,
            TICKER_REGION,
            PROPER_NAME,
            FF_MKT_VAL,
            FF_PE,
            FF_PSALES,
            FF_PCF,
            FF_GROSS_MGN,
            FF_OPER_MGN,
            FF_NET_MGN,
            FF_EBITDA_OPER,
            FF_FREE_CF_FCFE,
            peer_score
        FROM peer_set
        ORDER BY is_target DESC, peer_score ASC, PROPER_NAME
        LIMIT {int(limit) + 1}
    """)
    rows = cur.fetchall()
    results = []
    for r in rows:
        tr = r[1]
        results.append({
            "is_target": bool(r[0]),
            "ticker": tr.split("-")[0] if "-" in tr else tr,
            "ticker_region": tr,
            "name": r[2] or (tr.split("-")[0] if "-" in tr else tr),
            "mkt_cap": float(r[3]) if r[3] is not None else None,
            "pe": float(r[4]) if r[4] is not None else None,
            "ps": float(r[5]) if r[5] is not None else None,
            "pcf": float(r[6]) if r[6] is not None else None,
            "gross_margin": float(r[7]) if r[7] is not None else None,
            "oper_margin": float(r[8]) if r[8] is not None else None,
            "net_margin": float(r[9]) if r[9] is not None else None,
            "ebitda": float(r[10]) if r[10] is not None else None,
            "free_cf": float(r[11]) if r[11] is not None else None,
        })
    return results

def fetch_peers_comparison_metrics(fsym_ids: list) -> pd.DataFrame:
    """Batch-fetch LTM actuals + NTM consensus for a list of fsym_ids.

    Returns a DataFrame (one row per fsym_id) with:
      - LTM margins, EV multiples (LTM), P/E, FCF yield, Net Debt/EBITDA
      - LTM ROIC, ROE, Asset Turnover (from most recent annual filing)
      - NTM consensus SALES, EPS, EBITDA, EBIT (next FY from FE_BASIC_CONH_AF)
      - NTM derived multiples: EVSALES_NTM, EVEBITDA_NTM, EVEBIT_NTM, PE_NTM
      - Growth estimates: SALES_GR_NTM, EPS_GR_NTM, EBIT_GR_NTM
    """
    if not fsym_ids:
        return pd.DataFrame()

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    ids_str = ", ".join(f"'{fid}'" for fid in fsym_ids)

    # ── 1. LTM basic + advanced metrics ─────────────────────────────────────
    cur.execute(f"""
        WITH ltm_b AS (
            SELECT FSYM_ID, DATE, FF_MKT_VAL, FF_PE, FF_PSALES, FF_PCF,
                   FF_GROSS_MGN, FF_OPER_MGN, FF_NET_MGN, FF_EBITDA_OPER,
                   FF_FREE_CF_FCFE, FF_DEBT_EBITDA_OPER,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_BASIC_DER_LTM
            WHERE FSYM_ID IN ({ids_str})
        ),
        ltm_a AS (
            SELECT FSYM_ID, DATE,
                   FF_EBITDA_OPER_MGN, FF_EBIT_OPER_MGN, FF_FCF_YLD,
                   FF_SALES_GR, FF_EPS_BASIC_GR,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_ADVANCED_DER_LTM
            WHERE FSYM_ID IN ({ids_str})
        )
        SELECT b.FSYM_ID,
               b.DATE,
               b.FF_MKT_VAL,
               b.FF_PE,
               b.FF_PSALES,
               b.FF_GROSS_MGN,
               b.FF_OPER_MGN,
               b.FF_NET_MGN,
               b.FF_EBITDA_OPER,
               b.FF_FREE_CF_FCFE,
               b.FF_DEBT_EBITDA_OPER,
               a.FF_EBITDA_OPER_MGN,
               a.FF_EBIT_OPER_MGN,
               a.FF_FCF_YLD,
               a.FF_SALES_GR,
               a.FF_EPS_BASIC_GR
        FROM ltm_b b
        LEFT JOIN ltm_a a ON a.FSYM_ID = b.FSYM_ID AND a.rn = 1
        WHERE b.rn = 1
    """)
    ltm_rows = cur.fetchall()
    ltm_cols = ["FSYM_ID", "DATE", "MKT_CAP", "PE_LTM", "PSALES_LTM",
                "GROSS_MARGIN", "OPER_MARGIN_LTM", "NET_MARGIN",
                "EBITDA_LTM_M", "FCF_LTM_M", "NET_DEBT_EBITDA_LTM",
                "EBITDA_MARGIN", "EBIT_MARGIN", "FCF_YIELD_LTM",
                "SALES_GR_LTM", "EPS_GR_LTM"]
    df_ltm = pd.DataFrame(ltm_rows, columns=ltm_cols)

    # ── 2. Annual: ROIC, ROE, Asset Turnover, Net Debt (most recent FY) ─────
    cur.execute(f"""
        WITH ann_b AS (
            SELECT bd.FSYM_ID, bd.DATE, bd.FF_ROE, bd.FF_ASSET_TURN, bd.FF_NET_DEBT,
                   ROW_NUMBER() OVER (PARTITION BY bd.FSYM_ID ORDER BY bd.DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_BASIC_DER_AF bd
            WHERE bd.FSYM_ID IN ({ids_str})
        ),
        ann_a AS (
            SELECT ad.FSYM_ID, ad.DATE, ad.FF_ROIC,
                   ROW_NUMBER() OVER (PARTITION BY ad.FSYM_ID ORDER BY ad.DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_ADVANCED_DER_AF ad
            WHERE ad.FSYM_ID IN ({ids_str})
        )
        SELECT b.FSYM_ID, b.FF_ROE, b.FF_ASSET_TURN, b.FF_NET_DEBT, a.FF_ROIC
        FROM ann_b b
        LEFT JOIN ann_a a ON a.FSYM_ID = b.FSYM_ID AND a.rn = 1
        WHERE b.rn = 1
    """)
    ann_rows = cur.fetchall()
    df_ann = pd.DataFrame(ann_rows, columns=["FSYM_ID", "ROE", "ASSET_TURNOVER", "NET_DEBT_M", "ROIC"])

    # ── 3. NTM consensus (nearest future fiscal year) ────────────────────────
    cur.execute(f"""
        WITH ntm AS (
            SELECT FSYM_ID, FE_ITEM, FE_MEAN,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID, FE_ITEM ORDER BY FE_FP_END ASC) AS rn
            FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
            WHERE FSYM_ID IN ({ids_str})
              AND FE_ITEM IN ('SALES', 'EPS', 'EBITDA', 'EBIT')
              AND FE_FP_END >= CURRENT_DATE()
              AND CONS_END_DATE IS NULL
        )
        SELECT FSYM_ID, FE_ITEM, FE_MEAN
        FROM ntm
        WHERE rn = 1
    """)
    ntm_rows = cur.fetchall()
    df_ntm_long = pd.DataFrame(ntm_rows, columns=["FSYM_ID", "FE_ITEM", "FE_MEAN"])
    if not df_ntm_long.empty:
        df_ntm = df_ntm_long.pivot(index="FSYM_ID", columns="FE_ITEM", values="FE_MEAN").reset_index()
        df_ntm.columns.name = None
    else:
        df_ntm = pd.DataFrame({"FSYM_ID": list(fsym_ids)})
    for col in ["SALES", "EPS", "EBITDA", "EBIT"]:
        if col not in df_ntm.columns:
            df_ntm[col] = None
    df_ntm = df_ntm.rename(columns={
        "SALES": "NTM_SALES_M", "EPS": "NTM_EPS",
        "EBITDA": "NTM_EBITDA_M", "EBIT": "NTM_EBIT_M",
    })

    # ── 4. Ticker / Name lookup ──────────────────────────────────────────────
    cur.execute(f"""
        SELECT tr.FSYM_ID, tr.TICKER_REGION, cov.PROPER_NAME
        FROM FACTSET.SYM_V1.SYM_TICKER_REGION tr
        JOIN FACTSET.SYM_V1.SYM_COVERAGE cov ON cov.FSYM_ID = tr.FSYM_ID
        WHERE tr.FSYM_ID IN ({ids_str})
          AND cov.REGIONAL_FLAG = TRUE
          AND cov.UNIVERSE_TYPE = 'EQ'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY tr.FSYM_ID ORDER BY tr.TICKER_REGION) = 1
    """)
    name_rows = cur.fetchall()
    df_names = pd.DataFrame(name_rows, columns=["FSYM_ID", "TICKER", "NAME"])

    # ── 5. Merge ─────────────────────────────────────────────────────────────
    df = df_ltm.merge(df_ann, on="FSYM_ID", how="left")
    df = df.merge(df_ntm, on="FSYM_ID", how="left")
    df = df.merge(df_names, on="FSYM_ID", how="left")

    num_cols = [c for c in df.columns if c not in ("FSYM_ID", "DATE", "TICKER", "NAME")]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # ── 6. Derived NTM multiples ─────────────────────────────────────────────
    # EV ≈ MktCap + NetDebt (millions)
    df["EV_M"] = df["MKT_CAP"] + df["NET_DEBT_M"].fillna(0)

    df["EVSALES_NTM"]   = (df["EV_M"] / df["NTM_SALES_M"]).where(df["NTM_SALES_M"]  > 0)
    df["EVEBITDA_NTM"]  = (df["EV_M"] / df["NTM_EBITDA_M"]).where(df["NTM_EBITDA_M"] > 0)
    df["EVEBIT_NTM"]    = (df["EV_M"] / df["NTM_EBIT_M"]).where(df["NTM_EBIT_M"]   > 0)

    # NTM P/E: PE_LTM scaled by consensus EPS growth (EPS items are per-share in same currency)
    # If we have both NTM_EPS and previous year actual EPS the ratio gives growth.
    # Simplest approximation with available data: PE_NTM = PE_LTM (forward proxy label)
    df["PE_NTM"] = df["PE_LTM"]

    df["FCF_YIELD_NTM"] = df["FCF_YIELD_LTM"]  # LTM proxy (no NTM FCF consensus item)

    df["NET_DEBT_EBITDA_NTM"] = (df["NET_DEBT_M"] / df["NTM_EBITDA_M"]).where(df["NTM_EBITDA_M"] > 0)

    # LTM implied Sales = MktCap / P/S
    df["SALES_LTM_M"] = (df["MKT_CAP"] / df["PSALES_LTM"]).where(df["PSALES_LTM"] > 0)
    df["SALES_GR_NTM"] = ((df["NTM_SALES_M"] / df["SALES_LTM_M"]) - 1).where(df["SALES_LTM_M"] > 0) * 100
    df["EBIT_GR_NTM"]  = ((df["NTM_EBIT_M"]  / df["EBITDA_LTM_M"]) - 1).where(df["EBITDA_LTM_M"] > 0) * 100
    df["EPS_GR_NTM"]   = df["EPS_GR_LTM"]  # proxy

    # FCF Margin (LTM)
    df["FCF_MARGIN"] = (df["FCF_LTM_M"] / df["SALES_LTM_M"] * 100).where(df["SALES_LTM_M"] > 0)

    return df


def fetch_earnings_calendar(days_ahead: int = 14, region_filter: str = "ALL") -> pd.DataFrame:
    """Fetch upcoming earnings events from FactSet EVT_V1 with consensus estimates.

    Joins CE_EVENTS → CE_EVENTS_COVERAGE → CE_SEC_ENTITY → SYM_TICKER_REGION
    and enriches each company row with NTM consensus EPS + Sales from FE_BASIC_CONH_QF.

    Parameters
    ----------
    days_ahead : int
        How many calendar days ahead to look (e.g. 7, 14, 30).
    region_filter : str
        'US', 'GB', 'EUR' (matches FR/DE/NL/IT/ES), or 'ALL'.

    Returns
    -------
    DataFrame with columns:
        EVENT_DATE, MARKET_TIME, TITLE, FISCAL_PERIOD, FISCAL_YEAR,
        PROJECTED, FSYM_ID, TICKER_REGION, TICKER, COMPANY_NAME,
        EPS_CONSENSUS, SALES_CONSENSUS, EPS_NUM_EST, CURRENCY
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    # Build region clause
    _EUR_REGIONS = ("FR", "DE", "NL", "IT", "ES", "BE", "PT", "FI", "AT", "IE")
    if region_filter == "US":
        region_clause = "AND tr.TICKER_REGION LIKE '%-US'"
    elif region_filter == "GB":
        region_clause = "AND tr.TICKER_REGION LIKE '%-GB'"
    elif region_filter == "EUR":
        eur_parts = " OR ".join(f"tr.TICKER_REGION LIKE '%-{r}'" for r in _EUR_REGIONS)
        region_clause = f"AND ({eur_parts})"
    else:
        region_clause = ""

    sql = f"""
        WITH upcoming AS (
            SELECT
                e.EVENT_ID,
                CAST(e.EVENT_DATETIME_UTC AS DATE)  AS EVENT_DATE,
                e.MARKET_TIME,
                e.TITLE,
                e.FISCAL_PERIOD,
                e.FISCAL_YEAR,
                e.PROJECTED,
                ec.FACTSET_ENTITY_ID
            FROM FACTSET.EVT_V1.CE_EVENTS e
            JOIN FACTSET.EVT_V1.CE_EVENTS_COVERAGE ec ON ec.EVENT_ID = e.EVENT_ID
            WHERE e.EVENT_DATETIME_UTC >= CURRENT_TIMESTAMP()
              AND e.EVENT_DATETIME_UTC <= DATEADD(day, {int(days_ahead)}, CURRENT_TIMESTAMP())
              AND e.EVENT_TYPE = 'ER'
        ),
        with_security AS (
            SELECT
                u.*,
                cov.FSYM_ID,
                tr.TICKER_REGION,
                SPLIT_PART(tr.TICKER_REGION, '-', 1)  AS TICKER,
                cov.PROPER_NAME                        AS COMPANY_NAME
            FROM upcoming u
            -- CE_SEC_ENTITY gives a -S security ID; bridge to regional via SYM_COVERAGE
            JOIN FACTSET.EVT_V1.CE_SEC_ENTITY se
                ON se.FACTSET_ENTITY_ID = u.FACTSET_ENTITY_ID
            JOIN FACTSET.SYM_V1.SYM_COVERAGE cov
                ON cov.FSYM_PRIMARY_EQUITY_ID = se.FSYM_ID
               AND cov.REGIONAL_FLAG = TRUE
               AND cov.UNIVERSE_TYPE  = 'EQ'
               AND cov.FREF_SECURITY_TYPE IN ('SHARE', 'PREFEQ', 'ADR', 'GDR', 'NVDR')
            JOIN FACTSET.SYM_V1.SYM_TICKER_REGION tr
                ON tr.FSYM_ID = cov.FSYM_ID
            {region_clause}
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY u.EVENT_ID
                ORDER BY CASE WHEN tr.TICKER_REGION LIKE '%-US' THEN 0 ELSE 1 END,
                         tr.TICKER_REGION
            ) = 1
        ),
        with_mktcap AS (
            SELECT
                ws.*,
                mkt.FF_MKT_VAL AS MKT_CAP_M
            FROM with_security ws
            LEFT JOIN (
                SELECT FSYM_ID, FF_MKT_VAL,
                       ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
                FROM FACTSET.FF_V3.FF_BASIC_DER_LTM
            ) mkt ON mkt.FSYM_ID = ws.FSYM_ID AND mkt.rn = 1
        ),
        with_sector AS (
            SELECT
                wm.*,
                sec_map.FACTSET_SECTOR_DESC AS SECTOR,
                ind_map.FACTSET_INDUSTRY_DESC AS INDUSTRY
            FROM with_mktcap wm
            LEFT JOIN FACTSET.SYM_V1.SYM_ENTITY_SECTOR es
                ON es.FACTSET_ENTITY_ID = wm.FACTSET_ENTITY_ID
            LEFT JOIN FACTSET.REF_V2.FACTSET_SECTOR_MAP sec_map
                ON sec_map.FACTSET_SECTOR_CODE = es.SECTOR_CODE
            LEFT JOIN FACTSET.REF_V2.FACTSET_INDUSTRY_MAP ind_map
                ON ind_map.FACTSET_INDUSTRY_CODE = es.INDUSTRY_CODE
        ),
        ntm_eps AS (
            SELECT FSYM_ID, FE_MEAN AS EPS_CONSENSUS, FE_NUM_EST AS EPS_NUM_EST, CURRENCY,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY FE_FP_END ASC) AS rn
            FROM FACTSET.FE_V4.FE_BASIC_CONH_QF
            WHERE FSYM_ID IN (SELECT DISTINCT FSYM_ID FROM with_sector)
              AND FE_ITEM = 'EPS'
              AND FE_FP_END >= CURRENT_DATE()
              AND CONS_END_DATE IS NULL
        ),
        ntm_sales AS (
            SELECT FSYM_ID, FE_MEAN AS SALES_CONSENSUS,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY FE_FP_END ASC) AS rn
            FROM FACTSET.FE_V4.FE_BASIC_CONH_QF
            WHERE FSYM_ID IN (SELECT DISTINCT FSYM_ID FROM with_sector)
              AND FE_ITEM = 'SALES'
              AND FE_FP_END >= CURRENT_DATE()
              AND CONS_END_DATE IS NULL
        )
        SELECT
            ws.EVENT_DATE,
            ws.MARKET_TIME,
            ws.TITLE,
            ws.FISCAL_PERIOD,
            ws.FISCAL_YEAR,
            ws.PROJECTED,
            ws.FSYM_ID,
            ws.TICKER_REGION,
            ws.TICKER,
            ws.COMPANY_NAME,
            ws.MKT_CAP_M,
            ws.SECTOR,
            ws.INDUSTRY,
            eps.EPS_CONSENSUS,
            sales.SALES_CONSENSUS,
            eps.EPS_NUM_EST,
            eps.CURRENCY
        FROM with_sector ws
        LEFT JOIN ntm_eps   eps   ON eps.FSYM_ID   = ws.FSYM_ID AND eps.rn   = 1
        LEFT JOIN ntm_sales sales ON sales.FSYM_ID = ws.FSYM_ID AND sales.rn = 1
        ORDER BY ws.EVENT_DATE ASC, ws.COMPANY_NAME ASC
    """

    cur.execute(sql)
    rows = cur.fetchall()
    cols = ["EVENT_DATE", "MARKET_TIME", "TITLE", "FISCAL_PERIOD", "FISCAL_YEAR",
            "PROJECTED", "FSYM_ID", "TICKER_REGION", "TICKER", "COMPANY_NAME",
            "MKT_CAP_M", "SECTOR", "INDUSTRY",
            "EPS_CONSENSUS", "SALES_CONSENSUS", "EPS_NUM_EST", "CURRENCY"]
    df = pd.DataFrame(rows, columns=cols)

    if not df.empty:
        df["EVENT_DATE"] = pd.to_datetime(df["EVENT_DATE"])
        for col in ["EPS_CONSENSUS", "SALES_CONSENSUS", "EPS_NUM_EST"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        # Human-readable timing
        df["TIMING"] = df["MARKET_TIME"].map({
            "B": "Pre-Market", "A": "After Close",
            "S": "After Close", "U": "Time TBC",
        }).fillna("Time TBC")
        df["CONFIRMED"] = ~df["PROJECTED"].astype(bool)

    return df


# ── Factor Tilt functions ─────────────────────────────────────────────────────

# Style factor definitions for GEMLTL model
GEMLTL_STYLE_FACTORS = {
    "GEMLT_BETA":     "Beta",
    "GEMLT_BTOP":     "Book-to-Price",
    "GEMLT_DIVYILD":  "Dividend Yield",
    "GEMLT_EARNQLTY": "Earnings Quality",
    "GEMLT_EARNVAR":  "Earnings Variability",
    "GEMLT_EARNYILD": "Earnings Yield",
    "GEMLT_GROWTH":   "Growth",
    "GEMLT_INVSQLTY": "Investment Quality",
    "GEMLT_LEVERAGE": "Leverage",
    "GEMLT_LIQUIDTY": "Liquidity",
    "GEMLT_LTREVRSL": "Long-Term Reversal",
    "GEMLT_MIDCAP":   "Mid Cap",
    "GEMLT_MOMENTUM": "Momentum",
    "GEMLT_PROFIT":   "Profitability",
    "GEMLT_RESVOL":   "Residual Volatility",
    "GEMLT_SIZE":     "Size",
}


def fetch_portfolio_factor_snapshot(
    holdings_dict: dict,
    model: str = "GEMLTL",
    factors: list = None,
    isin_override: dict = None,
) -> pd.DataFrame:
    """Compute weighted-average Barra style factor exposures for a portfolio snapshot.

    Parameters
    ----------
    holdings_dict : dict
        {yahoo_ticker: weight_pct} e.g. {'AAPL': 25.3, 'MSFT': 18.2}
    model : str
        Barra model, default 'GEMLTL'.
    factors : list[str] or None
        FACTOR codes to include. None = all Risk Indices.
    isin_override : dict or None
        {TICKER: ISIN} — these ISINs are used directly, bypassing the
        FactSet ticker lookup for those tickers.

    Returns
    -------
    DataFrame with columns:
        FACTOR, FACTOR_NAME, PORTFOLIO_SCORE, COVERAGE_PCT,
        MATCHED_TICKERS, UNMATCHED_TICKERS
    """
    if not holdings_dict:
        return pd.DataFrame()

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    isin_override = isin_override or {}

    # ── Step 1: resolve tickers → ISIN ───────────────────────────────────
    # Use stored ISINs first; fall back to FactSet lookup for the rest.
    ticker_isin = {}

    # Apply stored overrides immediately
    for ticker, weight in holdings_dict.items():
        stored_isin = isin_override.get(ticker.upper())
        if stored_isin:
            ticker_isin[ticker] = {"isin": stored_isin, "weight": weight}

    # FactSet lookup for tickers not covered by stored ISINs
    need_lookup = [t for t in holdings_dict if t not in ticker_isin]
    if need_lookup:
        fs_tickers = {t: _to_factset_ticker(t) for t in need_lookup}
        fs_list = list(set(fs_tickers.values()))
        ph = ", ".join("'{}'".format(t) for t in fs_list)

        cur.execute("""
            SELECT tr.TICKER_REGION, si.ISIN
            FROM FACTSET.SYM_V1.SYM_TICKER_REGION tr
            JOIN FACTSET.SYM_V1.SYM_COVERAGE cov ON cov.FSYM_ID = tr.FSYM_ID
            JOIN FACTSET.SYM_V1.SYM_ISIN si
                ON si.FSYM_ID = COALESCE(cov.FSYM_PRIMARY_EQUITY_ID, tr.FSYM_ID)
            WHERE tr.TICKER_REGION IN ({})
              AND si.ISIN IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY tr.TICKER_REGION
                ORDER BY (CASE WHEN si.ISIN LIKE 'US%' THEN 0 ELSE 1 END), si.ISIN
            ) = 1
        """.format(ph))
        fs_to_isin = {r[0]: r[1] for r in cur.fetchall()}

        # Fallback: SYM_ISIN_HIST for anything still unresolved
        unresolved = [t for t in fs_list if t not in fs_to_isin]
        if unresolved:
            ph2 = ", ".join("'{}'".format(t) for t in unresolved)
            cur.execute("""
                SELECT tr.TICKER_REGION, si.ISIN
                FROM FACTSET.SYM_V1.SYM_TICKER_REGION tr
                JOIN FACTSET.SYM_V1.SYM_ISIN_HIST si ON si.FSYM_ID = tr.FSYM_ID
                WHERE tr.TICKER_REGION IN ({})
                  AND si.ISIN IS NOT NULL
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY tr.TICKER_REGION
                    ORDER BY si.END_DATE DESC NULLS FIRST, si.ISIN
                ) = 1
            """.format(ph2))
            for r in cur.fetchall():
                if r[0] not in fs_to_isin:
                    fs_to_isin[r[0]] = r[1]

        for orig_ticker in need_lookup:
            fs_t = fs_tickers[orig_ticker]
            isin = fs_to_isin.get(fs_t)
            if isin:
                ticker_isin[orig_ticker] = {"isin": isin, "weight": holdings_dict[orig_ticker]}

    if not ticker_isin:
        return pd.DataFrame()

    matched_tickers = sorted(ticker_isin.keys())
    unmatched_tickers = sorted(
        t for t in holdings_dict if t not in ticker_isin
    )

    # Total weight of matched positions
    total_weight = sum(v["weight"] for v in ticker_isin.values())
    coverage_pct = total_weight / sum(holdings_dict.values()) * 100 if holdings_dict else 0

    # ── Step 2: ISIN → BARRA_ID → latest factor exposures ───────────────
    isin_list = [v["isin"] for v in ticker_isin.values()]
    isin_ph = ", ".join(f"'{i}'" for i in isin_list)

    factor_clause = ""
    if factors:
        flist = ", ".join(f"'{f}'" for f in factors)
        factor_clause = f"AND exp.FACTOR IN ({flist})"

    # Build VALUES clause for weights: (ISIN, WEIGHT)
    weights_vals = ", ".join(
        "('{}', {})".format(v["isin"], v["weight"])
        for v in ticker_isin.values()
    )

    # Build ticker-to-isin VALUES for matched/unmatched lookup
    ticker_isin_vals = ", ".join(
        "('{}', '{}')".format(orig, v["isin"])
        for orig, v in ticker_isin.items()
    )

    sql = f"""
    WITH holdings AS (
        SELECT column1 AS ISIN, column2 AS WEIGHT
        FROM VALUES {weights_vals}
    ),
    with_barra AS (
        SELECT h.ISIN, h.WEIGHT, sec.BARRA_ID
        FROM holdings h
        JOIN MSCI.INDEX.SECURITY sec ON sec.ISIN = h.ISIN
        QUALIFY ROW_NUMBER() OVER (PARTITION BY h.ISIN ORDER BY sec.CALC_DATE DESC) = 1
    ),
    latest_date AS (
        SELECT MAX(DATE_OF_DATA) AS MAX_DATE
        FROM MSCI.ANALYTICS.ASSET_EXPOSURES_TS
        WHERE MODEL = '{model}'
          AND FACTOR_GROUP = 'Risk Indices'
    ),
    exposures AS (
        SELECT
            wb.ISIN,
            wb.WEIGHT,
            exp.FACTOR,
            exp.FACTOR_NAME,
            exp.EXPOSURE
        FROM with_barra wb
        CROSS JOIN latest_date ld
        JOIN MSCI.ANALYTICS.ASSET_EXPOSURES_TS exp
            ON exp.BARRA_ID = wb.BARRA_ID
           AND exp.DATE_OF_DATA = ld.MAX_DATE
           AND exp.MODEL = '{model}'
           AND exp.FACTOR_GROUP = 'Risk Indices'
           {factor_clause}
    )
    SELECT
        FACTOR,
        FACTOR_NAME,
        SUM(WEIGHT * EXPOSURE) / NULLIF(SUM(WEIGHT), 0) AS PORTFOLIO_SCORE
    FROM exposures
    GROUP BY FACTOR, FACTOR_NAME
    ORDER BY FACTOR_NAME
    """

    cur.execute(sql)
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["FACTOR", "FACTOR_NAME", "PORTFOLIO_SCORE"])
    df["PORTFOLIO_SCORE"] = pd.to_numeric(df["PORTFOLIO_SCORE"], errors="coerce")
    df["COVERAGE_PCT"] = round(coverage_pct, 1)
    df["MATCHED_TICKERS"] = ", ".join(matched_tickers)
    df["UNMATCHED_TICKERS"] = ", ".join(unmatched_tickers)
    return df


def fetch_fund_list() -> pd.DataFrame:
    """Return list of MIF funds that have MSCI-matchable equity holdings.

    Returns DataFrame: MIL_FUND_KEY, FUND_NAME, FUND_CODE, FUND_ASSET_CLASS, FUND_CURRENCY
    Filters to CURRENT_ROW_INDICATOR=1 (active records only).
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute("""
        SELECT DISTINCT
            f.MIL_FUND_KEY,
            f.FUND_NAME,
            f.FUND_CODE,
            f.FUND_ASSET_CLASS,
            f.FUND_CURRENCY
        FROM PROD_MED_DATAHUB.DIMENSIONAL_WAREHOUSE.MIL_FUND_POSITION p
        JOIN PROD_MED_DATAHUB.DIMENSIONAL_WAREHOUSE.MIL_FUND_DIMENSION f
            ON f.MIL_FUND_KEY = p.MIL_FUND_KEY
           AND f.CURRENT_ROW_INDICATOR = 1
        WHERE f.FUND_NAME IS NOT NULL
        ORDER BY f.FUND_NAME
    """)
    rows = cur.fetchall()
    cols = ["MIL_FUND_KEY", "FUND_NAME", "FUND_CODE", "FUND_ASSET_CLASS", "FUND_CURRENCY"]
    return pd.DataFrame(rows, columns=cols)


def fetch_factor_tilt_history(
    fund_key: int,
    model: str = "GEMLTL",
    factors: list = None,
    start_date: str = "2022-01-01",
    end_date: str = None,
) -> pd.DataFrame:
    """Compute portfolio weighted-average Barra factor exposures over time.

    For each month-end date in the fund's history:
      1. Get equity positions (ISIN + weight)
      2. Join to MSCI SECURITY table to get BARRA_ID
      3. Join to ASSET_EXPOSURES_TS for factor exposures
      4. Compute weighted average exposure per factor

    Parameters
    ----------
    fund_key : int
        MIL_FUND_KEY identifier.
    model : str
        Barra model name, default 'GEMLTL'.
    factors : list[str] or None
        List of FACTOR codes to filter (e.g. ['GEMLT_GROWTH', 'GEMLT_MOMENTUM']).
        None = all Risk Indices style factors.
    start_date : str
        ISO date string, default '2022-01-01'.
    end_date : str or None
        ISO date string, default today.

    Returns
    -------
    DataFrame with columns: DATE, FACTOR, FACTOR_NAME, PORTFOLIO_SCORE, COVERAGE_PCT
    """
    import datetime as _dt
    if end_date is None:
        end_date = str(_dt.date.today())

    factor_clause = ""
    if factors:
        flist = ", ".join(f"'{f}'" for f in factors)
        factor_clause = f"AND exp.FACTOR IN ({flist})"

    sql = f"""
    WITH positions AS (
        SELECT
            d.CALENDAR_DATE,
            inst.ISIN_INSTRUMENT_REFERENCE    AS ISIN,
            p.FA_MIL_FUND_ACTUAL_WEIGHT_PCNT  AS WEIGHT
        FROM PROD_MED_DATAHUB.DIMENSIONAL_WAREHOUSE.MIL_FUND_POSITION p
        JOIN PROD_MED_DATAHUB.DIMENSIONAL_WAREHOUSE.DATE_DIMENSION d
            ON d.DATE_KEY = p.POSITION_DATE_KEY
        JOIN PROD_MED_DATAHUB.DIMENSIONAL_WAREHOUSE.MIL_FUND_DIMENSION f
            ON f.MIL_FUND_KEY = p.MIL_FUND_KEY
           AND f.CURRENT_ROW_INDICATOR = 1
        JOIN PROD_MED_DATAHUB.DIMENSIONAL_WAREHOUSE.INSTRUMENT_DIMENSION inst
            ON inst.INSTRUMENT_KEY = p.INSTRUMENT_KEY
           AND inst.CURRENT_ROW_INDICATOR = 1
        WHERE p.MIL_FUND_KEY = {int(fund_key)}
          AND d.CALENDAR_DATE BETWEEN '{start_date}' AND '{end_date}'
          AND LAST_DAY(d.CALENDAR_DATE) = d.CALENDAR_DATE
          AND inst.ISIN_INSTRUMENT_REFERENCE IS NOT NULL
          AND p.FA_MIL_FUND_ACTUAL_WEIGHT_PCNT > 0
    ),
    with_barra AS (
        SELECT
            pos.CALENDAR_DATE,
            pos.WEIGHT,
            sec.BARRA_ID
        FROM positions pos
        JOIN MSCI.INDEX.SECURITY sec
            ON sec.ISIN = pos.ISIN
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY pos.CALENDAR_DATE, pos.ISIN
            ORDER BY sec.CALC_DATE DESC
        ) = 1
    ),
    exposures AS (
        SELECT
            wb.CALENDAR_DATE,
            exp.FACTOR,
            exp.FACTOR_NAME,
            wb.WEIGHT,
            exp.EXPOSURE
        FROM with_barra wb
        JOIN MSCI.ANALYTICS.ASSET_EXPOSURES_TS exp
            ON exp.BARRA_ID = wb.BARRA_ID
           AND exp.DATE_OF_DATA = wb.CALENDAR_DATE
           AND exp.MODEL = '{model}'
           AND exp.FACTOR_GROUP = 'Risk Indices'
           {factor_clause}
    ),
    coverage AS (
        SELECT
            CALENDAR_DATE,
            SUM(WEIGHT) AS TOTAL_MATCHED_WEIGHT
        FROM with_barra
        GROUP BY CALENDAR_DATE
    ),
    total_weight AS (
        SELECT
            CALENDAR_DATE,
            SUM(WEIGHT) AS TOTAL_WEIGHT
        FROM positions
        GROUP BY CALENDAR_DATE
    )
    SELECT
        e.CALENDAR_DATE         AS DATE,
        e.FACTOR,
        e.FACTOR_NAME,
        SUM(e.WEIGHT * e.EXPOSURE) / NULLIF(SUM(e.WEIGHT), 0) AS PORTFOLIO_SCORE,
        c.TOTAL_MATCHED_WEIGHT / NULLIF(tw.TOTAL_WEIGHT, 0) * 100 AS COVERAGE_PCT
    FROM exposures e
    JOIN coverage c   ON c.CALENDAR_DATE = e.CALENDAR_DATE
    JOIN total_weight tw ON tw.CALENDAR_DATE = e.CALENDAR_DATE
    GROUP BY e.CALENDAR_DATE, e.FACTOR, e.FACTOR_NAME, c.TOTAL_MATCHED_WEIGHT, tw.TOTAL_WEIGHT
    ORDER BY e.CALENDAR_DATE, e.FACTOR
    """

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
    cur.execute(sql)
    rows = cur.fetchall()
    cols = ["DATE", "FACTOR", "FACTOR_NAME", "PORTFOLIO_SCORE", "COVERAGE_PCT"]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["DATE"] = pd.to_datetime(df["DATE"])
        df["PORTFOLIO_SCORE"] = pd.to_numeric(df["PORTFOLIO_SCORE"], errors="coerce")
        df["COVERAGE_PCT"] = pd.to_numeric(df["COVERAGE_PCT"], errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Comps Table — LTM + 1BF/2BF consensus for a list of fsym_ids
# ─────────────────────────────────────────────────────────────────────────────

def fetch_comps_table(fsym_ids: list) -> pd.DataFrame:
    """Return a wide DataFrame for a Comps Table page.

    For each fsym_id, returns LTM + 1BF (FY1) + 2BF (FY2) snapshots of:
      - Mkt Cap (USD mn), EV (USD mn)
      - P/E LTM / 1BF / 2BF
      - P/B LTM / 1BF / 2BF
      - EV/EBITDA LTM / 1BF / 2BF
      - ROE LTM / 1BF / 2BF
      - PEG (FY1 P/E / 2-year EPS CAGR)
      - EPS Growth (FY1 → FY2)
      - OPM LTM / 1BF
      - Dividend Yield LTM / 1BF

    All native amounts (MKT_CAP, EV) are converted to USD millions using
    spot FX from MSCI.INDEX.CURRENCY_EXCHANGE_RATES.
    """
    if not fsym_ids:
        return pd.DataFrame()

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")

    ids_str = ", ".join(f"'{fid}'" for fid in fsym_ids)

    # ── 1) LTM fundamentals + most recent annual + latest price ─────────
    #     FF_BASIC_DER_LTM  → MktCap, P/E, OPM, EBITDA, EPS, currency
    #     FF_ADVANCED_DER_LTM → Div Yield, EBIT margin (OPM proxy)
    #     FF_BASIC_DER_AF   → P/B, ROE, Net Debt, BPS, DPS (annual only)
    #     FP_BASIC_PRICES   → latest market price
    cur.execute(f"""
        WITH ltm_b AS (
            SELECT FSYM_ID, DATE, CURRENCY,
                   FF_MKT_VAL, FF_PE, FF_EBITDA_OPER,
                   FF_EPS_DIL, FF_OPER_MGN,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_BASIC_DER_LTM
            WHERE FSYM_ID IN ({ids_str})
        ),
        ltm_a AS (
            SELECT FSYM_ID, DATE,
                   FF_DIV_YLD       AS DIV_YLD_A,
                   FF_EBIT_OPER_MGN,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_ADVANCED_DER_LTM
            WHERE FSYM_ID IN ({ids_str})
        ),
        ann_der AS (
            SELECT FSYM_ID, DATE,
                   FF_PBK, FF_ROE, FF_NET_DEBT,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_BASIC_DER_AF
            WHERE FSYM_ID IN ({ids_str})
        ),
        ann_act AS (
            SELECT FSYM_ID, DATE,
                   FF_BPS, FF_DPS,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY DATE DESC) AS rn
            FROM FACTSET.FF_V3.FF_BASIC_AF
            WHERE FSYM_ID IN ({ids_str})
        ),
        latest_px AS (
            SELECT FSYM_ID, P_DATE, P_PRICE, CURRENCY AS PX_CCY,
                   ROW_NUMBER() OVER (PARTITION BY FSYM_ID ORDER BY P_DATE DESC) AS rn
            FROM FACTSET.FP_V2.FP_BASIC_PRICES
            WHERE FSYM_ID IN ({ids_str})
              AND P_DATE >= DATEADD(day, -30, CURRENT_DATE())
        )
        SELECT b.FSYM_ID, b.DATE, b.CURRENCY,
               b.FF_MKT_VAL,
               b.FF_PE,
               b.FF_EBITDA_OPER,
               b.FF_EPS_DIL,
               b.FF_OPER_MGN,
               a.DIV_YLD_A,
               a.FF_EBIT_OPER_MGN,
               ad.FF_PBK,
               ad.FF_ROE,
               ad.FF_NET_DEBT,
               aa.FF_BPS,
               aa.FF_DPS,
               p.P_PRICE, p.PX_CCY
        FROM ltm_b b
        LEFT JOIN ltm_a    a  ON a.FSYM_ID  = b.FSYM_ID AND a.rn  = 1
        LEFT JOIN ann_der  ad ON ad.FSYM_ID = b.FSYM_ID AND ad.rn = 1
        LEFT JOIN ann_act  aa ON aa.FSYM_ID = b.FSYM_ID AND aa.rn = 1
        LEFT JOIN latest_px p ON p.FSYM_ID  = b.FSYM_ID AND p.rn  = 1
        WHERE b.rn = 1
    """)
    rows = cur.fetchall()
    cols = ["FSYM_ID", "LTM_DATE", "CURRENCY",
            "MKT_CAP_LOC",
            "PE_LTM",
            "EBITDA_LTM",
            "EPS_LTM",
            "OPM_LTM_BASIC",
            "DIV_YLD_LTM",
            "EBIT_MGN_LTM",
            "PB_LTM",
            "ROE_LTM",
            "NET_DEBT_LOC",
            "BPS_LTM",
            "DPS_LTM",
            "PRICE", "PX_CCY"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    # Prefer EBIT margin from Advanced (OPM-style); fall back to Basic OPM
    df["OPM_LTM"] = pd.to_numeric(df["EBIT_MGN_LTM"], errors="coerce")
    df["OPM_LTM"] = df["OPM_LTM"].fillna(pd.to_numeric(df["OPM_LTM_BASIC"], errors="coerce"))

    # ── 2) Ticker + Name lookup ─────────────────────────────────────────
    cur.execute(f"""
        SELECT tr.FSYM_ID, MIN(tr.TICKER_REGION) AS TICKER_REGION,
               MAX(cov.PROPER_NAME)             AS NAME
        FROM FACTSET.SYM_V1.SYM_TICKER_REGION tr
        JOIN FACTSET.SYM_V1.SYM_COVERAGE cov ON cov.FSYM_ID = tr.FSYM_ID
        WHERE tr.FSYM_ID IN ({ids_str})
          AND cov.REGIONAL_FLAG = TRUE
          AND cov.UNIVERSE_TYPE = 'EQ'
        GROUP BY tr.FSYM_ID
    """)
    name_rows = cur.fetchall()
    df_names = pd.DataFrame(name_rows, columns=["FSYM_ID", "TICKER", "NAME"])
    df = df.merge(df_names, on="FSYM_ID", how="left")

    # ── 3) Consensus FY1 + FY2 for all needed items ─────────────────────
    items = ["EPS", "EBITDA", "EBIT", "SALES", "DPS", "BPS"]
    items_str = ", ".join(f"'{it}'" for it in items)
    cur.execute(f"""
        WITH fcast AS (
            SELECT FSYM_ID, FE_ITEM, FE_MEAN, FE_FP_END,
                   ROW_NUMBER() OVER (
                       PARTITION BY FSYM_ID, FE_ITEM
                       ORDER BY FE_FP_END ASC
                   ) AS fy_rank
            FROM FACTSET.FE_V4.FE_BASIC_CONH_AF
            WHERE FSYM_ID IN ({ids_str})
              AND FE_ITEM IN ({items_str})
              AND FE_FP_END >= CURRENT_DATE()
              AND CONS_END_DATE IS NULL
        )
        SELECT FSYM_ID, FE_ITEM, fy_rank, FE_MEAN, FE_FP_END
        FROM fcast
        WHERE fy_rank IN (1, 2)
    """)
    fc_rows = cur.fetchall()
    df_fc = pd.DataFrame(fc_rows, columns=["FSYM_ID", "FE_ITEM", "FY_RANK", "FE_MEAN", "FE_FP_END"])

    # Pivot to wide: one column per ITEM_FY
    if not df_fc.empty:
        df_fc["KEY"] = df_fc["FE_ITEM"] + "_FY" + df_fc["FY_RANK"].astype(str)
        df_wide = df_fc.pivot_table(
            index="FSYM_ID", columns="KEY", values="FE_MEAN", aggfunc="first"
        ).reset_index()
        df_wide.columns.name = None
    else:
        df_wide = pd.DataFrame({"FSYM_ID": list(fsym_ids)})

    for col in [
        "EPS_FY1", "EPS_FY2", "EBITDA_FY1", "EBITDA_FY2",
        "EBIT_FY1", "EBIT_FY2", "SALES_FY1", "SALES_FY2",
        "DPS_FY1", "DPS_FY2", "BPS_FY1", "BPS_FY2",
    ]:
        if col not in df_wide.columns:
            df_wide[col] = None

    df = df.merge(df_wide, on="FSYM_ID", how="left")

    # ── 4) FX → USD ─────────────────────────────────────────────────────
    needed_ccys = set(df["CURRENCY"].dropna().astype(str).tolist())
    needed_ccys.update(df["PX_CCY"].dropna().astype(str).tolist())
    needed_ccys.discard("USD")
    fx_map = {"USD": 1.0}
    if needed_ccys:
        try:
            ph = ",".join("'" + c + "'" for c in needed_ccys)
            cur.execute(f"""
                WITH ranked AS (
                    SELECT ISO_CURRENCY_SYMBOL, SPOT_FX_EOD00D, CALC_DATE,
                           ROW_NUMBER() OVER (
                               PARTITION BY ISO_CURRENCY_SYMBOL
                               ORDER BY CALC_DATE DESC
                           ) AS rn
                    FROM MSCI.INDEX.CURRENCY_EXCHANGE_RATES
                    WHERE ISO_CURRENCY_SYMBOL IN ({ph})
                      AND CALC_DATE >= DATEADD(day, -10, CURRENT_DATE())
                      AND SPOT_FX_EOD00D IS NOT NULL
                )
                SELECT ISO_CURRENCY_SYMBOL, SPOT_FX_EOD00D
                FROM ranked WHERE rn = 1
            """)
            for ccy, rate in cur.fetchall():
                if rate:
                    # MSCI stores units of CCY per 1 USD → divide LOC by rate to get USD
                    fx_map[ccy] = float(rate)
        except Exception:
            pass

    def _to_usd(amount_loc, ccy):
        if amount_loc is None or pd.isna(amount_loc):
            return None
        if ccy is None or ccy not in fx_map:
            return None
        rate = fx_map[ccy]
        if rate == 0:
            return None
        return float(amount_loc) / rate  # LOC / (LOC per USD) = USD

    # ── 5) Convert + compute ratios ─────────────────────────────────────
    for c in [
        "MKT_CAP_LOC", "PE_LTM", "PB_LTM", "DIV_YLD_LTM", "EBITDA_LTM",
        "NET_DEBT_LOC", "EPS_LTM", "BPS_LTM", "OPM_LTM", "ROE_LTM",
        "DPS_LTM", "PRICE",
        "EPS_FY1", "EPS_FY2", "EBITDA_FY1", "EBITDA_FY2",
        "EBIT_FY1", "EBIT_FY2", "SALES_FY1", "SALES_FY2",
        "DPS_FY1", "DPS_FY2", "BPS_FY1", "BPS_FY2",
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["MKT_CAP_USD_M"]  = df.apply(lambda r: _to_usd(r["MKT_CAP_LOC"], r["CURRENCY"]), axis=1)
    df["NET_DEBT_USD_M"] = df.apply(lambda r: _to_usd(r["NET_DEBT_LOC"], r["CURRENCY"]), axis=1)
    df["EV_USD_M"]       = df["MKT_CAP_USD_M"] + df["NET_DEBT_USD_M"].fillna(0)

    # EV in local currency (millions) — used to compute EV/EBITDA forward
    df["EV_LOC_M"]       = df["MKT_CAP_LOC"] + df["NET_DEBT_LOC"].fillna(0)

    # Forward P/E = Price / EPS_FYn
    df["PE_FY1"] = (df["PRICE"] / df["EPS_FY1"]).where(df["EPS_FY1"] > 0)
    df["PE_FY2"] = (df["PRICE"] / df["EPS_FY2"]).where(df["EPS_FY2"] > 0)

    # Forward P/B: prefer consensus BPS if available; otherwise grow LTM BPS
    #   by retained earnings (BPS_FY1 ≈ BPS_LTM + EPS_FY1*(1-payout))
    # Most consensus data won't have BPS, so proxy with LTM BPS
    bps_fy1 = df["BPS_FY1"].where(df["BPS_FY1"].notna(), df["BPS_LTM"])
    bps_fy2 = df["BPS_FY2"].where(df["BPS_FY2"].notna(), df["BPS_LTM"])
    df["PB_FY1"] = (df["PRICE"] / bps_fy1).where(bps_fy1 > 0)
    df["PB_FY2"] = (df["PRICE"] / bps_fy2).where(bps_fy2 > 0)

    # EV/EBITDA LTM
    df["EV_EBITDA_LTM"] = (df["EV_LOC_M"] / df["EBITDA_LTM"]).where(df["EBITDA_LTM"] > 0)

    # Forward EV/EBITDA: prefer consensus EBITDA; if not available, scale
    # LTM EBITDA by EPS growth (proportional profitability assumption)
    eps_growth_fy1 = (df["EPS_FY1"] / df["EPS_LTM"]).where(df["EPS_LTM"] > 0)
    eps_growth_fy2 = (df["EPS_FY2"] / df["EPS_LTM"]).where(df["EPS_LTM"] > 0)
    ebitda_fy1 = df["EBITDA_FY1"].fillna(df["EBITDA_LTM"] * eps_growth_fy1)
    ebitda_fy2 = df["EBITDA_FY2"].fillna(df["EBITDA_LTM"] * eps_growth_fy2)
    df["EV_EBITDA_FY1"] = (df["EV_LOC_M"] / ebitda_fy1).where(ebitda_fy1 > 0)
    df["EV_EBITDA_FY2"] = (df["EV_LOC_M"] / ebitda_fy2).where(ebitda_fy2 > 0)

    # Forward ROE proxy = EPS_FYn / BPS (%)
    df["ROE_FY1"] = (df["EPS_FY1"] / bps_fy1 * 100).where(bps_fy1 > 0)
    df["ROE_FY2"] = (df["EPS_FY2"] / bps_fy2 * 100).where(bps_fy2 > 0)

    # Forward OPM proxy = if consensus EBIT available use it; else use EPS growth as directional hint
    df["OPM_FY1"] = (df["EBIT_FY1"] / df["SALES_FY1"] * 100).where(df["SALES_FY1"] > 0)
    # If no EBIT consensus, leave as NaN (user table shows "?" for these)

    # Forward Div Yield = DPS_FY1 / Price (%)
    df["DIV_YLD_FY1"] = (df["DPS_FY1"] / df["PRICE"] * 100).where(df["PRICE"] > 0)

    # EPS Growth FY1 → FY2 and PEG
    df["EPS_GR_FY12"] = (df["EPS_FY2"] / df["EPS_FY1"] - 1).where(df["EPS_FY1"] > 0) * 100
    df["PEG"] = df["PE_FY1"] / df["EPS_GR_FY12"].where(df["EPS_GR_FY12"] != 0)

    return df
