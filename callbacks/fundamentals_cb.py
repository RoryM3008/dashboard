"""Callbacks for the Fundamentals deep-dive page — table, compare, chart grid."""

import io
import base64
import json
import numpy as np
import pandas as pd
import dash
from dash import Input, Output, State, html, dcc, no_update, ALL
import plotly.graph_objects as go

from theme import get_theme, FONT
from snowflake_data import search_tickers, _resolve_ids, fetch_annual_fundamentals
from pages.fundamentals_page import METRIC_GROUPS, CATEGORY_ORDER

# ── Colours ───────────────────────────────────────────────────────────────────
COL_A = "#ff8c00"   # Company A — orange
COL_B = "#4db8ff"   # Company B — blue


def _offline_banner():
    return html.Div([
        html.Div("📡", style={"fontSize": "2.5rem", "marginBottom": "0.5rem"}),
        html.Div("Offline Mode", style={"fontWeight": "800", "fontSize": "1.1rem",
                                        "color": "#ff8c00", "marginBottom": "0.4rem"}),
        html.Div("This page requires a Snowflake / FactSet connection.",
                 style={"color": "#888", "fontSize": "0.82rem", "marginBottom": "0.3rem"}),
        html.Div("Toggle 🔌 SF → 📡 YF in the top bar to switch to offline mode, or reconnect to the office network.",
                 style={"color": "#666", "fontSize": "0.75rem"}),
    ], style={"textAlign": "center", "padding": "3rem 2rem",
              "fontFamily": "'Inter', sans-serif"})


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_val(v, fmt_type):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        v = float(v)
    except Exception:
        return str(v)
    if fmt_type == "pct":
        return f"{v:.1f}%"
    if fmt_type == "x":
        return f"{v:.1f}x"
    if fmt_type in ("ratio", "ps"):
        return f"{v:.2f}"
    if fmt_type == "days":
        return f"{v:.0f}d"
    if fmt_type == "large":
        if abs(v) >= 1_000_000:
            return f"{v/1_000_000:.1f}T"
        if abs(v) >= 1_000:
            return f"{v/1_000:.1f}B"
        return f"{v:,.1f}M"
    return f"{v:.2f}"


def _to_float_series(df, col):
    """Return list of (fiscal_year, float_value) sorted by year."""
    if df is None or df.empty or col not in df.columns:
        return []
    fy_col = "FISCAL_YEAR"
    if fy_col not in df.columns:
        return []
    result = []
    for _, row in df.iterrows():
        try:
            fy  = int(row[fy_col])
            val = float(row[col])
            if not np.isnan(val):
                result.append((fy, val))
        except Exception:
            pass
    return sorted(result, key=lambda x: x[0])


# ── Heat colour for single-company table ────────────────────────────────────

def _heat(val, vmin, vmax, category, fmt_type):
    if vmin is None or vmax == vmin:
        return "#e6e6e6"
    intensity = (val - vmin) / (vmax - vmin)
    INVERT_CATS = {"Coverage", "Leverage"}
    if category in INVERT_CATS:
        intensity = 1 - intensity
    if intensity > 0.7:
        return "#00cc66"
    elif intensity < 0.3:
        return "#ff5555"
    return "#e6e6e6"


# ── Single-company table ──────────────────────────────────────────────────────

