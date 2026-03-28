from dash import dcc, html


def build_analyser_section(LBL, PANEL, C, FONT, NAV_BTN_ACTIVE, NAV_BTN, PERIODS):
    return html.Div([
        html.Div([
            html.Div("Stock Analyser", style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),

            html.Div([
                dcc.Input(id="lookup-input", type="text",
                          placeholder="Enter a ticker  e.g. NKE, AAPL, TSLA",
                          debounce=False,
                          className="theme-input",
                          style={"backgroundColor": C["bg"],
                                 "border": f"1px solid {C['blue']}",
                                 "borderRadius": "8px", "color": C["text"],
                                 "padding": "0.55rem 1rem", "fontFamily": FONT,
                                 "fontSize": "0.85rem", "flex": "1", "outline": "none"}),
                html.Button("Search", id="lookup-btn", n_clicks=0,
                            style={"backgroundColor": C["blue"], "color": "#000",
                                   "border": "none", "borderRadius": "8px",
                                   "padding": "0.55rem 1.4rem", "fontFamily": FONT,
                                   "fontWeight": "700", "fontSize": "0.85rem", "cursor": "pointer"}),
            ], style={"display": "flex", "gap": "0.75rem", "marginBottom": "1rem"}),

            html.Div(id="stock-header"),

            html.Div([
                html.Button("Price Chart",       id="tab-chart",     n_clicks=0, style=NAV_BTN_ACTIVE),
                html.Button("Valuation Metrics", id="tab-valuation", n_clicks=0, style=NAV_BTN),
                html.Button("Income Statement",  id="tab-income",    n_clicks=0, style=NAV_BTN),
                html.Button("Balance Sheet",     id="tab-balance",   n_clicks=0, style=NAV_BTN),
                html.Button("Cash Flow",         id="tab-cashflow",  n_clicks=0, style=NAV_BTN),
            ], id="tab-nav",
               style={"display": "none", "gap": "0.5rem", "flexWrap": "wrap", "marginBottom": "1rem"}),

            html.Div(
                [html.Div("Period:", style={"color": C["subtext"], "fontSize": "0.75rem",
                                            "alignSelf": "center", "fontFamily": FONT},
                          className="theme-subtext")] +
                [html.Button(p, id=f"period-{p}", n_clicks=0,
                             style={**NAV_BTN,
                                    "padding": "0.3rem 0.7rem", "fontSize": "0.75rem",
                                    **({"backgroundColor": C["accent"], "color": "#000",
                                        "border": f"1px solid {C['accent']}"} if p == "6mo" else {})})
                 for p in PERIODS],
                id="period-nav",
                style={"display": "none", "gap": "0.4rem", "alignItems": "center",
                       "marginBottom": "0.75rem", "flexWrap": "wrap"},
            ),

            html.Div(id="stock-content"),

            dcc.Store(id="active-tab",    data="chart"),
            dcc.Store(id="active-period", data="6mo"),
            dcc.Store(id="active-ticker", data=""),
        ], style=PANEL, className="theme-panel"),
    ], id="section-analyser", style={"display": "none"})
