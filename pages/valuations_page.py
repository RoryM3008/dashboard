from dash import dcc, html

# ── Metric groups ────────────────────────────────────────────────────────────
# All LTM daily metrics come from FF_BASIC_DER_LTM + FF_ADVANCED_DER_LTM (joined).
# Annual metrics come from FF_BASIC_DER_AF and are shown as bar charts.

VALUATION_METRICS = [
    # ── Valuation multiples (LTM daily) ─────────────────────────────────
    {"label": "── Valuation Multiples (LTM) ──────────────────",  "value": "_hdr1", "disabled": True},
    {"label": "P/E  —  Price / Earnings",                        "value": "P/E"},
    {"label": "P/S  —  Price / Sales",                           "value": "P/S"},
    {"label": "EV/S  —  Enterprise Value / Sales",               "value": "EV/S"},
    {"label": "EV/EBITDA  —  Enterprise Value / EBITDA",         "value": "EV/EBITDA"},
    {"label": "EV/EBIT  —  Enterprise Value / EBIT",             "value": "EV/EBIT"},
    {"label": "P/CF  —  Price / Cash Flow",                      "value": "P/CF"},
    {"label": "P/BV  —  Price / Book Value  (Annual)",           "value": "P/Book"},
    # ── Yield metrics (LTM daily, Advanced table) ───────────────────────
    {"label": "── Yield Metrics (LTM) ────────────────────────",  "value": "_hdr2", "disabled": True},
    {"label": "Dividend Yield %",                                 "value": "Div Yield %"},
    {"label": "FCFE Yield %",                                     "value": "FCF Yield %"},
    {"label": "CFO/EV %",                                         "value": "CFO/EV %"},
    {"label": "FCFF/EV %",                                        "value": "FCFF/EV %"},
    # ── Margin metrics (LTM daily, Basic table) ─────────────────────────
    {"label": "── Margin Metrics (LTM) ───────────────────────",  "value": "_hdr3", "disabled": True},
    {"label": "Gross Margin %",                                   "value": "Gross Margin %"},
    {"label": "Operating Margin %",                              "value": "Oper Margin %"},
    {"label": "Net Margin %",                                     "value": "Net Margin %"},
    {"label": "Pre-Tax Margin %",                                 "value": "PreTax Margin %"},
    {"label": "FCF Margin %  (Annual)",                          "value": "FCF Margin %"},
    {"label": "EBITDA Margin %  (Advanced)",                     "value": "EBITDA Margin %"},
    {"label": "EBIT Margin %  (Advanced)",                       "value": "EBIT Margin %"},
    {"label": "SG&A % of Sales  (LTM)",                          "value": "SGA % Sales"},
    {"label": "SG&A % of Sales  (Annual)",                       "value": "SGA % Sales (Ann)"},
    {"label": "R&D % of Sales  (Advanced)",                      "value": "RD % Sales"},
    # ── Growth metrics (LTM daily, Advanced table) ──────────────────────
    {"label": "── Growth Metrics (LTM) ───────────────────────",  "value": "_hdr4", "disabled": True},
    {"label": "Sales Growth %",                                   "value": "Sales Growth %"},
    {"label": "Operating Income Growth %",                       "value": "Oper Inc Growth %"},
    {"label": "Net Income Growth %",                             "value": "Net Inc Growth %"},
    {"label": "EPS (Diluted) Growth %",                          "value": "EPS Growth %"},
    {"label": "DPS Growth %",                                     "value": "DPS Growth %"},
    # ── Cash flow metrics (LTM daily, Advanced table) ───────────────────
    {"label": "── Cash Flow Metrics (LTM) ────────────────────",  "value": "_hdr5", "disabled": True},
    {"label": "CapEx % of Sales",                                 "value": "Capex % Sales"},
    {"label": "Cash Flow % of Sales",                            "value": "CF % Sales"},
    {"label": "Effective Tax Rate %",                            "value": "Tax Rate %"},
    {"label": "Payout Ratio %  (LTM)",                           "value": "Payout Ratio %"},
    # ── Annual balance sheet / returns (FF_BASIC_DER_AF) ────────────────
    {"label": "── Annual Metrics (Fiscal Year) ────────────────", "value": "_hdr6", "disabled": True},
    {"label": "Return on Equity %  (Annual)",                    "value": "ROE %"},
    {"label": "Return on Assets %  (Annual)",                    "value": "ROA %"},
    {"label": "Return on Total Capital %  (Annual)",             "value": "ROTC %"},
    {"label": "Net Debt / EBITDA  (Annual)",                     "value": "Net Debt/EBITDA"},
    {"label": "Debt / Assets  (Annual)",                         "value": "Debt/Assets %"},
    {"label": "Current Ratio  (Annual)",                         "value": "Current Ratio"},
    {"label": "Quick Ratio  (Annual)",                           "value": "Quick Ratio"},
]

# Metrics sourced from FF_BASIC_DER_AF and displayed as annual bar charts
ANNUAL_METRICS = {
    "P/Book",
    "Gross Margin %", "Oper Margin %", "Net Margin %", "PreTax Margin %",
    "FCF Margin %", "SGA % Sales (Ann)",
    "ROE %", "ROA %", "ROTC %",
    "Net Debt/EBITDA", "Debt/Assets %", "Current Ratio", "Quick Ratio",
}
# Keep old name as alias for backward compat in callback
ANNUAL_MARGIN_METRICS = ANNUAL_METRICS


