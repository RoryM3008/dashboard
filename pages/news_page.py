from dash import dcc, html


def build_news_section(LBL, PANEL):
    from theme import C, FONT
    return html.Div([
        html.Div([
            html.Div([
                html.Div("News Feed", style=LBL, className="theme-label"),
                html.Div(style={"flex": "1"}),
                html.Button("Load News", id="load-news-btn", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.4rem 1rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.78rem",
                    "cursor": "pointer"}),
            ], style={"display": "flex", "alignItems": "center", "gap": "0.5rem",
                      "marginBottom": "0.5rem"}),
            html.Div([
                html.Button("All",      id="news-filter-all",     n_clicks=1, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.4rem 1rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.78rem",
                    "cursor": "pointer"}),
                html.Button("Stock",    id="news-filter-stock",   n_clicks=0, style={
                    "backgroundColor": "transparent", "color": C["subtext"],
                    "border": f"1px solid {C['border']}",
                    "borderRadius": "8px", "padding": "0.4rem 1rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.78rem",
                    "cursor": "pointer"}),
                html.Button("General",  id="news-filter-general", n_clicks=0, style={
                    "backgroundColor": "transparent", "color": C["subtext"],
                    "border": f"1px solid {C['border']}",
                    "borderRadius": "8px", "padding": "0.4rem 1rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.78rem",
                    "cursor": "pointer"}),
            ], style={"display": "flex", "gap": "0.5rem", "marginBottom": "0.8rem"}),
            dcc.Store(id="news-cache", data=None),
            html.Div(id="news-feed"),
        ], style=PANEL, className="theme-panel"),
    ], id="section-news", style={"display": "none"})
