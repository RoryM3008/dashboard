"""Callback — Portfolio heatmap: size by weight, colour by return."""

import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State, no_update

from theme import FONT, get_theme
from portfolio import load_transactions, compute_holdings, _resolve_ticker


_PERIOD_LABEL = {
    "1d": "1 Day",
    "5d": "1 Week",
    "1mo": "1 Month",
    "3mo": "3 Months",
    "6mo": "6 Months",
    "ytd": "YTD",
    "1y": "1 Year",
}


def register_callbacks(app):

    @app.callback(
        Output("heatmap-portfolio-data", "data"),
        Output("heatmap-status", "children"),
        Input("heatmap-load-port", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_portfolio(n):
        try:
            txns = load_transactions()
            if txns.empty:
                return [], "No transactions found."

            hdf, summary = compute_holdings(txns)
            active = hdf[hdf["shares"] > 0].copy()
            if active.empty:
                return [], "No active holdings to map."

            # equity-only weight (% of securities only, excl. cash)
            total_mv = summary.get("total_mv", 0) or 1

            rows = []
            for _, r in active.iterrows():
                yf_t, _ = _resolve_ticker(r["ticker"])
                mv = float(r.get("market_value", 0) or 0)
                rows.append({
                    "ticker": r["ticker"],
                    "yf_ticker": yf_t,
                    "weight_pct": float(r.get("weight_pct", 0) or 0),
                    "weight_eq": round(mv / total_mv * 100, 1),
                })

            return rows, f"Loaded {len(rows)} holdings from Portfolio."
        except Exception as exc:
            return [], f"Error loading portfolio: {exc}"

    @app.callback(
        Output("heatmap-chart", "children"),
        Output("heatmap-status", "children", allow_duplicate=True),
        Input("heatmap-period", "value"),
        Input("heatmap-portfolio-data", "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def build_heatmap(period, data, theme_mode):
        c = get_theme(theme_mode or "dark")

        if not data:
            return html.Div(), "Load your current portfolio first."

        df = pd.DataFrame(data)
        if df.empty:
            return html.Div(), "No holdings loaded."

        yf_tickers = [t for t in df["yf_ticker"].tolist() if t]
        if not yf_tickers:
            return html.Div(), "No valid tickers available."

        # For 1d period yfinance returns only 1 row, need at least 2 for a return
        dl_period = "5d" if period == "1d" else (period or "1mo")
        is_1d = period == "1d"

        try:
            raw = yf.download(
                tickers=yf_tickers,
                period=dl_period,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
        except Exception as exc:
            return html.Div(), f"Data download error: {exc}"

        if raw is None or raw.empty:
            return html.Div(), "No price history found for selected period."

        if isinstance(raw.columns, pd.MultiIndex):
            close = raw.get("Close")
        else:
            close = raw

        if isinstance(close, pd.Series):
            close = close.to_frame(name=yf_tickers[0])

        close = close.dropna(how="all")
        if close.empty:
            return html.Div(), "No close prices available."

        returns = {}
        for t in yf_tickers:
            if t in close.columns:
                s = close[t].dropna()
                if is_1d:
                    # 1D: use last two available closes (yesterday vs today)
                    if len(s) >= 2 and s.iloc[-2] != 0:
                        returns[t] = round((s.iloc[-1] / s.iloc[-2] - 1) * 100, 2)
                    elif len(s) == 1:
                        returns[t] = 0.0   # only one data point → 0% change
                else:
                    if len(s) >= 2 and s.iloc[0] != 0:
                        returns[t] = round((s.iloc[-1] / s.iloc[0] - 1) * 100, 2)

        plot_rows = []
        for _, r in df.iterrows():
            yft = r["yf_ticker"]
            if yft in returns:
                plot_rows.append({
                    "label": r["ticker"],
                    "weight": max(float(r["weight_pct"]), 0.05),
                    "weight_eq": float(r.get("weight_eq", 0)),
                    "ret_pct": round(float(returns[yft]), 2),
                })

        if not plot_rows:
            return html.Div(), "No overlapping data between holdings and prices."

        plot_df = pd.DataFrame(plot_rows)

        fig = go.Figure(go.Treemap(
            labels=plot_df["label"],
            parents=[""] * len(plot_df),
            values=plot_df["weight"],
            marker={
                "colors": plot_df["ret_pct"],
                "colorscale": [
                    [0.0, "#ff0101"],
                    [0.5, "#222222"],
                    [1.0, "#05ff69"],
                ],
                "cmid": 0,
                "line": {"color": c["border"], "width": 1},
                "colorbar": {"title": "% Move", "tickformat": ".2f"},
            },
            texttemplate="<b>%{label}</b><br>Eq: %{customdata[0]:.1f}%  Tot: %{customdata[1]:.1f}%<br>%{customdata[2]:+.2f}%",
            customdata=plot_df[["weight_eq", "weight", "ret_pct"]].values,
            hovertemplate="<b>%{label}</b><br>Equity Wt: %{customdata[0]:.2f}%<br>Total Wt: %{customdata[1]:.2f}%<br>Move: %{customdata[2]:+.2f}%<extra></extra>",
        ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": FONT, "color": c["text"], "size": 11},
            margin={"l": 10, "r": 10, "t": 35, "b": 10},
            title={"text": f"Portfolio Move Heatmap — {_PERIOD_LABEL.get(period or '1mo', 'Custom')}",
                   "x": 0.5, "font": {"size": 14}},
            height=520,
        )

        shown_weight = plot_df["weight"].sum()
        status = (
            f"Showing {len(plot_df)} holdings. "
            f"Tile size = holding weight (% of total portfolio incl. cash). "
            f"Colour = return over {_PERIOD_LABEL.get(period or '1mo', 'selected period')}. "
            f"Displayed weight sum: {shown_weight:.1f}%"
        )

        return dcc.Graph(
            figure=fig,
            config={"displayModeBar": False},
            style={"height": "520px", "maxWidth": "900px", "margin": "0 auto"},
        ), status
