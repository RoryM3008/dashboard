"""Callbacks — Spread Analysis (Bloomberg HS <GO> replica).

Two-column output:
  LEFT:  Price overlay (top) + Spread time-series (bottom)
  RIGHT: Stats table   (top) + Horizontal histogram  (bottom)
"""

import dash
from dash import Input, Output, State, html, dcc, no_update
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yfinance as yf

from theme import get_theme, _panel

# ── helpers ──────────────────────────────────────────────────────────────────

_RESAMPLE = {"daily": None, "weekly": "W-FRI", "monthly": "ME"}
_BG = "#1a1a2e"          # Bloomberg navy
_GRID = "rgba(255,255,255,0.07)"
_AMBER = "#ff8c00"
_AMBER_LT = "rgba(255,140,0,{a})"


def _download(ticker: str, period: str, freq: str,
              start=None, end=None) -> pd.Series:
    tk = yf.Ticker(ticker.strip().upper())
    if period == "custom" and start:
        df = tk.history(start=start, end=end, auto_adjust=True)
    else:
        df = tk.history(period=period, auto_adjust=True)
    if df.empty:
        return pd.Series(dtype=float)
    s = df["Close"]
    s.index = s.index.tz_localize(None)
    rule = _RESAMPLE.get(freq)
    if rule:
        s = s.resample(rule).last().dropna()
    return s


def _base_layout(c, font, height, margin=None):
    """Minimal Bloomberg-style chart layout."""
    m = margin or dict(l=48, r=48, t=24, b=24)
    return dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=font, size=10, color=c["text"]),
        margin=m,
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left",
                    x=0, font=dict(size=9)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(30,30,50,0.9)", font_size=10,
                        font_family=font, font_color="#eee",
                        bordercolor="rgba(255,255,255,0.15)"),
        xaxis=dict(gridcolor=_GRID, zeroline=False, showgrid=True,
                   tickfont=dict(size=9), autorange=True),
        yaxis=dict(gridcolor=_GRID, zeroline=False, showgrid=True,
                   tickfont=dict(size=9), autorange=True),
    )



# ── Valuation metrics ─────────────────────────────────────────────────────────

_VAL_METRICS = [
    ("P/E (Trailing)",       "trailingPE",                    None,      "x"),
    ("P/E (Forward)",        "forwardPE",                     None,      "x"),
    ("EV / EBITDA",          "enterpriseToEbitda",            None,      "x"),
    ("EV / Revenue",         "enterpriseToRevenue",           None,      "x"),
    ("P / Sales",            "priceToSalesTrailingTwelveMonths", None,  "x"),
    ("P / Book",             "priceToBook",                   None,      "x"),
    ("PEG Ratio",            "pegRatio",                      None,      "x"),
    ("Dividend Yield",       "dividendYield",                 lambda v: v * 100, "%"),
    ("Gross Margin",         "grossMargins",                  lambda v: v * 100, "%"),
    ("Operating Margin",     "operatingMargins",              lambda v: v * 100, "%"),
    ("Net Margin",           "profitMargins",                 lambda v: v * 100, "%"),
    ("ROE",                  "returnOnEquity",                lambda v: v * 100, "%"),
    ("ROA",                  "returnOnAssets",                lambda v: v * 100, "%"),
    ("Debt / Equity",        "debtToEquity",                  None,      "x"),
    ("Current Ratio",        "currentRatio",                  None,      "x"),
    ("Revenue Growth (YoY)", "revenueGrowth",                 lambda v: v * 100, "%"),
    ("Earnings Growth (YoY)","earningsGrowth",                lambda v: v * 100, "%"),
]


def _fetch_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker.strip().upper()).info or {}
    except Exception:
        return {}


def _fmt_val(raw, transform, unit):
    if raw is None:
        return None, "—"
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None, "—"
    if transform:
        v = transform(v)
    if unit == "%":
        return v, f"{v:+.2f}%"
    return v, f"{v:.2f}x"


def _spread_badge(a_val, b_val, unit):
    """Return formatted spread string and a -1/0/1 direction for colouring."""
    if a_val is None or b_val is None:
        return "—", 0
    diff = a_val - b_val
    if unit == "%":
        return f"{diff:+.2f}pp", 1 if diff > 0 else (-1 if diff < 0 else 0)
    ratio = (a_val / b_val) if b_val else None
    if ratio is None:
        return "—", 0
    return f"{ratio:.2f}x", 1 if ratio > 1 else (-1 if ratio < 1 else 0)


