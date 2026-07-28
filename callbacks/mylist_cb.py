"""Callback — My Stocks: add/remove stocks, price returns, news feed,
valuation & profitability metrics in a single view."""

import json
from concurrent.futures import ThreadPoolExecutor

import dash
import yfinance as yf
from dash import html, dcc, Input, Output, State, ALL, no_update

from theme import FONT, get_theme
from data import parse_tickers, fetch_news


# ─────────────────────────────────────────────────────────────────────────────
# Return-period colour helpers (same as watchlist)
# ─────────────────────────────────────────────────────────────────────────────

def _return_bg(val):
    if val is None:
        return "transparent"
    clamped = max(-50, min(50, val))
    intensity = abs(clamped) / 50
    alpha = 0.10 + intensity * 0.45
    if clamped >= 0:
        return f"rgba(63,185,80,{alpha:.2f})"
    return f"rgba(248,81,73,{alpha:.2f})"


# ─────────────────────────────────────────────────────────────────────────────
# Data fetchers
# ─────────────────────────────────────────────────────────────────────────────

_RETURN_PERIODS = {
    "1D": "5d", "5D": "5d", "1W": "5d", "1M": "1mo",
    "3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y",
}


def _fetch_price_rows(tickers):
    """Fetch price + return data for each ticker (parallelised)."""

    def _one(ticker):
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            ccy = info.get("currency", "")

            row = {"Ticker": ticker, "Price": price, "Ccy": ccy}

            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
            if price and prev_close and prev_close != 0:
                row["1D"] = round((price / prev_close - 1) * 100, 2)
            else:
                row["1D"] = 0.0

            for label, period in _RETURN_PERIODS.items():
                if label == "1D":
                    continue
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
            return row
        except Exception:
            return {"Ticker": ticker, "Price": None, "Ccy": "",
                    **{lbl: None for lbl in _RETURN_PERIODS}}

    with ThreadPoolExecutor(max_workers=10) as pool:
        return list(pool.map(_one, tickers))


def _fetch_metrics_rows(tickers):
    """Fetch valuation + profitability metrics for each ticker (parallelised)."""

    def _one(ticker):
        try:
            info = yf.Ticker(ticker).info or {}

            def _r(key, mult=1):
                v = info.get(key)
                if v is None:
                    return None
                return round(float(v) * mult, 2)

            ev = info.get("enterpriseValue")
            rev = info.get("totalRevenue")
            ebitda = info.get("ebitda")

            return {
                "Ticker":           ticker,
                "P/E":              _r("trailingPE"),
                "Fwd P/E":          _r("forwardPE"),
                "PEG":              _r("pegRatio"),
                "P/S":              _r("priceToSalesTrailing12Months"),
                "P/B":              _r("priceToBook"),
                "EV/Sales":         round(ev / rev, 2) if (ev and rev and rev != 0) else None,
                "EV/EBITDA":        round(ev / ebitda, 2) if (ev and ebitda and ebitda != 0) else None,
                "Div Yld":          _r("dividendYield", 100),
                "Gross Mgn":        _r("grossMargins", 100),
                "EBITDA Mgn":       _r("ebitdaMargins", 100),
                "Op Mgn":           _r("operatingMargins", 100),
                "Net Mgn":          _r("profitMargins", 100),
                "ROE":              _r("returnOnEquity", 100),
                "ROA":              _r("returnOnAssets", 100),
                "Mkt Cap":          info.get("marketCap"),
            }
        except Exception:
            return {"Ticker": ticker}

    with ThreadPoolExecutor(max_workers=10) as pool:
        return list(pool.map(_one, tickers))


