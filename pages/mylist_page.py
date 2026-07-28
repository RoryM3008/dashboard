"""Layout — My Stocks page.

A single-page portfolio hub: add/remove stocks, see price returns over
multiple horizons, read stock-specific news, and scan quick valuation
& profitability metrics — all in one view.
"""

from dash import dcc, html


def build_mylist_section(LBL, PANEL, C, FONT):
    pill_area = html.Div(
        id="mylist-pills",
        style={"display": "flex", "gap": "0.4rem", "flexWrap": "wrap",
               "marginBottom": "0.6rem"},
    )

    input_row = html.Div([
        dcc.Input(
            id="mylist-input", type="text",
            placeholder="e.g. AAPL",
            className="theme-input",
            style={"backgroundColor": C["bg"], "border": f"1px solid {C['accent']}",
                   "borderRadius": "8px", "color": C["text"],
                   "padding": "0.55rem 1rem", "fontFamily": FONT,
                   "fontSize": "0.85rem", "flex": "1", "outline": "none"},
        ),
        html.Button("+ Add", id="mylist-add", n_clicks=0, style={
            "backgroundColor": C["accent"], "color": "#000", "border": "none",
            "borderRadius": "8px", "padding": "0.55rem 1.2rem",
            "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.85rem",
            "cursor": "pointer",
        }),
        html.Button("Clear All", id="mylist-clear", n_clicks=0,
                    className="theme-btn-outline-red",
                    style={
            "backgroundColor": "transparent", "color": C["red"],
            "border": f"1px solid {C['red']}",
            "borderRadius": "8px", "padding": "0.55rem 1rem",
            "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.82rem",
            "cursor": "pointer",
        }),
        html.Button("🔄 Refresh", id="mylist-refresh", n_clicks=0,
                    style={
            "backgroundColor": "transparent", "color": C["accent"],
            "border": f"1px solid {C['accent']}",
            "borderRadius": "8px", "padding": "0.55rem 1rem",
            "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.82rem",
            "cursor": "pointer",
        }),
    ], style={"display": "flex", "gap": "0.75rem", "marginBottom": "0.5rem"})

    # ── Price returns table ───────────────────────────────────────────────
    price_panel = html.Div([
        html.Div("Price Returns", style={**LBL, "color": C["accent"],
                 "fontSize": "0.68rem", "marginBottom": "0.4rem"},
                 className="theme-label-accent"),
        html.Div(id="mylist-price-table"),
    ], style={**PANEL, "flex": "1", "minWidth": "0"},
       className="theme-panel")

    # ── News feed ─────────────────────────────────────────────────────────
    news_panel = html.Div([
        html.Div("News", style={**LBL, "color": C["accent"],
                 "fontSize": "0.68rem", "marginBottom": "0.4rem"},
                 className="theme-label-accent"),
        html.Div(id="mylist-news", style={"maxHeight": "480px", "overflowY": "auto"}),
    ], style={**PANEL, "flex": "0 0 340px", "minWidth": "280px"},
       className="theme-panel")

    # ── Valuation & profitability metrics ─────────────────────────────────
    metrics_panel = html.Div([
        html.Div("Valuation & Profitability", style={**LBL, "color": C["accent"],
                 "fontSize": "0.68rem", "marginBottom": "0.4rem"},
                 className="theme-label-accent"),
        html.Div(id="mylist-metrics-table"),
    ], style=PANEL, className="theme-panel")

    return html.Div([
        html.Div([
            html.Div("My Stocks", style={**LBL, "color": C["accent"],
                     "fontSize": "0.72rem"}, className="theme-label-accent"),
            html.Div("Your personal stock list — returns, news, and key metrics in one place.",
                     style={"color": C["muted"], "fontSize": "0.78rem",
                            "marginBottom": "0.8rem", "fontFamily": FONT},
                     className="theme-muted"),
            input_row,
            pill_area,
            html.Div(id="mylist-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginBottom": "0.65rem"},
                     className="theme-muted"),

            # Top row: price returns + news side-by-side
            html.Div([price_panel, news_panel],
                     style={"display": "flex", "gap": "1rem",
                            "marginBottom": "1rem", "alignItems": "flex-start"}),

            # Bottom row: valuation & profitability
            metrics_panel,

            # Persistent store
            dcc.Store(id="mylist-store", data=[], storage_type="local"),
        ], style=PANEL, className="theme-panel"),
    ], id="section-mylist", style={"display": "none"})
