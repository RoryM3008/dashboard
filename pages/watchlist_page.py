"""Layout — Watchlist page."""

from dash import dcc, html


def build_watchlist_section(LBL, PANEL, C, FONT):
    return html.Div([
        html.Div([
            html.Div("Watchlist", style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),
            html.Div("Build a persistent watchlist — add or remove stocks one at a time.",
                     style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                            "fontFamily": FONT},
                     className="theme-muted"),

            # Add ticker row
            html.Div([
                dcc.Input(
                    id="watchlist-input",
                    type="text",
                    placeholder="e.g. AAPL",
                    className="theme-input",
                    style={"backgroundColor": C["bg"], "border": f"1px solid {C['accent']}",
                           "borderRadius": "8px", "color": C["text"],
                           "padding": "0.55rem 1rem", "fontFamily": FONT,
                           "fontSize": "0.85rem", "flex": "1", "outline": "none"},
                ),
                html.Button("+ Add", id="watchlist-add", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.2rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
                    "cursor": "pointer",
                }),
                html.Button("Clear All", id="watchlist-clear", n_clicks=0,
                            className="theme-btn-outline-red",
                            style={
                    "backgroundColor": "transparent", "color": C["red"],
                    "border": f"1px solid {C['red']}",
                    "borderRadius": "8px", "padding": "0.55rem 1rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.82rem",
                    "cursor": "pointer",
                }),
                html.Button("🔄 Refresh Prices", id="watchlist-refresh", n_clicks=0,
                            style={
                    "backgroundColor": "transparent", "color": C["accent"],
                    "border": f"1px solid {C['accent']}",
                    "borderRadius": "8px", "padding": "0.55rem 1rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.82rem",
                    "cursor": "pointer",
                }),
            ], style={"display": "flex", "gap": "0.75rem", "marginBottom": "0.5rem"}),

            html.Div("Type one or more tickers and click + Add. Click ✕ on a row to remove it.",
                     style={"color": C["muted"], "fontSize": "0.68rem",
                            "marginTop": "0.2rem", "marginBottom": "0.6rem", "fontFamily": FONT},
                     className="theme-muted"),

            # Hidden components to keep callback IDs valid
            dcc.Dropdown(id="watchlist-periods", style={"display": "none"},
                         value=["1D", "5D", "1W", "1M", "3M", "6M", "1Y", "2Y"]),
            dcc.DatePickerRange(id="watchlist-custom-dates", style={"display": "none"}),

            # Pill-style list of current tickers
            html.Div(id="watchlist-pills",
                     style={"display": "flex", "gap": "0.4rem", "flexWrap": "wrap",
                            "marginBottom": "1rem"}),

            html.Div(id="watchlist-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),
            html.Div(id="watchlist-table"),

            # Persistent store for the ticker list
            dcc.Store(id="watchlist-store", data=[], storage_type="local"),
        ], style=PANEL, className="theme-panel"),
    ], id="section-watchlist", style={"display": "none"})
