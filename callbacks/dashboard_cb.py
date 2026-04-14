"""Callback — Bloomberg-style dashboard home page."""

import datetime
import dash
import numpy as np
import plotly.graph_objects as go

from dash import html, dcc, Input, Output, State, no_update

from theme import (
    C, FONT, get_theme,
    INDICES, FX_PAIRS, BONDS, COMMODITIES, SECTOR_ETFS,
)
from data import (
    parse_tickers, fetch_index_data, fetch_prices,
    fetch_quote_table, fetch_sector_performance,
    fetch_chart_data, fetch_portfolio_history,
    fetch_news, fetch_sp500_movers,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mini_table(rows, c, decimals=2, show_pct=True):
    """Build a compact Bloomberg-style quote table from fetch_quote_table output."""
    trs = []
    for r in rows:
        col = c["green"] if r["chg"] >= 0 else c["red"]
        sign = "+" if r["chg"] >= 0 else ""
        price_str = f"{r['price']:.{decimals}f}" if r["price"] is not None else "—"
        chg_str = f"{sign}{r['chg']:.{decimals}f}"
        pct_str = f"{sign}{r['pct']:.2f}%" if show_pct else ""
        sym = r.get("symbol", "")

        td_base = {"padding": "0.25rem 0.4rem", "fontSize": "0.75rem",
                   "fontFamily": FONT, "borderBottom": f"1px solid {c['border']}"}
        click_style = {**td_base, "color": c["text"], "fontWeight": "600",
                       "whiteSpace": "nowrap", "cursor": "pointer"}
        trs.append(html.Tr([
            html.Td(r["name"], style=click_style,
                    className="clickable-ticker",
                    **{"data-ticker": sym}),
            html.Td(price_str, style={**td_base, "color": c["text"],
                                       "textAlign": "right", "fontFamily": "'Courier New', monospace"}),
            html.Td(chg_str, style={**td_base, "color": col,
                                     "textAlign": "right", "fontFamily": "'Courier New', monospace"}),
            html.Td(pct_str, style={**td_base, "color": col, "fontWeight": "700",
                                     "textAlign": "right", "fontFamily": "'Courier New', monospace"})
            if show_pct else None,
        ]))
    cols = 4 if show_pct else 3
    return html.Table(html.Tbody(trs),
                      style={"width": "100%", "borderCollapse": "collapse"})


def _index_chip(name, price, chg, pct, c, symbol=""):
    """Single index chip for the top strip."""
    col = c["green"] if chg >= 0 else c["red"]
    sign = "▲" if chg >= 0 else "▼"
    ps = f"{price:,.2f}" if price else "—"
    return html.Div([
        html.Span(name, style={"color": c["subtext"], "fontSize": "0.65rem",
                                "fontWeight": "700", "marginRight": "0.4rem",
                                "textTransform": "uppercase", "letterSpacing": "0.04em"}),
        html.Span(ps, style={"color": c["text"], "fontSize": "0.85rem",
                              "fontWeight": "700", "fontFamily": "'Courier New', monospace",
                              "marginRight": "0.35rem"}),
        html.Span(f"{sign} {abs(pct):.2f}%", style={"color": col, "fontSize": "0.75rem",
                                                      "fontWeight": "700"}),
    ], style={"display": "inline-flex", "alignItems": "center",
              "backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
              "borderRadius": "4px", "padding": "0.35rem 0.65rem",
              "whiteSpace": "nowrap", "cursor": "pointer"},
       className="clickable-ticker",
       **{"data-ticker": symbol})


def _render_news_compact(articles, c):
    """Compact news list for dashboard."""
    if not articles:
        return html.Div("No news found.",
                        style={"color": c["muted"], "fontSize": "0.78rem", "fontFamily": FONT})
    items = []
    for a in articles[:15]:
        items.append(
            html.A([
                html.Span(f"[{a['ticker']}] ",
                          style={"color": c["accent"], "fontWeight": "700",
                                 "fontSize": "0.68rem", "fontFamily": FONT}),
                html.Span(a["title"],
                          style={"color": c["text"], "fontSize": "0.76rem", "fontFamily": FONT}),
                html.Span(f"  {a.get('source', '')}",
                          style={"color": c["blue"], "fontSize": "0.6rem",
                                 "marginLeft": "0.3rem", "fontFamily": FONT,
                                 "fontWeight": "600"}),
            ], href=a["link"], target="_blank",
               style={"display": "block", "padding": "0.35rem 0",
                      "borderBottom": f"1px solid {c['border']}",
                      "textDecoration": "none", "lineHeight": "1.45"})
        )
    return html.Div(items)


def register_callbacks(app):

    # ══════════════════════════════════════════════════════════════════════
    # 1) Main dashboard refresh — fires on load + refresh + interval
    # ══════════════════════════════════════════════════════════════════════
    @app.callback(
        Output("index-strip",          "children"),
        Output("fx-table",             "children"),
        Output("bond-table",           "children"),
        Output("commodity-table",      "children"),
        Output("sector-treemap",       "figure"),
        Output("top-gainers-table",    "children"),
        Output("top-losers-table",     "children"),
        Output("last-updated",         "children"),
        Input("refresh-btn",   "n_clicks"),
        Input("auto-refresh",  "n_intervals"),
        Input("theme-store",   "data"),
        State("ticker-input",  "value"),
    )
    def update_dashboard(n_clicks, n_intervals, theme_mode, raw):
        c = get_theme(theme_mode or "dark")
        now = datetime.datetime.now().strftime("%d %b %Y %H:%M")
        tickers = parse_tickers(raw)

        # ── Index strip ──────────────────────────────────────────────────
        idx_data = fetch_index_data()
        idx_chips = [_index_chip(d["name"], d["price"], d["chg"], d["pct"], c,
                                  symbol=d.get("symbol", ""))
                     for d in idx_data]

        # ── Left column tables ───────────────────────────────────────────
        fx_data = fetch_quote_table(FX_PAIRS)
        fx_content = _mini_table(fx_data, c, decimals=4, show_pct=True)

        bond_data = fetch_quote_table(BONDS)
        bond_content = _mini_table(bond_data, c, decimals=3, show_pct=True)

        comm_data = fetch_quote_table(COMMODITIES)
        comm_content = _mini_table(comm_data, c, decimals=2, show_pct=True)

        # ── Sector treemap ───────────────────────────────────────────────
        sector_data = fetch_sector_performance()
        sect_names = [s["name"] for s in sector_data]
        sect_pcts = [s["pct"] for s in sector_data]
        sect_abs = [abs(p) + 0.3 for p in sect_pcts]  # sizing (min size)
        sect_colors = [c["green"] if p >= 0 else c["red"] for p in sect_pcts]
        sect_text = [f"{n}<br>{'+' if p >= 0 else ''}{p:.2f}%"
                     for n, p in zip(sect_names, sect_pcts)]

        tree_fig = go.Figure(go.Treemap(
            labels=sect_names,
            parents=[""] * len(sect_names),
            values=sect_abs,
            text=sect_text,
            textinfo="text",
            marker=dict(colors=sect_colors),
            textfont=dict(family=FONT, size=12),
        ))
        tree_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            font=dict(family=FONT, color=c["text"]),
        )

        # ── Top movers (S&P 500) ──────────────────────────────────────
        gainers_df, losers_df = fetch_sp500_movers(n=10)

        def _build_movers_table(df):
            if df.empty:
                return html.Div("Unable to load data.",
                                style={"color": c["muted"], "fontSize": "0.78rem",
                                       "fontFamily": FONT})
            rows = []
            for _, row in df.iterrows():
                col = c["green"] if row["_chg"] >= 0 else c["red"]
                arrow = "▲" if row["_chg"] >= 0 else "▼"
                td_s = {"padding": "0.22rem 0.35rem", "fontSize": "0.74rem",
                        "fontFamily": FONT,
                        "borderBottom": f"1px solid {c['border']}"}
                rows.append(html.Tr([
                    html.Td(row["Ticker"],
                            style={**td_s, "color": c["accent"], "fontWeight": "700",
                                   "cursor": "pointer"},
                            className="clickable-ticker",
                            **{"data-ticker": row["Ticker"]}),
                    html.Td(row["Price"],
                            style={**td_s, "color": c["text"], "textAlign": "right",
                                   "fontFamily": "'Courier New', monospace"}),
                    html.Td(f"{arrow} {row['Chg %']}",
                            style={**td_s, "color": col, "fontWeight": "700",
                                   "textAlign": "right"}),
                ]))
            return html.Table(html.Tbody(rows),
                              style={"width": "100%", "borderCollapse": "collapse"})

        gainers_content = _build_movers_table(gainers_df)
        losers_content = _build_movers_table(losers_df)

        return (idx_chips, fx_content, bond_content, comm_content,
                tree_fig,
                gainers_content, losers_content, f"Updated {now}")

    # ══════════════════════════════════════════════════════════════════════
    # 2) Main chart — reacts to ticker input + frequency dropdown
    # ══════════════════════════════════════════════════════════════════════
    @app.callback(
        Output("sp500-chart",      "figure"),
        Output("sp500-last-price", "children"),
        Input("chart-ticker-input",  "value"),
        Input("chart-freq-dropdown", "value"),
        Input("theme-store",         "data"),
    )
    def update_main_chart(symbol, freq, theme_mode):
        c = get_theme(theme_mode or "dark")
        symbol = (symbol or "^GSPC").strip().upper()

        freq_map = {
            "intraday": ("5d",  "15m"),
            "daily":    ("6mo", "1d"),
            "weekly":   ("2y",  "1wk"),
            "monthly":  ("5y",  "1mo"),
        }
        period, interval = freq_map.get(freq, ("6mo", "1d"))

        sp_df = fetch_chart_data(symbol=symbol, period=period, interval=interval)
        if not sp_df.empty:
            date_col = next((c for c in sp_df.columns if c in ("Datetime", "Date")), sp_df.columns[0])
            sp_fig = go.Figure(go.Candlestick(
                x=sp_df[date_col], open=sp_df["Open"], high=sp_df["High"],
                low=sp_df["Low"], close=sp_df["Close"],
                increasing_line_color=c["green"], decreasing_line_color=c["red"],
            ))
            last_p = sp_df["Close"].iloc[-1]
            sp_price_text = f"{symbol}  {last_p:,.2f}"
        else:
            sp_fig = go.Figure()
            sp_price_text = f"{symbol}  —"

        sp_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showgrid=False, color=c["subtext"], rangeslider_visible=False),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["subtext"]),
            font=dict(family=FONT, size=10, color=c["subtext"]),
            showlegend=False,
        )
        return sp_fig, sp_price_text

    # ══════════════════════════════════════════════════════════════════════

    # 3) News page callbacks (kept for the dedicated News page)
    # ══════════════════════════════════════════════════════════════════════
    @app.callback(
        Output("news-feed",  "children"),
        Output("news-cache", "data"),
        Output("load-news-btn", "children"),
        Input("load-news-btn", "n_clicks"),
        State("theme-store",  "data"),
        State("ticker-input", "value"),
        prevent_initial_call=True,
    )
    def load_news_page(n, theme_mode, raw):
        c = get_theme(theme_mode or "dark")
        tickers = parse_tickers(raw)
        if not tickers:
            return (html.Div("Enter tickers above to load news.",
                             style={"color": c["muted"], "fontSize": "0.82rem",
                                    "fontFamily": FONT}),
                    None, "Load News")
        news_data = fetch_news(tickers)
        arts = news_data.get("all", [])
        if arts:
            news_content = _render_news_full(arts, c)
        else:
            news_content = html.Div("No news found.",
                                    style={"color": c["muted"], "fontSize": "0.82rem",
                                           "fontFamily": FONT})
        return news_content, news_data, "Load News"

    @app.callback(
        Output("news-feed",           "children", allow_duplicate=True),
        Output("news-filter-all",     "style"),
        Output("news-filter-stock",   "style"),
        Output("news-filter-general", "style"),
        Input("news-filter-all",     "n_clicks"),
        Input("news-filter-stock",   "n_clicks"),
        Input("news-filter-general", "n_clicks"),
        State("news-cache",  "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def filter_news(n_all, n_stock, n_general, cache, theme_mode):
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        if not ctx.triggered or not cache:
            return no_update, no_update, no_update, no_update

        btn = ctx.triggered[0]["prop_id"].split(".")[0]
        key_map = {
            "news-filter-all":     "all",
            "news-filter-stock":   "stock",
            "news-filter-general": "general",
        }
        key = key_map.get(btn, "all")
        arts = cache.get(key, [])

        active_s = {
            "backgroundColor": c["accent"], "color": "#000", "border": "none",
            "borderRadius": "8px", "padding": "0.4rem 1rem",
            "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.78rem",
            "cursor": "pointer"}
        inactive_s = {
            "backgroundColor": "transparent", "color": c["subtext"],
            "border": f"1px solid {c['border']}",
            "borderRadius": "8px", "padding": "0.4rem 1rem",
            "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.78rem",
            "cursor": "pointer"}

        styles = {
            "news-filter-all":     active_s if key == "all" else inactive_s,
            "news-filter-stock":   active_s if key == "stock" else inactive_s,
            "news-filter-general": active_s if key == "general" else inactive_s,
        }

        return (_render_news_full(arts, c),
                styles["news-filter-all"],
                styles["news-filter-stock"],
                styles["news-filter-general"])


def _render_news_full(articles, c):
    """Full news renderer for the dedicated News page."""
    if not articles:
        return html.Div("No news found.",
                        style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})
    return html.Div([
        html.A([
            html.Span(f"[{a['ticker']}] ",
                      style={"color": c["accent"], "fontWeight": "700",
                             "fontSize": "0.72rem", "fontFamily": FONT}),
            html.Span(a["title"],
                      style={"color": c["text"], "fontSize": "0.82rem", "fontFamily": FONT}),
            html.Span(f"  {a.get('source', '')}",
                      style={"color": c["blue"], "fontSize": "0.65rem",
                             "marginLeft": "0.4rem", "fontFamily": FONT,
                             "fontWeight": "600"}),
            html.Span(f"  {a['published'][:16]}",
                      style={"color": c["muted"], "fontSize": "0.68rem",
                             "marginLeft": "0.3rem", "fontFamily": FONT}),
        ], href=a["link"], target="_blank",
           style={"display": "block", "padding": "0.55rem 0",
                  "borderBottom": f"1px solid {c['border']}",
                  "textDecoration": "none", "lineHeight": "1.5"})
        for a in articles
    ])
