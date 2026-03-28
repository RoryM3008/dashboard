from dash import html


def build_news_section(LBL, PANEL):
    return html.Div([
        html.Div([
            html.Div("News Feed · Your Holdings", style=LBL, className="theme-label"),
            html.Div(id="news-feed"),
        ], style=PANEL, className="theme-panel"),
    ], id="section-news", style={"display": "none"})
