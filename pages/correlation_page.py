from dash import dcc, html


def build_correlation_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Stock Correlation Matrix", style={**LBL, "color": C["blue"], "fontSize": "0.72rem"},
                     className="theme-label-blue"),
            html.Div("Compare how your selected stocks move together.",
                     style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                            "fontFamily": FONT},
                     className="theme-muted"),

            html.Div([
                html.Div([
                    html.Div("Tickers", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="corr-tickers",
                        type="text",
                        placeholder="e.g. PYPL, NKE, BA, BABA",
                        value="PYPL, NKE, BA, BABA",
                        className="theme-input",
                        style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "100%", "outline": "none"},
                    ),
                ], style={"flex": "1"}),

                html.Div([
                    html.Div("Frequency", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="corr-frequency",
                        options=[
                            {"label": "Daily", "value": "daily"},
                            {"label": "Weekly", "value": "weekly"},
                            {"label": "Monthly", "value": "monthly"},
                        ],
                        value="weekly",
                        clearable=False,
                        style={"width": "170px", "fontSize": "0.82rem"},
                    ),
                ]),

                html.Button("Calculate", id="corr-run", n_clicks=0, style={
                    "backgroundColor": C["blue"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.5rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
                html.Button("\U0001F4C2 Load from Portfolio", id="corr-load-port", n_clicks=0,
                            style={"backgroundColor": C["accent"], "color": "#000",
                                   "border": "none", "borderRadius": "8px",
                                   "padding": "0.55rem 1.2rem", "fontFamily": FONT,
                                   "fontWeight": "700", "fontSize": "0.78rem",
                                   "cursor": "pointer", "alignSelf": "flex-end"}),
            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.9rem"}),

            html.Div(id="corr-load-port-status",
                     style={"color": C["muted"], "fontSize": "0.72rem",
                            "fontFamily": FONT, "marginBottom": "0.3rem"},
                     className="theme-muted"),
            html.Div(id="corr-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),
            html.Div(id="corr-heatmap", style={"marginBottom": "0.9rem"}),
            html.Div(id="corr-table"),

            # ── Rolling Correlation Section ───────────────────────────────
            html.Hr(style={"borderColor": C["border"], "margin": "1.5rem 0"}),
            html.Div("Rolling Correlation", style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),
            html.Div("Select pairs to chart rolling correlation over time.",
                     style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                            "fontFamily": FONT},
                     className="theme-muted"),

            html.Div([
                html.Div([
                    html.Div("Base Ticker (A)", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="rolling-corr-base",
                        type="text",
                        placeholder="e.g. AAPL",
                        className="theme-input",
                        style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "100%", "outline": "none"},
                    ),
                ], style={"flex": "1"}),

                html.Div([
                    html.Div("Compare Against (B, C, …)", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="rolling-corr-others",
                        type="text",
                        placeholder="e.g. MSFT, GOOG, TSLA",
                        className="theme-input",
                        style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "100%", "outline": "none"},
                    ),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "0.75rem", "marginBottom": "0.6rem"}),

            html.Div([
                html.Div([
                    html.Div("Rolling Window", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="rolling-corr-window",
                        options=[
                            {"label": "1 Week (5d)",    "value": 5},
                            {"label": "2 Weeks (10d)",  "value": 10},
                            {"label": "1 Month (21d)",  "value": 21},
                            {"label": "3 Months (63d)", "value": 63},
                            {"label": "6 Months (126d)","value": 126},
                            {"label": "1 Year (252d)",  "value": 252},
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
                        id="rolling-corr-history",
                        options=[
                            {"label": "1 Year",  "value": "1y"},
                            {"label": "2 Years", "value": "2y"},
                            {"label": "3 Years", "value": "3y"},
                            {"label": "5 Years", "value": "5y"},
                            {"label": "Max",     "value": "max"},
                        ],
                        value="3y",
                        clearable=False,
                        style={"width": "160px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Div([
                    html.Div("Return Frequency", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="rolling-corr-freq",
                        options=[
                            {"label": "Daily",   "value": "daily"},
                            {"label": "Weekly",  "value": "weekly"},
                            {"label": "Monthly", "value": "monthly"},
                        ],
                        value="daily",
                        clearable=False,
                        style={"width": "140px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Button("Chart", id="rolling-corr-run", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.5rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.9rem"}),

            html.Div(id="rolling-corr-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.4rem"},
                     className="theme-muted"),
            html.Div(id="rolling-corr-chart"),

        ], style=PANEL, className="theme-panel"),
    ], id="section-correlation", style={"display": "none"})