def _render_valuation_table(leg_a: str, leg_b: str, c: dict, font: str):
    info_a = _fetch_info(leg_a)
    info_b = _fetch_info(leg_b)

    th_s = {
        "padding": "0.3rem 0.6rem", "fontSize": "0.6rem", "fontWeight": "700",
        "textTransform": "uppercase", "letterSpacing": "0.05em",
        "borderBottom": f"2px solid {c['border']}", "fontFamily": font,
        "color": c["muted"], "whiteSpace": "nowrap",
    }
    td_s = {
        "padding": "0.3rem 0.6rem", "fontSize": "0.78rem", "fontFamily": font,
        "color": c["text"], "borderBottom": f"1px solid {c['border']}",
        "whiteSpace": "nowrap",
    }

    header = html.Thead(html.Tr([
        html.Th("Metric",           style={**th_s, "textAlign": "left"}),
        html.Th(leg_a,              style={**th_s, "textAlign": "right", "color": "#00e676"}),
        html.Th(leg_b,              style={**th_s, "textAlign": "right", "color": "#ff5252"}),
        html.Th("Spread (A÷B)",     style={**th_s, "textAlign": "right", "color": c["accent"]}),
    ]))

    rows = []
    for label, key, transform, unit in _VAL_METRICS:
        a_val, a_str = _fmt_val(info_a.get(key), transform, unit)
        b_val, b_str = _fmt_val(info_b.get(key), transform, unit)
        sp_str, direction = _spread_badge(a_val, b_val, unit)

        if direction > 0:
            sp_col, sp_bg = "#00d26a", "rgba(0,210,100,0.12)"
        elif direction < 0:
            sp_col, sp_bg = "#ff5555", "rgba(255,50,50,0.12)"
        else:
            sp_col, sp_bg = c["muted"], "transparent"

        rows.append(html.Tr([
            html.Td(label, style={**td_s, "color": c["subtext"], "fontWeight": "600"}),
            html.Td(a_str, style={**td_s, "textAlign": "right", "fontWeight": "600",
                                   "color": "#00e676" if a_str != "—" else c["muted"]}),
            html.Td(b_str, style={**td_s, "textAlign": "right", "fontWeight": "600",
                                   "color": "#ff5252" if b_str != "—" else c["muted"]}),
            html.Td(sp_str, style={**td_s, "textAlign": "right", "fontWeight": "700",
                                    "color": sp_col, "backgroundColor": sp_bg}),
        ]))

    note = html.Div(
        "Source: Yahoo Finance (TTM / most recent reported). "
        "Spread = A ÷ B for multiples; A − B in percentage-points for margin/growth metrics.",
        style={"color": c["muted"], "fontSize": "0.62rem", "fontFamily": font,
               "marginTop": "0.5rem"},
    )

    return html.Div([
        html.Table([header, html.Tbody(rows)],
                   style={"width": "100%", "borderCollapse": "collapse"}),
        note,
    ])


# ── Historical metric reconstruction ─────────────────────────────────────────

_METRIC_LABELS = {
    "pe":           ("P/E (Trailing)",    "ratio"),
    "ps":           ("P / Sales",         "ratio"),
    "pb":           ("P / Book",          "ratio"),
    "ev_ebitda":    ("EV / EBITDA",       "ratio"),
    "ev_revenue":   ("EV / Revenue",      "ratio"),
    "gross_margin": ("Gross Margin %",    "diff"),
    "op_margin":    ("Operating Margin %","diff"),
    "net_margin":   ("Net Margin %",      "diff"),
}

_PERIOD_MAP = {
    "6mo": "6mo", "1y": "1y", "2y": "2y",
    "3y": "3y",  "5y": "5y", "max": "max",
    "custom": "5y",
}


def _get_row(df, *names):
    """Return first matching row from a financials/balance-sheet DataFrame,
    as a Series with ascending tz-naive DatetimeIndex."""
    for name in names:
        if not df.empty and name in df.index:
            s = df.loc[name].dropna()
            s.index = pd.to_datetime(s.index).tz_localize(None)
            return s.sort_index()
    return pd.Series(dtype=float)


def _ttm(s: pd.Series) -> pd.Series:
    """Rolling 4-quarter trailing-twelve-month sum."""
    if s.empty:
        return pd.Series(dtype=float)
    return s.rolling(4, min_periods=1).sum()


def _ffill_onto(quarterly: pd.Series, daily_prices: pd.Series) -> pd.DataFrame:
    """Left-join quarterly values onto daily price index, forward-fill."""
    merged = daily_prices.to_frame("price").join(
        quarterly.to_frame("q"), how="left"
    )
    merged["q"] = merged["q"].ffill()
    return merged


