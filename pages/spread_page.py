"""Layout — Spread Analysis page: Bloomberg HS <GO> replica.

Single-screen, two-column layout:
  LEFT  (70%) — Price overlay chart (top) + Spread time series (bottom)
  RIGHT (30%) — Statistics table   (top) + Histogram           (bottom)
Controls bar pinned to the top.
"""

from dash import dcc, html


def build_spread_section(LBL, PANEL, C, FONT):
    # ── compact input style ──────────────────────────────────────────
    _inp = {
        "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
        "borderRadius": "4px", "color": C["text"], "fontFamily": FONT,
        "padding": "0.3rem 0.55rem", "fontSize": "0.78rem", "outline": "none",
    }
    _lbl = {**LBL, "marginBottom": "2px", "fontSize": "0.65rem",
            "letterSpacing": "0.04em"}

    return html.Div([
        html.Div([
            # ═══════════════════ CONTROL BAR ═══════════════════════════
            html.Div([
                html.Div("HS", style={
                    "color": "#ff8c00", "fontWeight": "800", "fontSize": "1rem",
                    "fontFamily": "Consolas, monospace", "marginRight": "0.6rem",
                    "alignSelf": "center",
                }),
                # Asset A
                html.Div([
                    html.Div("ASSET A", style={**_lbl, "color": C["green"]}),
                    dcc.Input(id="spread-leg-a", type="text",
                              placeholder="Ticker", style={**_inp, "width": "90px"}),
                ]),
                html.Div([
                    html.Div("×", style={**_lbl, "color": C["muted"]}),
                    dcc.Input(id="spread-mult-a", type="number", value=1,
                              step=0.01, style={**_inp, "width": "52px"}),
                ]),
                html.Div("−", style={"color": C["accent"], "fontWeight": "800",
                                      "fontSize": "1.1rem", "alignSelf": "center",
                                      "margin": "0 0.15rem"}),
                # Asset B
                html.Div([
                    html.Div("ASSET B", style={**_lbl, "color": C["red"]}),
                    dcc.Input(id="spread-leg-b", type="text",
                              placeholder="Ticker", style={**_inp, "width": "90px"}),
                ]),
                html.Div([
                    html.Div("×", style={**_lbl, "color": C["muted"]}),
                    dcc.Input(id="spread-mult-b", type="number", value=1,
                              step=0.01, style={**_inp, "width": "52px"}),
                ]),
                # Divider
                html.Div(style={"borderLeft": f"1px solid {C['border']}",
                                "height": "28px", "alignSelf": "center",
                                "margin": "0 0.4rem"}),
                # Spread type
                html.Div([
                    html.Div("TYPE", style=_lbl),
                    dcc.Dropdown(id="spread-type", options=[
                        {"label": "A − B", "value": "diff"},
                        {"label": "A / B", "value": "ratio"},
                        {"label": "Z-Score", "value": "zscore"},
                        {"label": "Indexed", "value": "indexed"},
                    ], value="diff", clearable=False,
                    style={"width": "95px", "fontSize": "0.76rem"}),
                ]),
                # History
                html.Div([
                    html.Div("PERIOD", style=_lbl),
                    dcc.Dropdown(id="spread-history", options=[
                        {"label": "6M", "value": "6mo"},
                        {"label": "1Y", "value": "1y"},
                        {"label": "2Y", "value": "2y"},
                        {"label": "3Y", "value": "3y"},
                        {"label": "5Y", "value": "5y"},
                        {"label": "MAX", "value": "max"},
                        {"label": "Custom", "value": "custom"},
                    ], value="2y", clearable=False,
                    style={"width": "85px", "fontSize": "0.76rem"}),
                ]),
                # Custom date range (hidden until "Custom" selected)
                html.Div([
                    html.Div("FROM", style=_lbl),
                    dcc.DatePickerSingle(id="spread-date-start",
                        placeholder="Start",
                        style={"fontSize": "0.74rem"}),
                ], id="spread-date-start-wrap",
                   style={"display": "none"}),
                html.Div([
                    html.Div("TO", style=_lbl),
                    dcc.DatePickerSingle(id="spread-date-end",
                        placeholder="End",
                        style={"fontSize": "0.74rem"}),
                ], id="spread-date-end-wrap",
                   style={"display": "none"}),
                # Frequency
                html.Div([
                    html.Div("FREQ", style=_lbl),
                    dcc.Dropdown(id="spread-freq", options=[
                        {"label": "D", "value": "daily"},
                        {"label": "W", "value": "weekly"},
                        {"label": "M", "value": "monthly"},
                    ], value="daily", clearable=False,
                    style={"width": "58px", "fontSize": "0.76rem"}),
                ]),
                # Z-window
                html.Div([
                    html.Div("Z-WIN", style=_lbl),
                    dcc.Input(id="spread-zscore-window", type="number", value=60,
                              min=5, step=1, style={**_inp, "width": "50px"}),
                ]),
                # Go button
                html.Button("GO", id="spread-run", n_clicks=0, style={
                    "backgroundColor": "#ff8c00", "color": "#000", "border": "none",
                    "borderRadius": "3px", "padding": "0.35rem 1.2rem",
                    "fontFamily": "Consolas, monospace", "fontWeight": "800",
                    "fontSize": "0.85rem", "cursor": "pointer", "alignSelf": "flex-end",
                    "letterSpacing": "0.05em",
                }),
            ], style={
                "display": "flex", "gap": "0.45rem", "flexWrap": "wrap",
                "alignItems": "flex-end", "padding": "0.45rem 0.5rem",
                "backgroundColor": "rgba(255,140,0,0.06)",
                "borderBottom": f"1px solid {C['border']}",
                "borderRadius": "4px 4px 0 0",
            }),

            # Status bar
            html.Div(id="spread-status", style={
                "color": C["muted"], "fontSize": "0.68rem", "fontFamily": FONT,
                "padding": "0.25rem 0.5rem",
                "borderBottom": f"1px solid {C['border']}",
            }),

            # ═══════════════════ MAIN BODY: 2-COLUMN ══════════════════
            html.Div([

                # ── LEFT COLUMN (charts) ──────────────────────────────
                html.Div([
                    html.Div(id="spread-price-chart"),
                    html.Div(id="spread-series-chart"),
                    html.Div(id="spread-relative-chart"),
                ], style={
                    "flex": "7", "minWidth": "400px",
                    "display": "flex", "flexDirection": "column",
                    "gap": "2px",
                }),

                # ── RIGHT COLUMN (stats + histogram) ─────────────────
                html.Div([
                    html.Div(id="spread-stats-table", style={
                        "borderBottom": f"1px solid {C['border']}",
                        "paddingBottom": "0.3rem",
                    }),
                    html.Div(id="spread-histogram"),
                ], style={
                    "flex": "3", "minWidth": "260px",
                    "display": "flex", "flexDirection": "column",
                    "gap": "2px",
                }),

            ], style={
                "display": "flex", "gap": "2px",
                "flex": "1", "overflow": "hidden",
            }),

        ], style={
            **PANEL,
            "display": "flex", "flexDirection": "column",
            "padding": "0",
            "height": "calc(100vh - 180px)",
            "overflow": "hidden",
        }, className="theme-panel"),
    ], id="section-spread", style={"display": "none"})
