"""Layout — Spread Analysis page: Bloomberg HS-style pairs / relative-value tool."""

from dash import dcc, html


def build_spread_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Spread Analysis",
                     style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),
            html.Div("Pairs / relative-value analysis — overlay two instruments, "
                     "compute their spread, and evaluate current extremeness vs history.",
                     style={"color": C["muted"], "fontSize": "0.78rem",
                            "marginBottom": "0.8rem", "fontFamily": FONT},
                     className="theme-muted"),

            # ── Inputs ────────────────────────────────────────────────────
            html.Div([
                # Leg A
                html.Div([
                    html.Div("Leg A (Buy)", style={**LBL, "marginBottom": "0.3rem",
                             "color": C["green"]}, className="theme-label"),
                    dcc.Input(
                        id="spread-leg-a", type="text",
                        placeholder="e.g. AAPL",
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "120px", "outline": "none"},
                    ),
                ]),
                # Multiplier A
                html.Div([
                    html.Div("Mult A", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="spread-mult-a", type="number", value=1, step=0.01,
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "80px", "outline": "none"},
                    ),
                ]),
                # Leg B
                html.Div([
                    html.Div("Leg B (Sell)", style={**LBL, "marginBottom": "0.3rem",
                             "color": C["red"]}, className="theme-label"),
                    dcc.Input(
                        id="spread-leg-b", type="text",
                        placeholder="e.g. MSFT",
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "120px", "outline": "none"},
                    ),
                ]),
                # Multiplier B
                html.Div([
                    html.Div("Mult B", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="spread-mult-b", type="number", value=1, step=0.01,
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "80px", "outline": "none"},
                    ),
                ]),
            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.6rem"}),

            # Row 2: spread type, history, frequency, run button
            html.Div([
                html.Div([
                    html.Div("Spread Type", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="spread-type",
                        options=[
                            {"label": "Difference (A − B)", "value": "diff"},
                            {"label": "Ratio (A / B)",      "value": "ratio"},
                            {"label": "Z-Score",            "value": "zscore"},
                        ],
                        value="diff", clearable=False,
                        style={"width": "190px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Div([
                    html.Div("History", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="spread-history",
                        options=[
                            {"label": "6 Months", "value": "6mo"},
                            {"label": "1 Year",   "value": "1y"},
                            {"label": "2 Years",  "value": "2y"},
                            {"label": "3 Years",  "value": "3y"},
                            {"label": "5 Years",  "value": "5y"},
                            {"label": "Max",      "value": "max"},
                        ],
                        value="2y", clearable=False,
                        style={"width": "140px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Div([
                    html.Div("Frequency", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="spread-freq",
                        options=[
                            {"label": "Daily",   "value": "daily"},
                            {"label": "Weekly",  "value": "weekly"},
                            {"label": "Monthly", "value": "monthly"},
                        ],
                        value="daily", clearable=False,
                        style={"width": "130px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Div([
                    html.Div("Z-Score Window", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="spread-zscore-window", type="number", value=60,
                        min=5, step=1,
                        className="theme-input",
                        style={"backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}",
                               "borderRadius": "8px", "color": C["text"],
                               "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                               "fontSize": "0.82rem", "width": "80px", "outline": "none"},
                    ),
                ]),
                html.Button("Analyse", id="spread-run", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.5rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.9rem"}),

            html.Div(id="spread-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),

            # ── Outputs ───────────────────────────────────────────────────

            # 1) Dual price overlay
            html.Div("Price Overlay", style={**LBL, "marginBottom": "0.3rem"},
                     className="theme-label"),
            html.Div(id="spread-price-chart", style={"marginBottom": "1rem"}),

            html.Hr(style={"borderColor": C["border"], "margin": "0.8rem 0"}),

            # 2) Spread time-series
            html.Div("Spread Time Series", style={**LBL, "marginBottom": "0.3rem"},
                     className="theme-label"),
            html.Div(id="spread-series-chart", style={"marginBottom": "1rem"}),

            html.Hr(style={"borderColor": C["border"], "margin": "0.8rem 0"}),

            # 3) Stats table + histogram side-by-side
            html.Div([
                # Stats summary
                html.Div([
                    html.Div("Spread Statistics", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    html.Div(id="spread-stats-table"),
                ], style={"flex": "1", "minWidth": "260px"}),
                # Histogram
                html.Div([
                    html.Div("Spread Distribution", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    html.Div(id="spread-histogram"),
                ], style={"flex": "1.5", "minWidth": "350px"}),
            ], style={"display": "flex", "gap": "1.2rem", "flexWrap": "wrap"}),

        ], style=PANEL, className="theme-panel"),
    ], id="section-spread", style={"display": "none"})
