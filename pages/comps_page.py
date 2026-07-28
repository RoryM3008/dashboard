"""Layout — Comps Table page.

A multi-group comparable-companies table with LTM + 1BF/2BF forward
consensus metrics. Includes preset peer groups (Japanese apparel,
sportswear, food services, grocery retail; Europe & U.S. equivalents)
and free-form ticker entry.
"""

from dash import dcc, html


# ─────────────────────────────────────────────────────────────────────────────
# Preset peer groups (FactSet TICKER-REGION format)
# ─────────────────────────────────────────────────────────────────────────────
PEER_GROUPS = {
    # ── Japan ──────────────────────────────────────────────────────────
    "JP_APPAREL": {
        "label": "Japanese Apparel Retailers",
        "tickers": [
            "9983-JP",   # Fast Retailing
            "7453-JP",   # Ryohin Keikaku (Muji)
        ],
    },
    "JP_SPORTSWEAR": {
        "label": "Japanese Sportswear",
        "tickers": [
            "7936-JP",   # Asics
            "8022-JP",   # Mizuno
            "7906-JP",   # Yonex
        ],
    },
    "JP_FOOD_SERVICES": {
        "label": "Japan Food Services",
        "tickers": [
            "3563-JP",   # Food & Life (Sushiro)
            "2695-JP",   # Kura Sushi
            "7581-JP",   # Saizeriya
            "7550-JP",   # Zensho
            "3097-JP",   # Monogatari Corp
            "3197-JP",   # Skylark Holdings
            "9936-JP",   # Ohsho Food Service (Onsho proxy)
        ],
    },
    "JP_GROCERY": {
        "label": "Japanese Grocery Retailers",
        "tickers": [
            "7532-JP",   # PPIH (Pan Pacific International / Don Quijote)
            "8267-JP",   # Aeon
            "3382-JP",   # Seven & i
            "141A-JP",   # Trial Holdings
            "8273-JP",   # Izumi
            "3038-JP",   # Kobe Bussan
            "8194-JP",   # Life Corp
            "3349-JP",   # Cosmos Pharmaceutical
            "3088-JP",   # Matsukiyococokara
            "9989-JP",   # Sundrug
            "7649-JP",   # Sugi Holdings
            "3549-JP",   # Kusuri no Aoki
        ],
    },
    # ── Europe ─────────────────────────────────────────────────────────
    "EU_APPAREL": {
        "label": "Europe Apparel Retailers",
        "tickers": [
            "ITX-ES",    # Inditex
            "HMB-SE",    # H&M
        ],
    },
    "EU_SPORTSWEAR": {
        "label": "Europe Sportswear",
        "tickers": [
            "ADS-DE",    # Adidas
            "PUM-DE",    # Puma
        ],
    },
    "EU_FOOD_SERVICES": {
        "label": "Europe Food Services",
        "tickers": [
            "CPG-GB",    # Compass Group
            "ELIOR-FR",  # Elior
            "EAT-PL",    # AmRest
        ],
    },
    "EU_GROCERY": {
        "label": "Europe Grocery Retailers",
        "tickers": [
            "CA-FR",     # Carrefour
            "TSCO-GB",   # Tesco
        ],
    },
    # ── United States ──────────────────────────────────────────────────
    "US_APPAREL": {
        "label": "U.S. Apparel Retailers",
        "tickers": [
            "GAP-US",    # Gap
            "ANF-US",    # Abercrombie & Fitch
            "AEO-US",    # American Eagle
            "RL-US",     # Ralph Lauren
        ],
    },
    "US_SPORTSWEAR": {
        "label": "U.S. Sportswear",
        "tickers": [
            "NKE-US",    # Nike
            "LULU-US",   # Lululemon
            "UAA-US",    # Under Armour
            "AS-US",     # Amer Sports
            "ONON-US",   # On Holding
            "DECK-US",   # Deckers
        ],
    },
    "US_FOOD_SERVICES": {
        "label": "U.S. Food Services",
        "tickers": [
            "MCD-US",    # McDonald's
            "CMG-US",    # Chipotle
            "DRI-US",    # Darden
        ],
    },
    "US_GROCERY": {
        "label": "US Grocery Retailers",
        "tickers": [
            "WMT-US",    # Walmart
            "COST-US",   # Costco
            "TGT-US",    # Target
        ],
    },
}

