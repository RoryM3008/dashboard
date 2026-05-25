from dash import html, dcc


def build_dashboard_section(LBL, PANEL):
    from theme import C, FONT

    # ── Compact panel style for the Bloomberg look ───────────────────────
    BP = {**PANEL, "padding": "0.7rem 0.9rem", "marginBottom": "0.6rem",
          "borderRadius": "6px"}

    return html.Div([

        # Hidden store for ticker clicks
        dcc.Store(id="ticker-click-store", data=""),

        # ══════════════════════════════════════════════════════════════════
        # ROW 1 — Scrolling index ticker strip
        # ══════════════════════════════════════════════════════════════════
        html.Div(id="index-strip",
                 style={"display": "flex", "gap": "0.6rem", "overflowX": "auto",
                        "paddingBottom": "0.4rem", "marginBottom": "0.75rem"}),

        # ══════════════════════════════════════════════════════════════════
        # ROW 2 — Three-column Bloomberg grid
        # ══════════════════════════════════════════════════════════════════
        html.Div([

            # ── LEFT COLUMN ──────────────────────────────────────────────
            html.Div([
                # FX pairs
                html.Div([
                    html.Div("FX Rates", style=LBL, className="theme-label"),
                    html.Div(id="fx-table"),
                ], style=BP, className="theme-panel"),

                # Bond yields
                html.Div([
                    html.Div("Bond Yields", style=LBL, className="theme-label"),
                    html.Div(id="bond-table"),
                ], style=BP, className="theme-panel"),

                # Commodities
                html.Div([
                    html.Div("Commodities", style=LBL, className="theme-label"),
                    html.Div(id="commodity-table"),
                ], style=BP, className="theme-panel"),

            ], style={"width": "270px", "flexShrink": "0", "overflow": "hidden"}),

            # ── CENTER COLUMN ────────────────────────────────────────────
            html.Div([
                # Main chart
                html.Div([
                    html.Div([
                        dcc.Input(
                            id="chart-ticker-input", type="text",
                            value="SPY", debounce=True,
                            placeholder="Ticker e.g. SPY, AAPL",
                            style={"backgroundColor": C["bg"],
                                   "border": f"1px solid {C['border']}",
                                   "borderRadius": "4px", "color": C["text"],
                                   "padding": "0.3rem 0.5rem", "fontFamily": FONT,
                                   "fontSize": "0.78rem", "width": "130px"},
                        ),
                        html.Div(style={"flex": "1"}),
                        html.Div(id="sp500-last-price",
                                 style={"fontFamily": FONT, "fontSize": "0.82rem",
                                        "fontWeight": "700", "color": C["text"]}),
                    ], style={"display": "flex", "alignItems": "center",
                              "gap": "0.5rem", "marginBottom": "0.4rem"}),

                    # Bloomberg-style date controls
                    html.Div([
                        html.Div([
                            html.Span("START", style={"fontSize": "0.55rem",
                                      "fontWeight": "700", "color": "#000",
                                      "marginRight": "0.3rem"}),
                            dcc.Input(id="dash-chart-start", type="text",
                                      value="", debounce=True,
                                      style={"backgroundColor": "transparent",
                                             "border": "none", "color": "#000",
                                             "fontFamily": "Consolas, monospace",
                                             "fontSize": "0.72rem", "width": "80px",
                                             "padding": "0", "outline": "none"}),
                        ], style={"display": "inline-flex", "alignItems": "center",
                                  "backgroundColor": "#ff8c00", "borderRadius": "3px",
                                  "padding": "0.2rem 0.5rem", "marginRight": "0.4rem"}),
                        html.Div([
                            html.Span("END", style={"fontSize": "0.55rem",
                                      "fontWeight": "700", "color": "#000",
                                      "marginRight": "0.3rem"}),
                            dcc.Input(id="dash-chart-end", type="text",
                                      value="", debounce=True,
                                      style={"backgroundColor": "transparent",
                                             "border": "none", "color": "#000",
                                             "fontFamily": "Consolas, monospace",
                                             "fontSize": "0.72rem", "width": "80px",
                                             "padding": "0", "outline": "none"}),
                        ], style={"display": "inline-flex", "alignItems": "center",
                                  "backgroundColor": "#ff8c00", "borderRadius": "3px",
                                  "padding": "0.2rem 0.5rem", "marginRight": "0.8rem"}),
                        *[html.Button(lbl, id=f"dash-preset-{pid}",
                                      n_clicks=0,
                                      style={"backgroundColor": "transparent",
                                             "border": f"1px solid {C['border']}",
                                             "borderRadius": "3px", "color": C["muted"],
                                             "fontFamily": "Consolas, monospace",
                                             "fontSize": "0.65rem", "padding": "0.18rem 0.5rem",
                                             "cursor": "pointer", "marginRight": "0.2rem"})
                          for lbl, pid in [("1D","1d"),("5D","5d"),("1M","1m"),
                                           ("3M","3m"),("YTD","ytd"),("1Y","1y"),
                                           ("5Y","5y"),("MAX","max")]],
                    ], style={"display": "flex", "alignItems": "center",
                              "marginBottom": "0.3rem"}),

                    dcc.Graph(id="sp500-chart",
                              config={"displayModeBar": False},
                              style={"height": "320px"}),
                ], style=BP, className="theme-panel"),

            ], style={"flex": "1", "minWidth": "340px"}),

            # ── RIGHT COLUMN ─────────────────────────────────────────────
            html.Div([
                # Sector heatmap
                html.Div([
                    html.Div("Sector Performance", style=LBL,
                             className="theme-label"),
                    dcc.Graph(id="sector-treemap",
                              config={"displayModeBar": False},
                              style={"height": "280px"}),
                ], style=BP, className="theme-panel"),

                # Sector drill-down heatmap (hidden until a sector is clicked)
                html.Div([
                    html.Div([
                        html.Div(id="sector-drilldown-title",
                                 style={**LBL, "flex": "1"}, className="theme-label"),
                        html.Button("✕", id="sector-drilldown-close", n_clicks=0,
                                    style={"background": "none", "border": "none",
                                           "color": C["muted"], "fontSize": "0.9rem",
                                           "cursor": "pointer", "padding": "0"}),
                    ], style={"display": "flex", "alignItems": "center",
                              "marginBottom": "0.4rem"}),
                    html.Div(id="sector-drilldown-status",
                             style={"color": C["muted"], "fontSize": "0.68rem",
                                    "fontFamily": FONT, "marginBottom": "0.3rem"}),
                    dcc.Graph(id="sector-drilldown-chart",
                              config={"displayModeBar": False},
                              style={"height": "320px"}),
                ], id="sector-drilldown-panel",
                   style={**BP, "display": "none"}, className="theme-panel"),

                # Top gainers
                html.Div([
                    html.Div("S&P 500 Top Gainers", style=LBL, className="theme-label"),
                    html.Div(id="top-gainers-table"),
                ], style=BP, className="theme-panel"),

                # Top losers
                html.Div([
                    html.Div("S&P 500 Top Losers", style=LBL, className="theme-label"),
                    html.Div(id="top-losers-table"),
                ], style=BP, className="theme-panel"),

                # FTSE 100 gainers
                html.Div([
                    html.Div("FTSE 100 Top Gainers", style=LBL, className="theme-label"),
                    html.Div(id="ftse-gainers-table",
                             style={"maxHeight": "220px", "overflowY": "auto"}),
                ], style=BP, className="theme-panel"),

                # FTSE 100 losers
                html.Div([
                    html.Div("FTSE 100 Top Losers", style=LBL, className="theme-label"),
                    html.Div(id="ftse-losers-table",
                             style={"maxHeight": "220px", "overflowY": "auto"}),
                ], style=BP, className="theme-panel"),

                # Euro Stoxx 50 gainers
                html.Div([
                    html.Div("Euro Stoxx 50 Top Gainers", style=LBL, className="theme-label"),
                    html.Div(id="euro-gainers-table",
                             style={"maxHeight": "220px", "overflowY": "auto"}),
                ], style=BP, className="theme-panel"),

                # Euro Stoxx 50 losers
                html.Div([
                    html.Div("Euro Stoxx 50 Top Losers", style=LBL, className="theme-label"),
                    html.Div(id="euro-losers-table",
                             style={"maxHeight": "220px", "overflowY": "auto"}),
                ], style=BP, className="theme-panel"),

            ], style={"width": "280px", "flexShrink": "0"}),

        ], style={"display": "flex", "gap": "0.75rem", "alignItems": "flex-start"}),

    ], id="section-dashboard", style={"display": "block"})
