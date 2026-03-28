"""Callbacks - Stock Analyser: load stock, tab/period switching, render content."""

import dash
import yfinance as yf
from dash import dcc, html, Input, Output, State

from theme import FONT, LBL, get_theme, _nav_btn, _nav_btn_active, PERIODS
from data import build_price_chart, build_valuation_table, build_financials


def register_callbacks(app):

    # -- Load stock header --
    @app.callback(
        Output("active-ticker", "data"),
        Output("stock-header",  "children"),
        Output("tab-nav",       "style"),
        Input("lookup-btn",   "n_clicks"),
        State("lookup-input", "value"),
        State("theme-store",  "data"),
        prevent_initial_call=True,
    )
    def load_stock(n, raw, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not raw:
            return "", html.Div(), {"display": "none"}
        ticker = raw.strip().upper()
        try:
            info     = yf.Ticker(ticker).info
            name     = info.get("longName") or info.get("shortName") or ticker
            price    = info.get("currentPrice") or info.get("regularMarketPrice")
            prev     = info.get("previousClose")
            chg      = round(price - prev, 2) if price and prev else 0
            pct      = round((chg / prev) * 100, 2) if prev else 0
            col      = c["green"] if chg >= 0 else c["red"]
            sign     = "^" if chg >= 0 else "v"
            sector   = info.get("sector", "")
            industry = info.get("industry", "")

            header = html.Div([
                html.Div([
                    html.Span(name,
                              style={"fontFamily": FONT, "fontWeight": "800",
                                     "fontSize": "1.3rem", "color": c["text"]}),
                    html.Span(f"  {ticker}",
                              style={"color": c["subtext"], "fontSize": "0.85rem",
                                     "fontFamily": FONT, "marginLeft": "0.4rem"}),
                ]),
                html.Div([
                    html.Span(f"${price:,.2f}" if price else "\u2014",
                              style={"fontSize": "1.55rem", "fontWeight": "700",
                                     "color": c["text"], "fontFamily": FONT}),
                    html.Span(f"  {sign} {abs(chg):.2f} ({abs(pct):.2f}%)",
                              style={"color": col, "fontSize": "0.88rem",
                                     "fontFamily": FONT, "marginLeft": "0.5rem",
                                     "fontWeight": "600"}),
                ], style={"marginTop": "0.2rem"}),
                html.Div(f"{sector}  \u00b7  {industry}",
                         style={"color": c["muted"], "fontSize": "0.72rem",
                                "fontFamily": FONT, "marginTop": "0.2rem"}),
            ], style={"marginBottom": "1rem", "paddingBottom": "0.75rem",
                      "borderBottom": f"1px solid {c['border']}"})

        except Exception:
            header = html.Div(f"Could not find ticker: {ticker}",
                              style={"color": c["red"], "fontFamily": FONT, "fontSize": "0.85rem"})

        nav_style = {"display": "flex", "gap": "0.5rem", "flexWrap": "wrap", "marginBottom": "1rem"}
        return ticker, header, nav_style

    # -- Tab switching --
    @app.callback(
        Output("tab-chart",     "style"),
        Output("tab-valuation", "style"),
        Output("tab-income",    "style"),
        Output("tab-balance",   "style"),
        Output("tab-cashflow",  "style"),
        Output("active-tab",    "data"),
        Output("period-nav",    "style"),
        Input("tab-chart",     "n_clicks"),
        Input("tab-valuation", "n_clicks"),
        Input("tab-income",    "n_clicks"),
        Input("tab-balance",   "n_clicks"),
        Input("tab-cashflow",  "n_clicks"),
        Input("theme-store",   "data"),
        State("active-tab",    "data"),
    )
    def switch_tab(c1, c2, c3, c4, c5, theme_mode, current):
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        if not ctx.triggered or not any([c1, c2, c3, c4, c5]):
            active = current or "chart"
        else:
            prop = ctx.triggered[0]["prop_id"].split(".")[0]
            if prop.startswith("tab-"):
                active = prop.replace("tab-", "")
            else:
                active = current or "chart"

        tabs   = ["chart", "valuation", "income", "balance", "cashflow"]
        btn    = _nav_btn(c)
        btn_a  = _nav_btn_active(c)
        styles = [btn_a if t == active else btn for t in tabs]
        period_vis = ({"display": "flex", "gap": "0.4rem", "alignItems": "center",
                       "marginBottom": "0.75rem", "flexWrap": "wrap"}
                      if active == "chart" else {"display": "none"})
        return *styles, active, period_vis

    # -- Period switching --
    @app.callback(
        *[Output(f"period-{p}", "style") for p in PERIODS],
        Output("active-period", "data"),
        *[Input(f"period-{p}",  "n_clicks") for p in PERIODS],
        Input("theme-store", "data"),
        State("active-period",  "data"),
    )
    def switch_period(*args):
        clicks     = args[:len(PERIODS)]
        theme_mode = args[len(PERIODS)]
        current    = args[len(PERIODS) + 1]
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        if not ctx.triggered or not any(clicks):
            active = current or "6mo"
        else:
            prop = ctx.triggered[0]["prop_id"].split(".")[0]
            if prop.startswith("period-"):
                active = prop.replace("period-", "")
            else:
                active = current or "6mo"

        btn = _nav_btn(c)
        styles = [{**btn, "padding": "0.3rem 0.7rem", "fontSize": "0.75rem",
                   **({"backgroundColor": c["accent"], "color": "#000",
                       "border": f"1px solid {c['accent']}"} if p == active else {})}
                  for p in PERIODS]
        return *styles, active

    # -- Render stock content --
    @app.callback(
        Output("stock-content", "children"),
        Input("active-tab",    "data"),
        Input("active-period", "data"),
        Input("active-ticker", "data"),
        Input("theme-store",   "data"),
    )
    def render_content(tab, period, ticker, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not ticker:
            return html.Div("Search for a stock above to get started.",
                            style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})

        if tab == "chart":
            fig = build_price_chart(ticker, period, c=c)
            return dcc.Graph(figure=fig, config={"displayModeBar": False},
                             style={"height": "380px"})
        elif tab == "valuation":
            return html.Div([html.Div("Valuation & Key Metrics", style=LBL),
                             build_valuation_table(ticker, c=c)])
        elif tab == "income":
            return build_financials(ticker, "income", c=c)
        elif tab == "balance":
            return build_financials(ticker, "balance", c=c)
        elif tab == "cashflow":
            return build_financials(ticker, "cashflow", c=c)
        return html.Div()