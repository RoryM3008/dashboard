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
from pages.port_page import build_port_section
from pages.prices_page import build_prices_section
from pages.risk_page import build_risk_section
from pages.heatmap_page import build_heatmap_section
from pages.spread_page import build_spread_section

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
    port_cb,
    prices_cb,
    risk_cb,
    heatmap_cb,
    spread_cb,
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
        html.Div(id="last-updated",
                 style={"marginLeft": "0.75rem", "color": C["muted"],
                        "fontSize": "0.7rem", "alignSelf": "flex-end", "fontFamily": FONT},
                 className="theme-muted"),
    ], style={"display": "flex", "alignItems": "center", "gap": "1rem", "marginBottom": "1.5rem"}),

    # Holdings input
    html.Div([
        html.Div("Your Holdings", style=LBL, id="holdings-label", className="theme-label"),
        html.Div([
            dcc.Input(id="ticker-input", type="text",
                      placeholder="e.g. AAPL, MSFT, TSLA, NVDA", debounce=False,
                      className="theme-input",
                      style={"backgroundColor": C["bg"], "border": f"1px solid {C['accent']}",
                             "borderRadius": "8px", "color": C["text"],
                             "padding": "0.55rem 1rem", "fontFamily": FONT,
                             "fontSize": "0.85rem", "flex": "1", "outline": "none"}),
            html.Button("Refresh", id="refresh-btn", n_clicks=0,
                        style={"backgroundColor": C["accent"], "color": "#000",
                               "border": "none", "borderRadius": "8px",
                               "padding": "0.55rem 1.4rem", "fontFamily": FONT,
                               "fontWeight": "700", "fontSize": "0.85rem", "cursor": "pointer"}),
        ], style={"display": "flex", "gap": "0.75rem"}),
        html.Div("Enter tickers separated by commas, then click Refresh.",
                 style={"color": C["muted"], "fontSize": "0.68rem",
                        "marginTop": "0.4rem", "fontFamily": FONT},
                 className="theme-muted"),
    ], id="holdings-panel", style=PANEL, className="theme-panel"),

    # Sidebar menu + page sections
    html.Div([
        # Sidebar
        html.Div([
            html.Div("Menu", style={**LBL, "marginBottom": "0.5rem"}, id="sidebar-label",
                     className="theme-label"),
            html.Button("Dashboard",      id="menu-dashboard",    n_clicks=0, style=MAIN_MENU_BTN_ACTIVE),
            html.Button("News",           id="menu-news",         n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Stock Analyser", id="menu-analyser",     n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Screener",       id="menu-screener",     n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Correlation",    id="menu-correlation",  n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Performance",    id="menu-performance",  n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Watchlist",      id="menu-watchlist",    n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Markets",        id="menu-markets",      n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Portfolio",      id="menu-port",         n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Prices",        id="menu-prices",      n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Risk",          id="menu-risk",        n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Heatmap",       id="menu-heatmap",     n_clicks=0, style=MAIN_MENU_BTN),
            html.Button("Spread",        id="menu-spread",      n_clicks=0, style=MAIN_MENU_BTN),
            dcc.Store(id="active-main-menu", data="dashboard"),
        ], id="sidebar-panel", className="theme-panel", style={**PANEL, "width": "220px", "padding": "0.9rem", "display": "flex",
                  "flexDirection": "column", "gap": "0.45rem", "position": "sticky", "top": "1rem"}),

        # Page sections (one visible at a time)
        html.Div([
            build_dashboard_section(LBL, PANEL),
            build_news_section(LBL, PANEL),
            build_analyser_section(LBL, PANEL, C, FONT, NAV_BTN_ACTIVE, NAV_BTN, PERIODS),
            build_screener_section(LBL, PANEL, C, FONT),
            build_correlation_section(LBL, PANEL, C, FONT),
            build_performance_section(LBL, PANEL, C, FONT),
            build_watchlist_section(LBL, PANEL, C, FONT),
            build_markets_section(LBL, PANEL, C, FONT),
            build_port_section(LBL, PANEL, C, FONT),
            build_prices_section(LBL, PANEL, C, FONT),
            build_risk_section(LBL, PANEL, C, FONT),
            build_heatmap_section(LBL, PANEL, C, FONT),
            build_spread_section(LBL, PANEL, C, FONT),
        ], style={"flex": "1", "minWidth": "280px"}),
    ], style={"display": "flex", "gap": "1rem", "alignItems": "flex-start", "flexWrap": "wrap"}),

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
port_cb.register_callbacks(app)
prices_cb.register_callbacks(app)
risk_cb.register_callbacks(app)
heatmap_cb.register_callbacks(app)
spread_cb.register_callbacks(app)

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
    Output("holdings-panel", "style"),
    Output("sidebar-panel", "style"),
    Output("ticker-input", "style"),
    Output("title-text", "style"),
    Output("subtitle-text", "style"),
    Input("theme-store", "data"),
)
def restyle_shell(mode):
    c = get_theme(mode)
    root_style = {
        "backgroundColor": c["bg"],
        "minHeight": "100vh",
        "padding": "1.75rem 2rem",
        "fontFamily": FONT,
        "color": c["text"],
    }
    body_class = "light-mode" if mode == "light" else "dark-mode"
    panel = _panel(c)
    sidebar = {**_panel(c), "width": "220px", "padding": "0.9rem", "display": "flex",
               "flexDirection": "column", "gap": "0.45rem", "position": "sticky", "top": "1rem"}
    inp_style = {
        "backgroundColor": c["bg"], "border": f"1px solid {c['accent']}",
        "borderRadius": "8px", "color": c["text"],
        "padding": "0.55rem 1rem", "fontFamily": FONT,
        "fontSize": "0.85rem", "flex": "1", "outline": "none",
    }
    title_style = {"margin": 0, "fontFamily": FONT, "fontWeight": "800",
                   "fontSize": "1.7rem", "color": c["text"]}
    subtitle_style = {"color": c["subtext"], "fontSize": "0.75rem",
                      "marginTop": "2px", "fontFamily": FONT}
    return root_style, body_class, panel, sidebar, inp_style, title_style, subtitle_style

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("DASH_PORT", "8051"))
    print("\n  Stock Dashboard")
    print("  ----------------------------------------")
    print(f"  Open your browser at -> http://127.0.0.1:{port}\n")
    debug_mode = os.getenv("DASH_DEBUG", "0") == "1"
    app.run(debug=debug_mode, port=port, use_reloader=False)
