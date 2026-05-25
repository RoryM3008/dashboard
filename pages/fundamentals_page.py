"""Fundamentals page — comprehensive annual metrics table + comparison + charts."""

from dash import dcc, html

# ── Metric group definitions ─────────────────────────────────────────────────
# Each entry: (display_label, column_name, format_type)
# format_type: "pct" | "x" | "ps" | "days" | "large" | "ratio" | "raw"

METRIC_GROUPS = {
    "Profitability": [
        ("Gross Margin %",          "GROSS_MARGIN",                "pct"),
        ("SG&A / Sales %",          "SGA_TO_SALES",                "pct"),
        ("Operating Margin %",      "OPERATING_MARGIN",            "pct"),
        ("Pre-Tax Margin %",        "PRETAX_MARGIN",               "pct"),
        ("Net Margin %",            "NET_MARGIN",                  "pct"),
        ("FCF Margin %",            "FREE_CASH_FLOW_MARGIN",       "pct"),
        ("FCF Conversion",          "FCF_CONVERSION_RATIO",        "ratio"),
        ("CapEx / Sales %",         "CAPEX_TO_SALES",              "pct"),
        ("Return on Assets %",      "RETURN_ON_ASSETS",            "pct"),
        ("Return on Equity %",      "RETURN_ON_EQUITY",            "pct"),
        ("ROCE %",                  "RETURN_ON_COMMON_EQUITY",     "pct"),
        ("ROTC %",                  "RETURN_ON_TOTAL_CAPITAL",     "pct"),
        ("ROIC %",                  "RETURN_ON_INVESTED_CAPITAL",  "pct"),
        ("CF ROIC %",               "CASH_FLOW_ROIC",              "pct"),
    ],
    "Valuation": [
        ("P/Sales",                 "PRICE_TO_SALES",              "x"),
        ("P/Earnings",              "PRICE_TO_EARNINGS",           "x"),
        ("P/Book",                  "PRICE_TO_BOOK",               "x"),
        ("P/Tang Book",             "PRICE_TO_TANGIBLE_BOOK",      "x"),
        ("P/Cash Flow",             "PRICE_TO_CASH_FLOW",          "x"),
        ("P/FCF",                   "PRICE_TO_FREE_CASH_FLOW",     "x"),
        ("Dividend Yield %",        "DIVIDEND_YIELD_PCT",          "pct"),
        ("EV / EBIT",               "EV_TO_EBIT",                  "x"),
        ("EV / EBITDA",             "EV_TO_EBITDA",                "x"),
        ("EV / Sales",              "EV_TO_SALES",                 "x"),
        ("Total Debt / EV %",       "TOTAL_DEBT_TO_EV",            "pct"),
    ],
    "Per Share": [
        ("Sales / Share",           "SALES_PER_SHARE",             "ps"),
        ("EBIT / Share",            "EBIT_PER_SHARE",              "ps"),
        ("EPS (Recurring)",         "EPS_RECURRING",               "ps"),
        ("EPS (Basic)",             "EPS_BASIC",                   "ps"),
        ("EPS (Diluted)",           "EPS_DILUTED",                 "ps"),
        ("DPS",                     "DIVIDENDS_PER_SHARE",         "ps"),
        ("Payout Ratio %",          "DIVIDEND_PAYOUT_RATIO",       "pct"),
        ("Book Value / Share",      "BOOK_VALUE_PER_SHARE",        "ps"),
        ("Tang BV / Share",         "TANGIBLE_BV_PER_SHARE",       "ps"),
        ("CF / Share",              "CASH_FLOW_PER_SHARE",         "ps"),
        ("FCF / Share",             "FREE_CASH_FLOW_PER_SHARE",    "ps"),
        ("Diluted Shares (M)",      "DILUTED_SHARES_M",            "large"),
        ("Basic Shares (M)",        "BASIC_SHARES_M",              "large"),
        ("Total Shares (M)",        "TOTAL_SHARES_M",              "large"),
    ],
    "DuPont": [
        ("Asset Turnover",          "ASSET_TURNOVER",              "ratio"),
        ("Pre-Tax Margin %",        "PRETAX_MARGIN",               "pct"),
        ("Pre-Tax ROA %",           "PRETAX_ROA",                  "pct"),
        ("Tax Rate %",              "TAX_RATE",                    "pct"),
        ("Tax Rate Complement",     "TAX_RATE_COMPLEMENT",         "ratio"),
        ("ROA %",                   "RETURN_ON_ASSETS",            "pct"),
        ("Equity Multiplier",       "EQUITY_MULTIPLIER",           "ratio"),
        ("ROE %",                   "RETURN_ON_EQUITY",            "pct"),
        ("Earnings Retention",      "EARNINGS_RETENTION",          "ratio"),
        ("Reinvestment Rate",       "REINVESTMENT_RATE",           "ratio"),
        ("EBIT ROA %",              "EBIT_ROA",                    "pct"),
    ],
    "Efficiency": [
        ("Revenue / Employee",      "REVENUE_PER_EMPLOYEE",        "large"),
        ("Net Income / Employee",   "NET_INCOME_PER_EMPLOYEE",     "large"),
        ("Assets / Employee",       "ASSETS_PER_EMPLOYEE",         "large"),
        ("Receivables Turnover",    "RECEIVABLES_TURNOVER",        "ratio"),
        ("Inventory Turnover",      "INVENTORY_TURNOVER",          "ratio"),
        ("Payables Turnover",       "PAYABLES_TURNOVER_PROXY",     "ratio"),
        ("Asset Turnover",          "ASSET_TURNOVER",              "ratio"),
        ("Working Capital Turnover","WORKING_CAPITAL_TURNOVER",    "ratio"),
        ("Days Inventory (DIO)",    "DAYS_INVENTORY_ON_HAND",      "days"),
        ("Days Sales Out. (DSO)",   "DAYS_SALES_OUTSTANDING",      "days"),
        ("Operating Cycle",         "OPERATING_CYCLE",             "days"),
        ("Days Payables Out. (DPO)","DAYS_PAYABLES_OUTSTANDING",   "days"),
        ("Net Operating Cycle",     "NET_OPERATING_CYCLE",         "days"),
    ],
    "Liquidity": [
        ("Current Ratio",           "CURRENT_RATIO",               "ratio"),
        ("Quick Ratio",             "QUICK_RATIO",                 "ratio"),
        ("Cash Ratio",              "CASH_RATIO",                  "ratio"),
        ("Cash % Curr Assets",      "CASH_ST_INV_PCT_CURR_ASSETS", "pct"),
        ("CFO / Curr Liabilities",  "CFO_TO_CURRENT_LIABILITIES",  "ratio"),
    ],
    "Coverage": [
        ("Net Debt / EBITDA",            "NET_DEBT_TO_EBITDA",                  "ratio"),
        ("Net Debt / (EBITDA-CapEx)",    "NET_DEBT_TO_EBITDA_MINUS_CAPEX",      "ratio"),
        ("Total Debt / EBITDA",          "TOTAL_DEBT_TO_EBITDA",                "ratio"),
        ("EBIT Interest Coverage",       "EBIT_INTEREST_COVERAGE",              "ratio"),
        ("EBITDA Interest Coverage",     "EBITDA_INTEREST_COVERAGE",            "ratio"),
        ("Fixed Charge Coverage",        "FIXED_CHARGE_COVERAGE",               "ratio"),
        ("CFO Interest Coverage",        "CFO_INTEREST_COVERAGE",               "ratio"),
        ("Cash Dividend Coverage",       "CASH_DIVIDEND_COVERAGE",              "ratio"),
        ("LT Debt / EBITDA",             "LT_DEBT_TO_EBITDA",                   "ratio"),
        ("Net Debt / FFO",               "NET_DEBT_TO_FFO",                     "ratio"),
        ("LT Debt / FFO",                "LT_DEBT_TO_FFO",                      "ratio"),
        ("FCF / Total Debt",             "FCF_TO_TOTAL_DEBT",                   "ratio"),
        ("CFO / Total Debt",             "CFO_TO_TOTAL_DEBT",                   "ratio"),
        ("Total Debt / EBIT",            "TOTAL_DEBT_TO_EBIT",                  "ratio"),
        ("Net Debt / EBIT",              "NET_DEBT_TO_EBIT",                    "ratio"),
        ("(EBITDA-CapEx) / Interest",    "EBITDA_MINUS_CAPEX_INT_COVERAGE",     "ratio"),
    ],
    "Leverage": [
        ("LT Debt / Equity",             "LT_DEBT_TO_EQUITY",                   "pct"),
        ("LT Debt / Total Cap %",        "LT_DEBT_TO_TOTAL_CAPITAL",            "pct"),
        ("LT Debt / Total Assets %",     "LT_DEBT_TO_TOTAL_ASSETS",             "pct"),
        ("Total Debt / Assets %",        "TOTAL_DEBT_TO_ASSETS",                "pct"),
        ("Net Debt / Equity %",          "NET_DEBT_TO_EQUITY",                  "pct"),
        ("Total Debt / Equity",          "TOTAL_DEBT_TO_EQUITY",                "ratio"),
        ("Net Debt / Total Cap %",       "NET_DEBT_TO_TOTAL_CAPITAL",           "pct"),
        ("Total Debt / Total Cap",       "TOTAL_DEBT_TO_TOTAL_CAPITAL",         "ratio"),
    ],
    "Asset Analysis": [
        ("Total Assets",                 "TOTAL_ASSETS",                        "large"),
        ("Cash % Assets",                "CASH_ST_INV_PCT_ASSETS",              "pct"),
        ("Receivables % Assets",         "RECEIVABLES_PCT_ASSETS",              "pct"),
        ("Inventories % Assets",         "INVENTORIES_PCT_ASSETS",              "pct"),
        ("Current Assets % Assets",      "CURRENT_ASSETS_PCT_ASSETS",           "pct"),
        ("Fixed Assets % Assets",        "FIXED_ASSETS_PCT_ASSETS",             "pct"),
    ],
}

