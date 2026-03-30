"""Callback — main dashboard: index cards, earnings, portfolio, news."""

import datetime
import dash

from dash import html, dcc, Input, Output, State, no_update

from theme import C, FONT, get_theme, SCREENER_UNIVERSE
from data import (
    parse_tickers, fetch_index_data, index_card,
    fetch_earnings, fetch_prices, fetch_news,
)


def _render_news(articles, c):
    """Turn a list of article dicts into Dash HTML."""
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


def register_callbacks(app):

    # ── 1) Fast dashboard: indices + portfolio (no earnings, no news) ─────
    @app.callback(
        Output("index-cards",     "children"),
        Output("portfolio-table", "children"),
        Output("last-updated",    "children"),
        Input("refresh-btn",   "n_clicks"),
        Input("auto-refresh",  "n_intervals"),
        Input("theme-store",   "data"),
        State("ticker-input",  "value"),
    )
    def update_dashboard(n_clicks, n_intervals, theme_mode, raw):
        c       = get_theme(theme_mode or "dark")
        now     = datetime.datetime.now().strftime("%d %b %Y %H:%M")
        tickers = parse_tickers(raw)

        idx_cards = [index_card(d["name"], d["price"], d["chg"], d["pct"], c)
                     for d in fetch_index_data()]

        # ── Portfolio ─────────────────────────────────────────────────────
        if tickers:
            pdf = fetch_prices(tickers)
            port_rows = []
            for _, row in pdf.iterrows():
                col = c["green"] if row["_chg"] >= 0 else c["red"]
                port_rows.append(html.Tr([
                    html.Td(row["Ticker"],
                            style={"color": c["accent"], "fontWeight": "700",
                                   "padding": "0.45rem 0.75rem",
                                   "borderBottom": f"1px solid {c['border']}",
                                   "fontFamily": FONT, "fontSize": "0.83rem"}),
                    html.Td(row["Price"],
                            style={"color": c["text"], "padding": "0.45rem 0.75rem",
                                   "borderBottom": f"1px solid {c['border']}",
                                   "textAlign": "right", "fontFamily": FONT, "fontSize": "0.83rem"}),
                    html.Td(row["Change"],
                            style={"color": col, "padding": "0.45rem 0.75rem",
                                   "borderBottom": f"1px solid {c['border']}",
                                   "textAlign": "right", "fontFamily": FONT, "fontSize": "0.83rem"}),
                    html.Td(row["Chg %"],
                            style={"color": col, "fontWeight": "700",
                                   "padding": "0.45rem 0.75rem",
                                   "borderBottom": f"1px solid {c['border']}",
                                   "textAlign": "right", "fontFamily": FONT, "fontSize": "0.83rem"}),
                    html.Td(row["Mkt Cap"],
                            style={"color": c["subtext"], "padding": "0.45rem 0.75rem",
                                   "borderBottom": f"1px solid {c['border']}",
                                   "textAlign": "right", "fontFamily": FONT, "fontSize": "0.78rem"}),
                ]))
            port_content = html.Table([
                html.Thead(html.Tr([
                    html.Th(h, style={"color": c["muted"], "padding": "0.35rem 0.75rem",
                                       "fontSize": "0.62rem", "textTransform": "uppercase",
                                       "letterSpacing": "0.07em", "fontWeight": "700",
                                       "borderBottom": f"2px solid {c['border']}",
                                       "fontFamily": FONT,
                                       "textAlign": "right" if i > 0 else "left"})
                    for i, h in enumerate(["Ticker", "Price", "Change", "Chg %", "Mkt Cap"])
                ])),
                html.Tbody(port_rows),
            ], style={"width": "100%", "borderCollapse": "collapse"})
        else:
            port_content = html.Div("No tickers entered yet.",
                                    style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})

        return idx_cards, port_content, f"Updated {now}"

    # ── 2) Earnings — triggered only by "Load Earnings" button ────────────
    @app.callback(
        Output("earnings-table",  "children"),
        Output("earnings-legend", "children"),
        Output("load-earnings-btn", "children"),
        Input("load-earnings-btn", "n_clicks"),
        State("theme-store",  "data"),
        State("ticker-input", "value"),
        prevent_initial_call=True,
    )
    def load_earnings(n, theme_mode, raw):
        c       = get_theme(theme_mode or "dark")
        tickers = parse_tickers(raw)
        edf = fetch_earnings(SCREENER_UNIVERSE)
        if edf.empty:
            earn_content = html.Div("No upcoming earnings within 30 days.",
                                    style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})
            legend = html.Div()
        else:
            rows = []
            for _, row in edf.iterrows():
                days = row["Days Away"]
                urg  = c["red"] if days <= 7 else (c["accent"] if days <= 14 else c["green"])
                mine = row["Ticker"] in tickers

                est_eps  = f"{row['Est EPS']:.2f}" if row.get("Est EPS") is not None else "—"
                last_eps = f"{row['Last EPS']:.2f}" if row.get("Last EPS") is not None else "—"
                sector   = row.get("Sector", "—") or "—"

                td = {"padding": "0.45rem 0.75rem",
                      "borderBottom": f"1px solid {c['border']}",
                      "fontSize": "0.8rem", "fontFamily": FONT}

                rows.append(html.Tr([
                    html.Td([row["Ticker"],
                             html.Span(" ★", style={"color": c["accent"]}) if mine else None],
                            style={**td, "color": c["accent"] if mine else c["text"],
                                   "fontWeight": "700" if mine else "500",
                                   "fontSize": "0.83rem"}),
                    html.Td(sector, style={**td, "color": c["subtext"]}),
                    html.Td(row["Earnings Date"], style={**td, "color": c["subtext"]}),
                    html.Td(f"{days}d",
                            style={**td, "color": urg, "fontWeight": "700",
                                   "textAlign": "right"}),
                    html.Td(est_eps, style={**td, "color": c["blue"], "textAlign": "right"}),
                    html.Td(last_eps, style={**td, "color": c["text"], "textAlign": "right"}),
                ], style={"backgroundColor": "rgba(240,180,41,0.06)" if mine else "transparent"}))

            th_s = {"color": c["muted"], "padding": "0.35rem 0.75rem",
                    "fontSize": "0.62rem", "textTransform": "uppercase",
                    "letterSpacing": "0.07em", "fontWeight": "700",
                    "borderBottom": f"2px solid {c['border']}",
                    "fontFamily": FONT}

            earn_content = html.Table([
                html.Thead(html.Tr([
                    html.Th("Ticker",    style={**th_s, "textAlign": "left"}),
                    html.Th("Sector",    style={**th_s, "textAlign": "left"}),
                    html.Th("Date",      style={**th_s, "textAlign": "left"}),
                    html.Th("Days",      style={**th_s, "textAlign": "right"}),
                    html.Th("Est EPS",   style={**th_s, "textAlign": "right"}),
                    html.Th("Last EPS",  style={**th_s, "textAlign": "right"}),
                ])),
                html.Tbody(rows),
            ], style={"width": "100%", "borderCollapse": "collapse"})

            legend = html.Div([
                html.Span("★ ", style={"color": c["accent"]}),
                html.Span("you own  ", style={"color": c["subtext"], "fontSize": "0.7rem", "fontFamily": FONT}),
                html.Span("■ ", style={"color": c["red"]}),
                html.Span("≤7d  ",    style={"color": c["subtext"], "fontSize": "0.7rem", "fontFamily": FONT}),
                html.Span("■ ", style={"color": c["accent"]}),
                html.Span("≤14d  ",   style={"color": c["subtext"], "fontSize": "0.7rem", "fontFamily": FONT}),
                html.Span("■ ", style={"color": c["green"]}),
                html.Span(">14d",     style={"color": c["subtext"], "fontSize": "0.7rem", "fontFamily": FONT}),
            ])

        return earn_content, legend, "Load Earnings"

    # ── 3) News — triggered only by "Load News" button ────────────────────
    @app.callback(
        Output("news-feed",  "children"),
        Output("news-cache", "data"),
        Output("load-news-btn", "children"),
        Input("load-news-btn", "n_clicks"),
        State("theme-store",  "data"),
        State("ticker-input", "value"),
        prevent_initial_call=True,
    )
    def load_news(n, theme_mode, raw):
        c       = get_theme(theme_mode or "dark")
        tickers = parse_tickers(raw)

        if not tickers:
            return (html.Div("Enter tickers above to load news.",
                             style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT}),
                    None, "Load News")

        news_data = fetch_news(tickers)
        arts = news_data.get("all", [])
        if arts:
            news_content = _render_news(arts, c)
        else:
            news_content = html.Div("No news found.",
                                    style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})

        return news_content, news_data, "Load News"

    # ── News filter toggle (All / Stock / General) ────────────────────────
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

        # Button styles
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

        return (_render_news(arts, c),
                styles["news-filter-all"],
                styles["news-filter-stock"],
                styles["news-filter-general"])
