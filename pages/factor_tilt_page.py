"""Layout - Style Analytics-style factor tilt page."""
from dash import dcc, html


def build_factor_tilt_section(LBL, PANEL, C, FONT):

    def _chip(label, btn_id, active=False):
        return html.Button(label, id=btn_id, n_clicks=0, style={
            "backgroundColor": C["accent"] if active else C["panel"],
            "color": "#000" if active else C["text"],
            "border": f"1px solid {C['border']}",
            "borderRadius": "6px", "padding": "0.32rem 0.7rem",
            "fontFamily": FONT, "fontWeight": "700",
            "fontSize": "0.72rem", "cursor": "pointer",
        })

    def _inp(id_, placeholder, width, type_="text", **extra):
        return dcc.Input(id=id_, type=type_, placeholder=placeholder,
            className="theme-input",
            style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                   "borderRadius": "6px", "color": C["text"],
                   "padding": "0.32rem 0.6rem", "fontFamily": FONT,
                   "fontSize": "0.76rem", "width": width, "outline": "none"},
            **extra)

    def _btn(label, id_, colour=None, text_col="#fff", ghost=False):
        bg = colour or C["blue"]
        style = {"border": "none", "borderRadius": "6px", "cursor": "pointer",
                 "padding": "0.38rem 0.85rem", "fontFamily": FONT,
                 "fontWeight": "700", "fontSize": "0.74rem"}
        if ghost:
            style.update({"background": "none", "border": f"1px solid {C['border']}",
                          "color": C["muted"]})
        else:
            style.update({"backgroundColor": bg, "color": text_col})
        return html.Button(label, id=id_, n_clicks=0, style=style)

    return html.Div([
        dcc.Store(id="ft-data-store", data={}),
        dcc.Store(id="ft-isin-refresh", data=0),
        dcc.Store(id="ft-holdings-store", data=[]),

        # ── Header ────────────────────────────────────────────────────
        html.Div([
            html.Div("Style Analytics", style={**LBL, "color": C["accent"],
                     "fontSize": "0.72rem"}, className="theme-label-accent"),
            html.Div(
                "Barra GEMLTL factor exposures  portfolio weighted-average style positioning",
                style={"color": C["muted"], "fontSize": "0.78rem", "fontFamily": FONT},
                className="theme-muted",
            ),
        ], style={"marginBottom": "1rem"}),

        # ── Controls ──────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Div("View", style={**LBL, "marginBottom": "0.3rem",
                         "fontSize": "0.65rem"}, className="theme-label"),
                html.Div([
                    _chip("Overview",      "ft-view-overview-btn", True),
                    _chip("Factor Detail", "ft-view-detail-btn",   False),
                    _chip("Style Map",     "ft-view-map-btn",       False),
                ], style={"display": "flex", "gap": "0.3rem"}),
            ], style={"marginRight": "1.5rem"}),
            html.Div([
                html.Div(" ", style={"marginBottom": "0.3rem", "fontSize": "0.65rem"}),
                html.Button("Run Analysis", id="ft-load-btn", n_clicks=0,
                    style={"backgroundColor": C["accent"], "color": "#000",
                           "border": "none", "borderRadius": "6px",
                           "padding": "0.45rem 1.1rem", "fontFamily": FONT,
                           "fontWeight": "700", "fontSize": "0.78rem", "cursor": "pointer"}),
            ]),
        ], style={"display": "flex", "alignItems": "flex-end",
                  "flexWrap": "wrap", "gap": "0.5rem", "marginBottom": "1.2rem"}),

        # ── Methodology mini demo ───────────────────────────────────
        html.Div([
            html.Div("Methodology Demo (small example)", style={
                **LBL, "color": C["blue"], "fontSize": "0.68rem", "marginBottom": "0.3rem"
            }, className="theme-label-blue"),
            html.Div(
                "Toy 3-stock portfolio vs benchmark showing how style scores and active tilts are calculated.",
                style={"color": C["muted"], "fontSize": "0.72rem", "fontFamily": FONT,
                       "marginBottom": "0.45rem"},
                className="theme-muted",
            ),
            html.Div([
                _btn("Run Example", "ft-method-demo-btn", colour=C["blue"]),
                html.Span("Uses weighted-average exposure and active tilt = portfolio - benchmark.",
                          style={"color": C["muted"], "fontSize": "0.7rem", "fontFamily": FONT}),
            ], style={"display": "flex", "gap": "0.5rem", "alignItems": "center", "flexWrap": "wrap"}),
            html.Div(id="ft-method-demo-out", style={"marginTop": "0.65rem"}),
        ], style={
            "backgroundColor": C["panel"],
            "border": f"1px solid {C['border']}",
            "borderRadius": "8px",
            "padding": "0.75rem",
            "marginBottom": "1rem",
        }),

        # ── Custom portfolio vs benchmark demo ───────────────────────
        html.Div([
            html.Div("Custom Portfolio vs Benchmark", style={
                **LBL, "color": C["accent"], "fontSize": "0.68rem", "marginBottom": "0.3rem"
            }, className="theme-label-accent"),
            html.Div(
                "Choose stocks, weights, and a benchmark proxy to compare style and factor tilt.",
                style={"color": C["muted"], "fontSize": "0.72rem", "fontFamily": FONT,
                       "marginBottom": "0.55rem"},
                className="theme-muted",
            ),
            html.Div([
                html.Div([
                    html.Div("Tickers", style={**LBL, "marginBottom": "0.25rem", "fontSize": "0.64rem"}, className="theme-label"),
                    dcc.Input(
                        id="ft-custom-tickers",
                        type="text",
                        value="COST, UAL, NAT, WMT, CCI, PYPL",
                        debounce=True,
                        style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                               "borderRadius": "6px", "color": C["text"], "padding": "0.35rem 0.6rem",
                               "fontFamily": FONT, "fontSize": "0.75rem", "width": "360px", "outline": "none"},
                    ),
                ]),
                html.Div([
                    html.Div("Weights %", style={**LBL, "marginBottom": "0.25rem", "fontSize": "0.64rem"}, className="theme-label"),
                    dcc.Input(
                        id="ft-custom-weights",
                        type="text",
                        value="",
                        debounce=True,
                        placeholder="Blank = equal weight, or e.g. 16.7,16.7,16.7...",
                        style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                               "borderRadius": "6px", "color": C["text"], "padding": "0.35rem 0.6rem",
                               "fontFamily": FONT, "fontSize": "0.75rem", "width": "320px", "outline": "none"},
                    ),
                ]),
                html.Div([
                    html.Div("Benchmark", style={**LBL, "marginBottom": "0.25rem", "fontSize": "0.64rem"}, className="theme-label"),
                    dcc.Dropdown(
                        id="ft-custom-benchmark",
                        options=[
                            {"label": "S&P 500 (equal-weight constituent proxy)", "value": "sp500_eq"},
                            {"label": "FTSE 100 (equal-weight constituent proxy)", "value": "ftse100_eq"},
                            {"label": "Euro Stoxx 50 (equal-weight constituent proxy)", "value": "euro50_eq"},
                        ],
                        value="sp500_eq",
                        clearable=False,
                        style={"minWidth": "300px", "fontSize": "0.76rem"},
                    ),
                ]),
                _btn("Compare", "ft-custom-run-btn", colour=C["accent"], text_col="#000"),
            ], style={"display": "flex", "gap": "0.75rem", "alignItems": "flex-end", "flexWrap": "wrap", "marginBottom": "0.6rem"}),
            html.Div(id="ft-custom-status", style={"color": C["muted"], "fontSize": "0.72rem", "fontFamily": FONT, "marginBottom": "0.45rem"}, className="theme-muted"),
            html.Div(id="ft-custom-out"),
        ], style={
            "backgroundColor": C["panel"],
            "border": f"1px solid {C['border']}",
            "borderRadius": "8px",
            "padding": "0.75rem",
            "marginBottom": "1rem",
        }),

        # ── Status ────────────────────────────────────────────────────
        html.Div(id="ft-status", style={
            "color": C["muted"], "fontSize": "0.75rem", "fontFamily": FONT,
            "marginBottom": "0.6rem", "minHeight": "1.2rem",
        }, className="theme-muted"),

        # ── Chart area ────────────────────────────────────────────────
        html.Div(id="ft-chart-area", children=[
            html.Div(
                "Click Run Analysis to generate the style report.",
                style={"color": C["muted"], "fontSize": "0.85rem",
                       "textAlign": "center", "padding": "4rem", "fontFamily": FONT},
                className="theme-muted")
        ]),

        # ── Coverage ──────────────────────────────────────────────────
        html.Div(id="ft-coverage-info", style={
            "color": C["muted"], "fontSize": "0.72rem", "fontFamily": FONT,
            "marginTop": "0.6rem", "lineHeight": "1.6",
        }, className="theme-muted"),

        # ── What-If Portfolio Editor ───────────────────────────────────
        html.Div(id="ft-whatif-panel", style={"display": "none"}, children=[
            html.Hr(style={"borderColor": C["border"], "margin": "1.5rem 0"}),
            html.Div([
                # Title
                html.Div([
                    html.Div("What-If Portfolio", style={
                        **LBL, "color": C["accent"], "fontSize": "0.72rem",
                        "marginBottom": "0.2rem",
                    }, className="theme-label-accent"),
                    html.Div(
                        "Adjust weights, remove or add holdings, then click Recalculate.",
                        style={"color": C["muted"], "fontSize": "0.72rem", "fontFamily": FONT},
                        className="theme-muted",
                    ),
                ], style={"marginBottom": "0.9rem"}),

                # Holding rows (callback-populated)
                html.Div(id="ft-weight-rows"),

                # Add row
                html.Div([
                    _inp("ft-add-ticker", "Ticker (e.g. MSFT)", "140px"),
                    _inp("ft-add-weight", "Weight %", "85px", type_="number",
                         min=0, max=100, step=0.1),
                    _btn("+ Add", "ft-add-row-btn"),
                ], style={"display": "flex", "gap": "0.4rem",
                          "alignItems": "center", "marginTop": "0.75rem",
                          "flexWrap": "wrap"}),

                # Action row
                html.Div([
                    _btn("Recalculate", "ft-recalc-btn",
                         colour=C["accent"], text_col="#000"),
                    _btn("Reset to Portfolio", "ft-reset-btn", ghost=True),
                    html.Span(id="ft-whatif-status",
                        style={"color": C["muted"], "fontSize": "0.72rem",
                               "fontFamily": FONT, "marginLeft": "0.3rem"}),
                ], style={"display": "flex", "gap": "0.5rem",
                          "alignItems": "center", "marginTop": "0.6rem",
                          "flexWrap": "wrap"}),
            ], style={
                "backgroundColor": C["panel"],
                "border": f"1px solid {C['border']}",
                "borderRadius": "8px", "padding": "1rem",
            }),
        ]),

        html.Hr(style={"borderColor": C["border"], "margin": "1.5rem 0"}),

        # ── ISIN Editor ───────────────────────────────────────────────
        html.Details([
            html.Summary("ISIN Map - assign ISINs to tickers",
                style={"cursor": "pointer", "color": C["muted"],
                       "fontSize": "0.75rem", "fontFamily": FONT,
                       "fontWeight": "600", "marginBottom": "0.4rem"}),
            html.Div(
                "ISINs are used to look up Barra IDs directly. "
                "Equity tickers are resolved automatically. "
                "Enter ISINs here for ETFs or any ticker that failed to match.",
                style={"color": C["muted"], "fontSize": "0.7rem",
                       "fontFamily": FONT, "marginBottom": "0.6rem"},
                className="theme-muted",
            ),
            html.Div(id="ft-isin-table"),
            html.Div([
                _inp("ft-isin-ticker-input", "Ticker (e.g. CSPX.L)", "130px"),
                _inp("ft-isin-value-input",  "ISIN (12 chars)",       "180px"),
                _btn("Save", "ft-isin-save-btn"),
                html.Span(id="ft-isin-status",
                    style={"color": C["muted"], "fontSize": "0.72rem", "fontFamily": FONT}),
            ], style={"display": "flex", "gap": "0.5rem", "alignItems": "center",
                      "marginTop": "0.5rem", "flexWrap": "wrap"}),
        ]),

    ], id="section-factor-tilt", style={"display": "none"})
