"""Layout — Prices page: retrieve daily/weekly/monthly historical prices."""

from dash import dcc, html


def build_prices_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Prices", style={**LBL, "color": C["green"], "fontSize": "0.72rem"},
                     className="theme-label-green"),
            html.Div("Add stocks to view historical prices. Export to Excel when ready.",
                     style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                            "fontFamily": FONT},
                     className="theme-muted"),

            # Add / remove ticker row
            html.Div([
                dcc.Input(
                    id="prices-input",
                    type="text",
                    placeholder="e.g. AAPL, MSFT",
                    className="theme-input",
                    style={"backgroundColor": C["bg"], "border": f"1px solid {C['accent']}",
                           "borderRadius": "8px", "color": C["text"],
                           "padding": "0.55rem 1rem", "fontFamily": FONT,
                           "fontSize": "0.85rem", "flex": "1", "outline": "none"},
                ),
                html.Button("+ Add", id="prices-add", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.2rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer",
                }),
                html.Button("Clear All", id="prices-clear", n_clicks=0,
                            className="theme-btn-outline-red",
                            style={
                    "backgroundColor": "transparent", "color": C["red"],
                    "border": f"1px solid {C['red']}",
                    "borderRadius": "8px", "padding": "0.55rem 1rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.82rem",
                    "cursor": "pointer",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "marginBottom": "0.5rem"}),

            html.Div("Enter one or more tickers separated by commas, then click + Add.",
                     style={"color": C["muted"], "fontSize": "0.68rem",
                            "marginTop": "0.2rem", "marginBottom": "0.6rem", "fontFamily": FONT},
                     className="theme-muted"),

            # Pill-style list of current tickers
            html.Div(id="prices-pills",
                     style={"display": "flex", "gap": "0.4rem", "flexWrap": "wrap",
                            "marginBottom": "1rem"}),

            # Frequency + period selectors
            html.Div([
                html.Div([
                    html.Div("Frequency", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="prices-frequency",
                        options=[
                            {"label": "Daily",   "value": "daily"},
                            {"label": "Weekly",  "value": "weekly"},
                            {"label": "Monthly", "value": "monthly"},
                        ],
                        value="daily",
                        clearable=False,
                        style={"width": "160px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Div([
                    html.Div("Period", style={**LBL, "marginBottom": "0.3rem"},
                             className="theme-label"),
                    dcc.Dropdown(
                        id="prices-period",
                        options=[
                            {"label": "1 Month",   "value": "1mo"},
                            {"label": "3 Months",  "value": "3mo"},
                            {"label": "6 Months",  "value": "6mo"},
                            {"label": "1 Year",    "value": "1y"},
                            {"label": "2 Years",   "value": "2y"},
                            {"label": "5 Years",   "value": "5y"},
                            {"label": "Max",       "value": "max"},
                        ],
                        value="3mo",
                        clearable=False,
                        style={"width": "160px", "fontSize": "0.82rem"},
                    ),
                ]),
                html.Button("Fetch Prices", id="prices-fetch", n_clicks=0, style={
                    "backgroundColor": C["green"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
                html.Button("\u2B07 Export Excel", id="prices-export", n_clicks=0, style={
                    "backgroundColor": C["blue"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "alignItems": "flex-end",
                       "flexWrap": "wrap", "marginBottom": "1rem"}),

            html.Div(id="prices-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),

            # Table output
            html.Div(id="prices-table", style={"overflowX": "auto"}),

            # Persistent stores
            dcc.Store(id="prices-store", data=[], storage_type="local"),
            dcc.Download(id="prices-download"),

        ], style=PANEL, className="theme-panel"),
    ], id="section-prices", style={"display": "none"})
