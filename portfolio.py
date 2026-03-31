"""
Portfolio ledger & analytics — SQLite-backed transaction storage, FIFO P&L,
holdings computation, and daily portfolio time-series.

How to use
----------
Transactions are stored in a local SQLite file (portfolio.db) alongside Dash.py.
Supported sides: DEPOSIT, WITHDRAW, BUY, SELL.
  • DEPOSIT  – cash inflow  (funding the account)
  • WITHDRAW – cash outflow (taking money out)
  • BUY      – buy shares   (reduces cash, adds shares)
  • SELL     – sell shares   (increases cash, removes shares)

Start by adding a DEPOSIT row with your starting capital, then add BUY/SELL
rows as normal.  The equity curve, return, and drawdown are computed from the
daily portfolio value  =  market-value of holdings  +  cash balance.

Functions
---------
  init_db()                       → create the table if missing
  load_transactions()             → DataFrame of all txns
  add_transaction(...)            → insert one row, return new id
  delete_transaction(txn_id)      → remove one row
  import_csv(path_or_buf)         → bulk-insert from CSV
  export_csv()                    → return CSV string of all txns
  compute_holdings(txns, prices)  → holdings summary DataFrame + summary dict
  compute_portfolio_ts(txns, ...) → daily portfolio value / return / drawdown
"""

import io
import os
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime, date

import numpy as np
import pandas as pd
import yfinance as yf

# ─────────────────────────────────────────────────────────────────────────────
# SQLite helpers
# ─────────────────────────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio.db")

_VALID_SIDES = ("BUY", "SELL", "DEPOSIT", "WITHDRAW", "DIVIDEND", "INTEREST")


def _conn():
    return sqlite3.connect(_DB_PATH)


def init_db():
    """Create the transactions table if it doesn't exist.
    Migrates old tables that only allowed BUY/SELL.
    """
    _TARGET_COLS = ["id", "date", "ticker", "side", "quantity", "price",
                    "fees", "fx_rate", "notes", "total_gbp"]
    _CREATE_SQL = """
        CREATE TABLE transactions (
            id        TEXT PRIMARY KEY,
            date      TEXT NOT NULL,
            ticker    TEXT NOT NULL DEFAULT '',
            side      TEXT NOT NULL CHECK(side IN ('BUY','SELL','DEPOSIT','WITHDRAW','DIVIDEND','INTEREST')),
            quantity  REAL NOT NULL DEFAULT 0 CHECK(quantity >= 0),
            price     REAL NOT NULL DEFAULT 0 CHECK(price >= 0),
            fees      REAL NOT NULL DEFAULT 0,
            fx_rate   REAL NOT NULL DEFAULT 1.0,
            notes     TEXT DEFAULT '',
            total_gbp REAL DEFAULT NULL
        )
    """
    with _conn() as con:
        exists = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        ).fetchone()

        if exists:
            cols = [row[1] for row in con.execute("PRAGMA table_info(transactions)").fetchall()]
            if "total_gbp" in cols:
                con.execute("DROP TABLE IF EXISTS _txns_old")
                return
            try:
                leftover = con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='_txns_old'"
                ).fetchone()
                if leftover:
                    con.execute("DROP TABLE transactions")
                else:
                    con.execute("ALTER TABLE transactions RENAME TO _txns_old")
                con.execute(_CREATE_SQL)
                old_cols = [row[1] for row in con.execute("PRAGMA table_info(_txns_old)").fetchall()]
                src_parts = []
                for c in _TARGET_COLS:
                    if c in old_cols:
                        src_parts.append(c)
                    elif c == "fx_rate":
                        src_parts.append("1.0")
                    elif c == "total_gbp":
                        src_parts.append("NULL")
                    else:
                        src_parts.append(f"'' AS {c}")
                con.execute(f"""
                    INSERT INTO transactions ({', '.join(_TARGET_COLS)})
                    SELECT {', '.join(src_parts)} FROM _txns_old
                """)
                con.execute("DROP TABLE _txns_old")
            except Exception:
                con.execute(_CREATE_SQL.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS"))
        else:
            con.execute(_CREATE_SQL)


def load_transactions():
    """Return all transactions as a DataFrame, sorted by date then id."""
    init_db()
    with _conn() as con:
        df = pd.read_sql("SELECT * FROM transactions ORDER BY date, id", con)
    return df


def add_transaction(txn_date, ticker, side, quantity, price, fees=0.0, notes="", fx_rate=1.0, total_gbp=None):
    """Insert a single transaction. Returns the new id.

    For DEPOSIT / WITHDRAW the *price* field carries the cash amount (in GBP).
    For BUY / SELL the *price* is in the stock's currency; *fx_rate* converts
    it to GBP  (e.g. 0.79 for USD→GBP).  Cash impact = qty * price * fx_rate.

    If *total_gbp* is provided (the broker's actual settled GBP amount for the
    trade), it will be used for cash accounting instead of qty × price / fx.
    """
    init_db()
    side = side.upper().strip()
    if side not in _VALID_SIDES:
        raise ValueError(f"side must be one of {_VALID_SIDES}")
    txn_id = uuid.uuid4().hex[:12]

    # For cash-flow rows, ticker is "CASH" by convention, qty = 0
    if side in ("DEPOSIT", "WITHDRAW"):
        ticker = "CASH"
        quantity = 0
        fx_rate = 1.0          # deposits/withdrawals already in GBP
    elif side == "INTEREST":
        ticker = "CASH"
        quantity = 0
        fx_rate = 1.0
    elif side == "DIVIDEND":
        ticker = (ticker or "").upper().strip()
        quantity = 0
    else:
        ticker = (ticker or "").upper().strip()
        quantity = float(quantity)

    # Normalise total_gbp: None / NaN / 0 → NULL in the DB
    if total_gbp is not None:
        try:
            total_gbp = float(total_gbp)
            if pd.isna(total_gbp) or total_gbp == 0:
                total_gbp = None
        except (ValueError, TypeError):
            total_gbp = None

    with _conn() as con:
        con.execute(
            "INSERT INTO transactions (id, date, ticker, side, quantity, price, fees, fx_rate, notes, total_gbp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (txn_id, str(txn_date), ticker, side,
             float(quantity), float(price), float(fees or 0), float(fx_rate),
             notes or "", total_gbp),
        )
    return txn_id