def _build_metric_series(ticker: str, metric: str, period: str = "5y") -> pd.Series:
    """Reconstruct a historical valuation metric as a daily (or quarterly) time series."""
    yf_period = _PERIOD_MAP.get(period, "5y")
    tk = yf.Ticker(ticker.strip().upper())

    # Price history
    try:
        px_raw = tk.history(period=yf_period, auto_adjust=True)
    except Exception:
        return pd.Series(dtype=float, name=ticker)
    if px_raw.empty:
        return pd.Series(dtype=float, name=ticker)

    prices = px_raw["Close"].copy()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)

    info = tk.info or {}
    shares = float(
        info.get("sharesOutstanding")
        or info.get("impliedSharesOutstanding")
        or 0
    )

    try:
        fin = tk.quarterly_financials
    except Exception:
        fin = pd.DataFrame()
    try:
        bs = tk.quarterly_balance_sheet
    except Exception:
        bs = pd.DataFrame()
    try:
        cf = tk.quarterly_cashflow
    except Exception:
        cf = pd.DataFrame()

    try:
        if metric == "pe":
            if shares == 0:
                return pd.Series(dtype=float, name=ticker)
            ni = _ttm(_get_row(fin, "Net Income"))
            if ni.empty:
                return pd.Series(dtype=float, name=ticker)
            m = _ffill_onto(ni, prices)
            result = (m["price"] * shares) / m["q"]
            return result[(result > 0) & (result < 1000)].rename(ticker)

        elif metric == "ps":
            if shares == 0:
                return pd.Series(dtype=float, name=ticker)
            rev = _ttm(_get_row(fin, "Total Revenue"))
            if rev.empty:
                return pd.Series(dtype=float, name=ticker)
            m = _ffill_onto(rev, prices)
            result = (m["price"] * shares) / m["q"]
            return result[(result > 0) & (result < 500)].rename(ticker)

        elif metric == "pb":
            if shares == 0:
                return pd.Series(dtype=float, name=ticker)
            eq = _get_row(bs, "Stockholders Equity", "Common Stock Equity")
            if eq.empty:
                return pd.Series(dtype=float, name=ticker)
            bvps = eq / shares
            m = _ffill_onto(bvps, prices)
            result = m["price"] / m["q"]
            return result[(result > 0) & (result < 200)].rename(ticker)

        elif metric == "ev_ebitda":
            if shares == 0:
                return pd.Series(dtype=float, name=ticker)
            ebit = _ttm(_get_row(fin, "EBIT", "Operating Income"))
            da = _ttm(_get_row(cf,
                "Depreciation And Amortization", "Reconciled Depreciation")).abs()
            if ebit.empty:
                return pd.Series(dtype=float, name=ticker)
            ebitda = ebit.add(da, fill_value=0) if not da.empty else ebit
            debt_s = _get_row(bs, "Total Debt", "Long Term Debt",
                               "Long Term Debt And Capital Lease Obligation")
            cash_s = _get_row(bs, "Cash And Cash Equivalents",
                               "Cash Cash Equivalents And Short Term Investments")
            m = _ffill_onto(ebitda, prices)
            if not debt_s.empty:
                m = m.join(debt_s.to_frame("debt"), how="left")
                m["debt"] = m["debt"].ffill().fillna(0)
            else:
                m["debt"] = 0.0
            if not cash_s.empty:
                m = m.join(cash_s.to_frame("cash"), how="left")
                m["cash"] = m["cash"].ffill().fillna(0)
            else:
                m["cash"] = 0.0
            m["ev"] = m["price"] * shares + m["debt"] - m["cash"]
            result = m["ev"] / m["q"]
            return result[(result > 0) & (result < 500)].rename(ticker)

        elif metric == "ev_revenue":
            if shares == 0:
                return pd.Series(dtype=float, name=ticker)
            rev = _ttm(_get_row(fin, "Total Revenue"))
            if rev.empty:
                return pd.Series(dtype=float, name=ticker)
            debt_s = _get_row(bs, "Total Debt", "Long Term Debt",
                               "Long Term Debt And Capital Lease Obligation")
            cash_s = _get_row(bs, "Cash And Cash Equivalents",
                               "Cash Cash Equivalents And Short Term Investments")
            m = _ffill_onto(rev, prices)
            if not debt_s.empty:
                m = m.join(debt_s.to_frame("debt"), how="left")
                m["debt"] = m["debt"].ffill().fillna(0)
            else:
                m["debt"] = 0.0
            if not cash_s.empty:
                m = m.join(cash_s.to_frame("cash"), how="left")
                m["cash"] = m["cash"].ffill().fillna(0)
            else:
                m["cash"] = 0.0
            m["ev"] = m["price"] * shares + m["debt"] - m["cash"]
            result = m["ev"] / m["q"]
            return result[(result > 0) & (result < 500)].rename(ticker)

        elif metric == "gross_margin":
            gp = _ttm(_get_row(fin, "Gross Profit"))
            rev = _ttm(_get_row(fin, "Total Revenue"))
            if gp.empty or rev.empty:
                return pd.Series(dtype=float, name=ticker)
            return (gp / rev * 100).rename(ticker)

        elif metric == "op_margin":
            op = _ttm(_get_row(fin, "Operating Income", "EBIT"))
            rev = _ttm(_get_row(fin, "Total Revenue"))
            if op.empty or rev.empty:
                return pd.Series(dtype=float, name=ticker)
            return (op / rev * 100).rename(ticker)

        elif metric == "net_margin":
            ni = _ttm(_get_row(fin, "Net Income"))
            rev = _ttm(_get_row(fin, "Total Revenue"))
            if ni.empty or rev.empty:
                return pd.Series(dtype=float, name=ticker)
            return (ni / rev * 100).rename(ticker)

    except Exception:
        pass

    return pd.Series(dtype=float, name=ticker)


