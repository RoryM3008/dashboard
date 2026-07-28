"""Layout — Earnings Calendar page."""

from dash import dcc, html


def build_calendar_section(LBL, PANEL, C, FONT):
    def _toggle_btn(label, btn_id, active=False):
        return html.Button(
            label, id=btn_id, n_clicks=0,
            style={
                "backgroundColor": C["accent"] if active else C["panel"],
                "color": "#000" if active else C["text"],
                "border": f"1px solid {C['border']}",
                "borderRadius": "6px", "padding": "0.4rem 0.85rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.75rem", "cursor": "pointer",
            }
        )

    return html.Div([
        dcc.Store(id="cal-data-store", data={}),
        dcc.Store(id="cal-raw-store", data={}),
        dcc.Store(id="cal-window-store", data=14),
        dcc.Store(id="cal-region-store", data="ALL"),
        dcc.Store(id="cal-mktcap-store", data="ALL"),
        dcc.Store(id="cal-sector-store", data=[]),
        dcc.Download(id="cal-dl"),

        # ── Header ───────────────────────────────────────────────────────────
        html.Div([
            html.Div("Earnings Calendar", style={**LBL, "color": C["accent"],
                     "fontSize": "0.72rem"}, className="theme-label-accent"),
            html.Div(
                "Upcoming earnings releases · Scheduled report dates · Consensus EPS & Sales estimates",
                style={"color": C["muted"], "fontSize": "0.78rem",
                       "marginBottom": "0.8rem", "fontFamily": FONT},
                className="theme-muted",
            ),

            # Controls row
            html.Div([
                # Window toggle
                html.Div([
                    html.Div("Window", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    html.Div([
                        _toggle_btn("This Week",  "cal-w7",  False),
                        _toggle_btn("2 Weeks",    "cal-w14", True),
                        _toggle_btn("1 Month",    "cal-w30", False),
                    ], style={"display": "flex", "gap": "0.3rem"}),
                ], style={"marginRight": "1.5rem"}),

                # Region toggle
                html.Div([
                    html.Div("Region", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    html.Div([
                        _toggle_btn("All",    "cal-r-all", True),
                        _toggle_btn("US",     "cal-r-us",  False),
                        _toggle_btn("Europe", "cal-r-eur", False),
                        _toggle_btn("UK",     "cal-r-gb",  False),
                    ], style={"display": "flex", "gap": "0.3rem"}),
                ], style={"marginRight": "1.5rem"}),

                # Market cap filter
                html.Div([
                    html.Div("Market Cap", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    html.Div([
                        _toggle_btn("All",       "cal-mc-all",   True),
                        _toggle_btn("Mega (>$100B)",  "cal-mc-mega",  False),
                        _toggle_btn("Large ($10-100B)", "cal-mc-large", False),
                        _toggle_btn("Mid ($2-10B)",  "cal-mc-mid",   False),
                        _toggle_btn("Small (<$2B)",  "cal-mc-small",  False),
                    ], style={"display": "flex", "gap": "0.3rem", "flexWrap": "wrap"}),
                ], style={"marginRight": "1.5rem"}),

                # Sector multi-select dropdown
                html.Div([
                    html.Div("Sector", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Dropdown(
                        id="cal-sector-dd",
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="All sectors",
                        clearable=True,
                        style={"width": "260px", "fontSize": "0.75rem",
                               "backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}"},
                    ),
                ], style={"marginRight": "1.5rem"}),

                # Industry multi-select dropdown
                html.Div([
                    html.Div("Industry", style={**LBL, "marginBottom": "0.2rem",
                             "fontSize": "0.65rem"}, className="theme-label"),
                    dcc.Dropdown(
                        id="cal-industry-dd",
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="All industries",
                        clearable=True,
                        style={"width": "260px", "fontSize": "0.75rem",
                               "backgroundColor": C["bg"],
                               "border": f"1px solid {C['border']}"},
                    ),
                ], style={"marginRight": "1.5rem"}),
                html.Div([
                    html.Div(style={"height": "1.35rem"}),
                    html.Div([
                        html.Button("Refresh", id="cal-load-btn", n_clicks=0, style={
                            "backgroundColor": C["accent"], "color": "#000",
                            "border": "none", "borderRadius": "8px",
                            "padding": "0.55rem 1.2rem", "fontFamily": FONT,
                            "fontWeight": "700", "fontSize": "0.82rem",
                            "cursor": "pointer", "marginRight": "0.5rem",
                        }),
                        html.Button("⬇ xlsx", id="cal-dl-btn", n_clicks=0, style={
                            "backgroundColor": "transparent",
                            "border": f"1px solid {C['border']}",
                            "borderRadius": "5px", "color": C["subtext"],
                            "fontFamily": FONT, "fontSize": "0.75rem",
                            "padding": "0.5rem 0.85rem", "cursor": "pointer",
                        }),
                    ], style={"display": "flex", "alignItems": "center"}),
                ]),

                html.Div(style={"flex": "1"}),

                # Status
                html.Div(id="cal-status",
                         style={"color": C["muted"], "fontSize": "0.72rem",
                                "fontFamily": FONT, "alignSelf": "flex-end",
                                "paddingBottom": "0.15rem"},
                         className="theme-muted"),
            ], style={"display": "flex", "alignItems": "flex-end",
                      "flexWrap": "wrap", "gap": "0.5rem"}),
        ], style={**PANEL, "padding": "1rem 1.5rem", "marginTop": "0.8rem"}),

        # ── Summary chips ─────────────────────────────────────────────────────
        html.Div(id="cal-summary-strip", style={"marginTop": "0.5rem"}),

        # ── Calendar table ────────────────────────────────────────────────────
        html.Div([
            html.Div(id="cal-table-content",
                     style={"overflowX": "auto", "minHeight": "200px"}),
        ], style={**PANEL, "padding": "1rem 1.5rem", "marginTop": "0.6rem"}),

    ], id="section-calendar", style={"display": "none"})
