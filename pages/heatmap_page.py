from dash import dcc, html


def build_heatmap_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Portfolio Heatmap", style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),
            html.Div("Size = portfolio weight, colour = performance over selected period.",
                     style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                            "fontFamily": FONT},
                     className="theme-muted"),

            html.Div([
                html.Button("Load Current Portfolio", id="heatmap-load-port", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.2rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                    "cursor": "pointer",
                }),
                html.Div([
                    html.Div("Time Horizon", style={**LBL, "marginBottom": "0.2rem"}, className="theme-label"),
                    dcc.Dropdown(
                        id="heatmap-period",
                        options=[
                            {"label": "1 Day", "value": "1d"},
                            {"label": "1 Week", "value": "5d"},
                            {"label": "1 Month", "value": "1mo"},
                            {"label": "3 Months", "value": "3mo"},
                            {"label": "6 Months", "value": "6mo"},
                            {"label": "YTD", "value": "ytd"},
                            {"label": "1 Year", "value": "1y"},
                        ],
                        value="1mo",
                        clearable=False,
                        style={"width": "170px", "fontSize": "0.82rem"},
                    ),
                ]),
            ], style={"display": "flex", "gap": "0.75rem", "alignItems": "flex-end", "marginBottom": "0.8rem"}),

            dcc.Store(id="heatmap-portfolio-data", data=[]),
            html.Div(id="heatmap-status",
                     style={"color": C["muted"], "fontSize": "0.75rem", "fontFamily": FONT,
                            "marginBottom": "0.65rem"}, className="theme-muted"),
            html.Div(id="heatmap-chart"),
        ], style=PANEL, className="theme-panel"),
    ], id="section-heatmap", style={"display": "none"})
