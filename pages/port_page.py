"""Layout — Portfolio page: transaction ledger, holdings, performance."""

from dash import dcc, html


def build_port_section(LBL, PANEL, C, FONT):
    return html.Div([

        # ── Overview metrics ──────────────────────────────────────────────
        html.Div([
            html.Div("Portfolio Overview", style={**LBL, "color": C["accent"],
                     "fontSize": "0.72rem"}, className="theme-label-accent"),
            html.Div(id="port-overview",
                     style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap",
                            "marginTop": "0.5rem"}),
            # ── Set Cash balance ──
            html.Div([
                html.Div("Set Cash Balance", style={**LBL, "fontSize": "0.65rem",
                         "marginRight": "0.5rem", "color": C["muted"]},
                         className="theme-label"),
                dcc.Input(id="port-cash-input", type="number",
                          placeholder="e.g. 5000", step=0.01,
                          className="theme-input",
                          style={"backgroundColor": C["bg"],
                                 "border": f"1px solid {C['border']}",
                                 "borderRadius": "8px", "color": C["text"],
                                 "padding": "0.35rem 0.6rem", "fontFamily": FONT,
                                 "fontSize": "0.78rem", "width": "110px",
                                 "outline": "none"}),
                html.Button("Set", id="port-cash-set", n_clicks=0, style={
                    "backgroundColor": C["blue"], "color": "#fff", "border": "none",
                    "borderRadius": "8px", "padding": "0.35rem 0.8rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.78rem",
                    "cursor": "pointer"}),
                html.Button("Clear", id="port-cash-clear", n_clicks=0, style={
                    "backgroundColor": "transparent", "color": C["muted"],
                    "border": f"1px solid {C['border']}",
                    "borderRadius": "8px", "padding": "0.35rem 0.8rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.78rem",
                    "cursor": "pointer"}),
                html.Span(id="port-cash-status", style={"color": C["muted"],
                          "fontSize": "0.72rem", "fontFamily": FONT,
                          "marginLeft": "0.5rem"}),
            ], style={"display": "flex", "alignItems": "center", "gap": "0.4rem",
                      "marginTop": "0.6rem"}),
        ], style=PANEL, className="theme-panel"),

        # ── Add Transaction form ──────────────────────────────────────────
        html.Div([
            html.Div("Add Transaction", style={**LBL, "color": C["green"],
                     "fontSize": "0.72rem", "marginBottom": "0.6rem"},
                     className="theme-label-green"),

            html.Div([
                html.Div([
                    html.Div("Date", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(id="port-txn-date", type="text",
                              placeholder="DD-MM-YYYY",
                              className="theme-input",
                              style={"backgroundColor": C["bg"],
                                     "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.45rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "120px", "outline": "none"}),
                ]),
                html.Div([
                    html.Div("Ticker", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(id="port-txn-ticker", type="text",
                              placeholder="e.g. AAPL",
                              className="theme-input",
                              style={"backgroundColor": C["bg"],
                                     "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.45rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "90px", "outline": "none"}),
                ]),
                html.Div([
                    html.Div("Side", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Dropdown(id="port-txn-side",
                                 options=[{"label": "DEPOSIT", "value": "DEPOSIT"},
                                          {"label": "WITHDRAW", "value": "WITHDRAW"},
                                          {"label": "BUY", "value": "BUY"},
                                          {"label": "SELL", "value": "SELL"},
                                          {"label": "DIVIDEND", "value": "DIVIDEND"},
                                          {"label": "INTEREST", "value": "INTEREST"}],
                                 value="DEPOSIT", clearable=False,
                                 style={"width": "130px", "fontSize": "0.82rem"}),
                ]),
                html.Div([
                    html.Div("Quantity", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(id="port-txn-qty", type="number",
                              placeholder="100",
                              className="theme-input",
                              style={"backgroundColor": C["bg"],
                                     "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.45rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "90px", "outline": "none"}),
                ]),
                html.Div([
                    html.Div("Price / Amount", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(id="port-txn-price", type="number",
                              placeholder="150.00", step=0.01,
                              className="theme-input",
                              style={"backgroundColor": C["bg"],
                                     "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.45rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "100px", "outline": "none"}),
                ]),
                html.Div([
                    html.Div("FX Rate", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(id="port-txn-fx", type="number",
                              placeholder="1.0", step=0.0001, value=1.0,
                              className="theme-input",
                              style={"backgroundColor": C["bg"],
                                     "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.45rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "80px", "outline": "none"}),
                ]),
                html.Div([
                    html.Div("Fees", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(id="port-txn-fees", type="number",
                              placeholder="0", step=0.01, value=0,
                              className="theme-input",
                              style={"backgroundColor": C["bg"],
                                     "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.45rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "75px", "outline": "none"}),
                ]),
                html.Div([
                    html.Div("Notes", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(id="port-txn-notes", type="text",
                              placeholder="optional",
                              className="theme-input",
                              style={"backgroundColor": C["bg"],
                                     "border": f"1px solid {C['border']}",
                                     "borderRadius": "8px", "color": C["text"],
                                     "padding": "0.45rem 0.7rem", "fontFamily": FONT,
                                     "fontSize": "0.82rem", "width": "130px", "outline": "none"}),
                ]),
                html.Button("+ Add", id="port-txn-add", n_clicks=0, style={
                    "backgroundColor": C["green"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.45rem 1.1rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                    "cursor": "pointer", "alignSelf": "flex-end",
                }),
            ], style={"display": "flex", "gap": "0.5rem", "flexWrap": "wrap",
                      "alignItems": "flex-end"}),

            html.Div(id="port-txn-status",
                     style={"color": C["muted"], "fontSize": "0.72rem",
                            "fontFamily": FONT, "marginTop": "0.4rem"},
                     className="theme-muted"),
        ], style=PANEL, className="theme-panel"),

        # ── Transaction ledger + CSV buttons ──────────────────────────────
        html.Div([
            html.Div([
                html.Div("Transaction Ledger", style={**LBL, "color": C["blue"],
                         "fontSize": "0.72rem"}, className="theme-label-blue"),
                html.Div(style={"flex": "1"}),
                dcc.Upload(
                    id="port-csv-upload",
                    children=html.Button("Import CSV", style={
                        "backgroundColor": "transparent", "color": C["blue"],
                        "border": f"1px solid {C['blue']}",
                        "borderRadius": "8px", "padding": "0.35rem 0.9rem",
                        "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.75rem",
                        "cursor": "pointer"}),
                    multiple=False,
                ),
                html.Button("Export CSV", id="port-csv-export", n_clicks=0, style={
                    "backgroundColor": "transparent", "color": C["accent"],
                    "border": f"1px solid {C['accent']}",
                    "borderRadius": "8px", "padding": "0.35rem 0.9rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.75rem",
                    "cursor": "pointer"}),
                html.Button("Clear All", id="port-clear-all", n_clicks=0, style={
                    "backgroundColor": "transparent", "color": C["red"],
                    "border": f"1px solid {C['red']}",
                    "borderRadius": "8px", "padding": "0.35rem 0.9rem",
                    "fontFamily": FONT, "fontWeight": "600", "fontSize": "0.75rem",
                    "cursor": "pointer"}),
            ], style={"display": "flex", "gap": "0.5rem", "alignItems": "center",
                      "marginBottom": "0.6rem"}),

            html.Div(id="port-ledger-table", style={"overflowX": "auto",
                      "maxHeight": "350px", "overflowY": "auto"}),
            dcc.Download(id="port-csv-download"),
        ], style=PANEL, className="theme-panel"),

        # ── Holdings summary ──────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Div("Current Holdings", style={**LBL, "color": C["accent"],
                         "fontSize": "0.72rem"}, className="theme-label-accent"),
                html.Div(style={"flex": "1"}),
                html.Button("Refresh Prices", id="port-refresh", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.45rem 1.2rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                    "cursor": "pointer"}),
            ], style={"display": "flex", "gap": "0.5rem", "alignItems": "center",
                      "marginBottom": "0.6rem"}),

            html.Div(id="port-holdings-table", style={"overflowX": "auto"}),
        ], style=PANEL, className="theme-panel"),

        # ── Performance chart ─────────────────────────────────────────────
        html.Div([
            html.Div("Portfolio Performance", style={**LBL, "marginBottom": "0.4rem"},
                     className="theme-label"),
            html.Div([
                dcc.Dropdown(id="port-chart-mode",
                             options=[
                                 {"label": "Portfolio Value",    "value": "value"},
                                 {"label": "Cumulative Return",  "value": "return"},
                                 {"label": "Drawdown",           "value": "drawdown"},
                             ],
                             value="value", clearable=False,
                             style={"width": "220px", "fontSize": "0.82rem"}),
            ], style={"marginBottom": "0.6rem"}),
            html.Div(id="port-chart"),
        ], style=PANEL, className="theme-panel"),

        # Hidden store to trigger refreshes
        dcc.Store(id="port-refresh-trigger", data=0),

    ], id="section-port", style={"display": "none"})
