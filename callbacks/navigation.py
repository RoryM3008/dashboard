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
        Input("menu-stock-moves", "n_clicks"),
        Input("menu-prices", "n_clicks"),
        Input("menu-risk", "n_clicks"),
        Input("menu-port", "n_clicks"),
        Input("menu-heatmap", "n_clicks"),
        Input("menu-spread", "n_clicks"),
        Input("menu-ssa", "n_clicks"),
        Input("menu-financials", "n_clicks"),
        Input("menu-peers", "n_clicks"),
        Input("menu-valuations", "n_clicks"),
        Input("menu-fundamentals", "n_clicks"),
        Input("menu-earnings", "n_clicks"),
        Input("menu-calendar", "n_clicks"),
        Input("menu-factor-tilt", "n_clicks"),
        Input("menu-comps", "n_clicks"),
        Input("menu-mylist", "n_clicks"),
        State("menu-open", "data"),
    )
    def toggle_menu(n_toggle, n_backdrop, *rest):
        is_open = rest[-1] if rest else False
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
        Output("menu-stock-moves", "style"),
        Output("menu-prices", "style"),
        Output("menu-risk", "style"),
        Output("menu-port", "style"),
        Output("menu-heatmap", "style"),
        Output("menu-spread", "style"),
        Output("menu-ssa", "style"),
        Output("menu-financials", "style"),
        Output("menu-peers", "style"),
        Output("menu-valuations", "style"),
        Output("menu-fundamentals", "style"),
        Output("menu-earnings", "style"),
        Output("menu-calendar", "style"),
        Output("menu-factor-tilt", "style"),
        Output("menu-comps", "style"),
        Output("menu-mylist", "style"),
        Output("section-dashboard", "style"),
        Output("section-news", "style"),
        Output("section-analyser", "style"),
        Output("section-screener", "style"),
        Output("section-correlation", "style"),
        Output("section-performance", "style"),
        Output("section-watchlist", "style"),
        Output("section-markets", "style"),
        Output("section-stock-moves", "style"),
        Output("section-prices", "style"),
        Output("section-risk", "style"),
        Output("section-port", "style"),
        Output("section-heatmap", "style"),
        Output("section-spread", "style"),
        Output("section-ssa", "style"),
        Output("section-peers", "style"),
        Output("section-valuations", "style"),
        Output("section-fundamentals", "style"),
        Output("section-earnings", "style"),
        Output("section-calendar", "style"),
        Output("section-factor-tilt", "style"),
        Output("section-comps", "style"),
        Output("section-mylist", "style"),
        Output("active-main-menu", "data"),
        Input("menu-dashboard", "n_clicks"),
        Input("menu-news", "n_clicks"),
        Input("menu-analyser", "n_clicks"),
        Input("menu-screener", "n_clicks"),
        Input("menu-correlation", "n_clicks"),
        Input("menu-performance", "n_clicks"),
        Input("menu-watchlist", "n_clicks"),
        Input("menu-markets", "n_clicks"),
        Input("menu-stock-moves", "n_clicks"),
        Input("menu-prices", "n_clicks"),
        Input("menu-risk", "n_clicks"),
        Input("menu-port", "n_clicks"),
        Input("menu-heatmap", "n_clicks"),
        Input("menu-spread", "n_clicks"),
        Input("menu-ssa", "n_clicks"),
        Input("menu-financials", "n_clicks"),
        Input("menu-peers", "n_clicks"),
        Input("menu-valuations", "n_clicks"),
        Input("menu-fundamentals", "n_clicks"),
        Input("menu-earnings", "n_clicks"),
        Input("menu-calendar", "n_clicks"),
        Input("menu-factor-tilt", "n_clicks"),
        Input("menu-comps", "n_clicks"),
        Input("menu-mylist", "n_clicks"),
        Input("theme-store", "data"),
        State("active-main-menu", "data"),
    )
    def set_main_menu(*args):
        theme_mode = args[-2] if len(args) >= 2 else "dark"
        current = args[-1] if len(args) >= 1 else "dashboard"
        ctx = dash.callback_context
        if not ctx.triggered:
            active = current or "dashboard"
        else:
            prop = ctx.triggered[0]["prop_id"].split(".")[0]
            if prop.startswith("menu-"):
                active = prop.replace("menu-", "")
                # stock analysis children map to their own sections where relevant
                if active == "financials":
                    active = "ssa"
            else:
                active = current or "dashboard"

        c = get_theme(theme_mode or "dark")
        btn = _main_menu_btn(c)
        btn_active = _main_menu_btn_active(c)

        # Menu button names (for styling)
        menu_names = ["dashboard", "news", "analyser", "screener", "correlation",
                      "performance", "watchlist", "markets", "stock-moves", "prices", "risk",
                      "port", "heatmap", "spread", "ssa", "financials", "peers", "valuations", "fundamentals", "earnings", "calendar", "factor-tilt", "comps", "mylist"]
        # "ssa" and "financials" share the overview section highlight logic
        buttons = []
        for n in menu_names:
            is_active = (n == active) or (n in ("ssa", "financials") and active == "ssa")
            s = dict(btn_active if is_active else btn)
            if n in ("ssa", "financials", "peers", "valuations", "fundamentals", "earnings", "calendar", "factor-tilt", "comps"):
                s["paddingLeft"] = "1.4rem"
                s["fontSize"] = "0.72rem"
            buttons.append(s)

        # Section names (actual page sections)
        section_names = ["dashboard", "news", "analyser", "screener", "correlation",
                         "performance", "watchlist", "markets", "stock-moves", "prices", "risk",
                         "port", "heatmap", "spread", "ssa", "peers", "valuations", "fundamentals", "earnings", "calendar", "factor-tilt", "comps", "mylist"]
        sections = [{"display": "block"} if n == active else {"display": "none"}
                    for n in section_names]

        return *buttons, *sections, active

    # ── Sync menu ticker input → hidden ticker-input ──────────────────────
    @app.callback(
        Output("ticker-input", "value"),
        Input("menu-ticker-input", "value"),
    )
    def sync_ticker(val):
        return val or ""

    # ── Datasource toggle (Snowflake ↔ yfinance) ──────────────────────────
    @app.callback(
        Output("datasource",         "data"),
        Output("datasource-toggle",  "children"),
        Output("datasource-toggle",  "style"),
        Output("datasource-toggle",  "title"),
        Input("datasource-toggle",   "n_clicks"),
        State("datasource",          "data"),
        prevent_initial_call=True,
    )
    def toggle_datasource(n, current):
        from theme import FONT
        new_src = "yf" if current == "sf" else "sf"
        if new_src == "sf":
            label = "🔌 SF"
            colour = "#00cc66"
            tip    = "Data source: Snowflake/FactSet — click to switch to yfinance (offline)"
        else:
            label = "📡 YF"
            colour = "#ff8c00"
            tip    = "Data source: yfinance (offline) — click to switch to Snowflake"
        style = {
            "backgroundColor": colour, "color": "#000",
            "border": "none", "borderRadius": "6px",
            "padding": "0.35rem 0.7rem", "fontFamily": FONT,
            "fontWeight": "700", "fontSize": "0.72rem",
            "cursor": "pointer", "marginLeft": "0.4rem",
        }
        return new_src, label, style, tip


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
