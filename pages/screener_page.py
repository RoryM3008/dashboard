from dash import dcc, html


def build_screener_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Stock Screener", style={**LBL, "color": C["green"], "fontSize": "0.72rem"},
                     className="theme-label-green"),

            html.Div([
                html.Div([
                    html.Div("Add extra tickers (optional):", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(id="screener-extra", type="text",
                              placeholder="e.g. ABNB, GRAB, CRH",
                              className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.5rem 0.9rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100%", "outline": "none"}),
                ], style={"flex": "1"}),

                html.Div([
                    html.Div("P/E max:", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(id="f-pe-max", type="number", placeholder="e.g. 30",
                              className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.5rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100%", "outline": "none"}),
                ], style={"width": "90px"}),

                html.Div([
                    html.Div("EV/EBITDA max:", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(id="f-ev-max", type="number", placeholder="e.g. 20",
                              className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.5rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100%", "outline": "none"}),
                ], style={"width": "110px"}),

                html.Div([
                    html.Div("Profit Margin min %:", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(id="f-margin-min", type="number", placeholder="e.g. 10",
                              className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.5rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100%", "outline": "none"}),
                ], style={"width": "130px"}),

                html.Div([
                    html.Div("Rev Growth min %:", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(id="f-revgrowth-min", type="number", placeholder="e.g. 5",
                              className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.5rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100%", "outline": "none"}),
                ], style={"width": "120px"}),

                html.Div([
                    html.Div("Div Yield min %:", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(id="f-div-min", type="number", placeholder="e.g. 1",
                              className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.5rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100%", "outline": "none"}),
                ], style={"width": "110px"}),

                html.Div([
                    html.Div("Debt/Equity max:", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Input(id="f-de-max", type="number", placeholder="e.g. 2",
                              className="theme-input",
                              style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.5rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100%", "outline": "none"}),
                ], style={"width": "110px"}),

            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "1rem"}),

            html.Div([
                html.Div([
                    html.Div("Sector:", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="f-sector",
                        options=[{"label": s, "value": s} for s in [
                            "All","Technology","Healthcare","Financials","Consumer Cyclical",
                            "Consumer Defensive","Industrials","Energy","Utilities",
                            "Real Estate","Communication Services","Basic Materials",
                        ]],
                        value="All",
                        clearable=False,
                        style={"width": "200px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Div(style={"flex": "1"}),
                html.Button("▶  Run Screen", id="screener-run", n_clicks=0, style={
                    "backgroundColor": C["green"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.6rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
                html.Button("⬇  Download CSV", id="screener-download-btn", n_clicks=0,
                            className="theme-btn-outline-green",
                            style={
                    "backgroundColor": "transparent", "color": C["green"],
                    "border": f"1px solid {C['green']}",
                    "borderRadius": "8px", "padding": "0.55rem 1.2rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.82rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
                dcc.Download(id="screener-download"),
            ], style={"display": "flex", "gap": "0.75rem", "alignItems": "flex-end",
                      "marginBottom": "1rem", "flexWrap": "wrap"}),

            html.Div([
                dcc.Upload(
                    id="screener-raw-upload",
                    children=html.Button("Import Raw Screener (CSV/XLSX)", style={
                        "backgroundColor": "transparent", "color": C["blue"],
                        "border": f"1px solid {C['blue']}",
                        "borderRadius": "8px", "padding": "0.45rem 1rem",
                        "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.78rem",
                        "cursor": "pointer"
                    }),
                    multiple=False,
                ),
                html.Div(
                    "Handles merged-style 2-row headers (e.g. Return on Equity (%) + 2025/26/27/28).",
                    style={"color": C["muted"], "fontSize": "0.7rem", "fontFamily": FONT,
                           "alignSelf": "center"},
                    className="theme-muted",
                ),
            ], style={"display": "flex", "gap": "0.7rem", "alignItems": "center",
                      "marginBottom": "0.7rem", "flexWrap": "wrap"}),

            html.Div(id="screener-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),
            html.Div(id="screener-results"),

            dcc.Store(id="screener-data-store"),
        ], style=PANEL, className="theme-panel"),
    ], id="section-screener", style={"display": "none"})
