"""Callback — Portfolio: transaction CRUD, holdings, overview, performance chart."""

import base64
import json
from datetime import date

import dash
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from dash import dcc, html, Input, Output, State, ALL, no_update

from theme import FONT, get_theme
from portfolio import (
    load_transactions, add_transaction, delete_transaction,
    clear_all_transactions,
    import_csv, export_csv, compute_holdings, compute_portfolio_ts,
    set_cash_override, get_cash_override, clear_cash_override,
    set_price_override, clear_price_override, list_price_overrides,
)

_COLOURS = [
    "#ff8c00", "#4296f5", "#00d26a", "#ff3333", "#a855f7",
    "#e91e8f", "#06b6d4", "#eab308", "#6366f1", "#14b8a6",
]


# ─────────────────────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────────────────────

def _metric_card(label, value, colour, c):
    return html.Div([
        html.Div(label, style={"color": c["subtext"], "fontSize": "0.65rem",
                                "fontFamily": FONT, "textTransform": "uppercase",
                                "letterSpacing": "0.05em", "marginBottom": "2px"}),
        html.Div(value, style={"color": colour, "fontSize": "1.15rem",
                                "fontWeight": "700", "fontFamily": FONT}),
    ], style={"backgroundColor": c["bg"], "border": f"1px solid {c['border']}",
              "borderRadius": "10px", "padding": "0.75rem 1rem",
              "minWidth": "140px", "flex": "1"})


def _render_ledger(txns_df, c):
    """Render the transaction ledger as an HTML table with delete buttons."""
    if txns_df.empty:
        return html.Div("No transactions yet. Add one above.",
                        style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})

    th_s = {
        "padding": "0.3rem 0.5rem", "fontSize": "0.6rem", "fontWeight": "700",
        "textTransform": "uppercase", "letterSpacing": "0.05em",
        "borderBottom": f"2px solid {c['border']}", "fontFamily": FONT,
        "color": c["muted"], "whiteSpace": "nowrap",
    }
    td_s = {
        "padding": "0.3rem 0.5rem", "fontSize": "0.75rem", "fontFamily": FONT,
        "color": c["text"], "borderBottom": f"1px solid {c['border']}",
        "whiteSpace": "nowrap",
    }

    cols = ["date", "ticker", "side", "quantity", "price", "fx_rate", "fees", "total_gbp", "notes"]
    nice = {"fx_rate": "FX", "total_gbp": "TOTAL £"}
    header = html.Thead(html.Tr(
        [html.Th("", style={**th_s, "width": "55px"})] +
        [html.Th(nice.get(col, col.upper()), style={**th_s,
                 "textAlign": "right" if col in ("quantity", "price", "fx_rate", "fees", "total_gbp") else "left"})
         for col in cols]
    ))

    rows = []
    for _, tx in txns_df.iterrows():
        side = tx["side"]
        is_cash_flow = side in ("DEPOSIT", "WITHDRAW", "INTEREST")
        is_dividend = side == "DIVIDEND"

        if side == "DEPOSIT":
            side_col = c["blue"]
        elif side == "WITHDRAW":
            side_col = c["accent"]
        elif side == "DIVIDEND":
            side_col = c["green"]
        elif side == "INTEREST":
            side_col = c["blue"]
        elif side == "BUY":
            side_col = c["green"]
        else:
            side_col = c["red"]

        # Format date as dd-mm-yyyy for display
        try:
            from datetime import datetime as _dt
            display_date = _dt.strptime(tx["date"].strip(), "%Y-%m-%d").strftime("%d-%m-%Y")
        except Exception:
            display_date = tx["date"]

        # For cash-flow types: show amount in price col, dash for qty
        qty_text = "—" if (is_cash_flow or is_dividend) else f"{float(tx['quantity']):,.2f}"
        ticker_text = tx["ticker"] if (is_dividend or not is_cash_flow) else "—"
        fx_val = float(tx.get("fx_rate", 1.0) or 1.0)
        # Show price in original currency, £ for GBP amounts
        if is_cash_flow:
            price_text = f"£{float(tx['price']):,.2f}"
        else:
            price_text = f"${float(tx['price']):,.2f}"
        fx_text = f"{fx_val:.4f}"

        rows.append(html.Tr([
            html.Td(
                html.Div([
                    html.Button("✎", id={"type": "port-txn-edit", "id": tx["id"]},
                                n_clicks=0, style={
                        "background": "none", "border": "none", "color": c["blue"],
                        "cursor": "pointer", "fontWeight": "700", "fontSize": "0.75rem",
                        "padding": "0", "lineHeight": "1", "marginRight": "6px"}),
                    html.Button("✕", id={"type": "port-txn-del", "id": tx["id"]},
                                n_clicks=0, style={
                        "background": "none", "border": "none", "color": c["red"],
                        "cursor": "pointer", "fontWeight": "700", "fontSize": "0.75rem",
                        "padding": "0", "lineHeight": "1"}),
                ], style={"display": "flex", "gap": "2px"}),
                style={**td_s, "width": "55px"}),
            html.Td(display_date, style={**td_s, "fontWeight": "600"}),
            html.Td(ticker_text, style={**td_s, "color": c["accent"] if (not is_cash_flow or is_dividend) else c["subtext"],
                                         "fontWeight": "700"}),
            html.Td(side, style={**td_s, "color": side_col, "fontWeight": "700"}),
            html.Td(qty_text, style={**td_s, "textAlign": "right"}),
            html.Td(price_text, style={**td_s, "textAlign": "right"}),
            html.Td(fx_text, style={**td_s, "textAlign": "right", "color": c["subtext"]}),
            html.Td(f"£{float(tx['fees']):,.2f}", style={**td_s, "textAlign": "right"}),
            html.Td(f"£{float(tx['total_gbp']):,.2f}" if pd.notna(tx.get("total_gbp")) and tx.get("total_gbp") else "—",
                    style={**td_s, "textAlign": "right", "color": c["accent"], "fontWeight": "600"}),
            html.Td(tx.get("notes", ""), style={**td_s, "color": c["subtext"]}),
        ]))

    return html.Table([header, html.Tbody(rows)],
                      style={"width": "100%", "borderCollapse": "collapse"})


