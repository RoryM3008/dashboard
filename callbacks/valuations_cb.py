"""Callbacks for the Valuation History page."""

import json
import numpy as np
import pandas as pd
import dash
from dash import Input, Output, State, html, dcc, no_update, ALL
import plotly.graph_objects as go

from theme import get_theme, FONT
from snowflake_data import (
    search_tickers, _resolve_ids, fetch_valuation_history,
    fetch_annual_margins, download_ohlcv,
)
from pages.valuations_page import ANNUAL_MARGIN_METRICS


def _offline_banner():
    return html.Div([
        html.Div("📡", style={"fontSize": "2.5rem", "marginBottom": "0.5rem"}),
        html.Div("Offline Mode", style={"fontWeight": "800", "fontSize": "1.1rem",
                                        "color": "#ff8c00", "marginBottom": "0.4rem"}),
        html.Div("This page requires a Snowflake / FactSet connection.",
                 style={"color": "#888", "fontSize": "0.82rem", "marginBottom": "0.3rem"}),
        html.Div("Toggle the data source button (🔌 SF) to reconnect when on the office network.",
                 style={"color": "#666", "fontSize": "0.75rem"}),
    ], style={"textAlign": "center", "padding": "3rem 2rem",
              "fontFamily": "'Inter', sans-serif"})


# ── Utility helpers ───────────────────────────────────────────────────────────

def _resolve_val_ticker(raw: str):
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


def _period_to_years(period: str) -> int:
    return {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10, "MAX": 30}.get(period, 5)


def _fmt(v, pct=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if pct:
        return f"{v:.1f}%"
    return f"{v:.1f}x" if abs(v) < 1000 else f"{v:,.0f}"


def _percentile_rank(series, current_val):
    if series.isna().all() or pd.isna(current_val):
        return None
    return round((series.dropna() <= current_val).mean() * 100, 0)


# ── Chart builders ────────────────────────────────────────────────────────────

def _make_chart(df_col: pd.Series, metric: str, theme="dark",
                price_series: pd.Series = None):
    """LTM time-series line chart, optionally with share price on y-axis 2."""
    c = get_theme(theme)
    series = df_col.dropna()

    if series.empty:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
            font=dict(family=FONT, color=c["text"]),
            annotations=[dict(text="No data available", x=0.5, y=0.5,
                              xref="paper", yref="paper",
                              showarrow=False, font=dict(size=16, color=c["muted"]))],
        )
        return fig

    mean_val = series.mean()
    std_val = series.std()
    current_val = series.iloc[-1]
    pct_rank = _percentile_rank(series, current_val)
    is_pct = "%" in metric or "Yield" in metric or "Margin" in metric

    fig = go.Figure()

    # ±1 std dev band
    fig.add_trace(go.Scatter(
        x=pd.concat([series.index.to_series(), series.index.to_series()[::-1]]),
        y=list(np.full(len(series), mean_val + std_val)) +
          list(np.full(len(series), mean_val - std_val))[::-1],
        fill="toself", fillcolor="rgba(255,165,0,0.07)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip", name="±1 Std Dev", showlegend=True, yaxis="y1",
    ))

    # Mean line
    fig.add_trace(go.Scatter(
        x=series.index, y=[mean_val] * len(series),
        mode="lines", line=dict(color="#ff8c00", width=1, dash="dot"),
        name=f"Mean ({_fmt(mean_val, is_pct)})", yaxis="y1",
    ))

    # Main metric line
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines", line=dict(color="#00aaff", width=2),
        name=metric,
        hovertemplate=(
            "<b>%{x|%d %b %Y}</b><br>"
            f"{metric}: %{{y:.2f}}{'%' if is_pct else 'x'}<extra></extra>"
        ),
        yaxis="y1",
    ))

    # Current dot
    fig.add_trace(go.Scatter(
        x=[series.index[-1]], y=[current_val],
        mode="markers", marker=dict(color="#00ff88", size=10),
        name=f"Current ({_fmt(current_val, is_pct)})",
        hovertemplate=(
            f"Current: {_fmt(current_val, is_pct)}<br>"
            f"{pct_rank:.0f}th percentile<extra></extra>"
        ) if pct_rank is not None else None,
        yaxis="y1",
    ))

    # ── Price overlay on y-axis 2 ─────────────────────────────────────────
    has_price = price_series is not None and not price_series.empty
    if has_price:
        ps = price_series.reindex(
            pd.date_range(series.index.min(), series.index.max(), freq="B"),
            method="ffill",
        ).dropna()
        fig.add_trace(go.Scatter(
            x=ps.index, y=ps.values,
            mode="lines",
            line=dict(color="rgba(255,255,255,0.35)", width=1.5),
            name="Share Price",
            yaxis="y2",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Price: %{y:,.2f}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
        font=dict(family=FONT, color=c["text"], size=11),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=10),
        ),
        margin=dict(l=55, r=65 if has_price else 25, t=40, b=40),
        xaxis=dict(gridcolor="#1a1a1a", zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(
            gridcolor="#1a1a1a", zeroline=False, tickfont=dict(size=10),
            ticksuffix="%" if is_pct else "x",
            title=dict(text=metric, font=dict(size=10, color="#00aaff")),
        ),
        **({"yaxis2": dict(
            overlaying="y", side="right",
            gridcolor="rgba(0,0,0,0)", zeroline=False,
            tickfont=dict(size=10, color="rgba(255,255,255,0.45)"),
            title=dict(text="Price", font=dict(size=10, color="rgba(255,255,255,0.45)")),
            showgrid=False,
        )} if has_price else {}),
        hovermode="x unified",
    )
    return fig


