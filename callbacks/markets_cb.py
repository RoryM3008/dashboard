"""Callback — Markets page: sector ETF & country index performance + charting."""

import plotly.graph_objects as go
import yfinance as yf
from dash import dcc, html, Input, Output, State, no_update

from theme import FONT, get_theme


# ─────────────────────────────────────────────────────────────────────────────
# Ticker universes
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_ETFS = {
    "Technology":         "XLK",
    "Healthcare":         "XLV",
    "Financials":         "XLF",
    "Consumer Disc.":     "XLY",
    "Consumer Staples":   "XLP",
    "Energy":             "XLE",
    "Industrials":        "XLI",
    "Materials":          "XLB",
    "Utilities":          "XLU",
    "Real Estate":        "XLRE",
    "Communication":      "XLC",
}

COUNTRY_INDICES = {
    "S&P 500 (US)":      "^GSPC",
    "NASDAQ (US)":        "^IXIC",
    "Dow Jones (US)":     "^DJI",
    "FTSE 100 (UK)":      "^FTSE",
    "DAX (Germany)":      "^GDAXI",
    "CAC 40 (France)":    "^FCHI",
    "Nikkei 225 (Japan)": "^N225",
    "Hang Seng (HK)":     "^HSI",
    "Shanghai (China)":   "000001.SS",
    "S&P/ASX 200 (AU)":  "^AXJO",
    "STOXX 600 (EU)":    "^STOXX",
    "IBEX 35 (Spain)":   "^IBEX",
    "FTSE MIB (Italy)":  "FTSEMIB.MI",
    "TSX (Canada)":      "^GSPTSE",
    "BSE Sensex (India)":"^BSESN",
    "Bovespa (Brazil)":  "^BVSP",
}

# Merged lookup: display-name → ticker
ALL_MARKETS = {}
for name, ticker in SECTOR_ETFS.items():
    ALL_MARKETS[f"Sector: {name}"] = ticker
for name, ticker in COUNTRY_INDICES.items():
    ALL_MARKETS[name] = ticker

RETURN_PERIODS = {
    "1D":  "1d",
    "5D":  "5d",
    "1M":  "1mo",
    "3M":  "3mo",
    "6M":  "6mo",
    "YTD": "ytd",
    "1Y":  "1y",
}

# Plotly colour cycle for chart lines
_LINE_COLOURS = [
    "#58a6ff", "#f0b429", "#3fb950", "#f85149", "#bc8cff",
    "#ff9bce", "#39d2c0", "#f78166", "#79c0ff", "#d2a8ff",
    "#7ee787", "#ffa657", "#ff7b72", "#a5d6ff", "#ffd33d",
]