def delete_transaction(txn_id):
    """Delete a transaction by id."""
    with _conn() as con:
        con.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))


def clear_all_transactions():
    """Delete ALL transactions from the ledger."""
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM transactions")


def _init_cash_override_table():
    """Create the cash_override table if needed."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS cash_override (
                id    INTEGER PRIMARY KEY CHECK(id = 1),
                value REAL NOT NULL
            )
        """)


def set_cash_override(amount):
    """Store a manual cash balance override (GBP)."""
    _init_cash_override_table()
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO cash_override (id, value) VALUES (1, ?)",
            (float(amount),),
        )


def get_cash_override():
    """Return the cash override value, or None if not set."""
    _init_cash_override_table()
    with _conn() as con:
        row = con.execute("SELECT value FROM cash_override WHERE id = 1").fetchone()
    return row[0] if row else None


def clear_cash_override():
    """Remove the cash override so calculated cash is used."""
    _init_cash_override_table()
    with _conn() as con:
        con.execute("DELETE FROM cash_override")


def import_csv(csv_text):
    """Bulk-insert transactions from CSV text. Returns count inserted."""
    df = pd.read_csv(io.StringIO(csv_text))
    required = {"date", "ticker", "side", "quantity", "price"}
    if not required.issubset(set(df.columns.str.lower())):
        raise ValueError(f"CSV must contain columns: {required}")
    df.columns = df.columns.str.lower()
    # Strip whitespace from string columns
    for col in ("ticker", "side", "notes"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    count = 0
    for _, row in df.iterrows():
        try:
            # Normalise date to ISO yyyy-mm-dd
            raw_date = str(row["date"]).strip()
            try:
                iso_date = pd.to_datetime(raw_date, dayfirst=True, format="mixed").strftime("%Y-%m-%d")
            except Exception:
                iso_date = raw_date

            def _safe(val, default=0.0):
                try:
                    v = float(val)
                    return default if pd.isna(v) else v
                except (ValueError, TypeError):
                    return default

            # total_gbp: accept 'total_gbp' or 'total' column
            raw_total = row.get("total_gbp") if "total_gbp" in df.columns else row.get("total")
            total_val = _safe(raw_total, 0) if raw_total is not None else None
            if total_val == 0:
                total_val = None

            add_transaction(
                txn_date=iso_date,
                ticker=row["ticker"],
                side=row["side"],
                quantity=abs(_safe(row["quantity"], 0)),
                price=abs(_safe(row["price"], 0)),
                fees=abs(_safe(row.get("fees"), 0)),
                notes=row.get("notes", "") if pd.notna(row.get("notes", "")) else "",
                fx_rate=_safe(row.get("fx_rate"), 1.0) or 1.0,
                total_gbp=abs(total_val) if total_val is not None else None,
            )
            count += 1
        except Exception:
            pass
    return count


def export_csv():
    """Return all transactions as a CSV string."""
    df = load_transactions()
    return df.to_csv(index=False)


# ─────────────────────────────────────────────────────────────────────────────
# Holdings & FIFO P&L
# ─────────────────────────────────────────────────────────────────────────────

def _fifo_lots(txns_df):
    """
    Walk through transactions in date order.  Track open lots per ticker
    using FIFO.  Return (open_lots, realized_pnl_per_ticker, cash,
                         total_deposited, total_withdrawn,
                         dividends_per_ticker, total_interest).

    open_lots       : dict  ticker → list of (qty, cost_per_share)
    realized        : dict  ticker → total realized P&L
    cash            : float running cash balance
    total_deposited : float sum of all DEPOSIT amounts
    total_withdrawn : float sum of all WITHDRAW amounts
    dividends       : dict  ticker → total dividend income
    total_interest  : float sum of all INTEREST amounts
    """
    lots = defaultdict(list)       # ticker → [(qty, unit_cost), ...]
    realized = defaultdict(float)  # ticker → realized P&L
    dividends = defaultdict(float) # ticker → dividend income
    cash = 0.0
    total_deposited = 0.0
    total_withdrawn = 0.0
    total_interest = 0.0
    total_buy_cost = 0.0           # GBP spent on buys (excl fees)
    total_sell_proceeds = 0.0      # GBP received from sells (excl fees)
    total_fees = 0.0               # GBP total fees

    df_sorted = txns_df.copy()
    df_sorted["_dt"] = pd.to_datetime(df_sorted["date"], format="mixed", dayfirst=True)
    df_sorted = df_sorted.sort_values("_dt")

    for _, tx in df_sorted.iterrows():
        side = tx["side"]
        p = float(tx["price"])
        f = float(tx.get("fees", 0) or 0)
        fx = float(tx.get("fx_rate", 1.0) or 1.0)
        # Broker's actual GBP amount (if supplied)
        _tg = tx.get("total_gbp")
        tg = float(_tg) if (_tg is not None and not pd.isna(_tg)) else None

        if side == "DEPOSIT":
            amt = tg if tg is not None else p
            cash += amt
            total_deposited += amt
            continue
        elif side == "WITHDRAW":
            amt = tg if tg is not None else p
            cash -= amt
            total_withdrawn += amt
            continue
        elif side == "DIVIDEND":
            div_gbp = tg if tg is not None else p / fx
            cash += div_gbp
            dividends[tx["ticker"]] += div_gbp
            continue
        elif side == "INTEREST":
            amt = tg if tg is not None else p
            cash += amt
            total_interest += amt
            continue

        t = tx["ticker"]
        q = float(tx["quantity"])

        if side == "BUY":
            cost_gbp = tg if tg is not None else q * p / fx
            lots[t].append([q, cost_gbp / q])  # store GBP cost per share
            cash -= cost_gbp + f
            total_buy_cost += cost_gbp
            total_fees += f
        else:  # SELL
            proceeds_gbp = tg if tg is not None else q * p / fx
            cash += proceeds_gbp - f
            total_sell_proceeds += proceeds_gbp
            total_fees += f
            remaining = q
            sell_price_gbp = proceeds_gbp / q
            while remaining > 0 and lots[t]:
                lot_qty, lot_cost_gbp = lots[t][0]
                filled = min(remaining, lot_qty)
                realized[t] += filled * (sell_price_gbp - lot_cost_gbp)
                lots[t][0][0] -= filled
                remaining -= filled
                if lots[t][0][0] <= 1e-9:
                    lots[t].pop(0)

    return (dict(lots), dict(realized), cash, total_deposited, total_withdrawn,
            dict(dividends), total_interest, total_buy_cost, total_sell_proceeds, total_fees)


# ─────────────────────────────────────────────────────────────────────────────
# Live FX rate
# ─────────────────────────────────────────────────────────────────────────────
_FX_PAIR = "GBPUSD=X"          # 1 GBP = X USD
_FX_EUR  = "GBPEUR=X"          # 1 GBP = X EUR


def fetch_live_fx():
    """Return current GBPUSD rate (e.g. 1.29 means 1 GBP = 1.29 USD).
    Divide a USD price by this value to get GBP.
    If fetch fails, returns 1.0 as fallback.
    """
    try:
        info = yf.Ticker(_FX_PAIR).fast_info
        gbpusd = info.last_price      # e.g. 1.29 (1 GBP = 1.29 USD)
        return round(gbpusd, 6) if gbpusd else 1.0
    except Exception:
        return 1.0


# ── Ticker resolution cache ────────────────────────────────────────────────────────
# Explicit overrides for tickers where the bare US symbol is wrong.
# Map: user_ticker → correct yfinance ticker
_TICKER_OVERRIDES = {
    "PSH":  "PSH.L",    # Pershing Square Holdings (LSE, GBp)
    "DSY":  "DSY.PA",   # Dassault Systèmes (Euronext Paris, EUR)
}

_TICKER_SUFFIXES = ["", ".L", ".PA", ".AS", ".DE"]  # bare, London, Paris, Amsterdam, Frankfurt
_resolved_cache = {}            # user_ticker → yf_ticker


def _resolve_ticker(ticker):
    """Resolve a user ticker to a valid yfinance ticker.

    Priority order:
    1. Explicit override (_TICKER_OVERRIDES)
    2. Cached result from a previous call
    3. Try suffixes in order: bare, .L, .PA, .AS, .DE

    Returns (yf_ticker, fast_info) or (ticker, None) on total failure.
    Caches results for the session.
    """
    # 1. Check explicit overrides first
    if ticker in _TICKER_OVERRIDES and ticker not in _resolved_cache:
        candidate = _TICKER_OVERRIDES[ticker]
        try:
            fi = yf.Ticker(candidate).fast_info
            _ = fi.last_price
            _resolved_cache[ticker] = candidate
            return candidate, fi
        except Exception:
            pass  # fall through to suffix search

    # 2. Check cache
    if ticker in _resolved_cache:
        yf_t = _resolved_cache[ticker]
        try:
            fi = yf.Ticker(yf_t).fast_info
            _ = fi.last_price
            return yf_t, fi
        except Exception:
            pass

    # 3. Try suffixes
    for suffix in _TICKER_SUFFIXES:
        candidate = ticker + suffix
        try:
            fi = yf.Ticker(candidate).fast_info
            _ = fi.last_price   # force fetch to see if it works
            _resolved_cache[ticker] = candidate
            return candidate, fi
        except Exception:
            continue
    _resolved_cache[ticker] = ticker
    return ticker, None


def _detect_ccy(tickers):
    """Detect the quote currency for each ticker from yfinance.
    Returns dict  ticker → currency code  ('USD', 'GBp', 'GBP', 'EUR', …).
    'GBp' / 'GBX' = pence Sterling → divide by 100 to get GBP.
    """
    ccy_map = {}
    for t in tickers:
        try:
            _, fi = _resolve_ticker(t)
            ccy_map[t] = fi.currency if fi else "USD"
        except Exception:
            ccy_map[t] = "USD"
    return ccy_map


def compute_holdings(txns_df, last_prices=None):
    """
    Compute current holdings from the transaction ledger.

    Parameters
    ----------
    txns_df      : DataFrame of transactions
    last_prices  : dict ticker → last price (fetched if None)

    Returns
    -------
    holdings_df  : DataFrame with columns:
        ticker, shares, avg_cost, last_price, market_value,
        unrealized_pnl, unrealized_pnl_pct, realized_pnl, total_pnl, weight_pct
    summary      : dict with total_mv, total_pnl, cash, portfolio_value,
                   net_invested, total_deposited, total_withdrawn
    """
    if txns_df.empty:
        return pd.DataFrame(), {
            "total_mv": 0, "total_pnl": 0, "cash": 0,
            "cash_calculated": 0, "cash_overridden": False,
            "portfolio_value": 0, "net_invested": 0,
            "total_deposited": 0, "total_withdrawn": 0,
            "total_dividends": 0, "total_interest": 0,
            "total_buy_cost": 0, "total_sell_proceeds": 0, "total_fees": 0,
        }

    (lots, realized, cash, total_dep, total_wth, dividends, total_int,
     total_buy_cost, total_sell_proceeds, total_fees) = _fifo_lots(txns_df)
    net_invested = total_dep - total_wth
    total_dividends = sum(dividends.values())

    # Build holdings rows
    tickers = sorted(set(t for t, l in lots.items() if l))  # only open positions

    # Fetch last prices, detect currency, and get live FX rates
    live_fx_usd = fetch_live_fx()   # GBPUSD rate (e.g. 1.29)
    try:
        live_fx_eur = yf.Ticker(_FX_EUR).fast_info.last_price or 1.0
    except Exception:
        live_fx_eur = 1.0
    ticker_ccy = {}

    if last_prices is None:
        last_prices = {}
        for t in tickers:
            yf_t, fi = _resolve_ticker(t)
            if fi is not None:
                try:
                    last_prices[t] = round(fi.last_price, 2)
                except Exception:
                    last_prices[t] = None
                try:
                    ticker_ccy[t] = fi.currency
                except Exception:
                    ticker_ccy[t] = "USD"
            else:
                last_prices[t] = None
                ticker_ccy[t] = "USD"
    else:
        ticker_ccy = _detect_ccy(tickers)

    rows = []
    for t in tickers:
        open_lots = lots.get(t, [])
        shares = sum(l[0] for l in open_lots)
        if shares < 1e-9:
            continue
        total_cost = sum(l[0] * l[1] for l in open_lots)  # GBP cost
        avg_cost = total_cost / shares if shares > 0 else 0  # GBP per share
        lp_raw = last_prices.get(t)
        ccy = ticker_ccy.get(t, "USD")
        if ccy in ("GBp", "GBX"):
            lp_gbp = lp_raw / 100 if lp_raw else None       # pence → pounds
        elif ccy == "GBP":
            lp_gbp = lp_raw                                   # already pounds
        elif ccy == "EUR":
            lp_gbp = lp_raw / live_fx_eur if lp_raw else None  # EUR → GBP
        else:
            lp_gbp = lp_raw / live_fx_usd if lp_raw else None  # USD → GBP
        mv = shares * lp_gbp if lp_gbp else None             # market value in GBP
        u_pnl = (lp_gbp - avg_cost) * shares if lp_gbp else None
        u_pct = ((lp_gbp / avg_cost) - 1) * 100 if lp_gbp and avg_cost > 0 else None
        r_pnl = realized.get(t, 0)                           # already GBP
        t_pnl = (u_pnl + r_pnl) if u_pnl is not None else r_pnl

        div_inc = dividends.get(t, 0)                        # already GBP
        t_pnl_with_div = (t_pnl + div_inc) if t_pnl is not None else div_inc

        rows.append({
            "ticker": t,
            "shares": round(shares, 4),
            "avg_cost": round(avg_cost, 2),
            "last_price": round(lp_gbp, 2) if lp_gbp else None,
            "last_price_local": round(lp_raw, 2) if lp_raw else None,
            "currency": ccy,
            "market_value": round(mv, 2) if mv else None,
            "unrealized_pnl": round(u_pnl, 2) if u_pnl is not None else None,
            "unrealized_pnl_pct": round(u_pct, 2) if u_pct is not None else None,
            "realized_pnl": round(r_pnl, 2),
            "dividend_income": round(div_inc, 2),
            "total_pnl": round(t_pnl_with_div, 2) if t_pnl_with_div is not None else None,
        })

    # Also include fully-closed tickers that have realized P&L
    # Also include tickers with dividends but no open lots or realized
    all_relevant = set(realized.keys()) | set(dividends.keys())
    closed_tickers = all_relevant - set(r["ticker"] for r in rows)
    for t in sorted(closed_tickers):
        r_pnl = realized.get(t, 0)
        div_inc = dividends.get(t, 0)
        t_pnl = r_pnl + div_inc
        if abs(t_pnl) > 0.001 or abs(div_inc) > 0.001:
            rows.append({
                "ticker": t, "shares": 0, "avg_cost": 0, "last_price": None,
                "last_price_local": None, "currency": "",
                "market_value": 0, "unrealized_pnl": 0, "unrealized_pnl_pct": 0,
                "realized_pnl": round(r_pnl, 2), "dividend_income": round(div_inc, 2),
                "total_pnl": round(t_pnl, 2),
            })

    holdings_df = pd.DataFrame(rows)
    if holdings_df.empty or "market_value" not in holdings_df.columns:
        holdings_df = pd.DataFrame(columns=[
            "ticker", "shares", "avg_cost", "last_price", "market_value",
            "unrealized_pnl", "unrealized_pnl_pct", "realized_pnl",
            "dividend_income", "total_pnl", "weight_pct",
        ])
        total_mv = 0
        total_pnl = 0
    else:
        total_mv = holdings_df["market_value"].sum() or 0
        if total_mv > 0:
            holdings_df["weight_pct"] = (
                holdings_df["market_value"].fillna(0) / total_mv * 100
            ).round(1)
        else:
            holdings_df["weight_pct"] = 0.0
        total_pnl = holdings_df["total_pnl"].sum() or 0

    # Use cash override if user has set one
    cash_ov = get_cash_override()
    display_cash = cash_ov if cash_ov is not None else cash
    portfolio_value = total_mv + display_cash

    summary = {
        "total_mv": round(total_mv, 2),
        "total_pnl": round(total_pnl, 2),
        "cash": round(display_cash, 2),
        "cash_calculated": round(cash, 2),
        "cash_overridden": cash_ov is not None,
        "portfolio_value": round(portfolio_value, 2),
        "net_invested": round(net_invested, 2),
        "total_deposited": round(total_dep, 2),
        "total_withdrawn": round(total_wth, 2),
        "total_dividends": round(total_dividends, 2),
        "total_interest": round(total_int, 2),
        "total_buy_cost": round(total_buy_cost, 2),
        "total_sell_proceeds": round(total_sell_proceeds, 2),
        "total_fees": round(total_fees, 2),
    }

    return holdings_df, summary


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio time-series (equity curve)
# ─────────────────────────────────────────────────────────────────────────────

def compute_portfolio_ts(txns_df, return_debug=False):
    """
    Build a daily portfolio value time-series from the transaction ledger.

    Returns
    -------
    ts_df : DataFrame [portfolio_value, cumulative_return, drawdown, twr]
    debug_df : DataFrame (only if return_debug=True) — one row per day with
               per-stock qty/price/fx/gbp_value, cash, net_flow, daily_return, index
    """
    if txns_df.empty:
        return (pd.DataFrame(), pd.DataFrame()) if return_debug else pd.DataFrame()

    txns_df = txns_df.copy()
    txns_df["date"] = pd.to_datetime(txns_df["date"], format="mixed", dayfirst=False)
    start = txns_df["date"].min()

    # Identify stock tickers (exclude CASH rows from DEPOSIT/WITHDRAW)
    stock_txns = txns_df[txns_df["side"].isin(["BUY", "SELL"])]
    tickers = list(stock_txns["ticker"].unique()) if not stock_txns.empty else []

    # Resolve tickers (e.g. CSPX → CSPX.L) for yfinance download
    yf_map = {}   # user_ticker → yf_ticker
    for t in tickers:
        yf_t, _ = _resolve_ticker(t)
        yf_map[t] = yf_t

    # Detect currency for each ticker
    ticker_ccy = _detect_ccy(tickers)

    # Determine which FX pairs we need
    need_usd = any(ticker_ccy.get(t, "USD") not in ("GBP", "GBp", "GBX", "EUR") for t in tickers)
    need_eur = any(ticker_ccy.get(t, "USD") == "EUR" for t in tickers)
    fx_pairs = []
    if need_usd or not tickers:
        fx_pairs.append(_FX_PAIR)
    if need_eur:
        fx_pairs.append(_FX_EUR)

    # Download daily prices + FX rates from start to today
    dl_tickers = list(set(yf_map.values())) + fx_pairs
    if dl_tickers:
        try:
            raw = yf.download(
                tickers=dl_tickers,
                start=start,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
        except Exception:
            raw = None

        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                price_df = raw.get("Close")
            else:
                price_df = raw
            if isinstance(price_df, pd.Series):
                price_df = price_df.to_frame(name=dl_tickers[0])
            price_df = price_df.ffill().dropna(how="all")
        else:
            price_df = pd.DataFrame()
    else:
        price_df = pd.DataFrame()

    # If we have no price data but have cash-only txns, build a date range
    if price_df.empty:
        dr = pd.bdate_range(start=start, end=pd.Timestamp.today())
        price_df = pd.DataFrame(index=dr)

    if price_df.empty:
        return (pd.DataFrame(), pd.DataFrame()) if return_debug else pd.DataFrame()

    # Rename yf columns back to user tickers so the rest of the code works
    reverse_map = {v: k for k, v in yf_map.items()}
    price_df = price_df.rename(columns=reverse_map)

    # Categorise tickers
    gbp_native = set()   # tickers in GBP (no FX needed)
    eur_tickers = set()  # tickers in EUR
    for t in tickers:
        ccy = ticker_ccy.get(t, "USD")
        if ccy in ("GBp", "GBX") and t in price_df.columns:
            price_df[t] = price_df[t] / 100  # pence → pounds
            gbp_native.add(t)
        elif ccy == "GBP":
            gbp_native.add(t)
        elif ccy == "EUR":
            eur_tickers.add(t)
        # else: USD (default)

    # Walk through each trading day
    dates = price_df.index
    holdings = defaultdict(float)   # ticker → shares
    cash = 0.0                      # GBP cash balance
    txn_idx = 0
    sorted_txns = txns_df.sort_values("date").reset_index(drop=True)

    # Track net external flows (deposits - withdrawals) per date for TWR
    net_flow_by_date = defaultdict(float)
    for _, tx in txns_df.iterrows():
        d = pd.Timestamp(tx["date"]).normalize()
        side = tx["side"]
        _tg = tx.get("total_gbp")
        tg = float(_tg) if (_tg is not None and not pd.isna(_tg)) else None
        p = float(tx["price"])
        if side == "DEPOSIT":
            net_flow_by_date[d] += tg if tg is not None else p
        elif side == "WITHDRAW":
            net_flow_by_date[d] -= (tg if tg is not None else p)

    daily_values = []
    debug_rows = []

    for dt in dates:
        dt_date = pd.Timestamp(dt).normalize()

        # Apply all transactions up to and including this date
        while txn_idx < len(sorted_txns):
            tx = sorted_txns.iloc[txn_idx]
            tx_date = pd.Timestamp(tx["date"]).normalize()
            if tx_date > dt_date:
                break
            side = tx["side"]
            p = float(tx["price"])
            f = float(tx.get("fees", 0) or 0)
            fx = float(tx.get("fx_rate", 1.0) or 1.0)

            _tg = tx.get("total_gbp") if "total_gbp" in tx.index else None
            tg = float(_tg) if (_tg is not None and not pd.isna(_tg)) else None

            if side == "DEPOSIT":
                cash += tg if tg is not None else p
            elif side == "WITHDRAW":
                cash -= (tg if tg is not None else p)
            elif side == "DIVIDEND":
                cash += tg if tg is not None else p / fx
            elif side == "INTEREST":
                cash += tg if tg is not None else p
            elif side == "BUY":
                t = tx["ticker"]
                q = float(tx["quantity"])
                holdings[t] += q
                cost_gbp = tg if tg is not None else q * p / fx
                cash -= cost_gbp + f
            else:  # SELL
                t = tx["ticker"]
                q = float(tx["quantity"])
                holdings[t] -= q
                proceeds_gbp = tg if tg is not None else q * p / fx
                cash += proceeds_gbp - f
            txn_idx += 1

        # Get today's FX rates
        if _FX_PAIR in price_df.columns:
            fx_s = price_df.loc[:dt, _FX_PAIR].dropna()
            day_fx_usd = fx_s.iloc[-1] if not fx_s.empty else 1.0
        else:
            day_fx_usd = 1.0

        if _FX_EUR in price_df.columns:
            fx_e = price_df.loc[:dt, _FX_EUR].dropna()
            day_fx_eur = fx_e.iloc[-1] if not fx_e.empty else 1.0
        else:
            day_fx_eur = 1.0

        # Compute portfolio value in GBP
        mv = 0.0
        debug_stock = {}
        for t, shares in holdings.items():
            if shares > 0 and t in price_df.columns:
                px = price_df.loc[:dt, t].dropna()
                if not px.empty:
                    local_price = px.iloc[-1]
                    if t in gbp_native:
                        gbp_val = shares * local_price
                        fx_used = 1.0
                    elif t in eur_tickers:
                        gbp_val = shares * local_price / day_fx_eur
                        fx_used = day_fx_eur
                    else:  # USD
                        gbp_val = shares * local_price / day_fx_usd
                        fx_used = day_fx_usd
                    mv += gbp_val
                    if return_debug:
                        debug_stock[t] = {
                            "qty": round(shares, 4),
                            "local_price": round(local_price, 4),
                            "fx": round(fx_used, 6),
                            "gbp_value": round(gbp_val, 2),
                        }

        pv = cash + mv
        daily_values.append({"date": dt, "portfolio_value": pv})

        if return_debug:
            row = {"date": dt, "cash": round(cash, 2),
                   "market_value": round(mv, 2), "portfolio_value": round(pv, 2),
                   "net_flow": round(net_flow_by_date.get(dt_date, 0), 2),
                   "fx_gbpusd": round(day_fx_usd, 6),
                   "fx_gbpeur": round(day_fx_eur, 6)}
            for t_name, d in debug_stock.items():
                row[f"{t_name}_qty"] = d["qty"]
                row[f"{t_name}_price"] = d["local_price"]
                row[f"{t_name}_fx"] = d["fx"]
                row[f"{t_name}_gbp"] = d["gbp_value"]
            debug_rows.append(row)

    # Apply cash override to the latest day if set
    cash_ov = get_cash_override()
    if cash_ov is not None and daily_values:
        last = daily_values[-1]
        last_mv = last["portfolio_value"] - cash
        daily_values[-1] = {"date": last["date"], "portfolio_value": cash_ov + last_mv}

    ts_df = pd.DataFrame(daily_values).set_index("date")

    if ts_df.empty:
        return (ts_df, pd.DataFrame()) if return_debug else ts_df

    # ── Method-A TWR: daily_return = (V_today - net_flow - V_yesterday) / V_yesterday
    values = ts_df["portfolio_value"].values
    twr = np.ones(len(values))
    daily_returns = np.zeros(len(values))
    for i in range(1, len(values)):
        dt = ts_df.index[i]
        prev_val = values[i - 1]
        cf = net_flow_by_date.get(dt, 0)  # net deposits on this day
        if prev_val > 0:
            dr = (values[i] - cf - prev_val) / prev_val
        else:
            dr = 0.0
        daily_returns[i] = dr
        twr[i] = twr[i - 1] * (1 + dr)

    ts_df["cumulative_return"] = (twr - 1) * 100
    ts_df["twr"] = twr
    ts_df["daily_return"] = daily_returns

    # Drawdown
    running_max = ts_df["portfolio_value"].cummax()
    ts_df["drawdown"] = ((ts_df["portfolio_value"] - running_max) / running_max * 100).fillna(0)

    if return_debug:
        debug_df = pd.DataFrame(debug_rows)
        # Merge daily_return and index into debug
        if not debug_df.empty:
            debug_df = debug_df.set_index("date")
            debug_df["daily_return_pct"] = ts_df["daily_return"] * 100
            debug_df["index_100"] = ts_df["twr"] * 100
            debug_df["cumulative_return_pct"] = ts_df["cumulative_return"]
            debug_df["drawdown_pct"] = ts_df["drawdown"]
            debug_df = debug_df.reset_index()
        return ts_df, debug_df

    return ts_df