# Default selection — order they appear in the source table
DEFAULT_GROUPS = [
    "JP_APPAREL", "JP_SPORTSWEAR", "JP_FOOD_SERVICES", "JP_GROCERY",
    "EU_APPAREL", "EU_SPORTSWEAR", "EU_FOOD_SERVICES", "EU_GROCERY",
    "US_APPAREL", "US_SPORTSWEAR", "US_FOOD_SERVICES", "US_GROCERY",
]


def build_comps_section(LBL, PANEL, C, FONT):
    """Comps Table — multi-group comparable companies analysis."""

    btn_style = {
        "backgroundColor": C["accent"], "color": "#000",
        "border": "none", "borderRadius": "8px",
        "padding": "0.55rem 1.3rem", "fontFamily": FONT,
        "fontWeight": "700", "fontSize": "0.84rem",
        "cursor": "pointer",
    }

    group_options = [
        {"label": meta["label"], "value": code}
        for code, meta in PEER_GROUPS.items()
    ]

    return html.Div([
        # ── Header ───────────────────────────────────────────────────────
        html.Div("Comps Table",
                 style={**LBL, "color": C["accent"], "fontSize": "0.72rem"},
                 className="theme-label-accent"),
        html.Div(
            "Side-by-side comparable-companies analysis with LTM and forward "
            "(1BF / 2BF) consensus multiples. Pick one or more preset peer "
            "groups, or add custom tickers (FactSet format e.g. 9983-JP, NKE-US).",
            style={"color": C["muted"], "fontSize": "0.78rem",
                   "marginBottom": "0.9rem", "fontFamily": FONT},
            className="theme-muted",
        ),

        # ── Controls row ─────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Div("Peer Group(s)", style={**LBL, "marginBottom": "0.3rem"},
                         className="theme-label"),
                dcc.Dropdown(
                    id="comps-groups",
                    options=group_options,
                    value=["JP_APPAREL", "JP_SPORTSWEAR"],
                    multi=True,
                    clearable=False,
                    style={"minWidth": "420px", "fontSize": "0.82rem"},
                ),
            ]),
            html.Div([
                html.Div("Custom tickers (added as a separate group)",
                         style={**LBL, "marginBottom": "0.3rem"},
                         className="theme-label"),
                dcc.Input(
                    id="comps-custom-input",
                    type="text",
                    value="",
                    placeholder="e.g. 9983-JP, NKE-US, LULU-US",
                    debounce=True,
                    className="theme-input",
                    style={
                        "width": "420px", "fontFamily": FONT, "fontSize": "0.82rem",
                        "backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                        "borderRadius": "8px", "color": C["text"],
                        "padding": "0.55rem 0.85rem", "outline": "none",
                        "boxSizing": "border-box",
                    },
                ),
            ]),
            html.Button("Load Comps", id="comps-load-btn", n_clicks=0,
                        style=btn_style),
            html.Button("Load All Groups", id="comps-load-all-btn", n_clicks=0,
                        style={**btn_style,
                               "backgroundColor": "#0f2d0f",
                               "color": C["accent"],
                               "border": f"1px solid {C['accent']}"}),
        ], style={"display": "flex", "gap": "0.8rem",
                  "alignItems": "flex-end", "flexWrap": "wrap",
                  "marginBottom": "0.6rem"}),

        # ── Status ───────────────────────────────────────────────────────
        html.Div(id="comps-status",
                 style={"color": C["muted"], "fontSize": "0.75rem",
                        "fontFamily": FONT, "marginBottom": "0.6rem"},
                 className="theme-muted"),

        # ── Output area (one block per peer group) ───────────────────────
        html.Div(id="comps-output"),

    ], id="section-comps", style={"display": "none"})
