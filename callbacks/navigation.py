"""Callback — overlay menu switching + toggle."""

import dash
from dash import Input, Output, State, no_update

from theme import get_theme, _main_menu_btn, _main_menu_btn_active


def register_callbacks(app):

    # ── Menu open/close toggle ────────────────────────────────────────────
    @app.callback(
        Output("menu-open", "data"),
        Output("menu-overlay", "style"),
        Output("menu-backdrop", "style"),
        Input("menu-toggle-btn", "n_clicks"),
        Input("menu-backdrop", "n_clicks"),
        Input("menu-dashboard", "n_clicks"),
        Input("menu-news", "n_clicks"),
        Input("menu-analyser", "n_clicks"),
        Input("menu-screener", "n_clicks"),
        Input("menu-correlation", "n_clicks"),
        Input("menu-performance", "n_clicks"),
        Input("menu-watchlist", "n_clicks"),
        Input("menu-markets", "n_clicks"),
        Input("menu-prices", "n_clicks"),
        Input("menu-risk", "n_clicks"),
        Input("menu-port", "n_clicks"),
        Input("menu-heatmap", "n_clicks"),
        Input("menu-spread", "n_clicks"),
        State("menu-open", "data"),
    )
    def toggle_menu(n_toggle, n_backdrop,
                    n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12,n13,
                    is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            return False, _overlay_style(False), _backdrop_style(False)

        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger == "menu-toggle-btn":
            new_state = not is_open
        else:
            # Backdrop click or any menu item click → close
            new_state = False

        return new_state, _overlay_style(new_state), _backdrop_style(new_state)

    # ── Page switching (same logic as before) ─────────────────────────────
    @app.callback(
        Output("menu-dashboard", "style"),
        Output("menu-news", "style"),
        Output("menu-analyser", "style"),
        Output("menu-screener", "style"),
        Output("menu-correlation", "style"),
        Output("menu-performance", "style"),
        Output("menu-watchlist", "style"),
        Output("menu-markets", "style"),
        Output("menu-prices", "style"),
        Output("menu-risk", "style"),
        Output("menu-port", "style"),
        Output("menu-heatmap", "style"),
        Output("menu-spread", "style"),
        Output("section-dashboard", "style"),
        Output("section-news", "style"),
        Output("section-analyser", "style"),
        Output("section-screener", "style"),
        Output("section-correlation", "style"),
        Output("section-performance", "style"),
        Output("section-watchlist", "style"),
        Output("section-markets", "style"),
        Output("section-prices", "style"),
        Output("section-risk", "style"),
        Output("section-port", "style"),
        Output("section-heatmap", "style"),
        Output("section-spread", "style"),
        Output("active-main-menu", "data"),
        Input("menu-dashboard", "n_clicks"),
        Input("menu-news", "n_clicks"),
        Input("menu-analyser", "n_clicks"),
        Input("menu-screener", "n_clicks"),
        Input("menu-correlation", "n_clicks"),
        Input("menu-performance", "n_clicks"),
        Input("menu-watchlist", "n_clicks"),
        Input("menu-markets", "n_clicks"),
        Input("menu-prices", "n_clicks"),
        Input("menu-risk", "n_clicks"),
        Input("menu-port", "n_clicks"),
        Input("menu-heatmap", "n_clicks"),
        Input("menu-spread", "n_clicks"),
        Input("theme-store", "data"),
        State("active-main-menu", "data"),
    )
    def set_main_menu(n_dashboard, n_news, n_analyser, n_screener, n_correlation, n_performance, n_watchlist, n_markets, n_prices, n_risk, n_port, n_heatmap, n_spread, theme_mode, current):
        ctx = dash.callback_context
        if not ctx.triggered:
            active = current or "dashboard"
        else:
            prop = ctx.triggered[0]["prop_id"].split(".")[0]
            if prop.startswith("menu-"):
                active = prop.replace("menu-", "")
            else:
                active = current or "dashboard"

        c = get_theme(theme_mode or "dark")
        btn = _main_menu_btn(c)
        btn_active = _main_menu_btn_active(c)

        names = ["dashboard", "news", "analyser", "screener", "correlation", "performance", "watchlist", "markets", "prices", "risk", "port", "heatmap", "spread"]
        buttons  = [btn_active if n == active else btn for n in names]
        sections = [{"display": "block"} if n == active else {"display": "none"} for n in names]

        return *buttons, *sections, active

    # ── Sync menu ticker input → hidden ticker-input ──────────────────────
    @app.callback(
        Output("ticker-input", "value"),
        Input("menu-ticker-input", "value"),
    )
    def sync_ticker(val):
        return val or ""


def _overlay_style(is_open):
    return {
        "position": "fixed", "top": "0",
        "right": "0" if is_open else "-280px",
        "width": "280px", "height": "100vh", "zIndex": "999",
        "display": "flex", "alignItems": "flex-start",
        "paddingTop": "3.5rem", "paddingRight": "1rem",
        "justifyContent": "center",
        "transition": "right 0.25s ease",
    }


def _backdrop_style(is_open):
    return {
        "display": "block" if is_open else "none",
        "position": "fixed", "top": "0", "left": "0",
        "width": "100vw", "height": "100vh", "zIndex": "998",
        "backgroundColor": "rgba(0,0,0,0.5)",
    }
