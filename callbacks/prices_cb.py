"""Callback — Prices: add/remove tickers, fetch historical prices, export to Excel."""

import io
import json
import base64
from datetime import datetime

import dash
import pandas as pd
import yfinance as yf
from dash import html, dcc, Input, Output, State, ALL, no_update

from theme import FONT, get_theme
from data import parse_tickers


# ─────────────────────────────────────────────────────────────────────────────
# Data fetcher
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_prices(tickers, period, frequency):
    """Download historical Close prices and return a tidy DataFrame."""
    interval_map = {
        "daily":   "1d",
        "weekly":  "1wk",
        "monthly": "1mo",
    }
    interval = interval_map.get(frequency, "1d")

    frames = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period=period, interval=interval)
            if hist is not None and not hist.empty:
                s = hist["Close"].round(2)
                # Strip timezone so all markets share the same date key
                s.index = s.index.tz_localize(None).normalize()
                frames[ticker] = s
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    # Merge duplicate date rows (same calendar date, different tz)
    df = df.groupby(df.index).first()
    df.index.name = "Date"
    df = df.reset_index()

    # Clean up the date column
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%d-%m-%Y")
    # Most recent first
    df = df.iloc[::-1].reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # ── 1) Manage the stored ticker list (add / remove / clear) ───────────
    @app.callback(
        Output("prices-store", "data"),
        Output("prices-input", "value"),
        Input("prices-add",   "n_clicks"),
        Input("prices-clear", "n_clicks"),
        Input({"type": "prices-remove", "ticker": ALL}, "n_clicks"),
        State("prices-input", "value"),
        State("prices-store", "data"),
        prevent_initial_call=True,
    )
    def manage_prices_store(n_add, n_clear, n_removes, raw_input, store):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update

        trigger = ctx.triggered[0]["prop_id"]
        store = store or []

        if "prices-clear" in trigger:
            return [], ""

        if "prices-remove" in trigger:
            try:
                btn_id = json.loads(trigger.split(".")[0])
                store = [t for t in store if t != btn_id["ticker"]]
            except Exception:
                pass
            return store, no_update

        if "prices-add" in trigger:
            new_tickers = parse_tickers(raw_input)
            for t in new_tickers:
                if t not in store:
                    store.append(t)
            return store, ""

        return no_update, no_update

    # ── 2) Render pills whenever the store changes ────────────────────────
    @app.callback(
        Output("prices-pills", "children"),
        Input("prices-store", "data"),
        Input("theme-store",  "data"),
    )
    def render_pills(store, theme_mode):
        c = get_theme(theme_mode or "dark")
        store = store or []
        pills = []
        for ticker in store:
            pills.append(html.Div([
                html.Span(ticker, style={
                    "fontFamily": FONT, "fontSize": "0.78rem", "fontWeight": "700",
                    "color": c["text"], "marginRight": "0.3rem",
                }),
                html.Button("\u2715", id={"type": "prices-remove", "ticker": ticker},
                            n_clicks=0, style={
                    "background": "none", "border": "none", "color": c["red"],
                    "cursor": "pointer", "fontWeight": "700", "fontSize": "0.78rem",
                    "padding": "0", "lineHeight": "1",
                }),
            ], style={
                "display": "inline-flex", "alignItems": "center",
                "backgroundColor": c["border"], "borderRadius": "14px",
                "padding": "0.25rem 0.65rem",
            }))
        return pills

    # ── 3) Fetch prices and render table ──────────────────────────────────
    @app.callback(
        Output("prices-table",  "children"),
        Output("prices-status", "children"),
        Input("prices-fetch", "n_clicks"),
        State("prices-store",     "data"),
        State("prices-frequency", "value"),
        State("prices-period",    "value"),
        State("theme-store",      "data"),
        prevent_initial_call=True,
    )
    def fetch_and_render(n_clicks, store, frequency, period, theme_mode):
        c = get_theme(theme_mode or "dark")
        store = store or []

        if not store:
            return html.Div("Add tickers above first.",
                            style={"color": c["text"], "fontSize": "0.82rem",
                                   "fontFamily": FONT}), ""

        df = _fetch_prices(store, period, frequency)

        if df.empty:
            return html.Div("No data returned — check tickers.",
                            style={"color": c["red"], "fontSize": "0.82rem",
                                   "fontFamily": FONT}), ""

        freq_label = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}.get(frequency, "")
        status = f"{freq_label} prices  •  {len(df)} rows  •  {len(df.columns)-1} tickers"

        # ── Build HTML table ──────────────────────────────────────────────
        col_w = "72px"   # narrow fixed width for ticker columns
        th_style = {
            "padding": "0.25rem 0.4rem",
            "fontSize": "0.65rem",
            "fontWeight": "700",
            "textTransform": "uppercase",
            "letterSpacing": "0.04em",
            "whiteSpace": "nowrap",
            "borderBottom": f"2px solid {c['border']}",
            "fontFamily": FONT,
            "color": c["text"],
            "textAlign": "right",
            "position": "sticky",
            "top": "0",
            "backgroundColor": c["panel"],
            "zIndex": "1",
            "width": col_w, "minWidth": col_w, "maxWidth": col_w,
        }
        td_style = {
            "padding": "0.22rem 0.4rem",
            "fontSize": "0.72rem",
            "fontFamily": FONT,
            "color": c["text"],
            "borderBottom": f"1px solid {c['border']}",
            "textAlign": "right",
            "whiteSpace": "nowrap",
            "width": col_w, "minWidth": col_w, "maxWidth": col_w,
        }

        date_w = "82px"
        date_th = {**th_style, "textAlign": "left", "width": date_w,
                   "maxWidth": date_w, "minWidth": date_w}
        date_td = {**td_style, "textAlign": "left", "fontWeight": "600",
                   "width": date_w, "maxWidth": date_w, "minWidth": date_w}

        header = html.Thead(html.Tr(
            [html.Th(col, style=date_th if col == "Date" else th_style)
             for col in df.columns]
        ))

        body_rows = []
        for _, row in df.iterrows():
            cells = []
            for col in df.columns:
                val = row[col]
                if col == "Date":
                    cells.append(html.Td(val, style=date_td))
                else:
                    display = f"{val:,.2f}" if pd.notna(val) else "—"
                    cells.append(html.Td(display, style=td_style))
            body_rows.append(html.Tr(cells))

        # Fixed table layout so columns respect the widths above
        table = html.Table(
            [header, html.Tbody(body_rows)],
            style={"borderCollapse": "collapse",
                   "tableLayout": "fixed",
                   "width": "max-content"},
        )

        # Wrapper: top scrollbar + scrollable table
        top_scroll = html.Div(
            html.Div(style={"height": "1px"}),
            id="prices-top-scroll",
            style={"overflowX": "auto", "overflowY": "hidden",
                   "marginBottom": "-1px"},
        )
        wrapper = html.Div([
            top_scroll,
            html.Div(table, id="prices-table-inner", style={
                "maxHeight": "520px", "overflowY": "auto", "overflowX": "auto",
            }),
        ])

        return wrapper, status

    # ── 4) Export to Excel ────────────────────────────────────────────────
    @app.callback(
        Output("prices-download", "data"),
        Input("prices-export", "n_clicks"),
        State("prices-store",     "data"),
        State("prices-frequency", "value"),
        State("prices-period",    "value"),
        prevent_initial_call=True,
    )
    def export_excel(n_clicks, store, frequency, period):
        store = store or []
        if not store:
            return no_update

        df = _fetch_prices(store, period, frequency)
        if df.empty:
            return no_update

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Prices")
        buf.seek(0)

        today = datetime.now().strftime("%Y%m%d")
        freq_tag = frequency.capitalize()
        filename = f"Prices_{freq_tag}_{today}.xlsx"

        return dcc.send_bytes(buf.getvalue(), filename)
