from dash import dcc, html

from theme import BBG_ESTIMATES


def build_ssa_section(LBL, PANEL, C, FONT):
    """Single Stock Analysis page layout."""

    bbg = BBG_ESTIMATES

    card_style = {
        "backgroundColor": C["panel"], "border": f"1px solid {C['border']}",
        "borderRadius": "8px", "padding": "0.7rem 1rem", "flex": "1",
        "minWidth": "140px",
    }
    card_label = {**LBL, "fontSize": "0.6rem", "marginBottom": "0.15rem", "color": C["muted"]}
    card_value = {"fontFamily": FONT, "fontSize": "1.15rem", "fontWeight": "700", "color": C["text"]}

    return html.Div([
        html.Div([
            # ── Header ──────────────────────────────────────────────────
            html.Div("Single Stock Analysis",
                     style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                     className="theme-label-accent"),

            # ── Ticker input row ─────────────────────────────────────────
            html.Div([
                html.Div([
                    html.Div("Ticker / Company", style={**LBL, "marginBottom": "0.2rem"}, className="theme-label"),
                    dcc.Input(
                        id="ssa-ticker",
                        type="text",
                        value="AAPL-US",
                        placeholder="Type ticker or company name…",
                        autoComplete="off",
                        className="theme-input",
                        style={
                            "width": "420px", "fontFamily": FONT, "fontSize": "0.82rem",
                            "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                            "borderRadius": "8px", "color": C["text"], "padding": "0.55rem 0.85rem",
                            "outline": "none", "boxSizing": "border-box",
                        },
                    ),
                    html.Div(id="ssa-ticker-suggestions", style={
                        "width": "420px", "marginTop": "0.35rem", "display": "flex",
                        "flexDirection": "column", "gap": "0.2rem",
                    }),
                ], style={"marginRight": "1rem"}),
                html.Button("Load", id="ssa-load-btn", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                    "cursor": "pointer", "marginTop": "1.1rem",
                }),
                html.Div(id="ssa-status", style={"color": C["muted"], "fontSize": "0.75rem",
                                                   "fontFamily": FONT, "marginTop": "1.3rem",
                                                   "marginLeft": "1rem"},
                         className="theme-muted"),
            ], style={"display": "flex", "alignItems": "flex-start", "marginBottom": "0.8rem"}),

        ], style={**PANEL, "padding": "1rem 1.5rem", "marginTop": "0.8rem"}),

        # ── Company header ───────────────────────────────────────────────
        html.Div(id="ssa-company-header", style={"marginTop": "0.6rem"}),

        # ── Key metrics cards ────────────────────────────────────────────
        html.Div(id="ssa-metrics-cards", style={"marginTop": "0.6rem"}),

        # ── Price chart (Bloomberg-style) ────────────────────────────────
        html.Div([
            # Top row: date inputs + preset buttons
            html.Div([
                # Orange date boxes
                html.Div([
                    html.Div([
                        html.Div("START", style={"fontSize": "0.5rem", "color": "#000",
                                                  "fontFamily": "Consolas, monospace",
                                                  "fontWeight": "700", "letterSpacing": "0.05em"}),
                        dcc.Input(id="ssa-chart-start", type="text", placeholder="YYYY-MM-DD",
                                  style={"backgroundColor": "transparent", "border": "none",
                                         "color": "#000", "fontFamily": "Consolas, monospace",
                                         "fontSize": "0.78rem", "fontWeight": "700",
                                         "width": "100px", "outline": "none", "padding": "0"}),
                    ], style={"backgroundColor": "#ff8c00", "borderRadius": "3px",
                              "padding": "3px 8px", "marginRight": "6px"}),
                    html.Div([
                        html.Div("END", style={"fontSize": "0.5rem", "color": "#000",
                                                "fontFamily": "Consolas, monospace",
                                                "fontWeight": "700", "letterSpacing": "0.05em"}),
                        dcc.Input(id="ssa-chart-end", type="text", placeholder="YYYY-MM-DD",
                                  style={"backgroundColor": "transparent", "border": "none",
                                         "color": "#000", "fontFamily": "Consolas, monospace",
                                         "fontSize": "0.78rem", "fontWeight": "700",
                                         "width": "100px", "outline": "none", "padding": "0"}),
                    ], style={"backgroundColor": "#ff8c00", "borderRadius": "3px",
                              "padding": "3px 8px"}),
                ], style={"display": "flex", "alignItems": "center"}),
                # Preset period buttons
                html.Div([
                    html.Button(p, id=f"ssa-preset-{p.lower()}", n_clicks=0,
                                style={"backgroundColor": "transparent", "border": "1px solid #333",
                                       "borderRadius": "3px", "color": "#8a8e96",
                                       "fontFamily": "Consolas, monospace", "fontSize": "0.65rem",
                                       "fontWeight": "700", "padding": "2px 8px", "cursor": "pointer",
                                       "marginRight": "4px"})
                    for p in ["1D", "5D", "1M", "3M", "YTD", "1Y", "5Y", "MAX"]
                ], style={"display": "flex", "marginTop": "5px"}),
            ], style={"padding": "8px 10px"}),
            # Chart
            dcc.Graph(id="ssa-price-chart",
                      config={"displayModeBar": False, "scrollZoom": True},
                      style={"height": "380px"}),
        ], style={"backgroundColor": "#000000", "borderRadius": "8px",
                  "marginTop": "0.6rem", "border": "1px solid #1a1a1a"}),
        html.Div([
            # EPS Revisions chart
            html.Div([
                html.Div("EPS Consensus Revisions", style={**LBL, "color": C["accent"],
                         "fontSize": "0.6rem", "marginBottom": "0.3rem"},
                         className="theme-label-accent"),
                dcc.Graph(id="ssa-eps-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1"}),

            # Recommendations chart
            html.Div([
                html.Div("Analyst Recommendations", style={**LBL, "color": C["accent"],
                         "fontSize": "0.6rem", "marginBottom": "0.3rem"},
                         className="theme-label-accent"),
                dcc.Graph(id="ssa-rec-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1"}),
        ], style={"display": "flex", "gap": "0.6rem", "marginTop": "0.6rem"}),

        dcc.Store(id="ssa-est-meta", data={}),
        dcc.Store(id="ssa-est-growth-mode", data="yoy"),
        dcc.Store(id="ssa-est-chart-mode", data="values"),

        # ── Bloomberg-style Estimates / Ratios screen ───────────────────
        html.Div([
            html.Div([
                html.Div(id="ssa-est-security-name", children="—", style={
                    "color": bbg["text"], "fontFamily": FONT, "fontWeight": "700",
                    "fontSize": "0.88rem", "minWidth": "180px", "paddingTop": "0.15rem",
                }),
                html.Div([
                    html.Div("Periodicity", style={
                        "color": bbg["orange"], "fontFamily": FONT, "fontSize": "0.64rem",
                        "fontWeight": "700", "marginBottom": "0.15rem", "textTransform": "uppercase",
                    }),
                    dcc.Dropdown(
                        id="ssa-est-periodicity",
                        options=[
                            {"label": "Quarterly", "value": "quarterly"},
                            {"label": "Annual", "value": "annual"},
                        ],
                        value="quarterly",
                        clearable=False,
                        searchable=False,
                        style={"width": "128px", "fontFamily": FONT, "fontSize": "0.7rem"},
                        className="ssa-bbg-dropdown",
                    ),
                ]),
                html.Div([
                    html.Div("Source", style={
                        "color": bbg["orange"], "fontFamily": FONT, "fontSize": "0.64rem",
                        "fontWeight": "700", "marginBottom": "0.15rem", "textTransform": "uppercase",
                    }),
                    dcc.Dropdown(
                        id="ssa-est-source",
                        options=[{"label": "Standard", "value": "standard"}],
                        value="standard",
                        clearable=False,
                        searchable=False,
                        style={"width": "120px", "fontFamily": FONT, "fontSize": "0.7rem"},
                        className="ssa-bbg-dropdown",
                    ),
                ]),
                html.Div([
                    html.Div("Currency", style={
                        "color": bbg["orange"], "fontFamily": FONT, "fontSize": "0.64rem",
                        "fontWeight": "700", "marginBottom": "0.15rem", "textTransform": "uppercase",
                    }),
                    dcc.Dropdown(
                        id="ssa-est-currency",
                        options=[{"label": "USD", "value": "USD"}],
                        value="USD",
                        clearable=False,
                        searchable=False,
                        style={"width": "110px", "fontFamily": FONT, "fontSize": "0.7rem"},
                        className="ssa-bbg-dropdown",
                    ),
                ]),
            ], style={"display": "flex", "alignItems": "flex-end", "gap": "0.7rem", "flexWrap": "wrap"}),

            html.Div([
                html.Div("Measure", style={
                    "color": bbg["orange"], "fontFamily": FONT, "fontSize": "0.64rem",
                    "fontWeight": "700", "marginBottom": "0.15rem", "textTransform": "uppercase",
                }),
                dcc.Dropdown(
                    id="ssa-est-measure",
                    options=[
                        {"label": "EPS", "value": "EPS"},
                        {"label": "Sales", "value": "SALES"},
                        {"label": "CFPS", "value": "CFPS"},
                        {"label": "DPS", "value": "DPS"},
                        {"label": "P/E", "value": "PE"},
                        {"label": "P/S", "value": "PSALES"},
                        {"label": "P/CF", "value": "PCF"},
                        {"label": "Gross Margin", "value": "GROSS_MARGIN"},
                        {"label": "EBIT Margin", "value": "EBIT_MARGIN"},
                    ],
                    value="EPS",
                    clearable=False,
                    searchable=False,
                    style={"width": "220px", "fontFamily": FONT, "fontSize": "0.7rem"},
                    className="ssa-bbg-dropdown",
                ),
            ], style={"marginTop": "0.5rem"}),

            html.Div([
                html.Div([
                    html.Div("Values", style={
                        "color": bbg["orange"], "fontFamily": FONT, "fontSize": "0.65rem",
                        "fontWeight": "700", "letterSpacing": "0.04em", "marginBottom": "0.3rem",
                    }),
                    html.Div(id="ssa-est-values-table"),
                ], style={
                    "flex": "1", "backgroundColor": bbg["panel"], "border": f"1px solid {bbg['border']}",
                    "padding": "0.55rem 0.65rem", "minWidth": "0",
                }),
                html.Div([
                    html.Div([
                        html.Button("1) YoY % Growth", id="ssa-est-yoy-btn", n_clicks=0, style={
                            "backgroundColor": bbg["blue"], "color": "#ffffff", "border": f"1px solid {bbg['border']}",
                            "borderRadius": "0", "padding": "0.22rem 0.55rem", "fontSize": "0.68rem",
                            "fontFamily": FONT, "cursor": "pointer",
                        }),
                        html.Button("2) PoP % Growth", id="ssa-est-pop-btn", n_clicks=0, style={
                            "backgroundColor": bbg["tab_off"], "color": bbg["muted"], "border": f"1px solid {bbg['border']}",
                            "borderRadius": "0", "padding": "0.22rem 0.55rem", "fontSize": "0.68rem",
                            "fontFamily": FONT, "cursor": "pointer", "marginLeft": "0.2rem",
                        }),
                    ], style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "0.3rem"}),
                    html.Div(id="ssa-est-growth-table"),
                ], style={
                    "flex": "1", "backgroundColor": bbg["panel"], "border": f"1px solid {bbg['border']}",
                    "padding": "0.55rem 0.65rem", "minWidth": "0",
                }),
            ], style={"display": "flex", "gap": "0.55rem", "marginTop": "0.55rem"}),

            html.Div([
                html.Div([
                    html.Div([
                        html.Button("3) Values Chart", id="ssa-est-values-chart-btn", n_clicks=0, style={
                            "backgroundColor": bbg["blue"], "color": "#ffffff", "border": f"1px solid {bbg['border']}",
                            "borderRadius": "0", "padding": "0.22rem 0.55rem", "fontSize": "0.68rem",
                            "fontFamily": FONT, "cursor": "pointer",
                        }),
                        html.Button("4) Growth Chart", id="ssa-est-growth-chart-btn", n_clicks=0, style={
                            "backgroundColor": bbg["tab_off"], "color": bbg["muted"], "border": f"1px solid {bbg['border']}",
                            "borderRadius": "0", "padding": "0.22rem 0.55rem", "fontSize": "0.68rem",
                            "fontFamily": FONT, "cursor": "pointer", "marginLeft": "0.2rem",
                        }),
                    ], style={"display": "flex", "marginBottom": "0.35rem"}),
                    dcc.Graph(id="ssa-est-chart", config={"displayModeBar": False}, style={"height": "360px"}),
                ], style={
                    "flex": "1", "backgroundColor": bbg["panel"], "border": f"1px solid {bbg['border']}",
                    "padding": "0.55rem 0.65rem", "minWidth": "0",
                }),
                html.Div([
                    html.Div("Multiple", style={
                        "color": bbg["orange"], "fontFamily": FONT, "fontSize": "0.65rem",
                        "fontWeight": "700", "letterSpacing": "0.04em", "marginBottom": "0.3rem",
                    }),
                    html.Div(id="ssa-est-multiples-table"),
                ], style={
                    "width": "34%", "backgroundColor": bbg["panel"], "border": f"1px solid {bbg['border']}",
                    "padding": "0.55rem 0.65rem", "minWidth": "300px",
                }),
            ], style={"display": "flex", "gap": "0.55rem", "marginTop": "0.55rem"}),
        ], style={
            "backgroundColor": bbg["bg"], "border": f"1px solid {bbg['border']}",
            "padding": "0.7rem", "marginTop": "0.6rem",
        }),

        # ── Financial Statements (IS, BS, CF) ────────────────────────────
        html.Div([
            html.Div([
                html.Button("Load Financial Statements", id="ssa-load-financials-btn",
                            n_clicks=0, style={
                    "backgroundColor": C["panel"], "color": C["accent"],
                    "border": f"1px solid {C['accent']}",
                    "borderRadius": "6px", "padding": "0.4rem 1.2rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.75rem",
                    "cursor": "pointer", "marginRight": "0.8rem",
                }),
                # Annual / Quarterly toggle
                html.Div([
                    html.Button("Annual", id="ssa-fin-annual-btn", n_clicks=0, style={
                        "backgroundColor": C["accent"], "color": "#000", "border": "none",
                        "borderRadius": "4px 0 0 4px", "padding": "0.35rem 0.8rem",
                        "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.7rem",
                        "cursor": "pointer",
                    }),
                    html.Button("Quarterly", id="ssa-fin-quarterly-btn", n_clicks=0, style={
                        "backgroundColor": C["panel"], "color": C["muted"],
                        "border": f"1px solid {C['border']}",
                        "borderRadius": "0 4px 4px 0", "padding": "0.35rem 0.8rem",
                        "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.7rem",
                        "cursor": "pointer",
                    }),
                ], style={"display": "inline-flex"}),
                html.Div(id="ssa-financials-status", style={
                    "color": C["muted"], "fontSize": "0.7rem",
                    "fontFamily": FONT, "marginLeft": "1rem", "display": "inline"},
                    className="theme-muted"),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "0.6rem"}),

            dcc.Store(id="ssa-fin-freq", data="annual"),

            # Collapsible Income Statement
            html.Details([
                html.Summary("Income Statement", style={
                    "color": C["accent"], "fontFamily": FONT, "fontWeight": "700",
                    "fontSize": "0.78rem", "cursor": "pointer", "padding": "0.4rem 0",
                }),
                html.Div(id="ssa-income-statement"),
            ], open=True, style={**PANEL, "padding": "0.6rem 1rem", "marginBottom": "0.5rem"}),

            # Collapsible Balance Sheet
            html.Details([
                html.Summary("Balance Sheet", style={
                    "color": C["accent"], "fontFamily": FONT, "fontWeight": "700",
                    "fontSize": "0.78rem", "cursor": "pointer", "padding": "0.4rem 0",
                }),
                html.Div(id="ssa-balance-sheet"),
            ], open=True, style={**PANEL, "padding": "0.6rem 1rem", "marginBottom": "0.5rem"}),

            # Collapsible Cash Flow
            html.Details([
                html.Summary("Cash Flow Statement", style={
                    "color": C["accent"], "fontFamily": FONT, "fontWeight": "700",
                    "fontSize": "0.78rem", "cursor": "pointer", "padding": "0.4rem 0",
                }),
                html.Div(id="ssa-cash-flow"),
            ], open=True, style={**PANEL, "padding": "0.6rem 1rem"}),
        ], style={"marginTop": "0.6rem"}),

        # ── News, Filings & Transcripts (3-column) ──────────────────────
        html.Div([
            html.Button("Load News & Filings", id="ssa-load-news-btn", n_clicks=0, style={
                "backgroundColor": C["panel"], "color": C["accent"],
                "border": f"1px solid {C['accent']}",
                "borderRadius": "6px", "padding": "0.4rem 1.2rem",
                "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.75rem",
                "cursor": "pointer", "marginBottom": "0.6rem",
            }),
            html.Div(id="ssa-news-status", style={"color": C["muted"], "fontSize": "0.7rem",
                     "fontFamily": FONT, "marginBottom": "0.4rem"}, className="theme-muted"),
        ], style={"marginTop": "0.6rem"}),
        html.Div([
            # StreetAccount News
            html.Div([
                html.Div("News Headlines", style={**LBL, "color": C["accent"],
                         "fontSize": "0.6rem", "marginBottom": "0.3rem"},
                         className="theme-label-accent"),
                html.Div(id="ssa-news-feed",
                         style={"maxHeight": "400px", "overflowY": "auto"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "2",
                      "minWidth": "300px"}),

            # SEC Filings
            html.Div([
                html.Div("SEC Filings", style={**LBL, "color": C["accent"],
                         "fontSize": "0.6rem", "marginBottom": "0.3rem"},
                         className="theme-label-accent"),
                html.Div(id="ssa-sec-filings",
                         style={"maxHeight": "400px", "overflowY": "auto"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1",
                      "minWidth": "220px"}),

            # Earnings Call Transcripts
            html.Div([
                html.Div("Earnings Call Transcripts", style={**LBL, "color": C["accent"],
                         "fontSize": "0.6rem", "marginBottom": "0.3rem"},
                         className="theme-label-accent"),
                html.Div(id="ssa-transcripts",
                         style={"maxHeight": "400px", "overflowY": "auto"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1",
                      "minWidth": "220px"}),
        ], style={"display": "flex", "gap": "0.6rem", "marginTop": "0.3rem"}),

    ], id="section-ssa", style={"display": "none"})

