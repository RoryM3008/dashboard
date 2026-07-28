"""
Stock Dashboard
===============
Run with:  python Dash.py
Then open: http://127.0.0.1:8051

Dependencies (install once):
    pip install dash dash-bootstrap-components yfinance pandas feedparser requests plotly
"""

import os

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ClientsideFunction

# -- Shared constants ---------------------------------------------------------
from theme import (
    C, FONT, PANEL, LBL,
    NAV_BTN, NAV_BTN_ACTIVE,
    MAIN_MENU_BTN, MAIN_MENU_BTN_ACTIVE,
    PERIODS,
    DARK, LIGHT, get_theme,
    _panel, _lbl, _main_menu_btn, _main_menu_btn_active,
)

# -- Page section builders ----------------------------------------------------
from pages.dashboard_page import build_dashboard_section
from pages.news_page import build_news_section
from pages.analyser_page import build_analyser_section
from pages.screener_page import build_screener_section
from pages.correlation_page import build_correlation_section
from pages.performance_page import build_performance_section
from pages.watchlist_page import build_watchlist_section
from pages.markets_page import build_markets_section
from pages.stock_moves_page import build_stock_moves_section
from pages.port_page import build_port_section
from pages.prices_page import build_prices_section
from pages.risk_page import build_risk_section
from pages.heatmap_page import build_heatmap_section
from pages.spread_page import build_spread_section
from pages.ssa_page import build_ssa_section
from pages.peers_page import build_peers_section
from pages.valuations_page import build_valuations_section
from pages.fundamentals_page import build_fundamentals_section
from pages.earnings_page import build_earnings_section
from pages.calendar_page import build_calendar_section
from pages.factor_tilt_page import build_factor_tilt_section
from pages.comps_page import build_comps_section
from pages.mylist_page import build_mylist_section
import snowflake_data as _sf_mod

# -- Callback modules (each has register_callbacks(app)) ----------------------
from callbacks import (
    navigation,
    dashboard_cb,
    analyser_cb,
    screener_cb,
    correlation_cb,
    performance_cb,
    watchlist_cb,
    markets_cb,
    stock_moves_cb,
    port_cb,
    prices_cb,
    risk_cb,
    heatmap_cb,
    spread_cb,
    ssa_cb,
    peers_cb,
    valuations_cb,
    fundamentals_cb,
    earnings_cb,
    calendar_cb,
    factor_tilt_cb,
    comps_cb,
    mylist_cb,
)

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;600;700;800&display=swap",
    ],
    title="Stock Dashboard",
    suppress_callback_exceptions=True,
)

# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
app.layout = html.Div(id="root-container", style={
    "backgroundColor": C["bg"],
    "minHeight": "100vh",
    "padding": "1.75rem 2rem",
    "fontFamily": FONT,
    "color": C["text"],
}, children=[

    # Theme store (persists in browser localStorage)
    dcc.Store(id="theme-store", data="dark", storage_type="local"),
    # Datasource: 'sf' = Snowflake/FactSet, 'yf' = yfinance (offline mode)
    dcc.Store(id="datasource", data=("sf" if _sf_mod.SF_AVAILABLE else "yf"), storage_type="local"),

    # Title bar
    html.Div([
        html.Div("\U0001F4C8", style={"fontSize": "1.9rem"}),
        html.Div([
            html.H1("Investment Dashboard", id="title-text",
                     style={"margin": 0, "fontFamily": FONT, "fontWeight": "800",
                            "fontSize": "1.7rem", "color": C["text"]}),
            html.Div("Live market \u00b7 Earnings \u00b7 News \u00b7 Stock Analyser",
                     id="subtitle-text",
                     style={"color": C["subtext"], "fontSize": "0.75rem",
                            "marginTop": "2px", "fontFamily": FONT}),
        ]),
        html.Div(style={"flex": "1"}),
        html.Button("🌙", id="theme-toggle", n_clicks=0,
                     title="Toggle dark / light mode"),
        html.Button("🔌 SF", id="datasource-toggle", n_clicks=0,
                     title="Toggle data source: Snowflake ↔ yfinance (offline)",
                     style={"backgroundColor": "#00cc66", "color": "#000",
                            "border": "none", "borderRadius": "6px",
                            "padding": "0.35rem 0.7rem", "fontFamily": FONT,
                            "fontWeight": "700", "fontSize": "0.72rem",
                            "cursor": "pointer", "marginLeft": "0.4rem"}),
        html.Div(id="last-updated",
                 style={"marginLeft": "0.75rem", "color": C["muted"],
                        "fontSize": "0.7rem", "alignSelf": "flex-end", "fontFamily": FONT},
                 className="theme-muted"),
    ], style={"display": "flex", "alignItems": "center", "gap": "1rem", "marginBottom": "1.5rem"}),

    # Hidden holdings input (still used by callbacks)
    dcc.Input(id="ticker-input", type="text",
              placeholder="e.g. AAPL, MSFT, TSLA, NVDA", debounce=False,
              style={"display": "none"}),
    html.Button("Refresh", id="refresh-btn", n_clicks=0,
                style={"display": "none"}),

    # Menu button + overlay
    html.Button("☰ Menu", id="menu-toggle-btn", n_clicks=0,
                style={"position": "fixed", "top": "1.2rem", "right": "1.2rem",
                       "zIndex": "1000", "backgroundColor": C["accent"], "color": "#000",
                       "border": "none", "borderRadius": "8px",
                       "padding": "0.5rem 1rem", "fontFamily": FONT,
                       "fontWeight": "700", "fontSize": "0.82rem", "cursor": "pointer",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.4)"}),

    # Slide-out menu overlay
    html.Div([
        html.Div([
            html.Div("Navigate", style={**LBL, "marginBottom": "0.6rem"},
                     className="theme-label"),
            html.Button("Dashboard",      id="menu-dashboard",    n_clicks=0, style=MAIN_MENU_BTN_ACTIVE),
            html.Button("News",           id="menu-news",         n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Stock Analyser", id="menu-analyser",     n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Screener",       id="menu-screener",     n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Correlation",    id="menu-correlation",  n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Performance",    id="menu-performance",  n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("My Stocks",      id="menu-mylist",       n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Watchlist",      id="menu-watchlist",    n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Markets",        id="menu-markets",      n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Stock Moves",    id="menu-stock-moves",  n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Portfolio",      id="menu-port",         n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Prices",         id="menu-prices",       n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Risk",           id="menu-risk",         n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Heatmap",        id="menu-heatmap",      n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Spread",         id="menu-spread",       n_clicks=0, style=MAIN_MENU_BTN),
            html.Hr(style={"borderColor": C["border"], "margin": "0.3rem 0"}),
            html.Div("Stock Analysis", style={**LBL, "fontSize": "0.68rem",
                     "color": C["accent"], "marginBottom": "0.1rem"},
                     className="theme-label-accent"),
            html.Button("Overview",           id="menu-ssa",         n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Financial Statements", id="menu-financials", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Peers", id="menu-peers", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Valuations", id="menu-valuations", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Fundamentals", id="menu-fundamentals", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Earnings & Revisions", id="menu-earnings", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Earnings Calendar", id="menu-calendar", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Factor Tilt", id="menu-factor-tilt", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Button("Comps Table", id="menu-comps", n_clicks=0,
                        style={**MAIN_MENU_BTN, "paddingLeft": "1.4rem", "fontSize": "0.72rem"}),
            html.Hr(style={"borderColor": C["border"], "margin": "0.6rem 0"}),
            html.Div("Holdings", style={**LBL, "marginBottom": "0.3rem"},
                     className="theme-label"),
            dcc.Input(id="menu-ticker-input", type="text",
                      placeholder="e.g. AAPL, MSFT, TSLA", debounce=True,
                      className="theme-input",
                      style={"backgroundColor": C["bg"], "border": f"1px solid {C['border']}",
                             "borderRadius": "6px", "color": C["text"],
                             "padding": "0.4rem 0.6rem", "fontFamily": FONT,
                             "fontSize": "0.78rem", "width": "100%", "outline": "none",
                             "boxSizing": "border-box"}),
        ], style={**PANEL, "width": "220px", "padding": "1rem",
                  "display": "flex", "flexDirection": "column", "gap": "0.4rem",
                  "maxHeight": "90vh", "overflowY": "auto"}),
    ], id="menu-overlay",
       style={"position": "fixed", "top": "0", "right": "-280px",
              "width": "280px", "height": "100vh", "zIndex": "999",
              "display": "flex", "alignItems": "flex-start",
              "paddingTop": "3.5rem", "paddingRight": "1rem",
              "justifyContent": "center",
              "transition": "right 0.25s ease"}),

    # Backdrop (click to close)
    html.Div(id="menu-backdrop", n_clicks=0,
             style={"display": "none", "position": "fixed", "top": "0", "left": "0",
                    "width": "100vw", "height": "100vh", "zIndex": "998",
                    "backgroundColor": "rgba(0,0,0,0.5)"}),

    dcc.Store(id="active-main-menu", data="dashboard"),
    dcc.Store(id="menu-open", data=False),

    # Page sections (full width now)
    html.Div([
        build_dashboard_section(LBL, PANEL),
        build_news_section(LBL, PANEL),
        build_analyser_section(LBL, PANEL, C, FONT, NAV_BTN_ACTIVE, NAV_BTN, PERIODS),
        build_screener_section(LBL, PANEL, C, FONT),
        build_correlation_section(LBL, PANEL, C, FONT),
        build_performance_section(LBL, PANEL, C, FONT),
        build_watchlist_section(LBL, PANEL, C, FONT),
        build_markets_section(LBL, PANEL, C, FONT),
        build_stock_moves_section(LBL, PANEL, C, FONT),
        build_port_section(LBL, PANEL, C, FONT),
        build_prices_section(LBL, PANEL, C, FONT),
        build_risk_section(LBL, PANEL, C, FONT),
        build_heatmap_section(LBL, PANEL, C, FONT),
        build_spread_section(LBL, PANEL, C, FONT),
        build_ssa_section(LBL, PANEL, C, FONT),
        build_peers_section(LBL, PANEL, C, FONT),
        build_valuations_section(LBL, PANEL, C, FONT),
        build_fundamentals_section(LBL, PANEL, C, FONT),
        build_earnings_section(LBL, PANEL, C, FONT),
        build_calendar_section(LBL, PANEL, C, FONT),
        build_factor_tilt_section(LBL, PANEL, C, FONT),
        build_comps_section(LBL, PANEL, C, FONT),
        build_mylist_section(LBL, PANEL, C, FONT),
    ], style={"width": "100%"}),

    dcc.Interval(id="auto-refresh", interval=5 * 60 * 1000, n_intervals=0),
])

# -----------------------------------------------------------------------------
# Register all callbacks
# -----------------------------------------------------------------------------
navigation.register_callbacks(app)
dashboard_cb.register_callbacks(app)
analyser_cb.register_callbacks(app)
screener_cb.register_callbacks(app)
correlation_cb.register_callbacks(app)
performance_cb.register_callbacks(app)
watchlist_cb.register_callbacks(app)
markets_cb.register_callbacks(app)
stock_moves_cb.register_callbacks(app)
port_cb.register_callbacks(app)
prices_cb.register_callbacks(app)
risk_cb.register_callbacks(app)
heatmap_cb.register_callbacks(app)
spread_cb.register_callbacks(app)
ssa_cb.register_callbacks(app)
peers_cb.register_callbacks(app)
valuations_cb.register_callbacks(app)
fundamentals_cb.register_callbacks(app)
earnings_cb.register_callbacks(app)
calendar_cb.register_callbacks(app)
factor_tilt_cb.register_callbacks(app, C=C, FONT=FONT)
comps_cb.register_callbacks(app)
mylist_cb.register_callbacks(app)

# ── Theme toggle callback ────────────────────────────────────────────────────

@app.callback(
    Output("theme-store", "data"),
    Output("theme-toggle", "children"),
    Input("theme-toggle", "n_clicks"),
    State("theme-store", "data"),
)
def toggle_theme(n, current):
    if not n:
        # Initial load — return stored value (or default)
        mode = current or "dark"
    else:
        mode = "light" if current == "dark" else "dark" 
    icon = "☀️" if mode == "dark" else "🌙"
    return mode, icon


@app.callback(
    Output("root-container", "style"),
    Output("root-container", "className"),
    Output("title-text", "style"),
    Output("subtitle-text", "style"),
    Input("theme-store", "data"),
)
def restyle_shell(mode):
    c = get_theme(mode)
    root_style = {
        "backgroundColor": c["bg"],
        "minHeight": "100vh",
        "padding": "1.25rem 1.5rem",
        "fontFamily": FONT,
        "color": c["text"],
    }
    body_class = "light-mode" if mode == "light" else "dark-mode"
    title_style = {"margin": 0, "fontFamily": FONT, "fontWeight": "800",
                   "fontSize": "1.7rem", "color": c["text"]}
    subtitle_style = {"color": c["subtext"], "fontSize": "0.75rem",
                      "marginTop": "2px", "fontFamily": FONT}
    return root_style, body_class, title_style, subtitle_style

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("DASH_PORT", "8051"))
    print("\n  Stock Dashboard")
    print("  ----------------------------------------")

    # Pre-connect to Snowflake (SSO login happens here, before Dash starts).
    # If unreachable (e.g. at home without VPN), skip silently → offline/yfinance mode.
    import snowflake_data as _sf_mod
    try:
        from snowflake_data import _get_connection
        print("  Connecting to Snowflake (SSO)...")
        _get_connection()
        print("  [OK] Snowflake connected")
    except Exception as e:
        _sf_mod.SF_AVAILABLE = False
        print(f"  [WARN] Snowflake unavailable - running in offline (yfinance) mode: {e}")

    print(f"  Open your browser at -> http://127.0.0.1:{port}\n")
    debug_mode = os.getenv("DASH_DEBUG", "0") == "1"
    app.run(debug=debug_mode, port=port, use_reloader=False)
