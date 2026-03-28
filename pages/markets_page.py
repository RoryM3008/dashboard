"""Layout — Markets page: sector & country index performance."""

from dash import dcc, html


def build_markets_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Markets", style={**LBL, "color": C["blue"], "fontSize": "0.72rem"},
                     className="theme-label-blue"),
            html.Div("Sector ETF and country index performance across multiple time horizons.",
                     style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                            "fontFamily": FONT},
                     className="theme-muted"),

            html.Div([
                html.Button("Refresh", id="markets-refresh", n_clicks=0, style={
                    "backgroundColor": C["blue"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "marginBottom": "1rem"}),

            # Sector performance
            html.Div("Sector Performance (US Sector ETFs)", style={**LBL, "marginBottom": "0.4rem"},
                     className="theme-label"),
            html.Div(id="markets-status-sectors",
                     style={"color": C["muted"], "fontSize": "0.72rem",
                            "fontFamily": FONT, "marginBottom": "0.4rem"},
                     className="theme-muted"),
            html.Div(id="markets-sector-table", style={"marginBottom": "1.5rem"}),

            # Country index performance
            html.Div("Country / Region Index Performance", style={**LBL, "marginBottom": "0.4rem"},
                     className="theme-label"),
            html.Div(id="markets-status-countries",
                     style={"color": C["muted"], "fontSize": "0.72rem",
                            "fontFamily": FONT, "marginBottom": "0.4rem"},
                     className="theme-muted"),
            html.Div(id="markets-country-table", style={"marginBottom": "1.5rem"}),

            # ── Charting section ──────────────────────────────────────────
            html.Hr(style={"borderColor": C["border"], "margin": "1.2rem 0"}),
            html.Div("Chart Selected Markets", style={**LBL, "marginBottom": "0.4rem"},
                     className="theme-label"),
            html.Div("Pick any combination of sectors and country indices to chart.",
                     style={"color": C["muted"], "fontSize": "0.72rem",
                            "fontFamily": FONT, "marginBottom": "0.6rem"},
                     className="theme-muted"),

            html.Div([
                html.Div([
                    html.Div("Select markets", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="markets-chart-select",
                        multi=True,
                        placeholder="Choose sectors / indices…",
                        style={"fontSize": "0.82rem", "minWidth": "320px"},
                    ),
                ], style={"flex": "1"}),

                html.Div([
                    html.Div("View", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="markets-chart-mode",
                        options=[
                            {"label": "Absolute Price", "value": "absolute"},
                            {"label": "Relative Performance (rebased 100)", "value": "relative"},
                        ],
                        value="relative",
                        clearable=False,
                        style={"width": "270px", "fontSize": "0.82rem"},
                    ),
                ]),

                html.Div([
                    html.Div("Period", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="markets-chart-period",
                        options=[
                            {"label": "1 Month",  "value": "1mo"},
                            {"label": "3 Months", "value": "3mo"},
                            {"label": "6 Months", "value": "6mo"},
                            {"label": "YTD",      "value": "ytd"},
                            {"label": "1 Year",   "value": "1y"},
                            {"label": "2 Years",  "value": "2y"},
                            {"label": "5 Years",  "value": "5y"},
                        ],
                        value="6mo",
                        clearable=False,
                        style={"width": "160px", "fontSize": "0.82rem"},
                    ),
                ]),

                html.Button("Chart", id="markets-chart-btn", n_clicks=0, style={
                    "backgroundColor": C["blue"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.9rem"}),

            html.Div(id="markets-chart-status",
                     style={"color": C["muted"], "fontSize": "0.72rem",
                            "fontFamily": FONT, "marginBottom": "0.4rem"},
                     className="theme-muted"),
            html.Div(id="markets-chart"),

        ], style=PANEL, className="theme-panel"),
    ], id="section-markets", style={"display": "none"})
