"""Callback — Bloomberg-style dashboard home page."""

import datetime

import dash
import numpy as np
import plotly.graph_objects as go

from dash import html, dcc, Input, Output, State, no_update

from theme import (
    C, FONT, get_theme,
    INDICES, FX_PAIRS, BONDS, COMMODITIES, SECTOR_ETFS,
    FTSE100_TICKERS, EUROSTOXX50_TICKERS, SP500_TICKERS,
)
from data import (
    parse_tickers,
    fetch_news,
)
from snowflake_data import (
    fetch_quote_table_sf, fetch_fx_rates, fetch_movers_sf,
    fetch_sector_stocks_1d, SECTOR_CODE_MAP,
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
    _sector_drilldown_callbacks(app)

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
        Output("ftse-gainers-table",   "children"),
        Output("ftse-losers-table",    "children"),
        Output("euro-gainers-table",   "children"),
        Output("euro-losers-table",    "children"),
        Output("last-updated",         "children"),
        Input("refresh-btn",   "n_clicks"),
        Input("auto-refresh",  "n_intervals"),
        Input("theme-store",   "data"),
        State("ticker-input",  "value"),
        State("datasource",    "data"),
    )
    def update_dashboard(n_clicks, n_intervals, theme_mode, raw, datasource):
        c = get_theme(theme_mode or "dark")
        now = datetime.datetime.now().strftime("%d %b %Y %H:%M")
        tickers = parse_tickers(raw)

        if datasource == "yf":
            offline = html.Div("⚠️ Offline — Snowflake not available",
                               style={"color": "#ff8c00", "fontSize": "0.78rem",
                                      "fontFamily": FONT, "padding": "0.5rem"})
            return (offline,) * 11 + (f"Offline · {now}",)

        # ── Fire data fetches sequentially (Snowflake connector is not thread-safe) ─
        try:
            idx_data  = fetch_quote_table_sf(INDICES)
        except Exception:
            idx_data  = []
        try:
            fx_data   = fetch_fx_rates()
        except Exception:
            fx_data   = []
        try:
            bond_data = fetch_quote_table_sf(BONDS)
        except Exception:
            bond_data = []
        try:
            comm_data = fetch_quote_table_sf(COMMODITIES)
        except Exception:
            comm_data = []
        try:
            sector_data = fetch_quote_table_sf(SECTOR_ETFS)
        except Exception:
            sector_data = []
        try:
            gainers_df, losers_df = fetch_movers_sf(SP500_TICKERS, 10, "$")
        except Exception:
            import pandas as _pd
            gainers_df = losers_df = _pd.DataFrame()
        try:
            ftse_g, ftse_l = fetch_movers_sf(FTSE100_TICKERS, 10, "\u00a3")
        except Exception:
            import pandas as _pd
            ftse_g = ftse_l = _pd.DataFrame()
        try:
            euro_g, euro_l = fetch_movers_sf(EUROSTOXX50_TICKERS, 10, "\u20ac")
        except Exception:
            import pandas as _pd
            euro_g = euro_l = _pd.DataFrame()

        # ── Index strip ──────────────────────────────────────────────────
        idx_chips = [_index_chip(d["name"], d["price"], d["chg"], d["pct"], c,
                                  symbol=d.get("symbol", ""))
                     for d in idx_data]

        # ── Left column tables ───────────────────────────────────────────
        fx_content = _mini_table(fx_data, c, decimals=4, show_pct=True)

        bond_content = _mini_table(bond_data, c, decimals=3, show_pct=True)

        comm_content = _mini_table(comm_data, c, decimals=2, show_pct=True)

        # ── Sector treemap ───────────────────────────────────────────────
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
        ftse_g_content = _build_movers_table(ftse_g)
        ftse_l_content = _build_movers_table(ftse_l)
        euro_g_content = _build_movers_table(euro_g)
        euro_l_content = _build_movers_table(euro_l)

        return (idx_chips, fx_content, bond_content, comm_content,
                tree_fig,
                gainers_content, losers_content,
                ftse_g_content, ftse_l_content,
                euro_g_content, euro_l_content,
                f"Updated {now}")

    # ══════════════════════════════════════════════════════════════════════
    # 2a) Preset period buttons → set start / end date inputs
    # ══════════════════════════════════════════════════════════════════════
    @app.callback(
        Output("dash-chart-start", "value", allow_duplicate=True),
        Output("dash-chart-end",   "value", allow_duplicate=True),
        [Input(f"dash-preset-{p}", "n_clicks")
         for p in ["1d", "5d", "1m", "3m", "ytd", "1y", "5y", "max"]],
        prevent_initial_call=True,
    )
    def set_dash_chart_dates(*clicks):
        import datetime as _dt
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update
        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
        preset = btn_id.replace("dash-preset-", "").upper()
        today = _dt.date.today()
        end = today.strftime("%Y-%m-%d")
        mapping = {
            "1D": 1, "5D": 5, "1M": 30, "3M": 90,
            "YTD": None, "1Y": 365, "5Y": 1825, "MAX": 9999,
        }
        if preset == "YTD":
            start = _dt.date(today.year, 1, 1).strftime("%Y-%m-%d")
        else:
            days = mapping.get(preset, 365)
            start = (today - _dt.timedelta(days=days)).strftime("%Y-%m-%d")
        return start, end

    # ══════════════════════════════════════════════════════════════════════
    # 2b) Auto-set default dates when ticker changes (1Y)
    # ══════════════════════════════════════════════════════════════════════
    @app.callback(
        Output("dash-chart-start", "value"),
        Output("dash-chart-end",   "value"),
        Input("chart-ticker-input", "value"),
    )
    def reset_dash_dates_on_ticker(symbol):
        import datetime as _dt
        today = _dt.date.today()
        return (today - _dt.timedelta(days=365)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    # ══════════════════════════════════════════════════════════════════════
    # 2c) Main chart — reacts to date inputs (Bloomberg style)
    # ══════════════════════════════════════════════════════════════════════
    @app.callback(
        Output("sp500-chart",      "figure"),
        Output("sp500-last-price", "children"),
        Input("dash-chart-start",  "value"),
        Input("dash-chart-end",    "value"),
        State("chart-ticker-input", "value"),
        State("theme-store",        "data"),
        prevent_initial_call=True,
    )
    def update_main_chart(start_str, end_str, symbol, theme_mode):
        from snowflake_data import download_ohlcv
        import pandas as _pd
        c = get_theme(theme_mode or "dark")
        symbol = (symbol or "SPY").strip().upper()

        try:
            ohlcv = download_ohlcv(symbol, start=start_str, end=end_str)
        except Exception:
            ohlcv = _pd.DataFrame()

        bbg_grid = "rgba(60,65,75,0.4)"
        bbg_text = "#8a8e96"
        bbg_font = dict(family="Consolas, 'Courier New', monospace", size=10, color=bbg_text)

        if not ohlcv.empty:
            last_p = ohlcv["Close"].iloc[-1]
            first_p = ohlcv["Close"].iloc[0]
            ymin, ymax = ohlcv["Close"].min(), ohlcv["Close"].max()
            pad = (ymax - ymin) * 0.05

            sp_fig = go.Figure()
            sp_fig.add_trace(go.Scatter(
                x=ohlcv.index, y=ohlcv["Close"], mode="lines",
                line=dict(color="#1a6dcc", width=1.5),
                fill="tozeroy", fillcolor="rgba(58,130,220,0.12)",
                hovertemplate="%{y:,.2f}<extra></extra>",
                showlegend=False,
            ))
            sp_price_text = f"{symbol}  {last_p:,.2f}"
        else:
            sp_fig = go.Figure()
            ymin, ymax, pad = 0, 1, 0
            sp_price_text = f"{symbol}  —"

        sp_fig.update_layout(
            paper_bgcolor="#000000", plot_bgcolor="#0a0a0f", font=bbg_font,
            margin=dict(l=5, r=55, t=8, b=25), showlegend=False,
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#1a1d24", font_size=10,
                            font_family="Consolas, monospace",
                            font_color="#d0d4db", bordercolor="#333"),
            xaxis=dict(showgrid=True, gridcolor=bbg_grid, griddash="dot",
                       gridwidth=0.5, tickfont=bbg_font, color=bbg_text,
                       showline=False),
            yaxis=dict(showgrid=True, gridcolor=bbg_grid, griddash="dot",
                       gridwidth=0.5, side="right", tickprefix="$",
                       tickfont=bbg_font,
                       range=[ymin - pad, ymax + pad] if not ohlcv.empty else None,
                       zeroline=False, showline=False),
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

def _sector_drilldown_callbacks(app):
    """Callbacks for the sector drill-down heatmap."""

    @app.callback(
        Output("sector-drilldown-panel", "style"),
        Output("sector-drilldown-title", "children"),
        Output("sector-drilldown-chart", "figure"),
        Output("sector-drilldown-status", "children"),
        Input("sector-treemap", "clickData"),
        Input("sector-drilldown-close", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def on_sector_click(click_data, close_clicks, theme_mode):
        from theme import get_theme, FONT
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        trig = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""

        # Close button
        if trig == "sector-drilldown-close":
            return {"display": "none"}, "", go.Figure(), ""

        if not click_data:
            return {"display": "none"}, "", go.Figure(), ""

        sector_name = click_data["points"][0].get("label", "")
        if sector_name not in SECTOR_CODE_MAP:
            return {"display": "none"}, "", go.Figure(), ""

        # Fetch stocks
        try:
            stocks = fetch_sector_stocks_1d(sector_name, region="US", limit=80)
        except Exception as e:
            panel_style = {"backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
                           "borderRadius": "6px", "padding": "0.7rem 0.9rem",
                           "marginBottom": "0.6rem", "display": "block"}
            return panel_style, sector_name, go.Figure(), f"Error: {e}"

        if not stocks:
            panel_style = {"backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
                           "borderRadius": "6px", "padding": "0.7rem 0.9rem",
                           "marginBottom": "0.6rem", "display": "block"}
            return panel_style, sector_name, go.Figure(), "No data found for this sector."

        tickers  = [s["ticker"] for s in stocks]
        names    = [s["name"] for s in stocks]
        pcts     = [s["pct_chg"] for s in stocks]
        prices   = [s["price"] for s in stocks]

        # Colour: green for positive, red for negative, intensity by magnitude
        max_abs  = max(abs(p) for p in pcts) or 1
        colors   = []
        for p in pcts:
            intensity = min(abs(p) / max_abs, 1.0)
            if p >= 0:
                r = int(0 + intensity * 50)
                g = int(150 + intensity * 60)
                b = int(0 + intensity * 30)
            else:
                r = int(180 + intensity * 55)
                g = int(0)
                b = int(0)
            colors.append(f"rgb({r},{g},{b})")

        text_labels = [
            f"{t}<br>{'+' if p >= 0 else ''}{p:.2f}%"
            for t, p in zip(tickers, pcts)
        ]
        hover_text = [
            f"<b>{t}</b><br>{n}<br>Price: {price:,.2f}<br>1D: {'+' if p >= 0 else ''}{p:.2f}%"
            for t, n, p, price in zip(tickers, names, pcts, prices)
        ]

        # Size by absolute % change (min size so tiny movers are still visible)
        sizes = [abs(p) + 0.5 for p in pcts]

        fig = go.Figure(go.Treemap(
            labels=tickers,
            parents=[""] * len(tickers),
            values=sizes,
            text=text_labels,
            textinfo="text",
            hovertext=hover_text,
            hoverinfo="text",
            marker=dict(colors=colors),
            textfont=dict(family=FONT, size=11),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            font=dict(family=FONT, color=c["text"]),
        )

        pos = sum(1 for p in pcts if p > 0)
        neg = sum(1 for p in pcts if p < 0)
        avg = sum(pcts) / len(pcts) if pcts else 0
        status = (f"{len(stocks)} stocks  •  "
                  f"{pos} ▲  {neg} ▼  •  "
                  f"Avg 1D: {'+' if avg >= 0 else ''}{avg:.2f}%")

        panel_style = {"backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
                       "borderRadius": "6px", "padding": "0.7rem 0.9rem",
                       "marginBottom": "0.6rem", "display": "block"}
        title = f"{sector_name} — Stock Heatmap (1D)"
        return panel_style, title, fig, status