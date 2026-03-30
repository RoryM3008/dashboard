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
    with _conn() as con:
        # Check if the table exists
        exists = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        ).fetchone()

        if exists:
            # Migrate: drop the old CHECK constraint by recreating the table
            # (SQLite doesn't support ALTER CONSTRAINT)
            try:
                con.execute("ALTER TABLE transactions RENAME TO _txns_old")
                con.execute("""
                    CREATE TABLE transactions (
                        id       TEXT PRIMARY KEY,
                        date     TEXT NOT NULL,
                        ticker   TEXT NOT NULL DEFAULT '',
                        side     TEXT NOT NULL CHECK(side IN ('BUY','SELL','DEPOSIT','WITHDRAW','DIVIDEND','INTEREST')),
                        quantity REAL NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                        price    REAL NOT NULL DEFAULT 0 CHECK(price >= 0),
                        fees     REAL NOT NULL DEFAULT 0,
                        fx_rate  REAL NOT NULL DEFAULT 1.0,
                        notes    TEXT DEFAULT ''
                    )
                """)
                # Migrate old data — fx_rate defaults to 1.0 for existing rows
                cols = [row[1] for row in con.execute("PRAGMA table_info(_txns_old)").fetchall()]
                if "fx_rate" in cols:
                    con.execute("""
                        INSERT INTO transactions (id, date, ticker, side, quantity, price, fees, fx_rate, notes)
                        SELECT id, date, ticker, side, quantity, price, fees, fx_rate, notes
                        FROM _txns_old
                    """)
                else:
                    con.execute("""
                        INSERT INTO transactions (id, date, ticker, side, quantity, price, fees, fx_rate, notes)
                        SELECT id, date, ticker, side, quantity, price, fees, 1.0, notes
                        FROM _txns_old
                    """)
                con.execute("DROP TABLE _txns_old")
            except Exception:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id       TEXT PRIMARY KEY,
                        date     TEXT NOT NULL,
                        ticker   TEXT NOT NULL DEFAULT '',
                        side     TEXT NOT NULL CHECK(side IN ('BUY','SELL','DEPOSIT','WITHDRAW','DIVIDEND','INTEREST')),
                        quantity REAL NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                        price    REAL NOT NULL DEFAULT 0 CHECK(price >= 0),
                        fees     REAL NOT NULL DEFAULT 0,
                        fx_rate  REAL NOT NULL DEFAULT 1.0,
                        notes    TEXT DEFAULT ''
                    )
                """)
        else:
            con.execute("""
                CREATE TABLE transactions (
                    id       TEXT PRIMARY KEY,
                    date     TEXT NOT NULL,
                    ticker   TEXT NOT NULL DEFAULT '',
                    side     TEXT NOT NULL CHECK(side IN ('BUY','SELL','DEPOSIT','WITHDRAW','DIVIDEND','INTEREST')),
                    quantity REAL NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                    price    REAL NOT NULL DEFAULT 0 CHECK(price >= 0),
                    fees     REAL NOT NULL DEFAULT 0,
                    fx_rate  REAL NOT NULL DEFAULT 1.0,
                    notes    TEXT DEFAULT ''
                )
            """)


def load_transactions():
    """Return all transactions as a DataFrame, sorted by date then id."""
    init_db()
    with _conn() as con:
        df = pd.read_sql("SELECT * FROM transactions ORDER BY date, id", con)
    return df


def add_transaction(txn_date, ticker, side, quantity, price, fees=0.0, notes="", fx_rate=1.0):
    """Insert a single transaction. Returns the new id.

    For DEPOSIT / WITHDRAW the *price* field carries the cash amount (in GBP).
    For BUY / SELL the *price* is in the stock's currency; *fx_rate* converts
    it to GBP  (e.g. 0.79 for USD→GBP).  Cash impact = qty * price * fx_rate.
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
        # DIVIDEND keeps the ticker so we know which stock paid it
        ticker = (ticker or "").upper().strip()
        quantity = 0
    else:
        ticker = (ticker or "").upper().strip()
        quantity = float(quantity)

    with _conn() as con:
        con.execute(
            "INSERT INTO transactions (id, date, ticker, side, quantity, price, fees, fx_rate, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (txn_id, str(txn_date), ticker, side,
             float(quantity), float(price), float(fees or 0), float(fx_rate), notes or ""),
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
    count = 0
    for _, row in df.iterrows():
        try:
            # Normalise date to ISO yyyy-mm-dd
            raw_date = str(row["date"]).strip()
            try:
                iso_date = pd.to_datetime(raw_date, dayfirst=True, format="mixed").strftime("%Y-%m-%d")
            except Exception:
                iso_date = raw_date
            add_transaction(
                txn_date=iso_date,
                ticker=row["ticker"],
                side=row["side"],
                quantity=row["quantity"],
                price=row["price"],
                fees=row.get("fees", 0) or 0,
                notes=row.get("notes", "") or "",
                fx_rate=row.get("fx_rate", 1.0) or 1.0,
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

    df_sorted = txns_df.copy()
    df_sorted["_dt"] = pd.to_datetime(df_sorted["date"], format="mixed", dayfirst=True)
    df_sorted = df_sorted.sort_values("_dt")

    for _, tx in df_sorted.iterrows():
        side = tx["side"]
        p = float(tx["price"])
        f = float(tx.get("fees", 0) or 0)
        fx = float(tx.get("fx_rate", 1.0) or 1.0)

        if side == "DEPOSIT":
            cash += p                       # already GBP
            total_deposited += p
            continue
        elif side == "WITHDRAW":
            cash -= p
            total_withdrawn += p
            continue
        elif side == "DIVIDEND":
            cash += p / fx                  # convert to GBP
            dividends[tx["ticker"]] += p / fx
            continue
        elif side == "INTEREST":
            cash += p                       # already GBP
            total_interest += p
            continue

        t = tx["ticker"]
        q = float(tx["quantity"])

        if side == "BUY":
            lots[t].append([q, p / fx])     # store GBP cost per share
            cash -= q * p / fx + f          # fees assumed GBP
        else:  # SELL
            cash += q * p / fx - f
            remaining = q
            while remaining > 0 and lots[t]:
                lot_qty, lot_cost_gbp = lots[t][0]
                filled = min(remaining, lot_qty)
                realized[t] += filled * (p / fx - lot_cost_gbp)
                lots[t][0][0] -= filled
                remaining -= filled
                if lots[t][0][0] <= 1e-9:
                    lots[t].pop(0)

    return dict(lots), dict(realized), cash, total_deposited, total_withdrawn, dict(dividends), total_interest


# ─────────────────────────────────────────────────────────────────────────────
# Live FX rate
# ─────────────────────────────────────────────────────────────────────────────
_FX_PAIR = "GBPUSD=X"          # 1 GBP = X USD


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


def _detect_ccy(tickers):
    """Detect the quote currency for each ticker from yfinance.
    Returns dict  ticker → currency code  ('USD', 'GBp', 'GBP', 'EUR', …).
    'GBp' / 'GBX' = pence Sterling → divide by 100 to get GBP.
    """
    ccy_map = {}
    for t in tickers:
        try:
            ccy_map[t] = yf.Ticker(t).fast_info.currency
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
            "portfolio_value": 0, "net_invested": 0,
            "total_deposited": 0, "total_withdrawn": 0,
            "total_dividends": 0, "total_interest": 0,
        }

    lots, realized, cash, total_dep, total_wth, dividends, total_int = _fifo_lots(txns_df)
    net_invested = total_dep - total_wth
    total_dividends = sum(dividends.values())

    # Build holdings rows
    tickers = sorted(set(t for t, l in lots.items() if l))  # only open positions

    # Fetch last prices, detect currency, and get live GBPUSD rate
    live_fx = fetch_live_fx()   # GBPUSD rate (e.g. 1.29)
    ticker_ccy = {}

    if last_prices is None:
        last_prices = {}
        for t in tickers:
            try:
                fi = yf.Ticker(t).fast_info
                last_prices[t] = round(fi.last_price, 2)
                try:
                    ticker_ccy[t] = fi.currency
                except Exception:
                    ticker_ccy[t] = "USD"
            except Exception:
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
        else:
            lp_gbp = lp_raw / live_fx if lp_raw else None    # USD → GBP
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
                "market_value": 0, "unrealized_pnl": 0, "unrealized_pnl_pct": 0,
                "realized_pnl": round(r_pnl, 2), "dividend_income": round(div_inc, 2),
                "total_pnl": round(t_pnl, 2),
            })

    holdings_df = pd.DataFrame(rows)
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
    }

    return holdings_df, summary


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio time-series (equity curve)
# ─────────────────────────────────────────────────────────────────────────────

