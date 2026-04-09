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


def _download(ticker: str, period: str, freq: str) -> pd.Series:
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


def _base_layout(c, font, height, margin=None):
    """Minimal Bloomberg-style chart layout."""
    m = margin or dict(l=48, r=12, t=24, b=24)
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
        xaxis=dict(gridcolor=_GRID, zeroline=False, showgrid=True,
                   tickfont=dict(size=9)),
        yaxis=dict(gridcolor=_GRID, zeroline=False, showgrid=True,
                   tickfont=dict(size=9)),
    )


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

        # ── validate ─────────────────────────────────────────────────────
        if not leg_a or not leg_b:
            return no_update, no_update, no_update, no_update, \
                "⚠  Enter both Asset A and Asset B tickers."
        mult_a = float(mult_a or 1)
        mult_b = float(mult_b or 1)
        z_win  = int(z_win or 60)
        leg_a  = leg_a.strip().upper()
        leg_b  = leg_b.strip().upper()

        # ── download + align ─────────────────────────────────────────────
        try:
            pa = _download(leg_a, period, freq)
            pb = _download(leg_b, period, freq)
        except Exception as e:
            return no_update, no_update, no_update, no_update, f"⚠  {e}"

        if pa.empty or pb.empty:
            return no_update, no_update, no_update, no_update, \
                "⚠  No data for one or both tickers."

        df = pd.DataFrame({"A": pa, "B": pb}).dropna()
        if len(df) < 10:
            return no_update, no_update, no_update, no_update, \
                f"⚠  Only {len(df)} overlapping obs — need ≥ 10."

        # ── compute spread ───────────────────────────────────────────────
        a_w = df["A"] * mult_a
        b_w = df["B"] * mult_b

        if stype == "ratio":
            spread = a_w / b_w
            sp_lbl = f"{leg_a}/{leg_b}"
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
        gcfg = {"displayModeBar": False}

        # ─────────────────────────────────────────────────────────────────
        # 1) PRICE OVERLAY (top-left)
        # ─────────────────────────────────────────────────────────────────
        fig_px = go.Figure(layout=_base_layout(c, font, px_h))
        fig_px.update_layout(
            yaxis=dict(title=leg_a, side="left", gridcolor=_GRID),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        zeroline=False, tickfont=dict(size=9)),
        )
        fig_px.add_trace(go.Scatter(
            x=df.index, y=df["A"], name=leg_a, mode="lines",
            line=dict(color="#00e676", width=1.3),
        ))
        fig_px.add_trace(go.Scatter(
            x=df.index, y=df["B"], name=leg_b, mode="lines",
            line=dict(color="#ff5252", width=1.3), yaxis="y2",
        ))
        # last-price annotations at right edge
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
            line=dict(color="#ffeb3b", width=1.5),
            fill="tozeroy", fillcolor="rgba(0,230,118,0.25)",
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

        # ── wrap in dcc.Graph ────────────────────────────────────────────
        gs = {"overflow": "hidden"}
        price_chart  = dcc.Graph(figure=fig_px,   config=gcfg,
                                 style={**gs, "height": ch_h})
        series_chart = dcc.Graph(figure=fig_sp,   config=gcfg,
                                 style={**gs, "height": ch_h})
        hist_chart   = dcc.Graph(figure=fig_hist,  config=gcfg,
                                 style={**gs, "height": ch_h})

        status = (f"{leg_a} vs {leg_b}  ·  {sp_lbl}  ·  "
                  f"{len(spread)} obs  ·  Z = {s_z:+.2f}  ·  "
                  f"Pctile = {s_pct:.1f}%  ·  {freq.title()}")

        return price_chart, series_chart, stat_table, hist_chart, status