# ── register_callbacks ───────────────────────────────────────────────────────

def register_callbacks(app):

    # ── Show / hide custom date pickers ──────────────────────────────────
    @app.callback(
        Output("spread-date-start-wrap", "style"),
        Output("spread-date-end-wrap", "style"),
        Input("spread-history", "value"),
    )
    def toggle_custom_dates(period):
        show = {"display": "block"} if period == "custom" else {"display": "none"}
        return show, show

    # ── Valuation metrics comparison ──────────────────────────────────────
    @app.callback(
        Output("spread-valuation-table", "children"),
        Output("spread-val-status", "children"),
        Input("spread-run", "n_clicks"),
        State("spread-leg-a", "value"),
        State("spread-leg-b", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def render_valuation(n_clicks, leg_a, leg_b, theme_mode):
        if not n_clicks or not leg_a or not leg_b:
            return no_update, no_update
        c = get_theme(theme_mode or "dark")
        font = "Nunito Sans, sans-serif"
        leg_a = leg_a.strip().upper()
        leg_b = leg_b.strip().upper()
        try:
            table = _render_valuation_table(leg_a, leg_b, c, font)
            return table, f"Showing TTM fundamentals for {leg_a} vs {leg_b}"
        except Exception as exc:
            return html.Div(f"⚠ {exc}", style={"color": c["red"], "fontSize": "0.8rem",
                                                "fontFamily": font}), ""

    # ── Valuation metric history chart ────────────────────────────────────
    @app.callback(
        Output("spread-metric-chart", "children"),
        Output("spread-metric-status", "children"),
        Input("spread-metric-chart-btn", "n_clicks"),
        State("spread-leg-a", "value"),
        State("spread-leg-b", "value"),
        State("spread-metric-select", "value"),
        State("spread-history", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def render_metric_chart(n_clicks, leg_a, leg_b, metric, period, theme_mode):
        from plotly.subplots import make_subplots

        if not n_clicks or not leg_a or not leg_b or not metric:
            return no_update, no_update

        c = get_theme(theme_mode or "dark")
        font = "Nunito Sans, sans-serif"
        leg_a = leg_a.strip().upper()
        leg_b = leg_b.strip().upper()
        label, spread_type = _METRIC_LABELS.get(metric, (metric, "ratio"))
        yf_period = _PERIOD_MAP.get(period or "2y", "2y")

        sa = _build_metric_series(leg_a, metric, yf_period)
        sb = _build_metric_series(leg_b, metric, yf_period)

        if sa.empty and sb.empty:
            return html.Div(
                f"⚠ No data available for {label} on {leg_a} or {leg_b}.",
                style={"color": c["red"], "fontSize": "0.8rem", "fontFamily": font}
            ), ""

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.6, 0.4],
            vertical_spacing=0.06,
        )

        # ── Top panel: A and B metric lines ──────────────────────────────
        if not sa.empty:
            fig.add_trace(go.Scatter(
                x=sa.index, y=sa.values, name=leg_a, mode="lines",
                line=dict(color="#00e676", width=1.5),
            ), row=1, col=1)

        if not sb.empty:
            fig.add_trace(go.Scatter(
                x=sb.index, y=sb.values, name=leg_b, mode="lines",
                line=dict(color="#ff5252", width=1.5),
            ), row=1, col=1)

        # ── Bottom panel: spread ──────────────────────────────────────────
        sp = pd.Series(dtype=float)
        if not sa.empty and not sb.empty:
            if spread_type == "ratio":
                # Align on common index
                combined = pd.concat([sa, sb], axis=1).dropna()
                combined.columns = ["a", "b"]
                sp = combined["a"] / combined["b"].replace(0, np.nan)
                sp_lbl = f"{leg_a}/{leg_b} ratio"
                sp_ytitle = "Ratio (A÷B)"
            else:
                combined = pd.concat([sa, sb], axis=1).dropna()
                combined.columns = ["a", "b"]
                sp = combined["a"] - combined["b"]
                sp_lbl = f"{leg_a}−{leg_b} (pp)"
                sp_ytitle = "Difference (pp)"

        if not sp.empty:
            sp_mean = sp.mean()
            sp_std  = sp.std()
            idx_f = list(sp.index)
            idx_r = idx_f[::-1]

            # ±2σ band
            fig.add_trace(go.Scatter(
                x=idx_f + idx_r,
                y=[sp_mean + 2 * sp_std] * len(sp) + [sp_mean - 2 * sp_std] * len(sp),
                fill="toself", fillcolor="rgba(255,140,0,0.10)",
                line=dict(width=0), name="±2σ", hoverinfo="skip",
            ), row=2, col=1)
            # ±1σ band
            fig.add_trace(go.Scatter(
                x=idx_f + idx_r,
                y=[sp_mean + sp_std] * len(sp) + [sp_mean - sp_std] * len(sp),
                fill="toself", fillcolor="rgba(255,140,0,0.25)",
                line=dict(width=0), name="±1σ", hoverinfo="skip",
            ), row=2, col=1)
            # Spread line
            fig.add_trace(go.Scatter(
                x=sp.index, y=sp.values, name=sp_lbl, mode="lines",
                line=dict(color="#ffeb3b", width=1.5),
                fill="tozeroy", fillcolor="rgba(92,127,43,0.35)",
            ), row=2, col=1)
            # Mean dashed line
            fig.add_hline(y=sp_mean, line_dash="dash", line_width=0.9,
                          line_color="rgba(255,255,255,0.4)", row=2, col=1)

        # ── Layout ───────────────────────────────────────────────────────
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=font, size=10, color=c["text"]),
            height=520,
            margin=dict(l=54, r=48, t=32, b=24),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="left", x=0, font=dict(size=9)),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="rgba(30,30,50,0.9)", font_size=10,
                            font_family=font, font_color="#eee",
                            bordercolor="rgba(255,255,255,0.15)"),
        )
        fig.update_xaxes(gridcolor=_GRID, zeroline=False, tickfont=dict(size=9))
        fig.update_yaxes(gridcolor=_GRID, zeroline=False, tickfont=dict(size=9))
        fig.update_yaxes(title_text=label, row=1, col=1)
        if not sp.empty:
            fig.update_yaxes(title_text=sp_ytitle, row=2, col=1)

        gcfg = {"displayModeBar": True,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "pan2d", "toImage"],
                "displaylogo": False}

        status = (
            f"{label} history for {leg_a} vs {leg_b} · "
            f"{yf_period.upper()} · Quarterly TTM data forward-filled daily"
        )
        return dcc.Graph(figure=fig, config=gcfg,
                         style={"width": "100%"}), status

    @app.callback(
        Output("spread-price-chart", "children"),
        Output("spread-series-chart", "children"),
        Output("spread-stats-table", "children"),
        Output("spread-histogram", "children"),
        Output("spread-relative-chart", "children"),
        Output("spread-status", "children"),
        Input("spread-run", "n_clicks"),
        State("spread-leg-a", "value"),
        State("spread-mult-a", "value"),
        State("spread-leg-b", "value"),
        State("spread-mult-b", "value"),
        State("spread-type", "value"),
        State("spread-history", "value"),
        State("spread-freq", "value"),
        State("spread-zscore-window", "value"),
        State("spread-date-start", "date"),
        State("spread-date-end", "date"),
        State("theme-store", "data"),
    )
    def run_spread(n_clicks, leg_a, mult_a, leg_b, mult_b, stype, period,
                   freq, z_win, date_start, date_end, theme_mode):
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, ""

        c = get_theme(theme_mode or "dark")
        font = "Nunito Sans, sans-serif"

        # ── validate ─────────────────────────────────────────────────────
        if not leg_a or not leg_b:
            return no_update, no_update, no_update, no_update, no_update, \
                "⚠  Enter both Asset A and Asset B tickers."
        mult_a = float(mult_a or 1)
        mult_b = float(mult_b or 1)
        z_win  = int(z_win or 60)
        leg_a  = leg_a.strip().upper()
        leg_b  = leg_b.strip().upper()

        # ── validate custom dates ────────────────────────────────────────
        if period == "custom" and not date_start:
            return no_update, no_update, no_update, no_update, no_update, \
                "⚠  Select a start date for custom period."

        # ── download + align ─────────────────────────────────────────────
        try:
            pa = _download(leg_a, period, freq, start=date_start, end=date_end)
            pb = _download(leg_b, period, freq, start=date_start, end=date_end)
        except Exception as e:
            return no_update, no_update, no_update, no_update, no_update, f"⚠  {e}"

        if pa.empty or pb.empty:
            return no_update, no_update, no_update, no_update, no_update, \
                "⚠  No data for one or both tickers."

        df = pd.DataFrame({"A": pa, "B": pb}).dropna()
        if len(df) < 10:
            return no_update, no_update, no_update, no_update, no_update, \
                f"⚠  Only {len(df)} overlapping obs — need ≥ 10."

        # ── compute spread ───────────────────────────────────────────────
        a_w = df["A"] * mult_a
        b_w = df["B"] * mult_b

        if stype == "ratio":
            spread = a_w / b_w
            sp_lbl = f"{leg_a}/{leg_b}"
        elif stype == "indexed":
            # Rebase both to 100 at start; spread = difference of indexed
            idx_a = (a_w / a_w.iloc[0]) * 100
            idx_b = (b_w / b_w.iloc[0]) * 100
            spread = idx_a - idx_b
            sp_lbl = f"{leg_a} vs {leg_b} (indexed)"
        else:
            spread = a_w - b_w
            sp_lbl = f"{leg_a}−{leg_b}"

        # rolling z
        rm = spread.rolling(z_win, min_periods=max(z_win // 2, 5)).mean()
        rs = spread.rolling(z_win, min_periods=max(z_win // 2, 5)).std()
        z_series = (spread - rm) / rs

        # full-sample stats
        s_last   = spread.iloc[-1]
        s_mean   = spread.mean()
        s_median = spread.median()
        s_std    = spread.std()
        s_z      = (s_last - s_mean) / s_std if s_std else 0.0
        s_pct    = (spread < s_last).mean() * 100
        s_hi     = spread.max()
        s_lo     = spread.min()
        s_hi_dt  = spread.idxmax().strftime("%Y-%m-%d")
        s_lo_dt  = spread.idxmin().strftime("%Y-%m-%d")

        # chart heights — split viewport (minus control bar ~90px)
        ch_h = "calc((100vh - 290px) / 2)"
        px_h = 280   # plotly needs a numeric fallback
        gcfg = {"displayModeBar": True,
                "modeBarButtonsToRemove": ["select2d", "lasso2d",
                    "zoomIn2d", "zoomOut2d", "pan2d", "toImage"],
                "displaylogo": False}

        # ─────────────────────────────────────────────────────────────────
        # 1) PRICE OVERLAY (top-left)
        # ─────────────────────────────────────────────────────────────────
        fig_px = go.Figure(layout=_base_layout(c, font, px_h))

        if stype == "indexed":
            # Indexed performance: both rebased to 100
            idx_a = (df["A"] / df["A"].iloc[0]) * 100
            idx_b = (df["B"] / df["B"].iloc[0]) * 100
            fig_px.update_layout(
                yaxis=dict(title="Indexed (100)", gridcolor=_GRID),
            )
            fig_px.add_trace(go.Scatter(
                x=df.index, y=idx_a, name=leg_a, mode="lines",
                line=dict(color="#00e676", width=1.3),
            ))
            fig_px.add_trace(go.Scatter(
                x=df.index, y=idx_b, name=leg_b, mode="lines",
                line=dict(color="#ff5252", width=1.3),
            ))
            # last-value annotations
            for val, clr, nm in [
                (idx_a.iloc[-1], "#00e676", leg_a),
                (idx_b.iloc[-1], "#ff5252", leg_b),
            ]:
                fig_px.add_annotation(
                    x=df.index[-1], y=val,
                    text=f" {val:,.1f}", showarrow=False,
                    font=dict(color=clr, size=10, family="Consolas"),
                    xanchor="left", bgcolor="rgba(0,0,0,0.6)",
                )
            # Base-100 reference line
            fig_px.add_hline(y=100, line_dash="dot", line_width=0.8,
                             line_color="rgba(255,255,255,0.3)")
        else:
            # Normal dual-axis price overlay
            fig_px.update_layout(
                yaxis=dict(title=leg_a, side="left", gridcolor=_GRID, autorange=True),
                yaxis2=dict(overlaying="y", side="right", showgrid=False,
                            zeroline=False, tickfont=dict(size=9), autorange=True),
            )
            fig_px.add_trace(go.Scatter(
                x=df.index, y=df["A"], name=leg_a, mode="lines",
                line=dict(color="#00e676", width=1.3),
            ))
            fig_px.add_trace(go.Scatter(
                x=df.index, y=df["B"], name=leg_b, mode="lines",
                line=dict(color="#ff5252", width=1.3), yaxis="y2",
            ))
            for val, clr, nm, ya in [
                (df["A"].iloc[-1], "#00e676", leg_a, "y"),
                (df["B"].iloc[-1], "#ff5252", leg_b, "y2"),
            ]:
                fig_px.add_annotation(
                    x=df.index[-1], y=val, yref=ya,
                    text=f" {val:,.2f}", showarrow=False,
                    font=dict(color=clr, size=10, family="Consolas"),
                    xanchor="left", bgcolor="rgba(0,0,0,0.6)",
                )

        # ─────────────────────────────────────────────────────────────────
        # 2) SPREAD TIME SERIES (bottom-left)
        # ─────────────────────────────────────────────────────────────────
        if stype == "zscore":
            ps = z_series.dropna()
            ytitle = "Z-Score"
        else:
            ps = spread
            ytitle = "Spread"

        sp_m = ps.mean()
        sp_s = ps.std()

        fig_sp = go.Figure(layout=_base_layout(c, font, px_h))
        fig_sp.update_layout(yaxis_title=ytitle)

        idx_f = list(ps.index)
        idx_r = list(ps.index[::-1])

        # ±2σ band (lighter green — drawn first, sits behind)
        fig_sp.add_trace(go.Scatter(
            x=idx_f + idx_r,
            y=[sp_m + 2 * sp_s] * len(ps) + [sp_m - 2 * sp_s] * len(ps),
            fill="toself", fillcolor="rgba(255,140,0,0.10)",
            line=dict(width=0), showlegend=True, name="±2σ",
            hoverinfo="skip",
        ))
        # ±1σ band (darker green — on top)
        fig_sp.add_trace(go.Scatter(
            x=idx_f + idx_r,
            y=[sp_m + sp_s] * len(ps) + [sp_m - sp_s] * len(ps),
            fill="toself", fillcolor="rgba(255,140,0,0.25)",
            line=dict(width=0), showlegend=True, name="±1σ",
            hoverinfo="skip",
        ))
        # spread area (green fill, yellow line — 2-D area chart)
        fig_sp.add_trace(go.Scatter(
            x=ps.index, y=ps, name=sp_lbl, mode="lines",
            line=dict(color="#ffeb3b", width=1.5),  # keep yellow line
            fill="tozeroy",
            fillcolor="rgba(92, 127, 43, 0.45)",    # Bloomberg-style green

        ))
        # mean line
        fig_sp.add_hline(y=sp_m, line_dash="dash", line_width=1,
                         line_color="rgba(255,255,255,0.45)",
                         annotation_text="Mean", annotation_position="top left",
                         annotation_font=dict(size=9, color="#aaa"))
        # ±1σ / ±2σ boundary labels
        for v, lbl in [(sp_m + sp_s, "+1σ"), (sp_m - sp_s, "−1σ"),
                        (sp_m + 2 * sp_s, "+2σ"), (sp_m - 2 * sp_s, "−2σ")]:
            fig_sp.add_hline(y=v, line_dash="dot", line_width=0.6,
                             line_color="rgba(255,140,0,0.40)",
                             annotation_text=lbl,
                             annotation_position="top left",
                             annotation_font=dict(size=8, color="#888"))
        # annotate latest value at right edge
        fig_sp.add_annotation(
            x=ps.index[-1], y=ps.iloc[-1],
            text=f"  {ps.iloc[-1]:,.4f}", showarrow=False,
            font=dict(color="#ffeb3b", size=10, family="Consolas"),
            xanchor="left", bgcolor="rgba(0,0,0,0.6)",
        )

        # ─────────────────────────────────────────────────────────────────
        # 3) STATS TABLE (top-right)
        # ─────────────────────────────────────────────────────────────────
        def _f(v, dp=4):
            return f"{v:,.{dp}f}"

        z_clr = "#ff5252" if abs(s_z) > 2 else (
            _AMBER if abs(s_z) > 1 else "#00e676")

        rows = [
            ("Last",        _f(s_last)),
            ("Mean",        _f(s_mean)),
            ("Median",      _f(s_median)),
            ("Std Dev",     _f(s_std)),
            ("Z-Score",     html.Span(_f(s_z, 2),
                                      style={"color": z_clr, "fontWeight": "700"})),
            ("Percentile",  f"{s_pct:.1f}%"),
            ("High",        html.Span([_f(s_hi), html.Br(),
                                       html.Span(s_hi_dt, style={"fontSize": "0.65rem",
                                                                   "color": "#888"})])),
            ("Low",         html.Span([_f(s_lo), html.Br(),
                                       html.Span(s_lo_dt, style={"fontSize": "0.65rem",
                                                                   "color": "#888"})])),
            ("Obs",         str(len(spread))),
        ]

        td_s = {"padding": "0.25rem 0.45rem", "fontSize": "0.74rem",
                "fontFamily": font, "borderBottom": f"1px solid {c['border']}",
                "color": c["text"]}
        th_s = {**td_s, "fontWeight": "700", "fontSize": "0.68rem",
                "color": _AMBER, "letterSpacing": "0.04em"}

        stat_table = html.Div([
            html.Div(f"SPREAD STATISTICS — {sp_lbl}", style={
                "color": _AMBER, "fontSize": "0.7rem", "fontWeight": "700",
                "fontFamily": "Consolas, monospace", "padding": "0.4rem 0.45rem 0.2rem",
                "letterSpacing": "0.04em",
            }),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Metric", style=th_s), html.Th("Value", style=th_s),
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(lbl, style={**td_s, "color": "#aaa"}),
                        html.Td(val, style=td_s),
                    ]) for lbl, val in rows
                ]),
            ], style={"width": "100%", "borderCollapse": "collapse"}),
        ])

        # ─────────────────────────────────────────────────────────────────
        # 4) HORIZONTAL HISTOGRAM (bottom-right)
        # ─────────────────────────────────────────────────────────────────
        clean = ps.dropna()
        n_bins = max(30, min(80, int(np.sqrt(len(clean)) * 1.8)))

        fig_hist = go.Figure(layout=_base_layout(c, font, px_h,
                             margin=dict(l=12, r=12, t=24, b=24)))
        fig_hist.update_layout(
            xaxis_title="Frequency",
            yaxis_title="Spread",
            bargap=0.03,
        )
        # horizontal histogram (normalised to density for bell curve comparison)
        fig_hist.add_trace(go.Histogram(
            y=clean, nbinsy=n_bins, name="Distribution",
            marker_color=_AMBER, opacity=0.6,
            orientation="h", histnorm="probability density",
        ))
        # normal distribution bell curve (horizontal: x=pdf, y=spread values)
        y_range = np.linspace(clean.min(), clean.max(), 300)
        normal_pdf = (1 / (sp_s * np.sqrt(2 * np.pi))) * \
            np.exp(-0.5 * ((y_range - sp_m) / sp_s) ** 2)
        fig_hist.add_trace(go.Scatter(
            x=normal_pdf, y=y_range, mode="lines", name="Normal",
            line=dict(color="#ffffff", width=1.8),
        ))
        # mean horizontal line
        fig_hist.add_hline(y=sp_m, line_dash="dash", line_width=1,
                           line_color="rgba(255,255,255,0.5)",
                           annotation_text="Mean",
                           annotation_font=dict(size=9, color="#aaa"))
        # current spread horizontal line
        fig_hist.add_hline(y=ps.iloc[-1], line_dash="solid", line_width=1.5,
                           line_color="#00e676",
                           annotation_text="Current",
                           annotation_position="top right",
                           annotation_font=dict(size=9, color="#00e676"))

        # ─────────────────────────────────────────────────────────────────
        # 5) RELATIVE RETURN CHART — long A / short B, rebased to 100
        # ─────────────────────────────────────────────────────────────────
        rel_return = (df["A"] / df["A"].iloc[0]) / (df["B"] / df["B"].iloc[0]) * 100
        fig_rel = go.Figure(layout=_base_layout(c, font, px_h))
        fig_rel.update_layout(yaxis_title="Long/Short Return (100)")

        fig_rel.add_trace(go.Scatter(
            x=rel_return.index, y=rel_return,
            name=f"Long {leg_a} / Short {leg_b}",
            mode="lines", line=dict(color="#42a5f5", width=1.5),
            fill="tozeroy", fillcolor="rgba(66,165,245,0.12)",
        ))
        # 100 baseline
        fig_rel.add_hline(y=100, line_dash="dot", line_width=0.8,
                          line_color="rgba(255,255,255,0.35)")
        # latest value annotation
        last_rel = rel_return.iloc[-1]
        rel_clr = "#00e676" if last_rel >= 100 else "#ff5252"
        fig_rel.add_annotation(
            x=rel_return.index[-1], y=last_rel,
            text=f"  {last_rel:,.1f}  ({last_rel - 100:+.1f}%)",
            showarrow=False,
            font=dict(color=rel_clr, size=10, family="Consolas"),
            xanchor="left", bgcolor="rgba(0,0,0,0.6)",
        )

        # ── wrap in dcc.Graph ────────────────────────────────────────────
        gs = {"overflow": "hidden"}
        ch_h3 = "calc((100vh - 290px) / 3)"  # split 3 charts
        price_chart  = dcc.Graph(figure=fig_px,   config=gcfg,
                                 style={**gs, "height": ch_h3})
        series_chart = dcc.Graph(figure=fig_sp,   config=gcfg,
                                 style={**gs, "height": ch_h3})
        rel_chart    = dcc.Graph(figure=fig_rel,   config=gcfg,
                                 style={**gs, "height": ch_h3})
        hist_chart   = dcc.Graph(figure=fig_hist,  config=gcfg,
                                 style={**gs, "height": ch_h})

        status = (f"{leg_a} vs {leg_b}  ·  {sp_lbl}  ·  "
                  f"{len(spread)} obs  ·  Z = {s_z:+.2f}  ·  "
                  f"Pctile = {s_pct:.1f}%  ·  {freq.title()}  ·  "
                  f"Rel Return = {last_rel - 100:+.1f}%")

        return price_chart, series_chart, stat_table, hist_chart, rel_chart, status