_CCY_SYMBOLS = {"USD": "$", "GBP": "£", "GBp": "", "GBX": "", "EUR": "€"}


def _fmt_local(price, ccy):
    """Format a price in its local currency."""
    if price is None:
        return "—"
    sym = _CCY_SYMBOLS.get(ccy, "")
    if ccy in ("GBp", "GBX"):
        return f"{price:,.2f}p"
    return f"{sym}{price:,.2f}"


def _fetch_benchmark_prices(ticker, start, end):
    """Download daily close for a benchmark ticker, return as Series indexed by date."""
    try:
        raw = yf.download(ticker, start=start, end=end + pd.Timedelta(days=1),
                          interval="1d", auto_adjust=True, progress=False)
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                s = raw["Close"].iloc[:, 0]
            else:
                s = raw["Close"] if "Close" in raw.columns else raw.iloc[:, 0]
            return s.dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def _add_benchmark(fig, ticker, start_date, end_date, c):
    """Add an indexed-at-100 benchmark trace to the figure."""
    prices = _fetch_benchmark_prices(ticker, start_date, end_date)
    if prices.empty:
        return
    indexed = 100 * prices / prices.iloc[0]
    fig.add_trace(go.Scatter(
        x=indexed.index, y=indexed.values,
        mode="lines", name=ticker.upper(),
        line={"color": c["blue"], "width": 1.5, "dash": "dot"},
        hovertemplate=f"{ticker.upper()}: " + "%{y:.2f}<extra></extra>",
    ))


def _add_benchmark_return(fig, ticker, start_date, end_date, c):
    """Add a cumulative-return % benchmark trace to the figure."""
    prices = _fetch_benchmark_prices(ticker, start_date, end_date)
    if prices.empty:
        return
    cum_ret = (prices / prices.iloc[0] - 1) * 100
    fig.add_trace(go.Scatter(
        x=cum_ret.index, y=cum_ret.values,
        mode="lines", name=ticker.upper(),
        line={"color": c["blue"], "width": 1.5, "dash": "dot"},
        hovertemplate=f"{ticker.upper()}: " + "%{y:.2f}%<extra></extra>",
    ))


def _add_benchmark_drawdown(fig, ticker, start_date, end_date, c):
    """Add a benchmark drawdown % trace to the figure."""
    prices = _fetch_benchmark_prices(ticker, start_date, end_date)
    if prices.empty:
        return
    running_max = prices.cummax()
    dd = ((prices - running_max) / running_max * 100).fillna(0)
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        mode="lines", name=f"{ticker.upper()} DD",
        line={"color": c["blue"], "width": 1.5, "dash": "dot"},
        hovertemplate=f"{ticker.upper()} DD: " + "%{y:.2f}%<extra></extra>",
    ))


def _render_holdings(hdf, c):
    """Render the holdings summary as an HTML table (active positions only)."""
    # Filter to active positions only
    hdf = hdf[hdf["shares"] > 0].copy() if not hdf.empty and "shares" in hdf.columns else hdf
    if hdf.empty:
        return html.Div("No open positions.",
                        style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})

    th_s = {
        "padding": "0.3rem 0.5rem", "fontSize": "0.6rem", "fontWeight": "700",
        "textTransform": "uppercase", "letterSpacing": "0.05em",
        "borderBottom": f"2px solid {c['border']}", "fontFamily": FONT,
        "color": c["muted"], "whiteSpace": "nowrap",
    }
    td_s = {
        "padding": "0.3rem 0.5rem", "fontSize": "0.75rem", "fontFamily": FONT,
        "color": c["text"], "borderBottom": f"1px solid {c['border']}",
        "whiteSpace": "nowrap",
    }

    col_labels = ["Ticker", "Shares", "Avg Cost", "Last", "Mkt Value",
                  "Unreal P&L", "Unreal %", "Real P&L", "Divs", "Total P&L", "Weight"]

    header = html.Thead(html.Tr([
        html.Th(col, style={**th_s,
                "textAlign": "left" if col == "Ticker" else "right"})
        for col in col_labels
    ]))

    rows = []
    for _, h in hdf.iterrows():
        u_pnl = h.get("unrealized_pnl")
        u_pct = h.get("unrealized_pnl_pct")
        t_pnl = h.get("total_pnl")

        u_col = c["green"] if (u_pnl or 0) >= 0 else c["red"]
        t_col = c["green"] if (t_pnl or 0) >= 0 else c["red"]

        def _f(v, prefix="\u00a3"):
            if v is None:
                return "\u2014"
            return f"{prefix}{v:,.2f}"

        rows.append(html.Tr([
            html.Td(h["ticker"], style={**td_s, "color": c["accent"], "fontWeight": "700"}),
            html.Td(f"{h['shares']:,.2f}", style={**td_s, "textAlign": "right"}),
            html.Td(f"\u00a3{h['avg_cost']:,.2f}", style={**td_s, "textAlign": "right"}),
            html.Td(_fmt_local(h.get("last_price_local"), h.get("currency", "")),
                    style={**td_s, "textAlign": "right"}),
            html.Td(_f(h["market_value"]), style={**td_s, "textAlign": "right"}),
            html.Td(_f(u_pnl), style={**td_s, "textAlign": "right", "color": u_col,
                                       "fontWeight": "600"}),
            html.Td(f"{u_pct:+.1f}%" if u_pct is not None else "\u2014",
                     style={**td_s, "textAlign": "right", "color": u_col}),
            html.Td(_f(h["realized_pnl"]), style={**td_s, "textAlign": "right"}),
            html.Td(_f(h.get("dividend_income", 0)), style={**td_s, "textAlign": "right",
                                                             "color": c["green"]}),
            html.Td(_f(t_pnl), style={**td_s, "textAlign": "right", "color": t_col,
                                       "fontWeight": "700"}),
            html.Td(f"{h['weight_pct']:.1f}%", style={**td_s, "textAlign": "right"}),
        ]))

    return html.Table([header, html.Tbody(rows)],
                      style={"width": "100%", "borderCollapse": "collapse"})


