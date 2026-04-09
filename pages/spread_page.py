"""Layout — Spread Analysis page: Bloomberg HS-style pairs / relative-value tool."""

from dash import dcc, html


def build_spread_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div([
                html.Div("SPREAD ANALYSIS",
                         style={**LBL, "color": "#ffd24d", "fontSize": "0.76rem", "marginBottom": "0"},
                         className="theme-label-accent"),
                html.Div("Bloomberg HS-style pair monitor",
                         style={"color": "#d6dbe1", "fontSize": "0.76rem",
                                "fontFamily": FONT, "fontWeight": "600"}),
            ], style={"background": "linear-gradient(90deg, #7b0f1e 0%, #971128 55%, #6d0d1a 100%)",
                      "border": "1px solid #39050b", "borderRadius": "8px",
                      "padding": "0.42rem 0.72rem", "marginBottom": "0.5rem"}),

            html.Div([
                html.Div([
                    html.Div("BUY", style={**LBL, "color": "#ffd24d", "marginBottom": "0.2rem"}),
                    dcc.Input(
                        id="spread-leg-a", type="text", placeholder="e.g. SAN",
                        className="theme-input",
                        style={"backgroundColor": "#0f1114", "border": "1px solid #3d434f",
                               "borderRadius": "4px", "color": "#f1f3f6", "padding": "0.42rem 0.55rem",
                               "fontFamily": FONT, "fontSize": "0.8rem", "width": "110px", "outline": "none"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Div([
                    html.Div("MULT", style={**LBL, "marginBottom": "0.2rem"}),
                    dcc.Input(
                        id="spread-mult-a", type="number", value=1, step=0.01,
                        className="theme-input",
                        style={"backgroundColor": "#0f1114", "border": "1px solid #3d434f",
                               "borderRadius": "4px", "color": "#f1f3f6", "padding": "0.42rem 0.5rem",
                               "fontFamily": FONT, "fontSize": "0.8rem", "width": "70px", "outline": "none"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Div([
                    html.Div("SELL", style={**LBL, "color": "#ff9f80", "marginBottom": "0.2rem"}),
                    dcc.Input(
                        id="spread-leg-b", type="text", placeholder="e.g. BAYN.DE",
                        className="theme-input",
                        style={"backgroundColor": "#0f1114", "border": "1px solid #3d434f",
                               "borderRadius": "4px", "color": "#f1f3f6", "padding": "0.42rem 0.55rem",
                               "fontFamily": FONT, "fontSize": "0.8rem", "width": "110px", "outline": "none"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Div([
                    html.Div("MULT", style={**LBL, "marginBottom": "0.2rem"}),
                    dcc.Input(
                        id="spread-mult-b", type="number", value=1, step=0.01,
                        className="theme-input",
                        style={"backgroundColor": "#0f1114", "border": "1px solid #3d434f",
                               "borderRadius": "4px", "color": "#f1f3f6", "padding": "0.42rem 0.5rem",
                               "fontFamily": FONT, "fontSize": "0.8rem", "width": "70px", "outline": "none"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Div([
                    html.Div("CALC", style={**LBL, "marginBottom": "0.2rem"}, className="theme-label"),
                    dcc.Dropdown(
                        id="spread-type",
                        options=[
                            {"label": "Difference", "value": "diff"},
                            {"label": "Ratio", "value": "ratio"},
                            {"label": "Z-Score", "value": "zscore"},
                        ],
                        value="diff", clearable=False,
                        className="spread-toolbar-dropdown",
                        style={"width": "130px", "fontSize": "0.8rem"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Div([
                    html.Div("HISTORY", style={**LBL, "marginBottom": "0.2rem"}),
                    dcc.Dropdown(
                        id="spread-history",
                        options=[
                            {"label": "6M", "value": "6mo"},
                            {"label": "1Y", "value": "1y"},
                            {"label": "2Y", "value": "2y"},
                            {"label": "3Y", "value": "3y"},
                            {"label": "5Y", "value": "5y"},
                            {"label": "MAX", "value": "max"},
                        ],
                        value="2y", clearable=False,
                        className="spread-toolbar-dropdown",
                        style={"width": "105px", "fontSize": "0.8rem"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Div([
                    html.Div("FREQ", style={**LBL, "marginBottom": "0.2rem"}),
                    dcc.Dropdown(
                        id="spread-freq",
                        options=[
                            {"label": "Daily", "value": "daily"},
                            {"label": "Weekly", "value": "weekly"},
                            {"label": "Monthly", "value": "monthly"},
                        ],
                        value="daily", clearable=False,
                        className="spread-toolbar-dropdown",
                        style={"width": "100px", "fontSize": "0.8rem"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Div([
                    html.Div("Z WINDOW", style={**LBL, "marginBottom": "0.2rem"}),
                    dcc.Input(
                        id="spread-zscore-window", type="number", value=60, min=5, step=1,
                        className="theme-input",
                        style={"backgroundColor": "#0f1114", "border": "1px solid #3d434f",
                               "borderRadius": "4px", "color": "#f1f3f6", "padding": "0.42rem 0.5rem",
                               "fontFamily": FONT, "fontSize": "0.8rem", "width": "75px", "outline": "none"},
                    ),
                ], style={"display": "flex", "flexDirection": "column", "gap": "0.18rem"}),
                html.Button("Analyse", id="spread-run", n_clicks=0, style={
                    "backgroundColor": "#f0a20d", "color": "#101010", "border": "none",
                    "borderRadius": "4px", "padding": "0.5rem 1.2rem", "alignSelf": "flex-end",
                    "fontFamily": FONT, "fontWeight": "800", "fontSize": "0.82rem", "cursor": "pointer",
                }),
            ], style={"display": "flex", "gap": "0.5rem", "flexWrap": "wrap",
                      "alignItems": "flex-end", "marginBottom": "0.4rem",
                      "padding": "0.42rem", "backgroundColor": "#080c12",
                      "border": "1px solid #222d39", "borderRadius": "4px"}),

            html.Div(id="spread-status",
                     style={"color": "#aeb4bf", "fontSize": "0.74rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),

            html.Div([
                html.Div([
                    html.Div("PRICE OVERLAY", style={**LBL, "marginBottom": "0.15rem", "color": "#ffc84a"}),
                    html.Div(id="spread-price-chart", style={"marginBottom": "0.35rem"}),
                    html.Div("SPREAD TIME SERIES", style={**LBL, "marginBottom": "0.15rem", "color": "#ffc84a"}),
                    html.Div(id="spread-series-chart"),
                ], style={"minWidth": "640px"}),
                html.Div([
                    html.Div([
                        html.Div("SPREAD SUMMARY", style={**LBL, "marginBottom": "0.2rem", "color": "#ffc84a"}),
                        html.Div(id="spread-stats-table"),
                    ], style={"backgroundColor": "#06080b", "border": "1px solid #2d3440",
                              "borderRadius": "4px", "padding": "0.5rem", "marginBottom": "0.42rem"}),
                    html.Div([
                        html.Div("SPREAD DISTRIBUTION", style={**LBL, "marginBottom": "0.15rem", "color": "#ffc84a"}),
                        html.Div(id="spread-histogram"),
                    ], style={"backgroundColor": "#06080b", "border": "1px solid #2d3440",
                              "borderRadius": "4px", "padding": "0.42rem"}),
                ], style={"minWidth": "470px"}),
            ], style={"display": "grid", "gap": "0.5rem",
                      "gridTemplateColumns": "minmax(640px, 1.85fr) minmax(470px, 1fr)",
                      "alignItems": "start", "overflowX": "auto"}),

        ], style={**PANEL, "backgroundColor": "#10151c", "border": "1px solid #2c3440",
                  "padding": "0.62rem", "borderRadius": "6px"}, className="theme-panel"),
    ], id="section-spread", style={"display": "none"})
