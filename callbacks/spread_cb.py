"""Callbacks — Spread Analysis (Bloomberg HS-style pairs / relative-value)."""

from dash import Input, Output, State, html, dcc, no_update
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yfinance as yf

from theme import get_theme

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


def _chart_layout(title, c, font, yaxis_title="", y2=False, height=300):
    bloom_grid = "rgba(150, 176, 195, 0.38)"
    bloom_text = "#dce3ea"
    layout = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#162431",
        font=dict(family=font, size=11, color=bloom_text),
        title=dict(text=title, font=dict(size=13, color="#f5c14a"), x=0.01, xanchor="left"),
        margin=dict(l=44, r=40, t=44, b=30),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=0.99,
                    bgcolor="rgba(7,12,18,0.72)", bordercolor="#2c3a46", borderwidth=1),
        hovermode="x unified",
        xaxis=dict(
            gridcolor=bloom_grid,
            griddash="dot",
            zeroline=False,
            tickfont=dict(color=bloom_text),
            linecolor="#415262",
            mirror=True,
        ),
        yaxis=dict(
            title=yaxis_title,
            gridcolor=bloom_grid,
            griddash="dot",
            zeroline=False,
            tickfont=dict(color=bloom_text),
            linecolor="#415262",
            mirror=True,
        ),
    )
    if y2:
        layout["yaxis2"] = dict(
            overlaying="y", side="right", showgrid=False, zeroline=False,
            title="",
            tickfont=dict(color=bloom_text),
            linecolor="#415262",
            mirror=True,
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
            f"{leg_a} vs {leg_b} — Price Overlay", c, font, yaxis_title=leg_a, y2=True, height=340))
        fig_px.add_trace(go.Scatter(
            x=df.index, y=df["A"], name=leg_a, mode="lines",
            line=dict(color="#d7dde3", width=1.4)))
        fig_px.add_trace(go.Scatter(
            x=df.index, y=df["B"], name=leg_b, mode="lines",
            line=dict(color="#f7a211", width=1.6), yaxis="y2"))
        fig_px.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(7,12,18,0.72)",
                bordercolor="#2c3a46",
                borderwidth=1,
            ),
            margin=dict(l=44, r=40, t=48, b=30),
        )

        # Add quick read hi/low tags similar to Bloomberg overlays.
        a_hi_idx = df["A"].idxmax()
        a_lo_idx = df["A"].idxmin()
        fig_px.add_annotation(x=a_hi_idx, y=df.loc[a_hi_idx, "A"], text=f"Hi: {df['A'].max():.2f}",
                              font=dict(color="#d7dde3", size=10), showarrow=False,
                              xanchor="left", yanchor="bottom", bgcolor="rgba(10,14,20,0.45)")
        fig_px.add_annotation(x=a_lo_idx, y=df.loc[a_lo_idx, "A"], text=f"Low: {df['A'].min():.2f}",
                              font=dict(color="#d7dde3", size=10), showarrow=False,
                              xanchor="left", yanchor="top", bgcolor="rgba(10,14,20,0.45)")

        # ── 2) Spread time-series chart ──────────────────────────────────
        if stype == "zscore":
            plot_series = z_series.dropna()
            series_title = f"Rolling Z-Score ({z_win}-period) of {spread_label}"
            y_title = "Z-Score"
        else:
            plot_series = spread
            series_title = f"Spread: {spread_label}"
            y_title = "Spread"

        fig_sp = go.Figure(layout=_chart_layout(series_title, c, font, yaxis_title=y_title, height=340))
        fig_sp.add_trace(go.Scatter(
            x=plot_series.index, y=plot_series, name="Spread", mode="lines",
            line=dict(color="#d8b63e", width=1.7),
            fill="tozeroy",
            fillcolor="rgba(96, 170, 42, 0.55)"))
        fig_sp.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(7,12,18,0.72)",
                bordercolor="#2c3a46",
                borderwidth=1,
                groupclick="togglegroup",
            ),
            margin=dict(l=44, r=40, t=48, b=30),
        )

        # Mean + ±1σ / ±2σ bands
        sp_mean_val = plot_series.mean()
        sp_std_val  = plot_series.std()

        # ±2σ band (light amber — drawn first so it sits behind)
        plus2  = sp_mean_val + 2 * sp_std_val
        minus2 = sp_mean_val - 2 * sp_std_val
        fig_sp.add_trace(go.Scatter(
            x=list(plot_series.index) + list(plot_series.index[::-1]),
            y=[plus2] * len(plot_series) + [minus2] * len(plot_series),
            fill="toself", fillcolor="rgba(245,197,24,0.09)",
            line=dict(width=0), showlegend=False, name="Std Dev Bands",
            legendgroup="stddev",
            hoverinfo="skip",
        ))
        # ±1σ band (darker amber — on top)
        plus1  = sp_mean_val + sp_std_val
        minus1 = sp_mean_val - sp_std_val
        fig_sp.add_trace(go.Scatter(
            x=list(plot_series.index) + list(plot_series.index[::-1]),
            y=[plus1] * len(plot_series) + [minus1] * len(plot_series),
            fill="toself", fillcolor="rgba(245,197,24,0.18)",
            line=dict(width=0), showlegend=True, name="Std Dev Bands",
            legendgroup="stddev",
            hoverinfo="skip",
        ))
        fig_sp.add_trace(go.Scatter(
            x=plot_series.index,
            y=[sp_mean_val] * len(plot_series),
            name="Mean",
            mode="lines",
            line=dict(color="#cfd5dd", width=1.1, dash="dash"),
            hoverinfo="skip",
        ))
        for lvl, lbl in [(plus1, "+1σ"), (minus1, "−1σ"),
                         (plus2, "+2σ"), (minus2, "−2σ")]:
            fig_sp.add_trace(go.Scatter(
                x=plot_series.index,
                y=[lvl] * len(plot_series),
                name=lbl,
                mode="lines",
                line=dict(color="rgba(245,197,24,0.42)", width=0.7, dash="dot"),
                hoverinfo="skip",
                showlegend=False,
                legendgroup="stddev",
            ))

        sp_hi_idx = plot_series.idxmax()
        sp_lo_idx = plot_series.idxmin()
        fig_sp.add_annotation(x=sp_hi_idx, y=plot_series.max(), text=f"Hi: {plot_series.max():.2f}",
                      font=dict(color="#f5c14a", size=10), showarrow=False,
                      xanchor="left", yanchor="bottom")
        fig_sp.add_annotation(x=sp_lo_idx, y=plot_series.min(), text=f"Low: {plot_series.min():.2f}",
                      font=dict(color="#f5c14a", size=10), showarrow=False,
                      xanchor="left", yanchor="top")

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

        tbl_hdr = {"backgroundColor": "#090c12", "padding": "0.28rem 0.4rem",
                "borderBottom": "1px solid #2f3a47", "fontWeight": "700",
                "fontSize": "0.72rem", "fontFamily": font, "color": "#f0f3f6"}
        tbl_td_lbl = {"padding": "0.22rem 0.4rem", "fontSize": "0.78rem",
                  "fontFamily": font, "borderBottom": "1px solid #24303d",
                  "color": "#f0ad30"}
        tbl_td_val = {"padding": "0.22rem 0.4rem", "fontSize": "0.78rem",
                  "fontFamily": font, "borderBottom": "1px solid #24303d",
                  "color": "#f2f5f8"}

        stat_table = html.Table([
            html.Thead(html.Tr([html.Th("Statistic", style=tbl_hdr),
                                html.Th("Value", style=tbl_hdr)])),
            html.Tbody([
                html.Tr([html.Td(lbl, style=tbl_td_lbl), html.Td(val, style=tbl_td_val)])
                for lbl, val in rows
            ]),
        ], style={"width": "100%", "borderCollapse": "collapse", "backgroundColor": "#05080d"})

        # ── 4) Histogram + Normal curve ────────────────────────────────
        clean = plot_series.dropna()
        n_obs = len(clean)
        # Use Freedman-Diaconis or ~80 bins for smoothness
        n_bins = max(40, min(100, int(np.sqrt(n_obs) * 2)))

        fig_hist = go.Figure(layout=_chart_layout(
            "", c, font, yaxis_title="Spread", height=370))

        hist_vals, bin_edges = np.histogram(clean, bins=n_bins)
        y_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_h = (bin_edges[1] - bin_edges[0]) if len(bin_edges) > 1 else 1.0

        fig_hist.add_trace(go.Bar(
            x=hist_vals,
            y=y_centers,
            orientation="h",
            name="Observed",
            marker_color="rgba(115, 203, 36, 0.78)",
            marker_line=dict(color="rgba(55, 92, 24, 0.92)", width=0.2),
        ))

        # Normal distribution curve scaled to bar counts
        if sp_std_val and sp_std_val > 0:
            y_curve = np.linspace(clean.min(), clean.max(), 320)
            normal_pdf = (1 / (sp_std_val * np.sqrt(2 * np.pi))) * \
                np.exp(-0.5 * ((y_curve - sp_mean_val) / sp_std_val) ** 2)
            scaled_counts = normal_pdf * len(clean) * bin_h
            fig_hist.add_trace(go.Scatter(
                x=scaled_counts,
                y=y_curve,
                mode="lines",
                name="Normal",
                line=dict(color="#e4a327", width=2.0, dash="solid"),
            ))

        # Reference lines: mean, current, ±1σ, ±2σ
        max_count = float(hist_vals.max()) if len(hist_vals) else 1.0
        fig_hist.add_hline(y=sp_mean_val, line_dash="dash", line_width=1.1,
                           line_color="#cfd5dd", annotation_text="Mean")
        fig_hist.add_hline(y=plot_series.iloc[-1], line_dash="dot", line_width=1.3,
                           line_color="#f0ad30", annotation_text="Current")
        for sigma, lbl in [(1, "±1σ"), (2, "±2σ")]:
            fig_hist.add_hline(y=sp_mean_val + sigma * sp_std_val,
                               line_dash="dot", line_width=0.7,
                               line_color="rgba(245,197,24,0.5)")
            fig_hist.add_hline(y=sp_mean_val - sigma * sp_std_val,
                               line_dash="dot", line_width=0.7,
                               line_color="rgba(245,197,24,0.5)",
                               annotation_text=lbl)

        fig_hist.update_layout(
            height=370,
            barmode="overlay",
            margin=dict(l=48, r=16, t=4, b=34),
            xaxis=dict(
                title="Count",
                gridcolor="rgba(150, 176, 195, 0.24)",
                griddash="dot",
                zeroline=False,
                range=[0, max_count * 1.2],
                tickfont=dict(color="#dce3ea"),
                linecolor="#415262",
                mirror=True,
            ),
            yaxis=dict(
                title="Spread",
                gridcolor="rgba(150, 176, 195, 0.24)",
                griddash="dot",
                zeroline=False,
                tickfont=dict(color="#dce3ea"),
                linecolor="#415262",
                mirror=True,
            ),
            legend=dict(orientation="h", yanchor="top", y=0.97, xanchor="left", x=0.02,
                        bgcolor="rgba(0,0,0,0)", borderwidth=0),
        )

        # ── Wrap in dcc.Graph ────────────────────────────────────────────
        graph_style = {"borderRadius": "4px", "overflow": "hidden", "border": "1px solid #2d3a46", "width": "100%"}
        price_chart = dcc.Graph(figure=fig_px, config={"displayModeBar": False},
                                style=graph_style)
        series_chart = dcc.Graph(figure=fig_sp, config={"displayModeBar": False},
                                 style=graph_style)
        hist_chart = dcc.Graph(figure=fig_hist, config={"displayModeBar": False},
                               style=graph_style)

        status = (f"✅  {leg_a} vs {leg_b}  |  {len(spread)} obs  |  "
                  f"Z = {s_z:+.2f}  |  Pctile = {s_pct:.1f}%")

        return price_chart, series_chart, stat_table, hist_chart, status