# ─────────────────────────────────────────────────────────────────────────────
# Data fetcher — table returns
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_performance(name_to_ticker: dict) -> list[dict]:
    """Return list of dicts with Name + return columns for each period."""
    rows = []
    for name, ticker in name_to_ticker.items():
        row = {"Name": name, "Ticker": ticker}
        for label, period in RETURN_PERIODS.items():
            try:
                hist = yf.Ticker(ticker).history(period=period)
                if hist is not None and len(hist) >= 2:
                    ret = ((hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                           / hist["Close"].iloc[0]) * 100
                    row[label] = round(ret, 2)
                else:
                    row[label] = None
            except Exception:
                row[label] = None
        rows.append(row)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Conditional-format helpers (background shading, black text)
# ─────────────────────────────────────────────────────────────────────────────

def _return_bg(val):
    if val is None:
        return "transparent"
    clamped = max(-50, min(50, val))
    intensity = abs(clamped) / 50
    alpha = 0.10 + intensity * 0.45
    if clamped >= 0:
        return f"rgba(63,185,80,{alpha:.2f})"
    return f"rgba(248,81,73,{alpha:.2f})"


# ─────────────────────────────────────────────────────────────────────────────
# Table builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_table(data: list[dict], c: dict) -> html.Div:
    """Build a themed HTML table from fetched performance data."""
    return_cols = list(RETURN_PERIODS.keys())
    all_cols = ["Name", "Ticker"] + return_cols

    th_style = {
        "padding": "0.38rem 0.6rem", "fontSize": "0.62rem", "textTransform": "uppercase",
        "letterSpacing": "0.06em", "fontWeight": "700", "whiteSpace": "nowrap",
        "borderBottom": "2px solid " + c["border"], "fontFamily": FONT, "color": c["text"],
    }

    header = html.Thead(html.Tr(
        [html.Th(col, style={**th_style, "textAlign": "left" if col in ("Name", "Ticker") else "right"})
         for col in all_cols]
    ))

    body_rows = []
    for row in data:
        cells = []
        for col in all_cols:
            val = row.get(col)
            if col == "Name":
                cells.append(html.Td(val, style={
                    "color": c["text"], "fontWeight": "700",
                    "padding": "0.4rem 0.6rem",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.82rem", "fontFamily": FONT,
                    "whiteSpace": "nowrap",
                }))
            elif col == "Ticker":
                cells.append(html.Td(val, style={
                    "color": c["text"], "fontWeight": "600",
                    "padding": "0.4rem 0.6rem",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.78rem", "fontFamily": FONT,
                    "whiteSpace": "nowrap", "opacity": "0.7",
                }))
            else:
                if val is not None:
                    sign = "+" if val > 0 else ""
                    display = f"{sign}{val:.2f}%"
                else:
                    display = "\u2014"
                cells.append(html.Td(display, style={
                    "color": c["text"],
                    "backgroundColor": _return_bg(val),
                    "fontWeight": "700",
                    "padding": "0.4rem 0.6rem", "textAlign": "right",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.8rem", "fontFamily": FONT,
                    "borderRadius": "4px",
                }))
        body_rows.append(html.Tr(cells))

    return html.Div(
        html.Table([header, html.Tbody(body_rows)],
                   style={"width": "100%", "borderCollapse": "collapse"}),
        style={"overflowX": "auto"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # ── 1) Refresh tables + populate chart dropdown ──────────────────────
    @app.callback(
        Output("markets-sector-table",    "children"),
        Output("markets-country-table",   "children"),
        Output("markets-status-sectors",  "children"),
        Output("markets-status-countries","children"),
        Output("markets-chart-select",    "options"),
        Input("markets-refresh", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def refresh_markets(n, theme_mode):
        c = get_theme(theme_mode or "dark")

        sector_data  = _fetch_performance(SECTOR_ETFS)
        country_data = _fetch_performance(COUNTRY_INDICES)

        sector_table  = _build_table(sector_data, c)
        country_table = _build_table(country_data, c)

        s_status = f"{len(SECTOR_ETFS)} sector ETFs loaded"
        c_status = f"{len(COUNTRY_INDICES)} country/region indices loaded"

        # Build dropdown options grouped by category
        options = (
            [{"label": name, "value": name} for name in ALL_MARKETS]
        )

        return sector_table, country_table, s_status, c_status, options

    # ── 2) Chart selected markets ────────────────────────────────────────
    @app.callback(
        Output("markets-chart",        "children"),
        Output("markets-chart-status", "children"),
        Input("markets-chart-btn", "n_clicks"),
        State("markets-chart-select", "value"),
        State("markets-chart-mode",   "value"),
        State("markets-chart-period", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def draw_chart(n, selected, mode, period, theme_mode):
        c = get_theme(theme_mode or "dark")

        if not selected:
            return html.Div(), "Select at least one market to chart."

        fig = go.Figure()
        plotted = []

        for idx, name in enumerate(selected):
            ticker = ALL_MARKETS.get(name)
            if not ticker:
                continue
            try:
                hist = yf.Ticker(ticker).history(period=period or "6mo")
                if hist is None or len(hist) < 2:
                    continue

                series = hist["Close"]
                if mode == "relative":
                    series = (series / series.iloc[0]) * 100

                colour = _LINE_COLOURS[idx % len(_LINE_COLOURS)]
                fig.add_trace(go.Scatter(
                    x=series.index,
                    y=series.values,
                    mode="lines",
                    name=name,
                    line={"color": colour, "width": 2},
                    hovertemplate="%{x|%d %b %Y}<br>" + name + ": %{y:.2f}<extra></extra>",
                ))
                plotted.append(name)
            except Exception:
                continue

        if not plotted:
            return html.Div(), "No data available for the selected markets."

        y_title = "Rebased (100)" if mode == "relative" else "Price"

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": FONT, "color": c["text"], "size": 11},
            margin={"l": 50, "r": 20, "t": 30, "b": 40},
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02,
                    "xanchor": "left", "x": 0, "font": {"size": 11}},
            xaxis={"gridcolor": c["border"], "showgrid": True,
                   "zeroline": False},
            yaxis={"title": y_title, "gridcolor": c["border"],
                   "showgrid": True, "zeroline": False},
            height=420,
            hovermode="x unified",
        )

        status = f"Charting {len(plotted)} market(s) — {mode.capitalize()} view, {period} period"
        return dcc.Graph(figure=fig, config={"displayModeBar": False}), status