def build_valuations_section(LBL, PANEL, C, FONT):
    """Valuation history page — time-series chart of selected valuation metric."""

    return html.Div([
        html.Div("Valuation History",
                 style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                 className="theme-label-accent"),

        # ── Ticker input row ─────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Div("Ticker / Company", style={**LBL, "marginBottom": "0.2rem"},
                         className="theme-label"),
                dcc.Input(
                    id="val-ticker",
                    type="text",
                    value="AAPL-US",
                    placeholder="Type ticker or company name…",
                    autoComplete="off",
                    className="theme-input",
                    style={
                        "width": "380px", "fontFamily": FONT, "fontSize": "0.82rem",
                        "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                        "borderRadius": "8px", "color": C["text"],
                        "padding": "0.55rem 0.85rem", "outline": "none",
                        "boxSizing": "border-box",
                    },
                ),
                html.Div(id="val-ticker-suggestions", style={
                    "width": "380px", "marginTop": "0.35rem",
                    "display": "flex", "flexDirection": "column", "gap": "0.2rem",
                }),
            ], style={"marginRight": "1rem"}),

            html.Button("Load", id="val-load-btn", n_clicks=0, style={
                "backgroundColor": C["accent"], "color": "#000", "border": "none",
                "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                "cursor": "pointer", "marginTop": "1.1rem",
            }),

            html.Div(id="val-status",
                     style={"color": C["muted"], "fontSize": "0.75rem",
                            "fontFamily": FONT, "marginTop": "1.3rem",
                            "marginLeft": "1rem"},
                     className="theme-muted"),
        ], style={"display": "flex", "alignItems": "flex-start",
                  "marginBottom": "0.8rem"}),

        # ── Metric selector + period toggle ──────────────────────────────
        html.Div([
            html.Div([
                html.Div("Metric", style={**LBL, "marginBottom": "0.2rem",
                                          "fontSize": "0.62rem"},
                         className="theme-label"),
                dcc.Dropdown(
                    id="val-metric",
                    options=VALUATION_METRICS,
                    value="P/E",
                    clearable=False,
                    searchable=False,
                    style={"width": "300px", "fontFamily": FONT, "fontSize": "0.78rem"},
                    className="ssa-bbg-dropdown",
                ),
            ], style={"marginRight": "1.2rem"}),

            html.Div([
                html.Div("History", style={**LBL, "marginBottom": "0.2rem",
                                            "fontSize": "0.62rem"},
                         className="theme-label"),
                html.Div([
                    html.Button(p, id=f"val-period-{p.lower()}", n_clicks=0,
                                style={
                                    "backgroundColor": C["panel"] if p != "5Y" else C["accent"],
                                    "color": "#000" if p == "5Y" else C["muted"],
                                    "border": f"1px solid {C['border']}",
                                    "borderRadius": "4px", "padding": "0.28rem 0.7rem",
                                    "fontFamily": FONT, "fontWeight": "700",
                                    "fontSize": "0.68rem", "cursor": "pointer",
                                    "marginRight": "3px",
                                })
                    for p in ["1Y", "3Y", "5Y", "10Y", "MAX"]
                ], style={"display": "flex"}),
            ]),
        ], style={"display": "flex", "alignItems": "flex-end",
                  "marginBottom": "0.6rem"}),

        # ── Summary stats bar ─────────────────────────────────────────────
        html.Div(id="val-summary-bar", style={"marginBottom": "0.5rem"}),
        # ── Price overlay toggle ──────────────────────────────────────────
        html.Div([
            dcc.Checklist(
                id="val-show-price",
                options=[{"label": "  Overlay share price", "value": "price"}],
                value=[],
                inline=True,
                style={"fontFamily": FONT, "fontSize": "0.74rem", "color": "#aaa"},
            ),
        ], style={"marginBottom": "0.4rem"}),
        # ── Main chart ────────────────────────────────────────────────────
        html.Div([
            dcc.Graph(
                id="val-chart",
                config={"displayModeBar": False, "scrollZoom": False},
                style={"height": "440px"},
            ),
        ], style={
            "backgroundColor": "#0a0a0a", "borderRadius": "8px",
            "border": f"1px solid {C['border']}", "padding": "0.5rem",
        }),

        # ── All-metrics snapshot table ────────────────────────────────────
        html.Div([
            html.Div("Current Snapshot — All Metrics",
                     style={**LBL, "color": C["accent"], "fontSize": "0.62rem",
                            "marginBottom": "0.5rem"},
                     className="theme-label-accent"),
            html.Div(id="val-snapshot-table"),
        ], style={
            **PANEL, "padding": "0.8rem 1rem", "marginTop": "0.6rem",
        }),

        # Hidden stores
        dcc.Store(id="val-data", data={}),
        dcc.Store(id="val-annual-data", data=[]),
        dcc.Store(id="val-price-data", data=[]),
        dcc.Store(id="val-period", data="5Y"),

    ], id="section-valuations", style={"display": "none"})
