from dash import dcc, html, dash_table


def build_snowflake_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Snowflake Data", style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),
            html.Div("Price data powered by FactSet via Snowflake (replaces yfinance).",
                     style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                            "fontFamily": FONT},
                     className="theme-muted"),

            # ── Ticker + period controls ─────────────────────────────────
            html.Div([
                html.Div([
                    html.Div("Tickers", style={**LBL, "marginBottom": "0.2rem"}, className="theme-label"),
                    dcc.Input(id="sf-tickers", type="text",
                              placeholder="e.g. AAPL, MSFT, COST",
                              debounce=True, className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "6px", "color": C["text"],
                                     "padding": "0.4rem 0.6rem", "fontFamily": FONT,
                                     "fontSize": "0.78rem", "width": "100%", "outline": "none"}),
                ], style={"flex": "2"}),
                html.Div([
                    html.Div("Period", style={**LBL, "marginBottom": "0.2rem"}, className="theme-label"),
                    dcc.Dropdown(
                        id="sf-period",
                        options=[
                            {"label": "1 Month",  "value": "1mo"},
                            {"label": "3 Months", "value": "3mo"},
                            {"label": "6 Months", "value": "6mo"},
                            {"label": "1 Year",   "value": "1y"},
                            {"label": "2 Years",  "value": "2y"},
                            {"label": "5 Years",  "value": "5y"},
                        ],
                        value="1y",
                        clearable=False,
                        className="theme-dropdown",
                        style={"fontSize": "0.78rem"},
                    ),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Display", style={**LBL, "marginBottom": "0.2rem"}, className="theme-label"),
                    dcc.Dropdown(
                        id="sf-display",
                        options=[
                            {"label": "Raw Prices", "value": "raw"},
                            {"label": "Rebased (100)", "value": "rebased"},
                        ],
                        value="raw",
                        clearable=False,
                        className="theme-dropdown",
                        style={"fontSize": "0.78rem"},
                    ),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "1rem", "marginBottom": "0.6rem",
                      "alignItems": "flex-end"}),

            html.Div([
                html.Button("Load", id="sf-load-btn", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.2rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                    "cursor": "pointer",
                }),
                html.Div(id="sf-status", style={"color": C["muted"], "fontSize": "0.75rem",
                                                  "fontFamily": FONT,
                                                  "marginLeft": "1rem"},
                         className="theme-muted"),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "0.8rem"}),

            # ── Chart ────────────────────────────────────────────────────
            dcc.Graph(id="sf-chart",
                      config={"displayModeBar": True, "scrollZoom": True},
                      style={"height": "420px"}),

            # ── Recent prices table ──────────────────────────────────────
            html.Div(id="sf-table-container", style={"marginTop": "1rem"}),

        ], style={**PANEL, "padding": "1.2rem 1.5rem", "marginTop": "0.8rem"}),
    ], id="section-snowflake", style={"display": "none"})
