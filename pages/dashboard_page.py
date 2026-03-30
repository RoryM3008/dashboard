from dash import html


def build_dashboard_section(LBL, PANEL):
    from theme import C, FONT
    return html.Div([
        html.Div([
            html.Div("Market Overview", style=LBL, className="theme-label"),
            html.Div(id="index-cards",
                     style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap"}),
        ], style=PANEL, className="theme-panel"),

        html.Div([
            html.Div([
                html.Div([
                    html.Div("Upcoming Earnings · Next 30 Days", style=LBL, className="theme-label"),
                    html.Div(style={"flex": "1"}),
                    html.Button("Load Earnings", id="load-earnings-btn", n_clicks=0, style={
                        "backgroundColor": C["accent"], "color": "#000", "border": "none",
                        "borderRadius": "8px", "padding": "0.4rem 1rem",
                        "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.78rem",
                        "cursor": "pointer"}),
                ], style={"display": "flex", "alignItems": "center", "gap": "0.5rem",
                          "marginBottom": "0.4rem"}),
                html.Div(id="earnings-legend", style={"marginBottom": "0.65rem"}),
                html.Div(id="earnings-table"),
            ], style={**PANEL, "flex": "1", "minWidth": "280px"}, className="theme-panel"),
            html.Div([
                html.Div("Portfolio Summary", style=LBL, className="theme-label"),
                html.Div(id="portfolio-table"),
            ], style={**PANEL, "flex": "1", "minWidth": "280px"}, className="theme-panel"),
        ], style={"display": "flex", "gap": "1.25rem", "flexWrap": "wrap"}),
    ], id="section-dashboard", style={"display": "block"})
