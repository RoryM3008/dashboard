"""Callbacks — Stock Screener: run screen + CSV download."""

import datetime

import pandas as pd
from dash import dcc, html, Input, Output, State

from theme import FONT, get_theme
from data import parse_tickers, run_screener


def register_callbacks(app):

    @app.callback(
        Output("screener-results",    "children"),
        Output("screener-status",     "children"),
        Output("screener-data-store", "data"),
        Input("screener-run",  "n_clicks"),
        State("screener-extra",    "value"),
        State("f-pe-max",          "value"),
        State("f-ev-max",          "value"),
        State("f-margin-min",      "value"),
        State("f-revgrowth-min",   "value"),
        State("f-div-min",         "value"),
        State("f-de-max",          "value"),
        State("f-sector",          "value"),
        State("theme-store",       "data"),
        prevent_initial_call=True,
    )
    def run_screen(n, extra_raw, pe_max, ev_max, margin_min, revgrowth_min, div_min, de_max, sector, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not n:
            return html.Div(), "", None
        extra = parse_tickers(extra_raw) if extra_raw else []
        df    = run_screener(extra)
        if df.empty:
            return html.Div("No data returned.", style={"color": c["muted"], "fontFamily": FONT}), "", None

        if sector and sector != "All":
            df = df[df["Sector"] == sector]
        if pe_max is not None:
            df = df[df["P/E"].isna() | (df["P/E"] <= float(pe_max))]
        if ev_max is not None:
            df = df[df["EV/EBITDA"].isna() | (df["EV/EBITDA"] <= float(ev_max))]
        if margin_min is not None:
            df = df[df["Profit Margin Raw"].isna() | (df["Profit Margin Raw"] >= float(margin_min)/100)]
        if revgrowth_min is not None:
            df = df[df["Rev Growth Raw"].isna() | (df["Rev Growth Raw"] >= float(revgrowth_min)/100)]
        if div_min is not None:
            df = df[df["Div Yield Raw"].isna() | (df["Div Yield Raw"] >= float(div_min)/100)]
        if de_max is not None:
            df = df[df["Debt/Equity"].isna() | (df["Debt/Equity"] <= float(de_max))]

        if df.empty:
            return html.Div("No stocks matched your filters.", style={"color": c["muted"], "fontFamily": FONT}), "0 results", None

        df = df.sort_values("Mkt Cap Raw", ascending=False).reset_index(drop=True)
        status = f"{len(df)} stock{'s' if len(df)!=1 else ''} matched \u00b7 sorted by Market Cap"
        display_cols = ["Ticker","Name","Sector","Price","Mkt Cap","P/E","EV/EBITDA",
                        "Rev Growth","Profit Margin","Div Yield","52w Chg %","Debt/Equity","Day Chg %"]

        th_s = {
            "padding": "0.38rem 0.6rem", "fontSize": "0.62rem", "textTransform": "uppercase",
            "letterSpacing": "0.06em", "fontWeight": "700", "whiteSpace": "nowrap",
            "borderBottom": "2px solid " + c["border"], "fontFamily": FONT, "color": c["muted"],
        }
        header = html.Thead(html.Tr(
            [html.Th(col, style={**th_s, "textAlign": "right" if i > 2 else "left"})
             for i, col in enumerate(display_cols)]
        ))

        def cell_color(col, val):
            if col in ("Day Chg %", "52w Chg %", "Rev Growth"):
                try:
                    nv = float(str(val).replace("%","").replace("+",""))
                    return c["green"] if nv > 0 else (c["red"] if nv < 0 else c["subtext"])
                except Exception:
                    return c["subtext"]
            if col == "Profit Margin":
                try:
                    nv = float(str(val).replace("%",""))
                    return c["green"] if nv >= 15 else (c["accent"] if nv >= 5 else c["red"])
                except Exception:
                    return c["subtext"]
            return c["text"]

        body_rows = []
        for _, row in df.iterrows():
            cells = []
            for i, col in enumerate(display_cols):
                val = row.get(col, "\u2014")
                val = "\u2014" if (val is None or (isinstance(val, float) and pd.isna(val))) else val
                is_right = i > 2
                color = cell_color(col, val) if i > 2 else (c["accent"] if col == "Ticker" else c["text"])
                fw = "700" if col == "Ticker" else ("600" if i > 2 else "400")
                cells.append(html.Td(str(val), style={
                    "color": color, "fontWeight": fw,
                    "padding": "0.4rem 0.6rem",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.78rem", "fontFamily": FONT,
                    "textAlign": "right" if is_right else "left",
                    "whiteSpace": "nowrap",
                }))
            body_rows.append(html.Tr(cells))

        table = html.Div(
            html.Table([header, html.Tbody(body_rows)],
                       style={"width": "100%", "borderCollapse": "collapse"}),
            style={"overflowX": "auto", "maxHeight": "520px", "overflowY": "auto"},
        )
        csv_df = df[display_cols].copy()
        store_data = csv_df.to_json(date_format="iso", orient="split")
        return table, status, store_data

    @app.callback(
        Output("screener-download", "data"),
        Input("screener-download-btn", "n_clicks"),
        State("screener-data-store",   "data"),
        prevent_initial_call=True,
    )
    def download_csv(n, store_data):
        if not store_data:
            return None
        df  = pd.read_json(store_data, orient="split")
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return dcc.send_data_frame(df.to_csv, f"screener_{now}.csv", index=False)
