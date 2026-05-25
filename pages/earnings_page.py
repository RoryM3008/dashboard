"""Layout — Earnings & Revisions page."""

from dash import dcc, html


def build_earnings_section(LBL, PANEL, C, FONT):
    return html.Div([
        # ── Stores ──────────────────────────────────────────────────────────
        dcc.Store(id="earn-data-store", data={}),
        dcc.Download(id="earn-dl-actuals"),
        dcc.Download(id="earn-dl-forward"),
        dcc.Download(id="earn-dl-revisions"),
        dcc.Download(id="earn-dl-recs"),
        dcc.Download(id="earn-dl-pt"),
        dcc.Download(id="earn-dl-recs-hist"),
        dcc.Download(id="earn-dl-fwd-table"),
        dcc.Download(id="earn-dl-price-react"),

        # ── Header / controls ────────────────────────────────────────────────
        html.Div([
            html.Div("Earnings & Revisions", style={**LBL, "color": C["accent"],
                     "fontSize": "0.72rem"}, className="theme-label-accent"),
            html.Div(
                "Historical actuals vs consensus · Forward estimates · Revision drift · Analyst recommendations",
                style={"color": C["muted"], "fontSize": "0.78rem",
                       "marginBottom": "0.8rem", "fontFamily": FONT},
                className="theme-muted",
            ),

            html.Div([
                # Ticker input
                html.Div([
                    html.Div("Company / Ticker", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Input(
                        id="earn-ticker",
                        type="text",
                        value="",
                        placeholder="e.g. WMT-US",
                        autoComplete="off",
                        className="theme-input",
                        style={
                            "width": "240px", "fontFamily": FONT, "fontSize": "0.82rem",
                            "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                            "borderRadius": "8px", "color": C["text"],
                            "padding": "0.55rem 0.85rem", "outline": "none",
                            "boxSizing": "border-box",
                        },
                    ),
                    html.Div(id="earn-ticker-suggestions", style={
                        "width": "240px", "marginTop": "0.35rem",
                        "display": "flex", "flexDirection": "column", "gap": "0.2rem",
                    }),
                ], style={"marginRight": "1.2rem"}),

                # Metric toggle
                html.Div([
                    html.Div("Metric", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    html.Div([
                        html.Button(label, id=f"earn-item-{val}", n_clicks=0,
                                    style={
                                        "backgroundColor": C["accent"] if val == "EPS" else C["panel"],
                                        "color": "#000" if val == "EPS" else C["text"],
                                        "border": f"1px solid {C['border']}",
                                        "borderRadius": "6px", "padding": "0.4rem 0.75rem",
                                        "fontFamily": FONT, "fontWeight": "700",
                                        "fontSize": "0.75rem", "cursor": "pointer",
                                    })
                        for label, val in [("EPS", "EPS"), ("Sales", "SALES"),
                                            ("EBITDA", "EBITDA"), ("EBIT", "EBIT"), ("DPS", "DPS")]
                    ], style={"display": "flex", "gap": "0.3rem"}),
                    dcc.Store(id="earn-item-store", data="EPS"),
                ], style={"marginRight": "1.2rem"}),

                # Periodicity toggle
                html.Div([
                    html.Div("Period", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    html.Div([
                        html.Button("Quarterly", id="earn-period-q", n_clicks=0,
                                    style={
                                        "backgroundColor": C["accent"], "color": "#000",
                                        "border": f"1px solid {C['border']}",
                                        "borderRadius": "6px", "padding": "0.4rem 0.75rem",
                                        "fontFamily": FONT, "fontWeight": "700",
                                        "fontSize": "0.75rem", "cursor": "pointer",
                                    }),
                        html.Button("Annual", id="earn-period-a", n_clicks=0,
                                    style={
                                        "backgroundColor": C["panel"], "color": C["text"],
                                        "border": f"1px solid {C['border']}",
                                        "borderRadius": "6px", "padding": "0.4rem 0.75rem",
                                        "fontFamily": FONT, "fontWeight": "700",
                                        "fontSize": "0.75rem", "cursor": "pointer",
                                    }),
                    ], style={"display": "flex", "gap": "0.3rem"}),
                    dcc.Store(id="earn-period-store", data="quarterly"),
                ], style={"marginRight": "1.2rem"}),

                # Load button + status
                html.Div([
                    html.Div(style={"height": "1.35rem"}),
                    html.Button("Load", id="earn-load-btn", n_clicks=0, style={
                        "backgroundColor": C["accent"], "color": "#000", "border": "none",
                        "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                        "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                        "cursor": "pointer",
                    }),
                    html.Div(id="earn-status",
                             style={"color": C["muted"], "fontSize": "0.72rem",
                                    "fontFamily": FONT, "marginTop": "0.4rem"},
                             className="theme-muted"),
                ]),
            ], style={"display": "flex", "alignItems": "flex-start",
                      "flexWrap": "wrap", "gap": "0.5rem"}),
        ], style={**PANEL, "padding": "1rem 1.5rem", "marginTop": "0.8rem"}),

        # ── Company header strip ─────────────────────────────────────────────
        html.Div(id="earn-header-strip", style={"marginTop": "0.6rem"}),

        # ── Revision scorecard chip strip ────────────────────────────────────
        html.Div(id="earn-revision-scorecard"),

        # ── Row 1: Actuals / Beat-Miss chart + Forward estimates ─────────────
        html.Div([
            html.Div([
                html.Div([
                    html.Div(id="earn-actuals-title",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    html.Button("⬇ xlsx", id="earn-dl-actuals-btn", n_clicks=0,
                                style={"backgroundColor": "transparent",
                                       "border": f"1px solid {C['border']}",
                                       "borderRadius": "5px", "color": C["subtext"],
                                       "fontFamily": FONT, "fontSize": "0.62rem",
                                       "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                       "flexShrink": "0", "opacity": "0.8"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                dcc.Graph(id="earn-actuals-chart",
                          config={"displayModeBar": False},
                          style={"height": "340px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1.4"}),

            html.Div([
                html.Div([
                    html.Div("Forward Consensus Estimates",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    html.Button("⬇ xlsx", id="earn-dl-forward-btn", n_clicks=0,
                                style={"backgroundColor": "transparent",
                                       "border": f"1px solid {C['border']}",
                                       "borderRadius": "5px", "color": C["subtext"],
                                       "fontFamily": FONT, "fontSize": "0.62rem",
                                       "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                       "flexShrink": "0", "opacity": "0.8"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                dcc.Graph(id="earn-forward-chart",
                          config={"displayModeBar": False},
                          style={"height": "340px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1"}),
        ], style={"display": "flex", "gap": "0.6rem", "marginTop": "0.6rem"}),

        # ── Row 1.5: Price Reaction on Earnings Day + NTM P/E time series ────
        html.Div([
            html.Div([
                html.Div([
                    html.Div("Price Reaction on Earnings Day",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    html.Button("⬇ xlsx", id="earn-dl-price-react-btn", n_clicks=0,
                                style={"backgroundColor": "transparent",
                                       "border": f"1px solid {C['border']}",
                                       "borderRadius": "5px", "color": C["subtext"],
                                       "fontFamily": FONT, "fontSize": "0.62rem",
                                       "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                       "flexShrink": "0", "opacity": "0.8"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                html.Div("Day-of stock return for each earnings release, coloured by beat (green) / miss (red).",
                         style={"color": C["muted"], "fontSize": "0.68rem",
                                "fontFamily": FONT, "marginBottom": "0.3rem"},
                         className="theme-muted"),
                dcc.Graph(id="earn-price-reaction-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1.4"}),

            html.Div([
                html.Div([
                    html.Div(id="earn-ntm-panel-title",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    dcc.Dropdown(
                        id="earn-ntm-view-dd",
                        options=[
                            {"label": "NTM P/E",       "value": "ntm_pe"},
                            {"label": "4W Rev %",      "value": "rev_4w"},
                            {"label": "13W Rev %",     "value": "rev_13w"},
                            {"label": "52W Rev %",     "value": "rev_52w"},
                        ],
                        value="ntm_pe",
                        clearable=False,
                        style={
                            "width": "130px", "fontSize": "0.72rem",
                            "backgroundColor": C["bg"],
                            "color": C["text"], "border": f"1px solid {C['border']}",
                        },
                    ),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                html.Div(id="earn-ntm-panel-subtitle",
                         style={"color": C["muted"], "fontSize": "0.68rem",
                                "fontFamily": FONT, "marginBottom": "0.3rem"},
                         className="theme-muted"),
                dcc.Graph(id="earn-ntm-pe-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1"}),
        ], style={"display": "flex", "gap": "0.6rem", "marginTop": "0.6rem"}),

        # ── Row 2: Revision drift + Recommendations ──────────────────────────
        html.Div([
            html.Div([
                html.Div([
                    html.Div("Estimate Revision History",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    html.Button("⬇ xlsx", id="earn-dl-revisions-btn", n_clicks=0,
                                style={"backgroundColor": "transparent",
                                       "border": f"1px solid {C['border']}",
                                       "borderRadius": "5px", "color": C["subtext"],
                                       "fontFamily": FONT, "fontSize": "0.62rem",
                                       "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                       "flexShrink": "0", "opacity": "0.8"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                html.Div("How analyst consensus has drifted over time for each forward fiscal year.",
                         style={"color": C["muted"], "fontSize": "0.68rem",
                                "fontFamily": FONT, "marginBottom": "0.3rem"},
                         className="theme-muted"),
                dcc.Graph(id="earn-revisions-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1.4"}),

            html.Div([
                html.Div([
                    html.Div("Analyst Recommendations",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    html.Button("⬇ xlsx", id="earn-dl-recs-btn", n_clicks=0,
                                style={"backgroundColor": "transparent",
                                       "border": f"1px solid {C['border']}",
                                       "borderRadius": "5px", "color": C["subtext"],
                                       "fontFamily": FONT, "fontSize": "0.62rem",
                                       "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                       "flexShrink": "0", "opacity": "0.8"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                dcc.Graph(id="earn-recs-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1"}),
        ], style={"display": "flex", "gap": "0.6rem", "marginTop": "0.6rem"}),

        # ── Row 3: Price target history + Recommendation history ────────────
        html.Div([
            html.Div([
                html.Div([
                    html.Div("Analyst Price Target History",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    html.Button("⬇ xlsx", id="earn-dl-pt-btn", n_clicks=0,
                                style={"backgroundColor": "transparent",
                                       "border": f"1px solid {C['border']}",
                                       "borderRadius": "5px", "color": C["subtext"],
                                       "fontFamily": FONT, "fontSize": "0.62rem",
                                       "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                       "flexShrink": "0", "opacity": "0.8"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                html.Div("Consensus mean PT (line) with high/low range (band) vs current price.",
                         style={"color": C["muted"], "fontSize": "0.68rem",
                                "fontFamily": FONT, "marginBottom": "0.3rem"},
                         className="theme-muted"),
                dcc.Graph(id="earn-pt-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1.4"}),

            html.Div([
                html.Div([
                    html.Div("Recommendation History",
                             style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                             className="theme-label-accent"),
                    html.Button("⬇ xlsx", id="earn-dl-recs-hist-btn", n_clicks=0,
                                style={"backgroundColor": "transparent",
                                       "border": f"1px solid {C['border']}",
                                       "borderRadius": "5px", "color": C["subtext"],
                                       "fontFamily": FONT, "fontSize": "0.62rem",
                                       "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                       "flexShrink": "0", "opacity": "0.8"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "0.3rem"}),
                html.Div("Buy / Overweight / Hold / Underweight / Sell split over 24 months.",
                         style={"color": C["muted"], "fontSize": "0.68rem",
                                "fontFamily": FONT, "marginBottom": "0.3rem"},
                         className="theme-muted"),
                dcc.Graph(id="earn-recs-history-chart",
                          config={"displayModeBar": False},
                          style={"height": "300px"}),
            ], style={**PANEL, "padding": "1rem 1.2rem", "flex": "1"}),
        ], style={"display": "flex", "gap": "0.6rem", "marginTop": "0.6rem"}),

        # ── Row 4: Forward estimates summary table ───────────────────────────
        html.Div([
            html.Div([
                html.Div("Forward Estimates Summary",
                         style={**LBL, "color": C["accent"], "fontSize": "0.6rem"},
                         className="theme-label-accent"),
                html.Button("⬇ xlsx", id="earn-dl-fwd-table-btn", n_clicks=0,
                            style={"backgroundColor": "transparent",
                                   "border": f"1px solid {C['border']}",
                                   "borderRadius": "5px", "color": C["subtext"],
                                   "fontFamily": FONT, "fontSize": "0.62rem",
                                   "padding": "0.18rem 0.5rem", "cursor": "pointer",
                                   "flexShrink": "0", "opacity": "0.8"}),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "alignItems": "center", "marginBottom": "0.5rem"}),
            html.Div(id="earn-fwd-table", style={"overflowX": "auto"}),
        ], style={**PANEL, "padding": "1rem 1.5rem", "marginTop": "0.6rem"}),

    ], id="section-earnings", style={"display": "none"})
