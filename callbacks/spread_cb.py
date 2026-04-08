"""Callbacks — Spread Analysis (Bloomberg HS-style pairs / relative-value)."""

import dash
from dash import Input, Output, State, html, dcc, no_update
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yfinance as yf

from theme import get_theme, _panel

# ── helpers ──────────────────────────────────────────────────────────────────

_RESAMPLE = {"daily": None, "weekly": "W-FRI", "monthly": "ME"}


def _download(ticker: str, period: str, freq: str) -> pd.Series:
    """Download adjusted close, optionally resample."""
    tk = yf.Ticker(ticker.strip().upper())
    df = tk.history(period=period, auto_adjust=True)
    if df.empty:
        return pd.Series(dtype=float)
    s = df["Close"]
    s.index = s.index.tz_localize(None)
    rule = _RESAMPLE.get(freq)
    if rule:
        s = s.resample(rule).last().dropna()
    return s


def _chart_layout(title, c, font, yaxis_title="", y2=False):
    layout = dict(
        template="plotly_dark" if c["bg"] == "#0b0e11" else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=font, size=11, color=c["text"]),
        title=dict(text=title, font=dict(size=13)),
        margin=dict(l=50, r=50, t=40, b=35),
        height=340,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        xaxis=dict(gridcolor=c["border"], zeroline=False),
        yaxis=dict(title=yaxis_title, gridcolor=c["border"], zeroline=False),
    )
    if y2:
        layout["yaxis2"] = dict(
            overlaying="y", side="right", showgrid=False, zeroline=False,
            title="",
        )
    return go.Layout(**layout)


# ── register_callbacks ───────────────────────────────────────────────────────

