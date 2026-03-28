"""Callback — main dashboard: index cards, earnings, portfolio, news."""

import datetime

from dash import html, Input, Output, State

from theme import C, FONT, get_theme
from data import (
    parse_tickers, fetch_index_data, index_card,
    fetch_earnings, fetch_prices, fetch_news,
)


def register_callbacks(app):

    @app.callback(
        Output("index-cards",     "children"),
        Output("earnings-table",  "children"),
        Output("earnings-legend", "children"),
        Output("portfolio-table", "children"),
        Output("news-feed",       "children"),
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

        # ── Earnings ──────────────────────────────────────────────────────
        if tickers:
            edf = fetch_earnings(tickers)
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
                    rows.append(html.Tr([
                        html.Td([row["Ticker"],
                                 html.Span(" ★", style={"color": c["accent"]}) if mine else None],
                                style={"color": c["accent"] if mine else c["text"],
                                       "fontWeight": "700" if mine else "500",
                                       "padding": "0.45rem 0.75rem",
                                       "borderBottom": f"1px solid {c['border']}",
                                       "fontFamily": FONT, "fontSize": "0.83rem"}),
                        html.Td(row["Earnings Date"],
                                style={"color": c["subtext"], "padding": "0.45rem 0.75rem",
                                       "borderBottom": f"1px solid {c['border']}",
                                       "fontSize": "0.8rem", "fontFamily": FONT}),
                        html.Td(f"{days}d",
                                style={"color": urg, "fontWeight": "700",
                                       "padding": "0.45rem 0.75rem",
                                       "borderBottom": f"1px solid {c['border']}",
                                       "textAlign": "right", "fontFamily": FONT, "fontSize": "0.8rem"}),
                    ], style={"backgroundColor": "rgba(240,180,41,0.06)" if mine else "transparent"}))

                earn_content = html.Table([
                    html.Thead(html.Tr([
                        html.Th(h, style={"color": c["muted"], "padding": "0.35rem 0.75rem",
                                           "fontSize": "0.62rem", "textTransform": "uppercase",
                                           "letterSpacing": "0.07em", "fontWeight": "700",
                                           "borderBottom": f"2px solid {c['border']}",
                                           "fontFamily": FONT,
                                           "textAlign": "right" if h == "Days" else "left"})
                        for h in ["Ticker", "Date", "Days"]
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
        else:
            earn_content = html.Div("Enter your tickers above and click Refresh.",
                                    style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})
            legend = html.Div()

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

        # ── News ──────────────────────────────────────────────────────────
        if tickers:
            arts = fetch_news(tickers)
            if arts:
                news_content = html.Div([
                    html.A([
                        html.Span(f"[{a['ticker']}] ",
                                  style={"color": c["accent"], "fontWeight": "700",
                                         "fontSize": "0.72rem", "fontFamily": FONT}),
                        html.Span(a["title"],
                                  style={"color": c["text"], "fontSize": "0.82rem", "fontFamily": FONT}),
                        html.Span(f"  {a['published'][:16]}",
                                  style={"color": c["muted"], "fontSize": "0.68rem",
                                         "marginLeft": "0.5rem", "fontFamily": FONT}),
                    ], href=a["link"], target="_blank",
                       style={"display": "block", "padding": "0.55rem 0",
                              "borderBottom": f"1px solid {c['border']}",
                              "textDecoration": "none", "lineHeight": "1.5"})
                    for a in arts
                ])
            else:
                news_content = html.Div("No news found.",
                                        style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})
        else:
            news_content = html.Div("Enter tickers above to load news.",
                                    style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})

        return idx_cards, earn_content, legend, port_content, news_content, f"Updated {now}"