def _render_past_positions(hdf, c):
    """Render a compact table of fully-closed positions (shares == 0)."""
    closed = hdf[(hdf["shares"] <= 0)].copy() if not hdf.empty and "shares" in hdf.columns else pd.DataFrame()
    if closed.empty:
        return html.Div()

    th_s = {
        "padding": "0.25rem 0.5rem", "fontSize": "0.58rem", "fontWeight": "700",
        "textTransform": "uppercase", "letterSpacing": "0.05em",
        "borderBottom": f"2px solid {c['border']}", "fontFamily": FONT,
        "color": c["muted"], "whiteSpace": "nowrap",
    }
    td_s = {
        "padding": "0.25rem 0.5rem", "fontSize": "0.72rem", "fontFamily": FONT,
        "color": c["text"], "borderBottom": f"1px solid {c['border']}",
        "whiteSpace": "nowrap",
    }

    header = html.Thead(html.Tr([
        html.Th("Ticker", style={**th_s, "textAlign": "left"}),
        html.Th("Real P&L", style={**th_s, "textAlign": "right"}),
        html.Th("Divs", style={**th_s, "textAlign": "right"}),
        html.Th("Total P&L", style={**th_s, "textAlign": "right"}),
    ]))

    rows = []
    for _, h in closed.iterrows():
        r_pnl = h.get("realized_pnl", 0) or 0
        div_inc = h.get("dividend_income", 0) or 0
        t_pnl = h.get("total_pnl", 0) or 0
        t_col = c["green"] if t_pnl >= 0 else c["red"]
        r_col = c["green"] if r_pnl >= 0 else c["red"]
        rows.append(html.Tr([
            html.Td(h["ticker"], style={**td_s, "color": c["subtext"], "fontWeight": "600"}),
            html.Td(f"\u00a3{r_pnl:,.2f}", style={**td_s, "textAlign": "right", "color": r_col}),
            html.Td(f"\u00a3{div_inc:,.2f}", style={**td_s, "textAlign": "right", "color": c["green"]}),
            html.Td(f"\u00a3{t_pnl:,.2f}", style={**td_s, "textAlign": "right", "color": t_col,
                                                    "fontWeight": "700"}),
        ]))

    total_r = closed["realized_pnl"].sum()
    total_d = closed["dividend_income"].sum()
    total_t = closed["total_pnl"].sum()
    total_col = c["green"] if total_t >= 0 else c["red"]
    rows.append(html.Tr([
        html.Td("TOTAL", style={**td_s, "fontWeight": "700", "borderTop": f"2px solid {c['border']}"}),
        html.Td(f"\u00a3{total_r:,.2f}", style={**td_s, "textAlign": "right", "fontWeight": "700",
                "borderTop": f"2px solid {c['border']}",
                "color": c["green"] if total_r >= 0 else c["red"]}),
        html.Td(f"\u00a3{total_d:,.2f}", style={**td_s, "textAlign": "right", "fontWeight": "700",
                "borderTop": f"2px solid {c['border']}", "color": c["green"]}),
        html.Td(f"\u00a3{total_t:,.2f}", style={**td_s, "textAlign": "right", "fontWeight": "700",
                "borderTop": f"2px solid {c['border']}", "color": total_col}),
    ]))

    return html.Details([
        html.Summary(f"Past Positions ({len(closed)})", style={
            "color": c["muted"], "fontSize": "0.72rem", "fontFamily": FONT,
            "fontWeight": "700", "cursor": "pointer", "marginBottom": "0.4rem",
            "textTransform": "uppercase", "letterSpacing": "0.05em",
        }),
        html.Table([header, html.Tbody(rows)],
                   style={"width": "100%", "borderCollapse": "collapse"}),
    ], style={"marginTop": "1.2rem"})