def compute_portfolio_ts(txns_df):
    """
    Build a daily portfolio value time-series from the transaction ledger.

    Handles DEPOSIT / WITHDRAW cash flows correctly:
    • Portfolio value  = market value of holdings + cash
    • Return is time-weighted (TWR): daily return is chained, and on days
      with a cash flow the return is reset so that deposits/withdrawals
      don't distort the cumulative return.

    Returns
    -------
    ts_df : DataFrame with columns [portfolio_value, cumulative_return, drawdown]
            index = dates
    """
    if txns_df.empty:
        return pd.DataFrame()

    txns_df = txns_df.copy()
    txns_df["date"] = pd.to_datetime(txns_df["date"], format="mixed", dayfirst=False)
    start = txns_df["date"].min()

    # Identify stock tickers (exclude CASH rows from DEPOSIT/WITHDRAW)
    stock_txns = txns_df[txns_df["side"].isin(["BUY", "SELL"])]
    tickers = list(stock_txns["ticker"].unique()) if not stock_txns.empty else []

    # Download daily prices + FX rate from start to today
    dl_tickers = tickers + [_FX_PAIR] if tickers else [_FX_PAIR]
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
        return pd.DataFrame()

    # Detect pence-denominated tickers and convert to GBP in price_df
    ticker_ccy = _detect_ccy(tickers)
    gbp_native = set()                       # tickers already in GBP
    for t in tickers:
        ccy = ticker_ccy.get(t, "USD")
        if ccy in ("GBp", "GBX") and t in price_df.columns:
            price_df[t] = price_df[t] / 100  # pence → pounds
            gbp_native.add(t)
        elif ccy == "GBP":
            gbp_native.add(t)

    # Walk through each trading day
    dates = price_df.index
    holdings = defaultdict(float)   # ticker → shares
    cash = 0.0                      # GBP cash balance
    txn_idx = 0
    sorted_txns = txns_df.sort_values("date").reset_index(drop=True)

    daily_values = []

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

            if side == "DEPOSIT":
                cash += p              # GBP
            elif side == "WITHDRAW":
                cash -= p
            elif side == "DIVIDEND":
                cash += p / fx         # convert to GBP
            elif side == "INTEREST":
                cash += p              # GBP
            elif side == "BUY":
                t = tx["ticker"]
                q = float(tx["quantity"])
                holdings[t] += q
                cash -= q * p / fx + f
            else:  # SELL
                t = tx["ticker"]
                q = float(tx["quantity"])
                holdings[t] -= q
                cash += q * p / fx - f
            txn_idx += 1

        # Get today's FX rate (USD→GBP)
        if _FX_PAIR in price_df.columns:
            fx_series = price_df.loc[:dt, _FX_PAIR].dropna()
            day_fx = fx_series.iloc[-1] if not fx_series.empty else 1.0
        else:
            day_fx = 1.0

        # Compute portfolio value in GBP
        mv = 0.0
        for t, shares in holdings.items():
            if shares > 0 and t in price_df.columns:
                px = price_df.loc[:dt, t].dropna()
                if not px.empty:
                    if t in gbp_native:
                        mv += shares * px.iloc[-1]           # already GBP
                    else:
                        mv += shares * px.iloc[-1] / day_fx  # USD / GBPUSD → GBP

        daily_values.append({"date": dt, "portfolio_value": cash + mv})

    # Apply cash override to the latest day if set
    cash_ov = get_cash_override()
    if cash_ov is not None and daily_values:
        last = daily_values[-1]
        # Replace the calculated cash with override for today's value
        last_mv = last["portfolio_value"] - cash  # extract market value
        daily_values[-1] = {"date": last["date"], "portfolio_value": cash_ov + last_mv}

    ts_df = pd.DataFrame(daily_values).set_index("date")

    if ts_df.empty:
        return ts_df

    # ── Time-weighted return (TWR) ────────────────────────────────────────
    # Identify days that have external cash flows (DEPOSIT / WITHDRAW)
    cash_flow_txns = txns_df[txns_df["side"].isin(["DEPOSIT", "WITHDRAW"])].copy()
    cf_by_date = {}
    for _, tx in cash_flow_txns.iterrows():
        d = pd.Timestamp(tx["date"]).normalize()
        amt = float(tx["price"])
        if tx["side"] == "DEPOSIT":
            cf_by_date[d] = cf_by_date.get(d, 0) + amt
        else:
            cf_by_date[d] = cf_by_date.get(d, 0) - amt

    # Chain daily returns, adjusting for cash flows
    values = ts_df["portfolio_value"].values
    twr = np.ones(len(values))
    for i in range(1, len(values)):
        dt = ts_df.index[i]
        prev_val = values[i - 1]
        cf = cf_by_date.get(dt, 0)  # cash flow on this day
        # Beginning-of-day value after cash flow = previous EOD + today's flow
        adjusted_prev = prev_val + cf
        if adjusted_prev > 0:
            twr[i] = twr[i - 1] * (values[i] / adjusted_prev)
        else:
            twr[i] = twr[i - 1]

    ts_df["cumulative_return"] = (twr - 1) * 100

    # Drawdown
    running_max = ts_df["portfolio_value"].cummax()
    ts_df["drawdown"] = ((ts_df["portfolio_value"] - running_max) / running_max * 100).fillna(0)

    return ts_df
