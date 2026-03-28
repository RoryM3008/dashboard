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
            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.9rem"}),

            html.Div(id="corr-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),
            html.Div(id="corr-heatmap", style={"marginBottom": "0.9rem"}),
            html.Div(id="corr-table"),
        ], style=PANEL, className="theme-panel"),
    ], id="section-correlation", style={"display": "none"})