def register_callbacks(app):

    @app.callback(
        Output("spread-price-chart", "children"),
        Output("spread-series-chart", "children"),
        Output("spread-stats-table", "children"),
        Output("spread-histogram", "children"),
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
        State("theme-store", "data"),
    )
    def run_spread(n_clicks, leg_a, mult_a, leg_b, mult_b, stype, period,
                   freq, z_win, theme_mode):
        if not n_clicks:
            return no_update, no_update, no_update, no_update, ""

        c = get_theme(theme_mode or "dark")
        font = "Nunito Sans, sans-serif"

        # ── Validate inputs ──────────────────────────────────────────────
        if not leg_a or not leg_b:
            msg = "⚠️  Enter both Leg A and Leg B tickers."
            return no_update, no_update, no_update, no_update, msg
        mult_a = float(mult_a or 1)
        mult_b = float(mult_b or 1)
        z_win  = int(z_win or 60)

        leg_a = leg_a.strip().upper()
        leg_b = leg_b.strip().upper()

        # ── Download prices ──────────────────────────────────────────────
        try:
            pa = _download(leg_a, period, freq)
            pb = _download(leg_b, period, freq)
        except Exception as e:
            return no_update, no_update, no_update, no_update, f"⚠️  Download error: {e}"

        if pa.empty or pb.empty:
            return no_update, no_update, no_update, no_update, \
                "⚠️  No data returned for one or both tickers."

        # Align
        df = pd.DataFrame({"A": pa, "B": pb}).dropna()
        if len(df) < 10:
            return no_update, no_update, no_update, no_update, \
                f"⚠️  Only {len(df)} overlapping observations — need ≥ 10."

        # ── Compute spread series ────────────────────────────────────────
        a_w = df["A"] * mult_a
        b_w = df["B"] * mult_b

        if stype == "ratio":
            spread = a_w / b_w
            spread_label = f"{mult_a}×{leg_a} / {mult_b}×{leg_b}"
        else:
            spread = a_w - b_w
            spread_label = f"{mult_a}×{leg_a} − {mult_b}×{leg_b}"

        spread.name = "spread"

        # Rolling Z-score series
        roll_mean = spread.rolling(z_win, min_periods=max(z_win // 2, 5)).mean()
        roll_std  = spread.rolling(z_win, min_periods=max(z_win // 2, 5)).std()
        z_series  = (spread - roll_mean) / roll_std

        # Full-sample stats
        s_last = spread.iloc[-1]
        s_mean = spread.mean()
        s_median = spread.median()
        s_std  = spread.std()
        s_z    = (s_last - s_mean) / s_std if s_std else 0
        s_pct  = (spread < s_last).mean() * 100
        s_hi   = spread.max()
        s_lo   = spread.min()
        s_hi_dt = spread.idxmax().strftime("%Y-%m-%d")
        s_lo_dt = spread.idxmin().strftime("%Y-%m-%d")

        # ── 1) Price overlay chart ───────────────────────────────────────
        fig_px = go.Figure(layout=_chart_layout(
            f"{leg_a} vs {leg_b} — Price Overlay", c, font, yaxis_title=leg_a, y2=True))
        fig_px.add_trace(go.Scatter(
            x=df.index, y=df["A"], name=leg_a, mode="lines",
            line=dict(color=c.get("green", "#00e676"), width=1.4)))
        fig_px.add_trace(go.Scatter(
            x=df.index, y=df["B"], name=leg_b, mode="lines",
            line=dict(color=c.get("red", "#ff5252"), width=1.4), yaxis="y2"))

        # ── 2) Spread time-series chart ──────────────────────────────────
        if stype == "zscore":
            plot_series = z_series.dropna()
            series_title = f"Rolling Z-Score ({z_win}-period) of {spread_label}"
            y_title = "Z-Score"
        else:
            plot_series = spread
            series_title = f"Spread: {spread_label}"
            y_title = "Spread"

        fig_sp = go.Figure(layout=_chart_layout(series_title, c, font, yaxis_title=y_title))
        fig_sp.add_trace(go.Scatter(
            x=plot_series.index, y=plot_series, name="Spread", mode="lines",
            line=dict(color=c.get("accent", "#f5c518"), width=1.5)))

        # Mean + ±1σ / ±2σ bands
        sp_mean_val = plot_series.mean()
        sp_std_val  = plot_series.std()

        # ±2σ band (light amber — drawn first so it sits behind)
        plus2  = sp_mean_val + 2 * sp_std_val
        minus2 = sp_mean_val - 2 * sp_std_val
        fig_sp.add_trace(go.Scatter(
            x=list(plot_series.index) + list(plot_series.index[::-1]),
            y=[plus2] * len(plot_series) + [minus2] * len(plot_series),
            fill="toself", fillcolor="rgba(245,197,24,0.12)",
            line=dict(width=0), showlegend=True, name="±2σ",
            hoverinfo="skip",
        ))
        # ±1σ band (darker amber — on top)
        plus1  = sp_mean_val + sp_std_val
        minus1 = sp_mean_val - sp_std_val
        fig_sp.add_trace(go.Scatter(
            x=list(plot_series.index) + list(plot_series.index[::-1]),
            y=[plus1] * len(plot_series) + [minus1] * len(plot_series),
            fill="toself", fillcolor="rgba(245,197,24,0.30)",
            line=dict(width=0), showlegend=True, name="±1σ",
            hoverinfo="skip",
        ))
        # Mean line
        fig_sp.add_hline(y=sp_mean_val, line_dash="dash", line_width=1.2,
                         line_color=c.get("muted", "#999"),
                         annotation_text="Mean", annotation_position="top left")
        # ±1σ / ±2σ boundary lines (thin dotted)
        for lvl, lbl in [(plus1, "+1σ"), (minus1, "−1σ"),
                          (plus2, "+2σ"), (minus2, "−2σ")]:
            fig_sp.add_hline(y=lvl, line_dash="dot", line_width=0.7,
                             line_color="rgba(245,197,24,0.45)",
                             annotation_text=lbl, annotation_position="top left",
                             annotation_font_size=9)

        # ── 3) Stats table ───────────────────────────────────────────────
        def _fmt(v, dp=4):
            return f"{v:,.{dp}f}"

        z_colour = c.get("red", "#ff5252") if abs(s_z) > 2 else (
            c.get("accent", "#f5c518") if abs(s_z) > 1 else c.get("green", "#00e676"))

        rows = [
            ("Last",           _fmt(s_last)),
            ("Mean",           _fmt(s_mean)),
            ("Median",         _fmt(s_median)),
            ("Std Dev",        _fmt(s_std)),
            ("Z-Score",        html.Span(_fmt(s_z, 2), style={"color": z_colour, "fontWeight": "700"})),
            ("Percentile",     f"{s_pct:.1f} %"),
            ("High",           f"{_fmt(s_hi)}  ({s_hi_dt})"),
            ("Low",            f"{_fmt(s_lo)}  ({s_lo_dt})"),
            ("Observations",   str(len(spread))),
        ]

        tbl_hdr = {"backgroundColor": c["panel"], "padding": "0.35rem 0.6rem",
                    "borderBottom": f"1px solid {c['border']}", "fontWeight": "700",
                    "fontSize": "0.75rem", "fontFamily": font, "color": c["text"]}
        tbl_td  = {"padding": "0.3rem 0.6rem", "fontSize": "0.78rem",
                    "fontFamily": font, "borderBottom": f"1px solid {c['border']}",
                    "color": c["text"]}

        stat_table = html.Table([
            html.Thead(html.Tr([html.Th("Statistic", style=tbl_hdr),
                                html.Th("Value", style=tbl_hdr)])),
            html.Tbody([
                html.Tr([html.Td(lbl, style=tbl_td), html.Td(val, style=tbl_td)])
                for lbl, val in rows
            ]),
        ], style={"width": "100%", "borderCollapse": "collapse"})

        # ── 4) Histogram + Normal curve ────────────────────────────────
        clean = plot_series.dropna()
        n_obs = len(clean)
        # Use Freedman-Diaconis or ~80 bins for smoothness
        n_bins = max(40, min(100, int(np.sqrt(n_obs) * 2)))

        fig_hist = go.Figure(layout=_chart_layout(
            "Spread Distribution", c, font, yaxis_title="Density"))

        # Histogram normalised to density so it matches the bell curve scale
        fig_hist.add_trace(go.Histogram(
            x=clean, nbinsx=n_bins, name="Observed",
            marker_color=c.get("accent", "#f5c518"), opacity=0.65,
            histnorm="probability density",
        ))

        # Normal distribution bell curve overlay
        x_range = np.linspace(clean.min(), clean.max(), 300)
        normal_pdf = (1 / (sp_std_val * np.sqrt(2 * np.pi))) * \
            np.exp(-0.5 * ((x_range - sp_mean_val) / sp_std_val) ** 2)
        fig_hist.add_trace(go.Scatter(
            x=x_range, y=normal_pdf, mode="lines", name="Normal",
            line=dict(color="#ffffff", width=2, dash="solid"),
        ))

        # Reference lines: mean, current, ±1σ, ±2σ
        fig_hist.add_vline(x=sp_mean_val, line_dash="dash", line_width=1.2,
                           line_color=c.get("muted", "#999"),
                           annotation_text="Mean")
        fig_hist.add_vline(x=plot_series.iloc[-1], line_dash="dot", line_width=1.5,
                           line_color=c.get("green", "#00e676"),
                           annotation_text="Current")
        for sigma, lbl in [(1, "±1σ"), (2, "±2σ")]:
            fig_hist.add_vline(x=sp_mean_val + sigma * sp_std_val,
                               line_dash="dot", line_width=0.7,
                               line_color="rgba(245,197,24,0.5)")
            fig_hist.add_vline(x=sp_mean_val - sigma * sp_std_val,
                               line_dash="dot", line_width=0.7,
                               line_color="rgba(245,197,24,0.5)",
                               annotation_text=lbl)
        fig_hist.update_layout(height=320, barmode="overlay")

        # ── Wrap in dcc.Graph ────────────────────────────────────────────
        graph_style = {"borderRadius": "10px", "overflow": "hidden"}
        price_chart = dcc.Graph(figure=fig_px, config={"displayModeBar": False},
                                style=graph_style)
        series_chart = dcc.Graph(figure=fig_sp, config={"displayModeBar": False},
                                 style=graph_style)
        hist_chart = dcc.Graph(figure=fig_hist, config={"displayModeBar": False},
                               style=graph_style)

        status = (f"✅  {leg_a} vs {leg_b}  |  {len(spread)} obs  |  "
                  f"Z = {s_z:+.2f}  |  Pctile = {s_pct:.1f}%")

        return price_chart, series_chart, stat_table, hist_chart, status
