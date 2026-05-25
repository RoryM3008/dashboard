from dash import dcc, html


def build_peers_section(LBL, PANEL, C, FONT):
    return html.Div([
        # ── Stores ──────────────────────────────────────────────────────────
        dcc.Store(id="peers-custom-list", storage_type="session", data=[]),
        dcc.Store(id="peers-recovery-store", storage_type="session", data={}),

        # ── Header / target input ────────────────────────────────────────────
        html.Div([
            html.Div("Peers", style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),
            html.Div(
                "Select a target stock, add custom peers, then Load to see the full comparison matrix.",
                style={"color": C["muted"], "fontSize": "0.78rem", "marginBottom": "0.8rem",
                       "fontFamily": FONT},
                className="theme-muted",
            ),

            # Target ticker row
            html.Div([
                html.Div([
                    html.Div("Target Company", style={**LBL, "marginBottom": "0.2rem"},
                             className="theme-label"),
                    dcc.Input(
                        id="peers-ticker",
                        type="text",
                        value="",
                        placeholder="e.g. 4911-JP",
                        autoComplete="off",
                        className="theme-input",
                        style={
                            "width": "260px", "fontFamily": FONT, "fontSize": "0.82rem",
                            "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                            "borderRadius": "8px", "color": C["text"],
                            "padding": "0.55rem 0.85rem", "outline": "none",
                            "boxSizing": "border-box",
                        },
                    ),
                    html.Div(id="peers-ticker-suggestions", style={
                        "width": "260px", "marginTop": "0.35rem",
                        "display": "flex", "flexDirection": "column", "gap": "0.2rem",
                    }),
                ], style={"marginRight": "1.2rem"}),

                # Custom peers input
                html.Div([
                    html.Div("Add Custom Peer", style={**LBL, "marginBottom": "0.2rem"},
                             className="theme-label"),
                    html.Div([
                        dcc.Input(
                            id="peers-custom-input",
                            type="text",
                            value="",
                            placeholder="e.g. EL-US",
                            autoComplete="off",
                            className="theme-input",
                            style={
                                "width": "190px", "fontFamily": FONT, "fontSize": "0.82rem",
                                "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                                "borderRadius": "8px", "color": C["text"],
                                "padding": "0.55rem 0.85rem", "outline": "none",
                                "boxSizing": "border-box",
                            },
                        ),
                        html.Button("＋ Add", id="peers-custom-add-btn", n_clicks=0, style={
                            "backgroundColor": "#0f2d0f", "color": C["accent"],
                            "border": f"1px solid {C['accent']}", "borderRadius": "8px",
                            "padding": "0.55rem 1rem", "fontFamily": FONT,
                            "fontWeight": "700", "fontSize": "0.8rem",
                            "cursor": "pointer", "marginLeft": "0.5rem",
                        }),
                    ], style={"display": "flex", "alignItems": "center"}),
                    html.Div(id="peers-custom-suggestions", style={
                        "width": "190px", "marginTop": "0.35rem",
                        "display": "flex", "flexDirection": "column", "gap": "0.2rem",
                    }),
                    html.Div(id="peers-custom-error",
                             style={"color": "#ff6b6b", "fontSize": "0.72rem",
                                    "fontFamily": FONT, "marginTop": "0.3rem"}),
                ], style={"marginRight": "1.2rem"}),

                # Load button + status
                html.Div([
                    html.Div(style={"height": "1.4rem"}),
                    html.Button("Load Peers", id="peers-load-btn", n_clicks=0, style={
                        "backgroundColor": C["accent"], "color": "#000", "border": "none",
                        "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                        "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                        "cursor": "pointer",
                    }),
                    html.Div(id="peers-status",
                             style={"color": C["muted"], "fontSize": "0.75rem",
                                    "fontFamily": FONT, "marginTop": "0.5rem"},
                             className="theme-muted"),
                ]),
            ], style={"display": "flex", "alignItems": "flex-start",
                      "flexWrap": "wrap", "marginBottom": "0.6rem"}),

            # Custom peer chips
            html.Div(id="peers-custom-chips", style={
                "display": "flex", "flexWrap": "wrap", "gap": "0.4rem",
                "marginTop": "0.2rem",
            }),
        ], style={**PANEL, "padding": "1rem 1.5rem", "marginTop": "0.8rem"}),

        # ── Summary banner ───────────────────────────────────────────────────
        html.Div(id="peers-summary", style={"marginTop": "0.6rem"}),

        # ── Legacy market data table + scatter ────────────────────────────────
        html.Div([
            html.Div([
                html.Div("Peer Market Data", style={**LBL, "color": C["accent"],
                         "fontSize": "0.6rem", "marginBottom": "0.3rem"},
                         className="theme-label-accent"),
                html.Div(id="peers-table"),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1.3"}),
            html.Div([
                html.Div("Valuation Map  (P/S vs P/E)", style={**LBL, "color": C["accent"],
                         "fontSize": "0.6rem", "marginBottom": "0.3rem"},
                         className="theme-label-accent"),
                dcc.Graph(id="peers-chart", config={"displayModeBar": False},
                          style={"height": "380px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1"}),
        ], style={"display": "flex", "gap": "0.6rem", "marginTop": "0.6rem"}),

        # ── 5-section comparison analysis ────────────────────────────────────
        html.Div(id="peers-analysis-div", style={"marginTop": "0.8rem"}),

    ], id="section-peers", style={"display": "none"})