def _make_annual_bar_chart(df_annual: pd.DataFrame, metric: str, theme="dark",
                           price_series: pd.Series = None):
    """Annual bar chart for a margin metric, with optional FY-end price line."""
    c = get_theme(theme)
    # Some metrics have display names that differ from the df column name
    COL_MAP = {"SGA % Sales (Ann)": "SGA % Sales"}
    col = COL_MAP.get(metric, metric)
    s = df_annual[col].dropna() if col in df_annual.columns else pd.Series(dtype=float)

    if s.empty:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
            font=dict(family=FONT, color=c["text"]),
            annotations=[dict(text="No annual data available", x=0.5, y=0.5,
                              xref="paper", yref="paper",
                              showarrow=False, font=dict(size=16, color=c["muted"]))],
        )
        return fig

    # Determine formatting — ratios (Current Ratio, P/Book, Net Debt/EBITDA) are not %
    RATIO_METRICS = {"Current Ratio", "Quick Ratio", "Net Debt/EBITDA", "P/Book"}
    is_pct = metric not in RATIO_METRICS
    suffix = "%" if is_pct else "x"
    fmt = f"{{:.2f}}{suffix}"

    mean_val = s.mean()
    bar_colors = ["#00cc66" if v >= mean_val else "#ff4444" for v in s.values]
    year_labels = [d.strftime("%Y") for d in s.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=year_labels, y=s.values, marker_color=bar_colors,
        name=metric, yaxis="y1",
        hovertemplate=f"<b>FY %{{x}}</b><br>{metric}: %{{y:.2f}}{suffix}<extra></extra>",
    ))

    fig.add_hline(
        y=mean_val, line_color="#ff8c00", line_dash="dot", line_width=1.5,
        annotation_text=f"Mean {mean_val:.2f}{suffix}",
        annotation_position="top left",
        annotation_font=dict(color="#ff8c00", size=10, family=FONT),
    )

    # ── Year-end price overlay ────────────────────────────────────────────
    has_price = price_series is not None and not price_series.empty
    if has_price:
        price_at_ye = []
        for ye_date in s.index:
            valid = price_series[price_series.index <= ye_date]
            price_at_ye.append(float(valid.iloc[-1]) if not valid.empty else None)

        fig.add_trace(go.Scatter(
            x=year_labels, y=price_at_ye,
            mode="lines+markers",
            line=dict(color="rgba(255,255,255,0.45)", width=2, dash="dot"),
            marker=dict(size=6, color="rgba(255,255,255,0.65)"),
            name="Share Price (FY-end)",
            yaxis="y2",
            hovertemplate="<b>FY %{x}</b><br>Price: %{y:,.2f}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
        font=dict(family=FONT, color=c["text"], size=11),
        bargap=0.25,
        margin=dict(l=55, r=65 if has_price else 25, t=30, b=40),
        xaxis=dict(gridcolor="#1a1a1a", zeroline=False, tickfont=dict(size=11)),
        yaxis=dict(
            gridcolor="#1a1a1a", zeroline=True, zerolinecolor="#333",
            tickfont=dict(size=10), ticksuffix=suffix,
        ),
        **({"yaxis2": dict(
            overlaying="y", side="right",
            gridcolor="rgba(0,0,0,0)", zeroline=False,
            tickfont=dict(size=10, color="rgba(255,255,255,0.45)"),
            title=dict(text="Price", font=dict(size=10, color="rgba(255,255,255,0.45)")),
            showgrid=False,
        )} if has_price else {}),
        showlegend=has_price,
        hovermode="x unified",
    )
    return fig


# ── Summary stats bar ─────────────────────────────────────────────────────────

def _make_summary_bar(series: pd.Series, metric: str, C: dict):
    def _stat(label, val, highlight=False):
        is_pct = "%" in metric or "Yield" in metric or "Margin" in metric
        return html.Div([
            html.Div(label, style={"fontSize": "0.55rem", "color": C["muted"],
                                   "fontFamily": FONT, "textTransform": "uppercase",
                                   "letterSpacing": "0.04em", "marginBottom": "0.15rem"}),
            html.Div(_fmt(val, is_pct), style={
                "fontSize": "1.05rem", "fontWeight": "700", "fontFamily": FONT,
                "color": "#00ff88" if highlight else C["text"],
            }),
        ], style={"textAlign": "center", "flex": "1",
                  "borderRight": f"1px solid {C['border']}", "padding": "0.5rem 0.4rem"})

    s = series.dropna()
    if s.empty:
        return html.Div()
    current = s.iloc[-1]
    five_y_slice = s[s.index >= s.index[-1] - pd.DateOffset(years=5)]
    pct_rank = _percentile_rank(s, current)

    return html.Div([
        _stat("Current", current, highlight=True),
        _stat("1Y Avg", s[s.index >= s.index[-1] - pd.DateOffset(years=1)].mean()),
        _stat("5Y Avg", five_y_slice.mean()),
        _stat("5Y High", five_y_slice.max() if not five_y_slice.empty else s.max()),
        _stat("5Y Low",  five_y_slice.min() if not five_y_slice.empty else s.min()),
        html.Div([
            html.Div("%-ile (Max Period)", style={
                "fontSize": "0.55rem", "color": C["muted"], "fontFamily": FONT,
                "textTransform": "uppercase", "letterSpacing": "0.04em",
                "marginBottom": "0.15rem",
            }),
            html.Div(
                f"{pct_rank:.0f}th" if pct_rank is not None else "—",
                style={"fontSize": "1.05rem", "fontWeight": "700", "fontFamily": FONT,
                       "color": (
                           "#ff4444" if pct_rank is not None and pct_rank > 80 else
                           "#00ff88" if pct_rank is not None and pct_rank < 20 else
                           C["text"]
                       )},
            ),
        ], style={"textAlign": "center", "flex": "1", "padding": "0.5rem 0.4rem"}),
    ], style={
        "display": "flex", "backgroundColor": C["panel"],
        "border": f"1px solid {C['border']}", "borderRadius": "6px",
        "marginBottom": "0.5rem",
    })


# ── Snapshot table ────────────────────────────────────────────────────────────

def _make_snapshot_table(df: pd.DataFrame, C: dict):
    if df.empty:
        return html.Div("No data.", style={"color": C["muted"], "fontFamily": FONT,
                                           "fontSize": "0.75rem"})
    headers = ["Metric", "Current", "1Y Avg", "5Y Avg", "All-Time High",
               "All-Time Low", "Pct-ile"]
    header_row = html.Tr([
        html.Th(h, style={
            "color": "#ff8c00", "fontFamily": FONT, "fontSize": "0.6rem",
            "fontWeight": "700", "padding": "0.25rem 0.6rem",
            "borderBottom": f"1px solid {C['border']}",
            "textAlign": "right" if i > 0 else "left",
        }) for i, h in enumerate(headers)
    ])
    rows = []
    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            continue
        is_pct = "%" in col or "Yield" in col or "Margin" in col
        current = s.iloc[-1]
        one_y = s[s.index >= s.index[-1] - pd.DateOffset(years=1)].mean()
        five_y = s[s.index >= s.index[-1] - pd.DateOffset(years=5)].mean()
        pct = _percentile_rank(s, current)
        pct_color = (
            "#ff4444" if pct is not None and pct > 80 else
            "#00ff88" if pct is not None and pct < 20 else C["text"]
        )

        def td(val, color=None, _is_pct=is_pct):
            return html.Td(_fmt(val, _is_pct), style={
                "fontFamily": FONT, "fontSize": "0.72rem",
                "padding": "0.22rem 0.6rem", "textAlign": "right",
                "color": color or C["text"],
                "borderBottom": f"1px solid {C['border']}",
            })

        rows.append(html.Tr([
            html.Td(col, style={"fontFamily": FONT, "fontSize": "0.72rem",
                                "padding": "0.22rem 0.6rem", "color": C["muted"],
                                "borderBottom": f"1px solid {C['border']}"}),
            td(current, color="#00aaff"),
            td(one_y), td(five_y), td(s.max()), td(s.min()),
            html.Td(f"{pct:.0f}th" if pct is not None else "—", style={
                "fontFamily": FONT, "fontSize": "0.72rem",
                "padding": "0.22rem 0.6rem", "textAlign": "right",
                "color": pct_color, "borderBottom": f"1px solid {C['border']}",
            }),
        ]))

    return html.Table([header_row] + rows,
                      style={"width": "100%", "borderCollapse": "collapse"})


# ── Register callbacks ────────────────────────────────────────────────────────

def register_callbacks(app):

    @app.callback(
        Output("val-ticker-suggestions", "children"),
        Input("val-ticker", "value"),
        prevent_initial_call=True,
    )
    def update_val_ticker_suggestions(search):
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
            region = f" · {r['region']}" if r.get("region") else ""
            exch = f" · {r['exchange']}" if r.get("exchange") else ""
            cards.append(html.Button(
                [html.Span(f"{r['ticker']}{region}{exch}", style={"fontWeight": "700"}),
                 html.Span(f"  {r['name']}", style={"marginLeft": "0.35rem"})],
                id={"type": "val-ticker-suggestion", "index": r["ticker_region"]},
                n_clicks=0,
                style={"backgroundColor": "#0b0b0b", "border": "1px solid #2a2a2a",
                       "color": "#e6e6e6", "padding": "0.45rem 0.65rem",
                       "textAlign": "left", "fontFamily": FONT,
                       "fontSize": "0.76rem", "cursor": "pointer"},
            ))
        return cards

    @app.callback(
        Output("val-ticker", "value", allow_duplicate=True),
        Output("val-ticker-suggestions", "children", allow_duplicate=True),
        Input({"type": "val-ticker-suggestion", "index": ALL}, "n_clicks"),
        State({"type": "val-ticker-suggestion", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def choose_val_ticker_suggestion(clicks, ids):
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

    @app.callback(
        Output("val-period-1y",  "style"),
        Output("val-period-3y",  "style"),
        Output("val-period-5y",  "style"),
        Output("val-period-10y", "style"),
        Output("val-period-max", "style"),
        Output("val-period", "data"),
        Input("val-period-1y",  "n_clicks"),
        Input("val-period-3y",  "n_clicks"),
        Input("val-period-5y",  "n_clicks"),
        Input("val-period-10y", "n_clicks"),
        Input("val-period-max", "n_clicks"),
        State("val-period", "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def update_period_buttons(n1, n2, n3, n4, n5, current_period, theme):
        c = get_theme(theme or "dark")
        ctx = dash.callback_context
        period_map = {"val-period-1y": "1Y", "val-period-3y": "3Y",
                      "val-period-5y": "5Y", "val-period-10y": "10Y",
                      "val-period-max": "MAX"}
        active = current_period or "5Y"
        if ctx.triggered:
            active = period_map.get(
                ctx.triggered[0]["prop_id"].split(".")[0], active)
        styles = []
        for p in ["1Y", "3Y", "5Y", "10Y", "MAX"]:
            styles.append({
                "backgroundColor": c["accent"] if p == active else c["panel"],
                "color": "#000" if p == active else c["muted"],
                "border": f"1px solid {c['border']}", "borderRadius": "4px",
                "padding": "0.28rem 0.7rem", "fontFamily": FONT,
                "fontWeight": "700", "fontSize": "0.68rem",
                "cursor": "pointer", "marginRight": "3px",
            })
        return *styles, active

    # ── Main load/render ──────────────────────────────────────────────────
    @app.callback(
        Output("val-chart",        "figure"),
        Output("val-summary-bar",  "children"),
        Output("val-snapshot-table", "children"),
        Output("val-status",       "children"),
        Output("val-data",         "data"),
        Output("val-annual-data",  "data"),
        Output("val-price-data",   "data"),
        Input("val-load-btn",   "n_clicks"),
        Input("val-metric",     "value"),
        Input("val-period",     "data"),
        Input("val-show-price", "value"),
        State("val-ticker",       "value"),
        State("val-data",         "data"),
        State("val-annual-data",  "data"),
        State("val-price-data",   "data"),
        State("theme-store",      "data"),
        State("datasource",       "data"),
        prevent_initial_call=True,
    )
    def load_valuations(n_load, metric, period, show_price,
                        ticker_raw, cached_ltm, cached_annual,
                        cached_price, theme, datasource):
        ctx = dash.callback_context
        if not ctx.triggered:
            return (no_update,) * 7
        if datasource == "yf":
            return go.Figure(), _offline_banner(), _offline_banner(), \
                   "⚠️ Offline mode — Snowflake required", no_update, no_update, no_update

        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        c = get_theme(theme or "dark")
        want_price = bool(show_price)

        # Re-render from cache if only display options changed
        if trigger in ("val-metric", "val-period", "val-show-price") and cached_ltm:
            try:
                df     = _deser(cached_ltm)
                df_ann = _deser(cached_annual) if cached_annual else pd.DataFrame()
                price_s = _deser_price(cached_price) if want_price else None
                fig, summary, snapshot = _render(
                    df, df_ann, metric, period, c, theme, price_s)
                return fig, summary, snapshot, no_update, no_update, no_update, no_update
            except Exception:
                pass

        # Full load
        if not ticker_raw:
            return no_update, no_update, no_update, \
                   "Enter a ticker first.", no_update, no_update, no_update

        ids = _resolve_val_ticker(ticker_raw.strip())
        if not ids:
            return no_update, no_update, no_update, \
                   f"❌ Could not resolve: {ticker_raw}", \
                   no_update, no_update, no_update

        fsym_id   = ids["fsym_id"]
        ticker_fs = ticker_raw.strip().upper()
        name      = ids.get("name", ticker_raw)
        years     = _period_to_years(period or "5Y")

        try:
            df = fetch_valuation_history(fsym_id, years=max(years, 10))
        except Exception as e:
            return no_update, no_update, no_update, \
                   f"❌ {e}", no_update, no_update, no_update

        # Fix order: (fig, summary, snapshot, status, ltm, ann, price)
        if df.empty:
            return no_update, no_update, no_update, \
                   f"No valuation data for {name}.", \
                   no_update, no_update, no_update

        try:
            df_annual = fetch_annual_margins(fsym_id, years=15)
        except Exception:
            df_annual = pd.DataFrame()

        try:
            price_raw    = download_ohlcv(ticker_fs, period="max")
            price_series = price_raw["Close"] if not price_raw.empty \
                           else pd.Series(dtype=float)
        except Exception:
            price_series = pd.Series(dtype=float)

        ltm_cache   = df.reset_index().to_dict("records")
        ann_cache   = (df_annual.reset_index().to_dict("records")
                       if not df_annual.empty else [])
        price_cache = (price_series.rename_axis("Date").reset_index()
                       .rename(columns={0: "Close"})
                       .assign(Close=price_series.values
                               if hasattr(price_series, "values") else [])
                       .to_dict("records")
                       if not price_series.empty else [])

        # Simpler serialisation for price
        if not price_series.empty:
            price_cache = [{"Date": str(d), "Close": float(v)}
                           for d, v in price_series.items()]

        price_s = price_series if want_price else None
        fig, summary, snapshot = _render(
            df, df_annual, metric, period, c, theme, price_s)

        status = (f"✅ {name}  ·  {len(df):,} LTM observations"
                  + (f"  ·  {len(df_annual)} fiscal years"
                     if not df_annual.empty else ""))
        return fig, summary, snapshot, status, ltm_cache, ann_cache, price_cache

    # ── Private helpers (closures) ────────────────────────────────────────

    def _deser(records):
        df = pd.DataFrame(records)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
        return df

    def _deser_price(records):
        if not records:
            return pd.Series(dtype=float)
        df = pd.DataFrame(records)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
        col = "Close" if "Close" in df.columns else df.columns[0]
        return pd.to_numeric(df[col], errors="coerce").dropna()

    def _render(df, df_annual, metric, period, c, theme, price_series=None):
        years  = _period_to_years(period or "5Y")
        cutoff = (df.index.max() - pd.DateOffset(years=years)
                  if not df.empty else None)
        df_slice = df[df.index >= cutoff] if cutoff is not None else df

        # Price sliced to same window for LTM charts
        ps_slice = None
        if price_series is not None and not price_series.empty and cutoff is not None:
            ps_slice = price_series[price_series.index >= cutoff]

        # Annual margin metrics → bar chart
        if metric in ANNUAL_MARGIN_METRICS:
            if df_annual.empty or metric not in df_annual.columns:
                fig = go.Figure()
                fig.update_layout(
                    paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
                    font=dict(family=FONT, color=c["text"]),
                    annotations=[dict(
                        text=f"Annual data not available for '{metric}'",
                        x=0.5, y=0.5, xref="paper", yref="paper",
                        showarrow=False, font=dict(size=14, color=c["muted"]),
                    )],
                )
                return fig, html.Div(), html.Div()

            ann_cutoff = df_annual.index.max() - pd.DateOffset(years=years)
            ann_slice  = df_annual[df_annual.index >= ann_cutoff]
            # For bar chart pass full price series (sampled at FY-end inside)
            price_for_ann = (price_series
                             if price_series is not None and not price_series.empty
                             else None)
            fig      = _make_annual_bar_chart(ann_slice, metric, theme, price_for_ann)
            # For summary bar, resolve display-name → actual column
            COL_MAP  = {"SGA % Sales (Ann)": "SGA % Sales"}
            col      = COL_MAP.get(metric, metric)
            summary  = _make_summary_bar(
                df_annual[col] if col in df_annual.columns else pd.Series(dtype=float),
                metric, c)
            mgn_cols = [c2 for c2 in df_annual.columns
                        if c2 in ANNUAL_MARGIN_METRICS or c2 == "SGA % Sales"]
            snapshot = _make_snapshot_table(df_annual[mgn_cols], c)
            return fig, summary, snapshot

        # LTM multiples → line chart
        if metric not in df_slice.columns:
            fig = go.Figure()
            fig.update_layout(
                paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
                font=dict(family=FONT, color=c["text"]),
                annotations=[dict(
                    text=f"'{metric}' not available for this security",
                    x=0.5, y=0.5, xref="paper", yref="paper",
                    showarrow=False, font=dict(size=14, color=c["muted"]),
                )],
            )
            return fig, html.Div(), html.Div()

        fig      = _make_chart(df_slice[metric], metric, theme, ps_slice)
        summary  = _make_summary_bar(df_slice[metric], metric, c)
        snapshot = _make_snapshot_table(df_slice, c)
        return fig, summary, snapshot