def _render_price_overrides_table(df, c):
    """Render underlying price overrides table."""
    if df.empty:
        return html.Div("No price overrides set.",
                        style={"color": c["muted"], "fontSize": "0.78rem", "fontFamily": FONT})

    th_s = {
        "padding": "0.28rem 0.5rem", "fontSize": "0.6rem", "fontWeight": "700",
        "textTransform": "uppercase", "letterSpacing": "0.05em",
        "borderBottom": f"2px solid {c['border']}", "fontFamily": FONT,
        "color": c["muted"], "whiteSpace": "nowrap",
    }
    td_s = {
        "padding": "0.28rem 0.5rem", "fontSize": "0.75rem", "fontFamily": FONT,
        "color": c["text"], "borderBottom": f"1px solid {c['border']}",
        "whiteSpace": "nowrap",
    }

    header = html.Thead(html.Tr([
        html.Th("Date", style=th_s),
        html.Th("Ticker", style=th_s),
        html.Th("Local Price", style={**th_s, "textAlign": "right"}),
        html.Th("Notes", style=th_s),
    ]))

    rows = []
    for _, r in df.iterrows():
        rows.append(html.Tr([
            html.Td(str(r.get("date", "")), style=td_s),
            html.Td(str(r.get("ticker", "")), style={**td_s, "color": c["accent"], "fontWeight": "700"}),
            html.Td(f"{float(r.get('price_local', 0)):,.4f}", style={**td_s, "textAlign": "right"}),
            html.Td(str(r.get("notes", "") or ""), style={**td_s, "color": c["subtext"]}),
        ]))

    return html.Table([header, html.Tbody(rows)],
                      style={"width": "100%", "borderCollapse": "collapse"})


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # ── Period buttons for performance chart ─────────────────────────────
    from datetime import datetime, timedelta
    import pandas as pd
    @app.callback(
        Output("port-index-date", "date"),
        Output("port-period-status", "children"),
        Input("port-period-ytd", "n_clicks"),
        Input("port-period-mtd", "n_clicks"),
        Input("port-period-3m", "n_clicks"),
        Input("port-period-6m", "n_clicks"),
        Input("port-period-1y", "n_clicks"),
        Input("port-period-max", "n_clicks"),
        prevent_initial_call=True,
    )
    def set_period(ytd, mtd, m3, m6, y1, max_, ):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, ""
        btn = ctx.triggered[0]["prop_id"].split(".")[0]
        today = pd.Timestamp.today().normalize()
        if btn == "port-period-ytd":
            start = pd.Timestamp(year=today.year, month=1, day=1)
            label = f"YTD from {start.strftime('%d-%b-%Y')}"
        elif btn == "port-period-mtd":
            start = pd.Timestamp(year=today.year, month=today.month, day=1)
            label = f"MTD from {start.strftime('%d-%b-%Y')}"
        elif btn == "port-period-3m":
            start = today - pd.DateOffset(months=3)
            label = f"3M from {start.strftime('%d-%b-%Y')}"
        elif btn == "port-period-6m":
            start = today - pd.DateOffset(months=6)
            label = f"6M from {start.strftime('%d-%b-%Y')}"
        elif btn == "port-period-1y":
            start = today - pd.DateOffset(years=1)
            label = f"1Y from {start.strftime('%d-%b-%Y')}"
        elif btn == "port-period-max":
            start = None
            label = "Max: all data"
        else:
            return no_update, ""
        if start is not None:
            return start.date().isoformat(), label
        else:
            return None, label

    # ── 1) Add transaction ────────────────────────────────────────────────
    @app.callback(
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Output("port-txn-status", "children"),
        Output("port-txn-ticker", "value"),
        Output("port-txn-qty",    "value"),
        Output("port-txn-price",  "value"),
        Output("port-txn-fx",     "value"),
        Output("port-txn-notes",  "value"),
        Input("port-txn-add", "n_clicks"),
        State("port-txn-date",   "value"),
        State("port-txn-ticker", "value"),
        State("port-txn-side",   "value"),
        State("port-txn-qty",    "value"),
        State("port-txn-price",  "value"),
        State("port-txn-fx",     "value"),
        State("port-txn-fees",   "value"),
        State("port-txn-notes",  "value"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def add_txn(n, txn_date, ticker, side, qty, price, fx_rate, fees, notes, trigger):
        # Parse dd-mm-yyyy → ISO yyyy-mm-dd for storage
        def _parse_date(d):
            from datetime import datetime as _dt
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return _dt.strptime(d.strip(), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return None

        # DEPOSIT / WITHDRAW / INTEREST — need date + amount only
        if side in ("DEPOSIT", "WITHDRAW", "INTEREST"):
            if not txn_date or not price:
                return no_update, "⚠ Fill in date and amount.", no_update, no_update, no_update, no_update, no_update
            iso_date = _parse_date(txn_date)
            if not iso_date:
                return no_update, "⚠ Date format must be DD-MM-YYYY.", no_update, no_update, no_update, no_update, no_update
            try:
                price = float(price)
            except (ValueError, TypeError):
                return no_update, "⚠ Amount must be a number.", no_update, no_update, no_update, no_update, no_update
            if price <= 0:
                return no_update, "⚠ Amount must be > 0.", no_update, no_update, no_update, no_update, no_update

            add_transaction(iso_date, "CASH", side, 0, price, 0, notes, fx_rate=1.0)
            label = {"DEPOSIT": "Deposited", "WITHDRAW": "Withdrawn", "INTEREST": "Interest received"}[side]
            return ((trigger or 0) + 1,
                    f"✓ {label} £{price:,.2f}",
                    "", None, None, 1.0, "")

        # DIVIDEND — need date + ticker + amount
        if side == "DIVIDEND":
            if not txn_date or not ticker or not price:
                return no_update, "⚠ Fill in date, ticker, and amount.", no_update, no_update, no_update, no_update, no_update
            iso_date = _parse_date(txn_date)
            if not iso_date:
                return no_update, "⚠ Date format must be DD-MM-YYYY.", no_update, no_update, no_update, no_update, no_update
            try:
                price = float(price)
                fx_val = float(fx_rate or 1.0)
            except (ValueError, TypeError):
                return no_update, "⚠ Amount and FX rate must be numbers.", no_update, no_update, no_update, no_update, no_update
            if price <= 0:
                return no_update, "⚠ Amount must be > 0.", no_update, no_update, no_update, no_update, no_update

            add_transaction(iso_date, ticker, side, 0, price, 0, notes, fx_rate=fx_val)
            return ((trigger or 0) + 1,
                    f"✓ Dividend £{price * fx_val:,.2f} from {ticker.upper().strip()}",
                    "", None, None, 1.0, "")

        # BUY / SELL — need date, ticker, qty, price
        if not txn_date or not ticker or not qty or not price:
            return no_update, "⚠ Fill in date, ticker, quantity, and price.", no_update, no_update, no_update, no_update, no_update

        iso_date = _parse_date(txn_date)
        if not iso_date:
            return no_update, "⚠ Date format must be DD-MM-YYYY.", no_update, no_update, no_update, no_update, no_update

        try:
            qty = float(qty)
            price = float(price)
            fees = float(fees or 0)
            fx_val = float(fx_rate or 1.0)
        except (ValueError, TypeError):
            return no_update, "⚠ Quantity, price, fees, and FX rate must be numbers.", no_update, no_update, no_update, no_update, no_update

        if qty <= 0 or price < 0:
            return no_update, "⚠ Quantity must be > 0, price ≥ 0.", no_update, no_update, no_update, no_update, no_update

        # For SELLs, check we have enough shares
        if side == "SELL":
            txns = load_transactions()
            if not txns.empty:
                t_upper = ticker.upper().strip()
                t_txns = txns[txns["ticker"] == t_upper]
                buys = t_txns[t_txns["side"] == "BUY"]["quantity"].sum()
                sells = t_txns[t_txns["side"] == "SELL"]["quantity"].sum()
                current_shares = buys - sells
                if qty > current_shares + 0.001:
                    return (no_update,
                            f"⚠ Cannot sell {qty} shares of {t_upper} — only {current_shares:.2f} held.",
                            no_update, no_update, no_update, no_update, no_update)

        add_transaction(iso_date, ticker, side, qty, price, fees, notes, fx_rate=fx_val)
        return ((trigger or 0) + 1,
                f"✓ Added {side} {qty} {ticker.upper()} @ ${price:.2f} (FX: {fx_val})",
                "", None, None, 1.0, "")

    # ── 2) Delete transaction ─────────────────────────────────────────────
    @app.callback(
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Input({"type": "port-txn-del", "id": ALL}, "n_clicks"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def del_txn(n_clicks_list, trigger):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update
        prop = ctx.triggered[0]["prop_id"]
        if ctx.triggered[0]["value"] is None or ctx.triggered[0]["value"] == 0:
            return no_update
        try:
            btn_id = json.loads(prop.split(".")[0])
            delete_transaction(btn_id["id"])
            return (trigger or 0) + 1
        except Exception:
            return no_update

    # ── 2a-edit) Edit transaction (populate form + delete old) ─────────
    @app.callback(
        Output("port-txn-date",    "value"),
        Output("port-txn-ticker",  "value", allow_duplicate=True),
        Output("port-txn-side",    "value"),
        Output("port-txn-qty",     "value", allow_duplicate=True),
        Output("port-txn-price",   "value", allow_duplicate=True),
        Output("port-txn-fx",      "value", allow_duplicate=True),
        Output("port-txn-fees",    "value"),
        Output("port-txn-notes",   "value", allow_duplicate=True),
        Output("port-txn-status",  "children", allow_duplicate=True),
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Input({"type": "port-txn-edit", "id": ALL}, "n_clicks"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def edit_txn(n_clicks_list, trigger):
        ctx = dash.callback_context
        if not ctx.triggered:
            return (no_update,) * 10
        prop = ctx.triggered[0]["prop_id"]
        if ctx.triggered[0]["value"] is None or ctx.triggered[0]["value"] == 0:
            return (no_update,) * 10
        try:
            btn_id = json.loads(prop.split(".")[0])
            txn_id = btn_id["id"]
            # Load the transaction data before deleting
            txns = load_transactions()
            row = txns[txns["id"] == txn_id]
            if row.empty:
                return (no_update,) * 10
            tx = row.iloc[0]
            # Parse date to DD-MM-YYYY for form display
            try:
                from datetime import datetime as _dt
                display_date = _dt.strptime(str(tx["date"]).strip(), "%Y-%m-%d").strftime("%d-%m-%Y")
            except Exception:
                display_date = tx["date"]
            # Delete the old transaction
            delete_transaction(txn_id)
            # Populate form fields
            side = tx["side"]
            ticker = tx["ticker"] if tx["ticker"] != "CASH" else ""
            qty = float(tx["quantity"]) if float(tx["quantity"]) > 0 else None
            price = float(tx["price"])
            fx = float(tx.get("fx_rate", 1.0) or 1.0)
            fees = float(tx.get("fees", 0) or 0)
            notes = tx.get("notes", "") or ""
            return (
                display_date,
                ticker,
                side,
                qty,
                price,
                fx,
                fees,
                notes,
                f"✎ Editing {side} {ticker or 'CASH'} — modify and click + Add",
                (trigger or 0) + 1,
            )
        except Exception:
            return (no_update,) * 10

    # ── 2b) Clear all transactions ────────────────────────────────────────
    @app.callback(
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Output("port-txn-status", "children", allow_duplicate=True),
        Input("port-clear-all", "n_clicks"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def clear_all(n, trigger):
        if not n:
            return no_update, no_update
        clear_all_transactions()
        return (trigger or 0) + 1, "✓ All transactions cleared."

    # ── 2c) Set cash override ────────────────────────────────────────
    @app.callback(
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Output("port-cash-status", "children"),
        Output("port-cash-input", "value"),
        Input("port-cash-set", "n_clicks"),
        State("port-cash-input", "value"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def set_cash(n, amount, trigger):
        if not n:
            return no_update, no_update, no_update
        if amount is None:
            return no_update, "⚠ Enter a cash amount.", no_update
        try:
            val = float(amount)
        except (ValueError, TypeError):
            return no_update, "⚠ Must be a number.", no_update
        set_cash_override(val)
        return (trigger or 0) + 1, f"✓ Cash set to £{val:,.2f}", None

    # ── 2d) Clear cash override ──────────────────────────────────────
    @app.callback(
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Output("port-cash-status", "children", allow_duplicate=True),
        Input("port-cash-clear", "n_clicks"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def clear_cash(n, trigger):
        if not n:
            return no_update, no_update
        clear_cash_override()
        return (trigger or 0) + 1, "✓ Cash override removed — using calculated value."

    # ── 2e) Underlying price overrides ───────────────────────────────
    @app.callback(
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Output("port-price-ovr-status", "children"),
        Output("port-price-ovr-ticker", "value"),
        Output("port-price-ovr-value", "value"),
        Input("port-price-ovr-set", "n_clicks"),
        Input("port-price-ovr-clear", "n_clicks"),
        Input("port-price-ovr-clear-all", "n_clicks"),
        State("port-price-ovr-date", "date"),
        State("port-price-ovr-ticker", "value"),
        State("port-price-ovr-value", "value"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def manage_price_overrides(n_set, n_clear, n_clear_all, ovr_date, ticker, value, trigger):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update

        action = ctx.triggered[0]["prop_id"].split(".")[0]

        if action == "port-price-ovr-clear-all":
            clear_price_override()
            return (trigger or 0) + 1, "✓ Cleared all underlying price overrides.", "", None

        if not ovr_date or not ticker:
            return no_update, "⚠ Select a date and ticker.", no_update, no_update

        t = (ticker or "").upper().strip()

        if action == "port-price-ovr-clear":
            clear_price_override(ovr_date, t)
            return (trigger or 0) + 1, f"✓ Cleared override for {t} on {ovr_date}.", "", None

        # Set/Update
        try:
            px = float(value)
        except (ValueError, TypeError):
            return no_update, "⚠ Enter a valid local price.", no_update, no_update

        if px <= 0:
            return no_update, "⚠ Price must be > 0.", no_update, no_update

        set_price_override(ovr_date, t, px)
        return (trigger or 0) + 1, f"✓ Override set: {t} on {ovr_date} = {px:,.4f}", "", None

    @app.callback(
        Output("port-price-ovr-table", "children"),
        Input("port-refresh-trigger", "data"),
        State("theme-store", "data"),
    )
    def render_price_override_table(trigger, theme_mode):
        c = get_theme(theme_mode or "dark")
        df = list_price_overrides()
        return _render_price_overrides_table(df, c)

    # ── 3) CSV import ─────────────────────────────────────────────────────
    @app.callback(
        Output("port-refresh-trigger", "data", allow_duplicate=True),
        Output("port-txn-status", "children", allow_duplicate=True),
        Input("port-csv-upload", "contents"),
        State("port-csv-upload", "filename"),
        State("port-refresh-trigger", "data"),
        prevent_initial_call=True,
    )
    def csv_import(contents, filename, trigger):
        if contents is None:
            return no_update, no_update
        try:
            _, content_string = contents.split(",")
            decoded = base64.b64decode(content_string).decode("utf-8")
            count = import_csv(decoded)
            return (trigger or 0) + 1, f"✓ Imported {count} transactions from {filename}"
        except Exception as e:
            return no_update, f"⚠ Import error: {e}"

    # ── 4) CSV export ─────────────────────────────────────────────────────
    @app.callback(
        Output("port-csv-download", "data"),
        Input("port-csv-export", "n_clicks"),
        prevent_initial_call=True,
    )
    def csv_export(n):
        csv_str = export_csv()
        return dcc.send_string(csv_str, "portfolio_transactions.csv")

    # ── 4b) Export daily breakdown CSV ─────────────────────────────────
    @app.callback(
        Output("port-debug-download", "data"),
        Input("port-debug-export", "n_clicks"),
        prevent_initial_call=True,
    )
    def debug_export(n):
        txns = load_transactions()
        if txns.empty:
            return no_update
        _, debug_df = compute_portfolio_ts(txns, return_debug=True)
        if debug_df.empty:
            return no_update
        return dcc.send_data_frame(debug_df.to_csv, "portfolio_daily_breakdown.csv", index=False)

    # ── 5) Master render: ledger + holdings + overview + chart + recon ────
    @app.callback(
        Output("port-ledger-table",   "children"),
        Output("port-holdings-data",  "data"),
        Output("port-overview",       "children"),
        Output("port-chart",          "children"),
        Output("port-recon-table",    "children"),
        Input("port-refresh-trigger", "data"),
        Input("port-refresh",         "n_clicks"),
        Input("port-chart-mode",      "value"),
        Input("port-show-net-deposits", "value"),
        Input("port-index-date",      "date"),
        Input("port-benchmark",       "value"),
        State("theme-store",          "data"),
    )
    def render_all(trigger, n_refresh, chart_mode, show_net_deposits, index_date, benchmark_ticker, theme_mode):
        c = get_theme(theme_mode or "dark")

        txns = load_transactions()

        # Ledger
        ledger_html = _render_ledger(txns, c)

        if txns.empty:
            empty = html.Div("Add transactions to see holdings and performance.",
                             style={"color": c["muted"], "fontSize": "0.82rem",
                                    "fontFamily": FONT})
            overview = [
                _metric_card("Portfolio Value", "£0.00", c["text"], c),
                _metric_card("Net Invested", "£0.00", c["text"], c),
                _metric_card("Total P&L", "£0.00", c["text"], c),
                _metric_card("Cash", "£0.00", c["text"], c),
            ]
            return ledger_html, [], overview, html.Div(), html.Div()

        # Holdings
        hdf, summary = compute_holdings(txns)

        # Serialize holdings to JSON for the sort callback to render
        holdings_data = hdf.where(hdf.notna(), None).to_dict("records")

        # Overview cards
        pv = summary["portfolio_value"]
        tp = summary["total_pnl"]
        cash = summary["cash"]
        mv = summary["total_mv"]
        net_inv = summary["net_invested"]
        total_div = summary.get("total_dividends", 0)
        total_int = summary.get("total_interest", 0)
        # Return = (portfolio value - net invested) / net invested
        ret_pct = ((pv - net_inv) / net_inv * 100) if net_inv > 0 else 0

        tp_col = c["green"] if tp >= 0 else c["red"]
        ret_col = c["green"] if ret_pct >= 0 else c["red"]
        income = total_div + total_int
        cash_label = "Cash ✎" if summary.get("cash_overridden") else "Cash"
        overview = [
            _metric_card("Portfolio Value", f"£{pv:,.2f}", c["text"], c),
            _metric_card("Market Value", f"£{mv:,.2f}", c["text"], c),
            _metric_card("Net Invested", f"£{net_inv:,.2f}", c["blue"], c),
            _metric_card("Total P&L", f"£{tp:,.2f}", tp_col, c),
            _metric_card("Return", f"{ret_pct:+.2f}%", ret_col, c),
            _metric_card(cash_label, f"£{cash:,.2f}",
                         c["red"] if cash < 0 else c["text"], c),
            _metric_card("Dividends", f"£{total_div:,.2f}", c["green"], c),
            _metric_card("Interest", f"£{total_int:,.2f}", c["green"], c),
        ]

        # Performance chart
        chart_html = html.Div()
        ts = compute_portfolio_ts(txns)
        if not ts.empty:
            # Apply selected start date to all chart modes
            ts_plot = ts
            if index_date:
                try:
                    start_dt = pd.Timestamp(index_date).normalize()
                    filtered = ts[ts.index >= start_dt]
                    if not filtered.empty:
                        ts_plot = filtered
                except Exception:
                    pass

            fig = go.Figure()
            show_deposits = isinstance(show_net_deposits, list) and ("on" in show_net_deposits)

            # Build cumulative net deposits over selected range (deposits - withdrawals)
            net_dep_series = None
            if show_deposits:
                flow_rows = []
                for _, r in txns.iterrows():
                    side = str(r.get("side", "")).upper()
                    if side not in ("DEPOSIT", "WITHDRAW"):
                        continue
                    d = pd.Timestamp(r.get("date")).normalize()
                    _tg = r.get("total_gbp")
                    amt = float(_tg) if (_tg is not None and not pd.isna(_tg)) else float(r.get("price", 0) or 0)
                    signed_amt = amt if side == "DEPOSIT" else -amt
                    flow_rows.append((d, signed_amt))

                if flow_rows:
                    flows = pd.DataFrame(flow_rows, columns=["date", "flow"]).groupby("date")["flow"].sum().sort_index()
                    all_idx = ts_plot.index.union(flows.index).sort_values()
                    net_all = flows.reindex(all_idx, fill_value=0.0).cumsum()
                    net_dep_series = net_all.reindex(ts_plot.index, method="ffill").fillna(0.0)
                else:
                    net_dep_series = pd.Series(0.0, index=ts_plot.index)

            if chart_mode == "value":
                fig.add_trace(go.Scatter(
                    x=ts_plot.index, y=ts_plot["portfolio_value"],
                    mode="lines", name="Portfolio Value",
                    line={"color": c["accent"], "width": 2},
                    fill="tozeroy",
                    fillcolor=f"rgba(255,140,0,0.08)",
                    hovertemplate="£%{y:,.2f}<extra></extra>",
                ))
                if net_dep_series is not None and not net_dep_series.empty:
                    fig.add_trace(go.Scatter(
                        x=net_dep_series.index,
                        y=net_dep_series.values,
                        mode="lines",
                        name="Net Deposits",
                        line={"color": c["muted"], "width": 1.8, "dash": "dot"},
                        hovertemplate="Net Deposits: £%{y:,.2f}<extra></extra>",
                    ))
                y_title = "Portfolio Value (£)"
            elif chart_mode == "return":
                if "twr" in ts_plot.columns:
                    base_twr = ts_plot["twr"].iloc[0]
                    cum_ret_plot = (ts_plot["twr"] / base_twr - 1) * 100
                else:
                    base_val = ts_plot["portfolio_value"].iloc[0]
                    cum_ret_plot = (ts_plot["portfolio_value"] / base_val - 1) * 100

                colour = c["green"] if cum_ret_plot.iloc[-1] >= 0 else c["red"]
                fig.add_trace(go.Scatter(
                    x=ts_plot.index, y=cum_ret_plot,
                    mode="lines", name="Cumulative Return",
                    line={"color": colour, "width": 2},
                    hovertemplate="%{y:.2f}%<extra></extra>",
                ))
                fig.add_hline(y=0, line_dash="solid", line_color=c["muted"], line_width=0.8)
                y_title = "Cumulative Return (%)"

                # Overlay benchmark if provided
                if benchmark_ticker and benchmark_ticker.strip():
                    _add_benchmark_return(fig, benchmark_ticker.strip(), ts_plot.index[0], ts_plot.index[-1], c)

            elif chart_mode == "indexed":
                # Rebase selected range to 100
                if "twr" in ts_plot.columns:
                    base_val = ts_plot["twr"].iloc[0]
                    indexed = 100 * ts_plot["twr"] / base_val
                else:
                    base_val = ts_plot["portfolio_value"].iloc[0]
                    indexed = 100 * ts_plot["portfolio_value"] / base_val

                last_val = indexed.iloc[-1]
                colour = c["green"] if last_val >= 100 else c["red"]
                fig.add_trace(go.Scatter(
                    x=indexed.index, y=indexed.values,
                    mode="lines", name="Indexed (100)",
                    line={"color": colour, "width": 2},
                    hovertemplate="%{y:.2f}<extra></extra>",
                ))
                fig.add_hline(y=100, line_dash="solid", line_color=c["muted"], line_width=0.8)
                y_title = "Indexed Return (100)"

                # Overlay benchmark if provided
                if benchmark_ticker and benchmark_ticker.strip():
                    _add_benchmark(fig, benchmark_ticker.strip(), indexed.index[0], indexed.index[-1], c)

            else:  # drawdown
                # Drawdown must be computed from the selected range so period buttons/date apply
                pv = ts_plot["portfolio_value"]
                running_max = pv.cummax()
                drawdown_plot = ((pv - running_max) / running_max * 100).fillna(0)
                fig.add_trace(go.Scatter(
                    x=ts_plot.index, y=drawdown_plot,
                    mode="lines", name="Drawdown",
                    line={"color": c["red"], "width": 2},
                    fill="tozeroy",
                    fillcolor=f"rgba(255,51,51,0.1)",
                    hovertemplate="%{y:.2f}%<extra></extra>",
                ))

                # Overlay benchmark drawdown if provided
                if benchmark_ticker and benchmark_ticker.strip():
                    _add_benchmark_drawdown(fig, benchmark_ticker.strip(), ts_plot.index[0], ts_plot.index[-1], c)
                y_title = "Drawdown (%)"

            has_benchmark = benchmark_ticker and benchmark_ticker.strip() and chart_mode in ("indexed", "return", "drawdown")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"family": FONT, "color": c["text"], "size": 11},
                margin={"l": 50, "r": 15, "t": 15, "b": 35},
                height=350,
                yaxis={"title": y_title, "gridcolor": c["border"],
                       "zerolinecolor": c["muted"]},
                xaxis={"gridcolor": c["border"]},
                showlegend=has_benchmark,
                legend={"font": {"size": 10}, "orientation": "h",
                        "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
                hoverlabel={
                    "bgcolor": c["panel"],
                    "bordercolor": c["border"],
                    "font": {"family": FONT, "color": c["text"], "size": 11},
                },
            )
            chart_html = dcc.Graph(figure=fig, config={"displayModeBar": False})

        # ── Cash reconciliation table ──────────────────────────────────
        recon_th = {"padding": "0.3rem 0.6rem", "fontSize": "0.65rem",
                    "fontWeight": "700", "textTransform": "uppercase",
                    "letterSpacing": "0.05em", "color": c["muted"],
                    "borderBottom": f"2px solid {c['border']}", "fontFamily": FONT}
        recon_td = {"padding": "0.3rem 0.6rem", "fontSize": "0.78rem",
                    "fontFamily": FONT, "color": c["text"],
                    "borderBottom": f"1px solid {c['border']}"}
        recon_items = [
            ("Total Deposits",       summary["total_deposited"]),
            ("Total Withdrawals",   -summary["total_withdrawn"]),
            ("Total Buy Cost",      -summary["total_buy_cost"]),
            ("Total Sell Proceeds",  summary["total_sell_proceeds"]),
            ("Total Fees",          -summary["total_fees"]),
            ("Total Dividends",      summary.get("total_dividends", 0)),
            ("Total Interest",       summary.get("total_interest", 0)),
        ]
        recon_rows = []
        for lbl, val in recon_items:
            val_col = c["green"] if val >= 0 else c["red"]
            recon_rows.append(html.Tr([
                html.Td(lbl, style={**recon_td, "fontWeight": "600"}),
                html.Td(f"£{val:,.2f}", style={**recon_td, "textAlign": "right", "color": val_col}),
            ]))
        # Calculated cash row
        calc_cash = summary["cash_calculated"]
        calc_col = c["green"] if calc_cash >= 0 else c["red"]
        recon_rows.append(html.Tr([
            html.Td("= Calculated Cash", style={**recon_td, "fontWeight": "700",
                    "borderTop": f"2px solid {c['accent']}"}),
            html.Td(f"£{calc_cash:,.2f}", style={**recon_td, "textAlign": "right",
                    "fontWeight": "700", "color": calc_col,
                    "borderTop": f"2px solid {c['accent']}"}),
        ]))
        # If broker cash override is set, show gap
        if summary.get("cash_overridden"):
            broker_cash = summary["cash"]
            gap = broker_cash - calc_cash
            gap_col = c["green"] if abs(gap) < 0.01 else c["red"]
            recon_rows.append(html.Tr([
                html.Td("Broker Cash (override)", style={**recon_td, "fontWeight": "600"}),
                html.Td(f"£{broker_cash:,.2f}", style={**recon_td, "textAlign": "right",
                        "color": c["accent"], "fontWeight": "600"}),
            ]))
            recon_rows.append(html.Tr([
                html.Td("Gap", style={**recon_td, "fontWeight": "700"}),
                html.Td(f"£{gap:,.2f}", style={**recon_td, "textAlign": "right",
                        "fontWeight": "700", "color": gap_col}),
            ]))

        recon_html = html.Table(
            [html.Thead(html.Tr([
                html.Th("Item", style=recon_th),
                html.Th("Amount", style={**recon_th, "textAlign": "right"}),
            ])), html.Tbody(recon_rows)],
            style={"width": "auto", "maxWidth": "360px", "borderCollapse": "collapse"},
        )

        return ledger_html, holdings_data, overview, chart_html, recon_html

    # ── 6) Sort + render holdings (lightweight — no data re-fetch) ─────────
    @app.callback(
        Output("port-holdings-table", "children"),
        Input("port-holdings-data",  "data"),
        Input("port-holdings-sort",  "value"),
        State("theme-store",         "data"),
    )
    def render_sorted_holdings(data, sort_val, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not data:
            return html.Div("Add transactions to see holdings.",
                            style={"color": c["muted"], "fontSize": "0.82rem",
                                   "fontFamily": FONT})
        hdf = pd.DataFrame(data)

        # Parse sort value → column + direction
        sort_val = sort_val or "weight_pct_desc"
        if sort_val.endswith("_asc"):
            sort_col = sort_val[:-4]
            ascending = True
        else:
            sort_col = sort_val[:-5]
            ascending = False

        # Sort active holdings
        active = hdf[hdf["shares"] > 0].copy() if "shares" in hdf.columns else hdf.copy()
        if sort_col in active.columns and not active.empty:
            active = active.sort_values(sort_col, ascending=ascending, na_position="last")

        return html.Div([
            _render_holdings(active, c),
            _render_past_positions(hdf, c),
        ])

    # ── 7) Starting cash calculation ──────────────────────────────────────────
    @app.callback(
        Output("port-starting-cash", "children"),
        Input("port-current-cash",   "value"),
        Input("port-refresh-trigger", "data"),
        Input("port-refresh",         "n_clicks"),
        prevent_initial_call=True,
    )
    def calc_starting_cash(current_cash, trigger, n_refresh):
        if not current_cash:
            return ""
        try:
            current_val = float(current_cash)
        except (ValueError, TypeError):
            return "Enter a valid number"
        txns = load_transactions()
        if txns.empty:
            return f"Starting Cash: £{current_val:,.2f}"
        _, summary = compute_holdings(txns)
        calc = summary.get("cash_calculated", 0)
        starting = current_val - calc
        return f"Starting Cash: £{starting:,.2f}"