"""Callback — Watchlist: persistent add/remove + conditional-formatted returns."""

import json

import dash
import yfinance as yf
from dash import html, dcc, Input, Output, State, ALL, no_update

from theme import FONT, get_theme
from data import parse_tickers


# ─────────────────────────────────────────────────────────────────────────────
# Data fetcher (unchanged logic, called only for the full ticker list)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_watchlist_data(tickers):
    period_map = {
        "1D":  "5d",
        "5D":  "5d",
        "1W":  "5d",
        "1M":  "1mo",
        "3M":  "3mo",
        "6M":  "6mo",
        "1Y":  "1y",
        "2Y":  "2y",
    }
    rows = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            ev  = info.get("enterpriseValue")
            rev = info.get("totalRevenue")
            ev_sales = round(ev / rev, 2) if (ev and rev and rev != 0) else None

            pe = info.get("trailingPE")
            pe = round(float(pe), 2) if pe is not None else None

            mc = info.get("marketCap")
            mc_fmt = (f"${mc/1e9:.2f}B" if mc and mc >= 1e9
                      else f"${mc/1e6:.1f}M" if mc else "—")

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            ccy = info.get("currency", "")

            row = {"Ticker": ticker, "Price": price, "Ccy": ccy,
                   "EV/Sales": ev_sales, "P/E": pe, "Mkt Cap": mc_fmt}

            # 1D: use currentPrice vs previousClose (yf period="1d" only gives 1 row)
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
            if price and prev_close and prev_close != 0:
                row["1D"] = round((price / prev_close - 1) * 100, 2)
            else:
                row["1D"] = 0.0

            for label, period in period_map.items():
                if label == "1D":
                    continue   # already handled above
                try:
                    hist = t.history(period=period)
                    if hist is not None and len(hist) >= 2:
                        ret = ((hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                               / hist["Close"].iloc[0]) * 100
                        row[label] = round(ret, 2)
                    else:
                        row[label] = None
                except Exception:
                    row[label] = None

            rows.append(row)
        except Exception:
            rows.append({"Ticker": ticker, "Price": None, "Ccy": "",
                         "EV/Sales": None, "P/E": None,
                         "Mkt Cap": "—",
                         **{lbl: None for lbl in period_map}})
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Conditional-format helper: returns an rgba background colour for a %
# ─────────────────────────────────────────────────────────────────────────────

def _return_bg(val):
    """Map a return % to a background colour on a red ↔ green gradient."""
    if val is None:
        return "transparent"
    # Clamp to ±50 % for colour intensity
    clamped = max(-50, min(50, val))
    intensity = abs(clamped) / 50          # 0 → 1
    alpha     = 0.10 + intensity * 0.45    # 0.10 → 0.55
    if clamped >= 0:
        return f"rgba(63,185,80,{alpha:.2f})"   # green
    return f"rgba(248,81,73,{alpha:.2f})"        # red


def _return_color(val, c):
    return c["text"]


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # ── 1) Manage the stored ticker list (add / remove / clear) ───────────
    @app.callback(
        Output("watchlist-store", "data"),
        Output("watchlist-input", "value"),
        Input("watchlist-add",   "n_clicks"),
        Input("watchlist-clear", "n_clicks"),
        Input({"type": "watchlist-remove", "ticker": ALL}, "n_clicks"),
        State("watchlist-input", "value"),
        State("watchlist-store", "data"),
        prevent_initial_call=True,
    )
    def manage_store(n_add, n_clear, n_removes, raw_input, store):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update

        trigger = ctx.triggered[0]["prop_id"]
        store = store or []

        # Clear all
        if "watchlist-clear" in trigger:
            return [], ""

        # Remove a single ticker
        if "watchlist-remove" in trigger:
            try:
                btn_id = json.loads(trigger.split(".")[0])
                ticker_to_remove = btn_id["ticker"]
                store = [t for t in store if t != ticker_to_remove]
            except Exception:
                pass
            return store, no_update

        # Add new tickers
        if "watchlist-add" in trigger:
            new_tickers = parse_tickers(raw_input)
            for t in new_tickers:
                if t not in store:
                    store.append(t)
            return store, ""

        return no_update, no_update

    # ── 2) Render pills + table whenever the store changes ────────────────
    @app.callback(
        Output("watchlist-pills",  "children"),
        Output("watchlist-table",  "children"),
        Output("watchlist-status", "children"),
        Input("watchlist-store", "data"),
        Input("watchlist-refresh", "n_clicks"),
        Input("theme-store",     "data"),
    )
    def render_watchlist(store, n_refresh, theme_mode):
        c = get_theme(theme_mode or "dark")
        store = store or []

        # Pills
        pills = []
        for ticker in store:
            pills.append(html.Div([
                html.Span(ticker, style={
                    "fontFamily": FONT, "fontSize": "0.78rem", "fontWeight": "700",
                    "color": c["text"], "marginRight": "0.3rem",
                }),
                html.Button("\u2715", id={"type": "watchlist-remove", "ticker": ticker},
                            n_clicks=0, style={
                    "background": "none", "border": "none", "color": c["red"],
                    "cursor": "pointer", "fontWeight": "700", "fontSize": "0.78rem",
                    "padding": "0", "lineHeight": "1",
                }),
            ], style={
                "display": "inline-flex", "alignItems": "center",
                "backgroundColor": c["border"], "borderRadius": "14px",
                "padding": "0.25rem 0.65rem",
            }))

        if not store:
            empty = html.Div("No stocks in watchlist yet.",
                             style={"color": c["text"], "fontSize": "0.82rem", "fontFamily": FONT})
            return pills, empty, ""

        # Fetch data
        data = _fetch_watchlist_data(store)

        metric_cols = ["EV/Sales", "P/E", "Mkt Cap"]
        return_cols = ["1D", "5D", "1W", "1M", "3M", "6M", "1Y", "2Y"]
        all_cols    = ["Ticker", "Price"] + metric_cols + return_cols

        th_style = {
            "padding": "0.38rem 0.6rem", "fontSize": "0.62rem", "textTransform": "uppercase",
            "letterSpacing": "0.06em", "fontWeight": "700", "whiteSpace": "nowrap",
            "borderBottom": "2px solid " + c["border"], "fontFamily": FONT, "color": c["text"],
        }

        # Extra column for the remove button
        header = html.Thead(html.Tr(
            [html.Th("", style={**th_style, "width": "28px"})] +
            [html.Th(col_name, style={**th_style, "textAlign": "left" if col_name == "Ticker" else "right"})
             for col_name in all_cols]
        ))

        body_rows = []
        for row in data:
            ticker = row["Ticker"]
            cells = [
                html.Td(
                    html.Button("\u2715", id={"type": "watchlist-remove", "ticker": ticker},
                                n_clicks=0, style={
                        "background": "none", "border": "none", "color": c["red"],
                        "cursor": "pointer", "fontWeight": "700", "fontSize": "0.82rem",
                        "padding": "0",
                    }),
                    style={"padding": "0.4rem 0.3rem", "borderBottom": "1px solid " + c["border"],
                           "textAlign": "center"},
                ),
            ]
            for col in all_cols:
                val = row.get(col)

                if col == "Ticker":
                    cells.append(html.Td(val, style={
                        "color": c["text"], "fontWeight": "700",
                        "padding": "0.4rem 0.6rem",
                        "borderBottom": "1px solid " + c["border"],
                        "fontSize": "0.82rem", "fontFamily": FONT,
                    }))
                elif col == "Price":
                    ccy = row.get("Ccy", "")
                    ccy_sym = {"USD": "$", "GBP": "£", "GBp": "", "GBX": "", "EUR": "€"}.get(ccy, "")
                    if val is not None:
                        suffix = "p" if ccy in ("GBp", "GBX") else ""
                        display = f"{ccy_sym}{val:,.2f}{suffix}"
                    else:
                        display = "\u2014"
                    cells.append(html.Td(display, style={
                        "color": c["accent"], "fontWeight": "700",
                        "padding": "0.4rem 0.6rem", "textAlign": "right",
                        "borderBottom": "1px solid " + c["border"],
                        "fontSize": "0.82rem", "fontFamily": FONT,
                    }))
                elif col == "Mkt Cap":
                    cells.append(html.Td(str(val), style={
                        "color": c["text"], "fontWeight": "600",
                        "padding": "0.4rem 0.6rem", "textAlign": "right",
                        "borderBottom": "1px solid " + c["border"],
                        "fontSize": "0.8rem", "fontFamily": FONT,
                    }))
                elif col in metric_cols:
                    display = f"{val:.2f}" if val is not None else "\u2014"
                    cells.append(html.Td(display, style={
                        "color": c["text"],
                        "fontWeight": "600",
                        "padding": "0.4rem 0.6rem", "textAlign": "right",
                        "borderBottom": "1px solid " + c["border"],
                        "fontSize": "0.8rem", "fontFamily": FONT,
                    }))
                else:
                    # Return column — conditional background + text colour
                    if val is not None:
                        sign    = "+" if val > 0 else ""
                        display = f"{sign}{val:.2f}%"
                    else:
                        display = "\u2014"
                    cells.append(html.Td(display, style={
                        "color": _return_color(val, c),
                        "backgroundColor": _return_bg(val),
                        "fontWeight": "700",
                        "padding": "0.4rem 0.6rem", "textAlign": "right",
                        "borderBottom": "1px solid " + c["border"],
                        "fontSize": "0.8rem", "fontFamily": FONT,
                        "borderRadius": "4px",
                    }))

            body_rows.append(html.Tr(cells))

        table = html.Div(
            html.Table([header, html.Tbody(body_rows)],
                       style={"width": "100%", "borderCollapse": "collapse"}),
            style={"overflowX": "auto"},
        )

        status = f"{len(data)} stock{'s' if len(data) != 1 else ''} in watchlist"
        return pills, table, status
