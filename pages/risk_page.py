"""Layout — Risk Contribution page: component contribution to tracking error."""

from dash import dcc, html


def build_risk_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Risk Contribution",
                     style={**LBL, "color": C["red"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),
            html.Div("Decompose portfolio tracking error into per-stock contributions.",
                     style={"color": C["muted"], "fontSize": "0.78rem",
                            "marginBottom": "0.8rem", "fontFamily": FONT},
                     className="theme-muted"),

            # ── Inputs ────────────────────────────────────────────────────
            html.Div([
                html.Div([
                    html.Div("Portfolio Tickers", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="risk-tickers",
                        type="text",
                        placeholder="e.g. AAPL, MSFT, GOOG, TSLA",
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "100%", "outline": "none"},
                    ),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Weights (same order)", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="risk-weights",
                        type="text",
                        placeholder="e.g. 0.30, 0.25, 0.25, 0.20",
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "100%", "outline": "none"},
                    ),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "0.75rem", "marginBottom": "0.6rem"}),

            html.Div([
                html.Button("\U0001F4C2 Load from Portfolio", id="risk-load-port", n_clicks=0,
                            style={"backgroundColor": C["accent"], "color": "#000",
                                   "border": "none", "borderRadius": "8px",
                                   "padding": "0.45rem 1.2rem", "fontFamily": FONT,
                                   "fontWeight": "700", "fontSize": "0.78rem",
                                   "cursor": "pointer"}),
                html.Span(id="risk-load-port-status",
                          style={"color": C["muted"], "fontSize": "0.72rem",
                                 "fontFamily": FONT, "alignSelf": "center"},
                          className="theme-muted"),
            ], style={"display": "flex", "gap": "0.75rem", "alignItems": "center",
                      "marginBottom": "0.6rem"}),

            html.Div([
                html.Div([
                    html.Div("Benchmark (optional)", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="risk-benchmark",
                        type="text",
                        placeholder="e.g. SPY (leave blank for absolute vol)",
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "100%", "outline": "none"},
                    ),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Rolling Window", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="risk-window",
                        options=[
                            {"label": "1 Month (21d)",   "value": 21},
                            {"label": "3 Months (63d)",  "value": 63},
                            {"label": "6 Months (126d)", "value": 126},
                            {"label": "1 Year (252d)",   "value": 252},
                        ],
                        value=63,
                        clearable=False,
                        style={"width": "200px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Div([
                    html.Div("History", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="risk-history",
                        options=[
                            {"label": "1 Year",  "value": "1y"},
                            {"label": "2 Years", "value": "2y"},
                            {"label": "3 Years", "value": "3y"},
                            {"label": "5 Years", "value": "5y"},
                        ],
                        value="3y",
                        clearable=False,
                        style={"width": "140px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Button("Calculate", id="risk-run", n_clicks=0, style={
                    "backgroundColor": C["red"], "color": "#fff", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.5rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.9rem"}),

            html.Div("Weights are auto-normalised to sum to 1. "
                     "If a benchmark is given, returns are computed as active (portfolio − benchmark).",
                     style={"color": C["muted"], "fontSize": "0.68rem",
                            "fontFamily": FONT, "marginBottom": "0.6rem"},
                     className="theme-muted"),

            # ── Outputs ───────────────────────────────────────────────────
            html.Div(id="risk-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),

            html.Div(id="risk-snapshot-table", style={"marginBottom": "1.2rem"}),

            html.Hr(style={"borderColor": C["border"], "margin": "1rem 0"}),
            html.Div("Rolling % Risk Contribution Over Time",
                     style={**LBL, "marginBottom": "0.4rem"},
                     className="theme-label"),
            html.Div(id="risk-rolling-chart"),

        ], style=PANEL, className="theme-panel"),
    ], id="section-risk", style={"display": "none"})