def _build_table(df: pd.DataFrame, category: str, C: dict) -> html.Div:
    metrics = METRIC_GROUPS.get(category, [])
    if df is None or df.empty or not metrics:
        return html.Div("No data loaded.",
                        style={"color": C["muted"], "fontFamily": FONT,
                               "fontSize": "0.78rem", "padding": "1rem"})

    fy_col = "FISCAL_YEAR"
    years  = sorted(df[fy_col].dropna().unique().astype(int).tolist()) if fy_col in df.columns else []
    fy_map = {int(r[fy_col]): r for _, r in df.iterrows()} if years else {}

    # Header
    hdr = [html.Th("Metric", style=_th_style(C, sticky=True))]
    for yr in years:
        hdr.append(html.Th(str(yr), style=_th_style(C, align="right")))

    rows = []
    for i, (label, col, fmt) in enumerate(metrics):
        bg = "#0f0f0f" if i % 2 == 0 else "#0a0a0a"
        raw_vals = [float(fy_map[y][col]) for y in years
                    if y in fy_map and col in fy_map[y].index
                    and _safe_float(fy_map[y][col]) is not None]
        vmin = min(raw_vals) if raw_vals else None
        vmax = max(raw_vals) if raw_vals else None

        cells = [html.Td(label, style=_td_label(C, bg))]
        for yr in years:
            row = fy_map.get(yr)
            val = _safe_float(row[col]) if (row is not None and col in row.index) else None
            color = _heat(val, vmin, vmax, category, fmt) if val is not None else C["muted"]
            cells.append(html.Td(_fmt_val(val, fmt),
                                 style=_td_val(C, bg, color)))
        rows.append(html.Tr(cells))

    tbl = html.Table(
        [html.Thead(html.Tr(hdr)), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )
    return html.Div(tbl, style={"overflowX": "auto", "overflowY": "auto", "maxHeight": "70vh"})


# ── Compare table (two companies side-by-side) ────────────────────────────────

def _build_compare_table(df_a, df_b, name_a, name_b, category, C):
    metrics = METRIC_GROUPS.get(category, [])
    if not metrics:
        return html.Div("No metrics for this category.",
                        style={"color": C["muted"], "fontFamily": FONT, "padding": "1rem"})

    fy_col = "FISCAL_YEAR"

    def _years(df):
        if df is None or df.empty or fy_col not in df.columns:
            return []
        return sorted(df[fy_col].dropna().unique().astype(int).tolist())

    def _map(df):
        if df is None or df.empty:
            return {}
        return {int(r[fy_col]): r for _, r in df.iterrows()}

    years_a = _years(df_a)
    years_b = _years(df_b)
    map_a   = _map(df_a)
    map_b   = _map(df_b)

    # ── Double header ────────────────────────────────────────────────────
    STICKY = {"position": "sticky", "left": "0", "zIndex": "2",
              "backgroundColor": "#0a0a0a"}
    hdr1 = [
        html.Th("Metric",
                style={**_th_style(C, sticky=True), "minWidth": "180px", "rowSpan": "2"}),
        html.Th(name_a or "Company A",
                colSpan=len(years_a) or 1,
                style={**_th_style(C, align="center"), "color": COL_A,
                       "borderBottom": f"2px solid {COL_A}44"}),
        html.Th(name_b or "Company B",
                colSpan=len(years_b) or 1,
                style={**_th_style(C, align="center"), "color": COL_B,
                       "borderBottom": f"2px solid {COL_B}44"}),
    ]
    hdr2_cells = []
    for yr in years_a:
        hdr2_cells.append(html.Th(str(yr),
                                  style={**_th_style(C, align="right"),
                                         "color": COL_A, "fontSize": "0.58rem"}))
    for yr in years_b:
        hdr2_cells.append(html.Th(str(yr),
                                  style={**_th_style(C, align="right"),
                                         "color": COL_B, "fontSize": "0.58rem"}))

    rows = []
    for i, (label, col, fmt) in enumerate(metrics):
        bg = "#0f0f0f" if i % 2 == 0 else "#0a0a0a"

        vals_a = [_safe_float(map_a[y][col])
                  for y in years_a if y in map_a and col in map_a[y].index]
        vals_b = [_safe_float(map_b[y][col])
                  for y in years_b if y in map_b and col in map_b[y].index]
        all_vals = [v for v in vals_a + vals_b if v is not None]
        vmin = min(all_vals) if all_vals else None
        vmax = max(all_vals) if all_vals else None

        cells = [html.Td(label, style=_td_label(C, bg))]

        for yr in years_a:
            row  = map_a.get(yr)
            val  = _safe_float(row[col]) if (row is not None and col in row.index) else None
            clr  = _heat(val, vmin, vmax, category, fmt) if val is not None else "#555"
            cells.append(html.Td(_fmt_val(val, fmt),
                                 style={**_td_val(C, bg, clr),
                                        "borderRight": f"1px solid {COL_A}22"}))

        # Divider cell
        cells.append(html.Td("│",
                             style={"padding": "0.1rem 0.2rem",
                                    "color": "#333", "fontSize": "0.6rem",
                                    "backgroundColor": bg,
                                    "borderLeft": f"1px solid {COL_B}44",
                                    "borderRight": f"1px solid {COL_B}44"}))

        for yr in years_b:
            row  = map_b.get(yr)
            val  = _safe_float(row[col]) if (row is not None and col in row.index) else None
            clr  = _heat(val, vmin, vmax, category, fmt) if val is not None else "#555"
            cells.append(html.Td(_fmt_val(val, fmt),
                                 style={**_td_val(C, bg, clr),
                                        "borderRight": f"1px solid {COL_B}22"}))
        rows.append(html.Tr(cells))

    tbl = html.Table(
        [html.Thead([html.Tr(hdr1), html.Tr(hdr2_cells)]),
         html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )
    return html.Div(tbl, style={"overflowX": "auto", "overflowY": "auto", "maxHeight": "70vh"})


# ── Chart grid ────────────────────────────────────────────────────────────────

def _build_chart_grid(df_a, df_b, name_a, name_b, category, C):
    metrics = METRIC_GROUPS.get(category, [])
    if not metrics or (df_a is None and df_b is None):
        return html.Div("No data to chart.",
                        style={"color": C["muted"], "fontFamily": FONT, "padding": "1rem"})

    charts = []
    for label, col, fmt in metrics:
        series_a = _to_float_series(df_a, col)
        series_b = _to_float_series(df_b, col)

        if not series_a and not series_b:
            continue  # skip empty metrics

        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="#0a0a0a",
            plot_bgcolor="#0a0a0a",
            margin=dict(l=36, r=10, t=28, b=28),
            font=dict(family=FONT, size=10, color="#999"),
            showlegend=(df_b is not None and bool(series_b)),
            legend=dict(orientation="h", y=-0.25, x=0,
                        font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=False, zeroline=False,
                       tickfont=dict(size=9), tickformat="d"),
            yaxis=dict(showgrid=True, gridcolor="#1e1e1e",
                       zeroline=True, zerolinecolor="#333",
                       tickfont=dict(size=9)),
            title=dict(text=label, font=dict(size=10, color="#ccc"), x=0.03, y=0.97),
            hovermode="x unified",
        )

        if series_a:
            xs, ys = zip(*series_a)
            fig.add_trace(go.Scatter(
                x=list(xs), y=list(ys),
                mode="lines+markers",
                line=dict(color=COL_A, width=2),
                marker=dict(size=4),
                name=name_a or "A",
                hovertemplate=f"%{{y:.2f}}<extra>{name_a or 'A'}</extra>",
            ))

        if series_b:
            xs, ys = zip(*series_b)
            fig.add_trace(go.Scatter(
                x=list(xs), y=list(ys),
                mode="lines+markers",
                line=dict(color=COL_B, width=2, dash="dot"),
                marker=dict(size=4),
                name=name_b or "B",
                hovertemplate=f"%{{y:.2f}}<extra>{name_b or 'B'}</extra>",
            ))

        charts.append(
            html.Div(
                dcc.Graph(figure=fig, config={"displayModeBar": False},
                          style={"height": "200px"}),
                style={
                    "width": "calc(33.33% - 0.6rem)",
                    "minWidth": "260px",
                    "backgroundColor": "#0a0a0a",
                    "border": f"1px solid {C['border']}",
                    "borderRadius": "6px",
                    "overflow": "hidden",
                }
            )
        )

    if not charts:
        return html.Div("No chartable data for this category.",
                        style={"color": C["muted"], "fontFamily": FONT, "padding": "1rem"})

    return html.Div(charts,
                    style={"display": "flex", "flexWrap": "wrap",
                           "gap": "0.6rem", "padding": "0.4rem"})


# ── Style helpers ─────────────────────────────────────────────────────────────

def _th_style(C, sticky=False, align="left"):
    s = {
        "textAlign": align, "padding": "0.32rem 0.7rem",
        "color": "#ff8c00", "fontFamily": FONT, "fontSize": "0.60rem",
        "fontWeight": "700", "borderBottom": f"2px solid {C['border']}",
        "whiteSpace": "nowrap",
    }
    if sticky:
        s.update({"position": "sticky", "left": "0",
                  "backgroundColor": "#0a0a0a", "zIndex": "2",
                  "minWidth": "180px"})
    else:
        s["minWidth"] = "65px"
    return s


def _td_label(C, bg):
    return {
        "padding": "0.26rem 0.7rem", "fontFamily": FONT, "fontSize": "0.70rem",
        "color": C["muted"], "fontWeight": "600",
        "borderBottom": f"1px solid {C['border']}",
        "position": "sticky", "left": "0",
        "backgroundColor": bg, "zIndex": "1",
        "whiteSpace": "nowrap",
    }


def _td_val(C, bg, color="#e6e6e6"):
    return {
        "textAlign": "right", "padding": "0.26rem 0.7rem",
        "fontFamily": FONT, "fontSize": "0.70rem",
        "color": color,
        "borderBottom": f"1px solid {C['border']}",
        "backgroundColor": bg,
    }


def _safe_float(v):
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except Exception:
        return None


# ── Serialise / deserialise ───────────────────────────────────────────────────

def _ser(df):
    return df.reset_index().to_dict("records") if df is not None and not df.empty else {}


def _deser(records):
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    return df


# ── Ticker resolver ───────────────────────────────────────────────────────────

def _resolve_fund_ticker(raw: str):
    if not raw:
        return None
    raw = raw.strip().upper()
    ids = _resolve_ids(raw)
    if ids:
        return ids
    try:
        results = search_tickers(raw, limit=5)
        if results:
            return _resolve_ids(results[0]["ticker_region"])
    except Exception:
        pass
    return None


# ── Register all callbacks ────────────────────────────────────────────────────

def register_callbacks(app):

    # ── Ticker A suggestions ──────────────────────────────────────────────
    @app.callback(
        Output("fund-ticker-suggestions", "children"),
        Input("fund-ticker", "value"),
        prevent_initial_call=True,
    )
    def fund_ticker_suggestions(search):
        return _suggestions(search)

    @app.callback(
        Output("fund-ticker", "value", allow_duplicate=True),
        Output("fund-ticker-suggestions", "children", allow_duplicate=True),
        Input({"type": "fund-ticker-suggestion", "index": ALL}, "n_clicks"),
        State({"type": "fund-ticker-suggestion", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def choose_fund_ticker_a(clicks, ids):
        return _choose_ticker(clicks, ids)

    # ── Ticker B suggestions ──────────────────────────────────────────────
    @app.callback(
        Output("fund-ticker-b-suggestions", "children"),
        Input("fund-ticker-b", "value"),
        prevent_initial_call=True,
    )
    def fund_ticker_b_suggestions(search):
        return _suggestions(search, stype="fund-ticker-b-suggestion")

    @app.callback(
        Output("fund-ticker-b", "value", allow_duplicate=True),
        Output("fund-ticker-b-suggestions", "children", allow_duplicate=True),
        Input({"type": "fund-ticker-b-suggestion", "index": ALL}, "n_clicks"),
        State({"type": "fund-ticker-b-suggestion", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def choose_fund_ticker_b(clicks, ids):
        return _choose_ticker(clicks, ids)

    # ── Compare toggle ────────────────────────────────────────────────────
    @app.callback(
        Output("fund-compare-row",    "style"),
        Output("fund-compare-mode",   "data"),
        Output("fund-compare-toggle", "style"),
        Input("fund-compare-toggle",  "n_clicks"),
        State("fund-compare-mode",    "data"),
        State("theme-store",          "data"),
        prevent_initial_call=True,
    )
    def toggle_compare(n, is_compare, theme):
        c        = get_theme(theme or "dark")
        new_mode = not bool(is_compare)
        row_style = {
            "display": "flex" if new_mode else "none",
            "alignItems": "flex-start", "flexWrap": "wrap", "gap": "0.8rem",
            "marginBottom": "0.8rem", "padding": "0.65rem 0.9rem",
            "border": "1px solid #4db8ff33", "borderRadius": "8px",
            "backgroundColor": "#0d1420",
        }
        btn_style = {
            "backgroundColor": COL_B if new_mode else c["panel"],
            "color": "#000" if new_mode else c["muted"],
            "border": f"1px solid {c['border']}",
            "borderRadius": "6px", "padding": "0.38rem 0.9rem",
            "fontFamily": FONT, "fontWeight": "700",
            "fontSize": "0.70rem", "cursor": "pointer",
        }
        return row_style, new_mode, btn_style

    # ── View mode toggle ──────────────────────────────────────────────────
    @app.callback(
        Output("fund-view-mode",      "data"),
        Output("fund-view-table-btn", "style"),
        Output("fund-view-chart-btn", "style"),
        Input("fund-view-table-btn",  "n_clicks"),
        Input("fund-view-chart-btn",  "n_clicks"),
        State("fund-view-mode",       "data"),
        State("theme-store",          "data"),
        prevent_initial_call=True,
    )
    def toggle_view_mode(n_tbl, n_chr, current, theme):
        c   = get_theme(theme or "dark")
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        mode = "chart" if ctx.triggered[0]["prop_id"].split(".")[0] == "fund-view-chart-btn" else "table"

        def _style(active):
            return {
                "backgroundColor": c["accent"] if active else c["panel"],
                "color": "#000" if active else c["muted"],
                "border": f"1px solid {c['border']}",
                "borderRadius": "6px", "padding": "0.38rem 0.9rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.70rem", "cursor": "pointer",
            }
        return mode, _style(mode == "table"), _style(mode == "chart")

    # ── Category buttons ──────────────────────────────────────────────────
    cat_btn_ids = [f"fund-cat-{c.lower().replace(' ', '-')}" for c in CATEGORY_ORDER]

    @app.callback(
        *[Output(bid, "style") for bid in cat_btn_ids],
        Output("fund-category", "data"),
        *[Input(bid, "n_clicks") for bid in cat_btn_ids],
        State("fund-category", "data"),
        State("theme-store",   "data"),
        prevent_initial_call=True,
    )
    def update_fund_category(*args):
        n    = len(CATEGORY_ORDER)
        current = args[n]
        theme   = args[n + 1]
        c = get_theme(theme or "dark")

        ctx    = dash.callback_context
        active = current or CATEGORY_ORDER[0]
        if ctx.triggered:
            prop = ctx.triggered[0]["prop_id"].split(".")[0]
            for i, bid in enumerate(cat_btn_ids):
                if prop == bid:
                    active = CATEGORY_ORDER[i]
                    break

        styles = []
        for cat in CATEGORY_ORDER:
            is_active = (cat == active)
            styles.append({
                "backgroundColor": c["accent"] if is_active else c["panel"],
                "color": "#000" if is_active else c["muted"],
                "border": f"1px solid {c['border']}",
                "borderRadius": "4px", "padding": "0.3rem 0.75rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.68rem", "cursor": "pointer",
                "marginRight": "4px", "marginBottom": "4px",
            })
        return *styles, active

    # ── Main load / re-render ─────────────────────────────────────────────
    @app.callback(
        Output("fund-table-container", "children"),
        Output("fund-status",          "children"),
        Output("fund-data",            "data"),
        Output("fund-data-b",          "data"),
        Output("fund-name-a",          "data"),
        Output("fund-name-b",          "data"),
        Output("fund-cmp-year-dd",     "options"),
        Output("fund-cmp-year-dd",     "value"),
        Input("fund-load-btn",         "n_clicks"),
        Input("fund-category",         "data"),
        Input("fund-view-mode",        "data"),
        Input("fund-cmp-year-dd",      "value"),
        State("fund-ticker",           "value"),
        State("fund-ticker-b",         "value"),
        State("fund-year-from",        "value"),
        State("fund-compare-mode",     "data"),
        State("fund-data",             "data"),
        State("fund-data-b",           "data"),
        State("fund-name-a",           "data"),
        State("fund-name-b",           "data"),
        State("theme-store",           "data"),
        State("datasource",            "data"),
        prevent_initial_call=True,
    )
    def load_fundamentals(n_load, category, view_mode, cmp_year,
                          ticker_a, ticker_b, year_from,
                          compare_mode,
                          cached_a, cached_b, name_a, name_b,
                          theme, datasource):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        if datasource == "yf":
            banner = _offline_banner()
            return banner, "⚠️ Offline mode — Snowflake required", no_update, no_update, no_update, no_update, no_update, no_update

        trigger  = ctx.triggered[0]["prop_id"].split(".")[0]
        c        = get_theme(theme or "dark")
        category = category or CATEGORY_ORDER[0]
        view     = view_mode or "table"

        # ── Cache hit: category / view mode / year change ─────────────
        if trigger in ("fund-category", "fund-view-mode", "fund-cmp-year-dd") and cached_a:
            try:
                df_a = _deser(cached_a)
                df_b = _deser(cached_b) if compare_mode and cached_b else None
                content = _render(df_a, df_b, name_a, name_b,
                                  category, view, compare_mode, c, cmp_year)
                return content, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            except Exception:
                pass

        # ── Full load ──────────────────────────────────────────────────
        if not ticker_a:
            return no_update, "Enter a ticker first.", no_update, no_update, no_update, no_update, no_update, no_update

        ids_a = _resolve_fund_ticker(ticker_a.strip())
        if not ids_a:
            return no_update, f"❌ Could not resolve: {ticker_a}", no_update, no_update, no_update, no_update, no_update, no_update

        name_a    = ids_a.get("name", ticker_a.strip().upper())
        year_from = int(year_from or 2005)

        try:
            df_a = fetch_annual_fundamentals(ids_a["fsym_id"], year_from=year_from)
        except Exception as e:
            return no_update, f"❌ {e}", no_update, no_update, no_update, no_update, no_update, no_update

        if df_a.empty:
            return no_update, f"No data for {name_a}.", no_update, no_update, no_update, no_update, no_update, no_update

        # ── Company B (compare mode) ───────────────────────────────────
        df_b   = None
        name_b = ""
        new_cached_b = {}

        if compare_mode and ticker_b and ticker_b.strip():
            ids_b = _resolve_fund_ticker(ticker_b.strip())
            if ids_b:
                try:
                    df_b   = fetch_annual_fundamentals(ids_b["fsym_id"], year_from=year_from)
                    name_b = ids_b.get("name", ticker_b.strip().upper())
                    new_cached_b = _ser(df_b)
                except Exception:
                    df_b   = None
                    name_b = ""

        # ── Build year dropdown options ────────────────────────────────
        fy_col  = "FISCAL_YEAR"
        yrs_a   = sorted(df_a[fy_col].dropna().unique().astype(int).tolist(), reverse=True) if fy_col in df_a.columns else []
        yrs_b   = sorted(df_b[fy_col].dropna().unique().astype(int).tolist(), reverse=True) if (df_b is not None and not df_b.empty and fy_col in df_b.columns) else []
        all_yrs = sorted(set(yrs_a) | set(yrs_b), reverse=True)
        year_opts  = [{"label": str(y), "value": y} for y in all_yrs]
        common_yrs = sorted(set(yrs_a) & set(yrs_b), reverse=True)
        default_yr = common_yrs[0] if common_yrs else (all_yrs[0] if all_yrs else None)
        if cmp_year is None or cmp_year not in all_yrs:
            cmp_year = default_yr

        # ── Render ─────────────────────────────────────────────────────
        content = _render(df_a, df_b, name_a, name_b, category, view, compare_mode, c, cmp_year)

        n_yrs  = df_a["FISCAL_YEAR"].nunique() if "FISCAL_YEAR" in df_a.columns else len(df_a)
        status = f"✅  {name_a}  ·  {n_yrs} fiscal years"
        if df_b is not None and not df_b.empty:
            n_yrs_b = df_b["FISCAL_YEAR"].nunique() if "FISCAL_YEAR" in df_b.columns else len(df_b)
            status += f"   vs   {name_b}  ·  {n_yrs_b} fiscal years"

        return content, status, _ser(df_a), new_cached_b, name_a, name_b, year_opts, cmp_year

    # ── Excel export ──────────────────────────────────────────────────
    @app.callback(
        Output("fund-dl", "data"),
        Input("fund-export-btn", "n_clicks"),
        State("fund-data",   "data"),
        State("fund-data-b", "data"),
        State("fund-name-a", "data"),
        State("fund-name-b", "data"),
        prevent_initial_call=True,
    )
    def export_excel(n, cached_a, cached_b, name_a, name_b):
        if not cached_a:
            return no_update
        try:
            df_a = _deser(cached_a)
            df_b = _deser(cached_b) if cached_b else None
            na   = (name_a or "A").replace(" ", "_")[:15]
            nb   = (name_b or "B").replace(" ", "_")[:15] if df_b is not None and not df_b.empty else ""
            fname = f"Fundamentals_{na}{'_vs_' + nb if nb else ''}.xlsx"
            content = _export_excel(df_a, df_b, name_a, name_b)
            return dict(content=content, filename=fname, base64=True,
                        type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            return no_update


# ── Render dispatcher ─────────────────────────────────────────────────────────

def _render(df_a, df_b, name_a, name_b, category, view, compare_mode, C, cmp_year=None):
    if view == "chart":
        return _build_chart_grid(df_a, df_b if compare_mode else None,
                                 name_a, name_b, category, C)
    if view == "bar":
        return _build_compare_bar_chart(
            df_a, df_b if compare_mode else None,
            name_a, name_b, category, cmp_year, C)
    if compare_mode and df_b is not None and not df_b.empty:
        return _build_compare_table(df_a, df_b, name_a, name_b, category, C)
    return _build_table(df_a, category, C)


# ── Shared suggestion helpers ─────────────────────────────────────────────────

def _suggestions(search, stype="fund-ticker-suggestion"):
    if not search or len(search.strip()) < 2:
        return []
    if "-" in search.strip() and len(search.strip()) >= 5:
        return []
    try:
        results = search_tickers(search.strip(), limit=20)
    except Exception:
        return []
    cards = []
    for r in results[:8]:
        region = f" · {r['region']}"   if r.get("region")   else ""
        exch   = f" · {r['exchange']}" if r.get("exchange")  else ""
        cards.append(html.Button(
            [html.Span(f"{r['ticker']}{region}{exch}", style={"fontWeight": "700"}),
             html.Span(f"  {r['name']}", style={"marginLeft": "0.35rem"})],
            id={"type": stype, "index": r["ticker_region"]},
            n_clicks=0,
            style={"backgroundColor": "#0b0b0b", "border": "1px solid #2a2a2a",
                   "color": "#e6e6e6", "padding": "0.45rem 0.65rem",
                   "textAlign": "left", "fontFamily": FONT,
                   "fontSize": "0.76rem", "cursor": "pointer"},
        ))
    return cards


def _choose_ticker(clicks, ids):
    if not clicks or not any(clicks):
        return no_update, no_update
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update
    try:
        id_dict = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
        return id_dict.get("index", ""), []
    except Exception:
        return no_update, no_update