# ─────────────────────────────────────────────────────────────────────────────
# Table builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_price_table(rows, c):
    return_cols = ["1D", "5D", "1W", "1M", "3M", "6M", "1Y", "2Y"]
    all_cols = ["Ticker", "Price"] + return_cols

    th = {
        "padding": "0.38rem 0.6rem", "fontSize": "0.62rem",
        "textTransform": "uppercase", "letterSpacing": "0.06em",
        "fontWeight": "700", "whiteSpace": "nowrap",
        "borderBottom": "2px solid " + c["border"],
        "fontFamily": FONT, "color": c["text"],
    }

    header = html.Thead(html.Tr(
        [html.Th("", style={**th, "width": "28px"})] +
        [html.Th(col, style={**th, "textAlign": "left" if col == "Ticker" else "right"})
         for col in all_cols]
    ))

    body_rows = []
    for row in rows:
        ticker = row["Ticker"]
        cells = [
            html.Td(
                html.Button("✕", id={"type": "mylist-remove", "ticker": ticker},
                            n_clicks=0, style={
                    "background": "none", "border": "none", "color": c["red"],
                    "cursor": "pointer", "fontWeight": "700", "fontSize": "0.82rem",
                    "padding": "0",
                }),
                style={"padding": "0.4rem 0.3rem",
                       "borderBottom": "1px solid " + c["border"],
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
                    display = "—"
                cells.append(html.Td(display, style={
                    "color": c["accent"], "fontWeight": "700",
                    "padding": "0.4rem 0.6rem", "textAlign": "right",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.82rem", "fontFamily": FONT,
                }))
            else:
                if val is not None:
                    sign = "+" if val > 0 else ""
                    display = f"{sign}{val:.2f}%"
                else:
                    display = "—"
                cells.append(html.Td(display, style={
                    "color": c["text"],
                    "backgroundColor": _return_bg(val),
                    "fontWeight": "700",
                    "padding": "0.4rem 0.6rem", "textAlign": "right",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.8rem", "fontFamily": FONT,
                    "borderRadius": "4px",
                }))
        body_rows.append(html.Tr(cells))

    return html.Div(
        html.Table([header, html.Tbody(body_rows)],
                   style={"width": "100%", "borderCollapse": "collapse"}),
        style={"overflowX": "auto"},
    )


def _build_news_feed(tickers, c):
    """Build a compact news feed for the given tickers."""
    if not tickers:
        return html.Div("Add stocks to see news.", style={
            "color": c["muted"], "fontSize": "0.78rem", "fontFamily": FONT})

    news = fetch_news(tickers, max_per=3)
    articles = news.get("stock", [])

    if not articles:
        return html.Div("No recent news found.", style={
            "color": c["muted"], "fontSize": "0.78rem", "fontFamily": FONT})

    items = []
    for a in articles[:30]:
        items.append(html.Div([
            html.Span(a.get("ticker", ""), style={
                "fontWeight": "700", "fontSize": "0.68rem",
                "color": c["accent"], "marginRight": "0.5rem",
                "fontFamily": FONT,
            }),
            html.A(a.get("title", ""), href=a.get("link", "#"),
                   target="_blank", rel="noopener noreferrer",
                   style={
                       "color": c["text"], "fontSize": "0.76rem",
                       "textDecoration": "none", "fontFamily": FONT,
                   }),
            html.Div([
                html.Span(a.get("source", ""), style={
                    "fontSize": "0.62rem", "color": c["muted"], "fontFamily": FONT}),
                html.Span(" · ", style={"color": c["muted"], "fontSize": "0.62rem"}),
                html.Span(a.get("published", ""), style={
                    "fontSize": "0.62rem", "color": c["muted"], "fontFamily": FONT}),
            ], style={"marginTop": "0.1rem"}),
        ], style={"padding": "0.45rem 0",
                  "borderBottom": f"1px solid {c['border']}"}))

    return html.Div(items)


def _build_metrics_table(rows, c):
    """Build a valuation & profitability table."""
    val_cols = ["P/E", "Fwd P/E", "PEG", "P/S", "P/B", "EV/Sales", "EV/EBITDA", "Div Yld"]
    prof_cols = ["Gross Mgn", "EBITDA Mgn", "Op Mgn", "Net Mgn", "ROE", "ROA"]
    pct_cols = {"Div Yld", "Gross Mgn", "EBITDA Mgn", "Op Mgn", "Net Mgn", "ROE", "ROA"}
    all_cols = ["Ticker", "Mkt Cap"] + val_cols + prof_cols

    th = {
        "padding": "0.38rem 0.6rem", "fontSize": "0.62rem",
        "textTransform": "uppercase", "letterSpacing": "0.06em",
        "fontWeight": "700", "whiteSpace": "nowrap",
        "borderBottom": "2px solid " + c["border"],
        "fontFamily": FONT, "color": c["text"],
    }

    # Group headers
    group_header = html.Tr([
        html.Th("", style={**th, "borderBottom": "none"}, colSpan=2),
        html.Th("Valuation", style={**th, "textAlign": "center",
                "borderBottom": f"1px solid {c['accent']}", "color": c["accent"]},
                colSpan=len(val_cols)),
        html.Th("Profitability", style={**th, "textAlign": "center",
                "borderBottom": f"1px solid {c['accent']}", "color": c["accent"]},
                colSpan=len(prof_cols)),
    ])
    col_header = html.Tr(
        [html.Th(col, style={**th, "textAlign": "left" if col == "Ticker" else "right"})
         for col in all_cols]
    )
    header = html.Thead([group_header, col_header])

    body_rows = []
    for row in rows:
        cells = []
        for col in all_cols:
            val = row.get(col)
            if col == "Ticker":
                cells.append(html.Td(val, style={
                    "color": c["text"], "fontWeight": "700",
                    "padding": "0.4rem 0.6rem",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.82rem", "fontFamily": FONT,
                }))
            elif col == "Mkt Cap":
                if val and val >= 1e9:
                    display = f"${val / 1e9:.1f}B"
                elif val and val >= 1e6:
                    display = f"${val / 1e6:.0f}M"
                else:
                    display = "—"
                cells.append(html.Td(display, style={
                    "color": c["text"], "fontWeight": "600",
                    "padding": "0.4rem 0.6rem", "textAlign": "right",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.8rem", "fontFamily": FONT,
                }))
            elif col in pct_cols:
                display = f"{val:.1f}%" if val is not None else "—"
                cells.append(html.Td(display, style={
                    "color": c["text"],
                    "padding": "0.4rem 0.6rem", "textAlign": "right",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.8rem", "fontFamily": FONT,
                }))
            else:
                display = f"{val:.2f}" if val is not None else "—"
                cells.append(html.Td(display, style={
                    "color": c["text"],
                    "padding": "0.4rem 0.6rem", "textAlign": "right",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.8rem", "fontFamily": FONT,
                }))
        body_rows.append(html.Tr(cells))

    return html.Div(
        html.Table([header, html.Tbody(body_rows)],
                   style={"width": "100%", "borderCollapse": "collapse"}),
        style={"overflowX": "auto"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Register callbacks
# ─────────────────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # ── 1) Manage the stored ticker list ──────────────────────────────────
    @app.callback(
        Output("mylist-store", "data"),
        Output("mylist-input", "value"),
        Input("mylist-add",   "n_clicks"),
        Input("mylist-clear", "n_clicks"),
        Input({"type": "mylist-remove", "ticker": ALL}, "n_clicks"),
        State("mylist-input", "value"),
        State("mylist-store", "data"),
        prevent_initial_call=True,
    )
    def manage_store(n_add, n_clear, n_removes, raw_input, store):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update

        trigger = ctx.triggered[0]["prop_id"]
        store = store or []

        if "mylist-clear" in trigger:
            return [], ""

        if "mylist-remove" in trigger:
            try:
                btn_id = json.loads(trigger.split(".")[0])
                store = [t for t in store if t != btn_id["ticker"]]
            except Exception:
                pass
            return store, no_update

        if "mylist-add" in trigger:
            new_tickers = parse_tickers(raw_input)
            for t in new_tickers:
                if t not in store:
                    store.append(t)
            return store, ""

        return no_update, no_update

    # ── 2) Render everything when store changes ───────────────────────────
    @app.callback(
        Output("mylist-pills",         "children"),
        Output("mylist-price-table",   "children"),
        Output("mylist-news",          "children"),
        Output("mylist-metrics-table", "children"),
        Output("mylist-status",        "children"),
        Input("mylist-store",   "data"),
        Input("mylist-refresh", "n_clicks"),
        Input("theme-store",   "data"),
    )
    def render_mylist(store, n_refresh, theme_mode):
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
                html.Button("✕", id={"type": "mylist-remove", "ticker": ticker},
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
            empty = html.Div("Add stocks above to get started.",
                             style={"color": c["text"], "fontSize": "0.82rem",
                                    "fontFamily": FONT})
            return pills, empty, "", "", ""

        # Fetch all data
        price_rows = _fetch_price_rows(store)
        metrics_rows = _fetch_metrics_rows(store)

        price_table = _build_price_table(price_rows, c)
        news_feed = _build_news_feed(store, c)
        metrics_table = _build_metrics_table(metrics_rows, c)

        status = f"{len(store)} stock{'s' if len(store) != 1 else ''}"
        return pills, price_table, news_feed, metrics_table, status