CATEGORY_ORDER = [
    "Profitability", "Valuation", "Per Share",
    "DuPont", "Efficiency", "Liquidity",
    "Coverage", "Leverage", "Asset Analysis",
]


def _inp_style(C, FONT, width="260px"):
    return {
        "width": width, "fontFamily": FONT, "fontSize": "0.82rem",
        "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
        "borderRadius": "8px", "color": C["text"],
        "padding": "0.55rem 0.85rem", "outline": "none",
        "boxSizing": "border-box",
    }


def build_fundamentals_section(LBL, PANEL, C, FONT):
    """Fundamentals deep-dive: table + comparison + chart grid."""

    cat_buttons = []
    for i, cat in enumerate(CATEGORY_ORDER):
        cat_buttons.append(
            html.Button(cat, id=f"fund-cat-{cat.lower().replace(' ', '-')}",
                        n_clicks=0,
                        style={
                            "backgroundColor": C["accent"] if i == 0 else C["panel"],
                            "color": "#000" if i == 0 else C["muted"],
                            "border": f"1px solid {C['border']}",
                            "borderRadius": "4px",
                            "padding": "0.3rem 0.75rem",
                            "fontFamily": FONT, "fontWeight": "700",
                            "fontSize": "0.68rem", "cursor": "pointer",
                            "marginRight": "4px", "marginBottom": "4px",
                        })
        )

    def _toolbar_btn(label, bid, accent=False):
        return html.Button(label, id=bid, n_clicks=0, style={
            "backgroundColor": C["accent"] if accent else C["panel"],
            "color": "#000" if accent else C["muted"],
            "border": f"1px solid {C['border']}",
            "borderRadius": "6px", "padding": "0.38rem 0.9rem",
            "fontFamily": FONT, "fontWeight": "700",
            "fontSize": "0.70rem", "cursor": "pointer",
        })

    return html.Div([
        html.Div("Fundamentals", style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                 className="theme-label-accent"),

        # ── Row 1: Ticker A + controls ────────────────────────────────────
        html.Div([
            # Company A input
            html.Div([
                html.Div("Ticker / Company", style={**LBL, "marginBottom": "0.2rem"},
                         className="theme-label"),
                dcc.Input(id="fund-ticker", type="text", value="AAPL-US",
                          placeholder="Type ticker…", autoComplete="off",
                          className="theme-input", style=_inp_style(C, FONT)),
                html.Div(id="fund-ticker-suggestions",
                         style={"width": "260px", "marginTop": "0.3rem",
                                "display": "flex", "flexDirection": "column", "gap": "0.2rem"}),
            ], style={"marginRight": "0.8rem"}),

            # From FY
            html.Div([
                html.Div("From FY", style={**LBL, "marginBottom": "0.2rem", "fontSize": "0.62rem"},
                         className="theme-label"),
                dcc.Input(id="fund-year-from", type="number", value=2005,
                          min=1990, max=2030, step=1,
                          style={**_inp_style(C, FONT, "80px"), "textAlign": "center"}),
            ], style={"marginRight": "0.8rem"}),

            # Load button
            html.Div([
                html.Div("\u00a0", style={"marginBottom": "0.2rem", "fontSize": "0.62rem"}),
                html.Button("Load", id="fund-load-btn", n_clicks=0, style={
                    "backgroundColor": C["accent"], "color": "#000", "border": "none",
                    "borderRadius": "8px", "padding": "0.55rem 1.4rem",
                    "fontFamily": FONT, "fontWeight": "700", "fontSize": "0.82rem",
                    "cursor": "pointer",
                }),
            ], style={"marginRight": "0.8rem"}),

            # Compare toggle
            html.Div([
                html.Div("\u00a0", style={"marginBottom": "0.2rem", "fontSize": "0.62rem"}),
                _toolbar_btn("⇄ Compare", "fund-compare-toggle"),
            ], style={"marginRight": "0.6rem"}),

            # View mode: Table | Chart | Bar
            html.Div([
                html.Div("View", style={**LBL, "marginBottom": "0.2rem", "fontSize": "0.62rem"},
                         className="theme-label"),
                html.Div([
                    _toolbar_btn("Table",   "fund-view-table-btn", accent=True),
                    html.Span(style={"width": "4px", "display": "inline-block"}),
                    _toolbar_btn("Chart",   "fund-view-chart-btn"),
                    html.Span(style={"width": "4px", "display": "inline-block"}),
                    _toolbar_btn("Bar",     "fund-view-bar-btn"),
                ], style={"display": "flex"}),
            ], style={"marginRight": "0.8rem"}),

            # Export
            html.Div([
                html.Div("\u00a0", style={"marginBottom": "0.2rem", "fontSize": "0.62rem"}),
                html.Button("\u2193 Excel", id="fund-export-btn", n_clicks=0, style={
                    "backgroundColor": C["panel"], "color": C["muted"],
                    "border": f"1px solid {C['border']}",
                    "borderRadius": "6px", "padding": "0.38rem 0.9rem",
                    "fontFamily": FONT, "fontWeight": "700",
                    "fontSize": "0.70rem", "cursor": "pointer",
                }),
                dcc.Download(id="fund-dl"),
            ], style={"marginRight": "0.6rem"}),

            # Status
            html.Div(id="fund-status",
                     style={"color": C["muted"], "fontSize": "0.74rem",
                            "fontFamily": FONT, "alignSelf": "flex-end",
                            "paddingBottom": "0.2rem"},
                     className="theme-muted"),

        ], style={"display": "flex", "alignItems": "flex-start",
                  "flexWrap": "wrap", "gap": "0rem", "marginBottom": "0.8rem"}),

        # ── Row 2: Compare ticker B (collapsed by default) ────────────────
        html.Div([
            html.Div([
                html.Div("vs Company", style={**LBL, "marginBottom": "0.2rem",
                                               "color": "#4db8ff"}, className="theme-label"),
                dcc.Input(id="fund-ticker-b", type="text", value="",
                          placeholder="Type ticker to compare…", autoComplete="off",
                          className="theme-input",
                          style={**_inp_style(C, FONT), "border": "1px solid #4db8ff66"}),
                html.Div(id="fund-ticker-b-suggestions",
                         style={"width": "260px", "marginTop": "0.3rem",
                                "display": "flex", "flexDirection": "column", "gap": "0.2rem"}),
            ]),
            html.Div("Enter ticker B and click Load to compare.",
                     style={"color": "#4db8ff66", "fontSize": "0.72rem",
                            "fontFamily": FONT, "alignSelf": "flex-end",
                            "paddingBottom": "0.25rem", "marginLeft": "1rem"}),
        ], id="fund-compare-row",
           style={"display": "none", "alignItems": "flex-start",
                  "flexWrap": "wrap", "gap": "0.8rem",
                  "marginBottom": "0.8rem", "padding": "0.65rem 0.9rem",
                  "border": "1px solid #4db8ff33",
                  "borderRadius": "8px", "backgroundColor": "#0d1420"}),

        # ── Bar chart year selector (hidden until bar view active) ─────────
        html.Div([
            html.Span("Compare year:", style={
                "fontFamily": FONT, "fontSize": "0.72rem",
                "color": C["muted"], "marginRight": "0.6rem",
            }),
            dcc.Dropdown(
                id="fund-cmp-year-dd",
                options=[], value=None, clearable=False,
                style={
                    "width": "100px", "fontSize": "0.78rem",
                    "backgroundColor": C["panel"], "color": C["text"],
                    "border": f"1px solid {C['border']}",
                },
            ),
        ], id="fund-cmp-year-row",
           style={"display": "none", "alignItems": "center",
                  "marginBottom": "0.6rem"}),

        # ── Category selector ─────────────────────────────────────────────
        html.Div(cat_buttons, style={"marginBottom": "0.75rem",
                                      "display": "flex", "flexWrap": "wrap"}),

        # ── Content area ──────────────────────────────────────────────────
        html.Div(id="fund-table-container",
                 style={"overflowX": "auto",
                        "backgroundColor": "#0a0a0a",
                        "border": f"1px solid {C['border']}",
                        "borderRadius": "8px",
                        "padding": "0.5rem"}),

        # ── Stores ───────────────────────────────────────────────────────
        dcc.Store(id="fund-data",         data={}),
        dcc.Store(id="fund-data-b",       data={}),
        dcc.Store(id="fund-name-a",       data=""),
        dcc.Store(id="fund-name-b",       data=""),
        dcc.Store(id="fund-category",     data="Profitability"),
        dcc.Store(id="fund-compare-mode", data=False),
        dcc.Store(id="fund-view-mode",    data="table"),
        dcc.Store(id="fund-cmp-year",     data=None),

    ], id="section-fundamentals", style={"display": "none"})
