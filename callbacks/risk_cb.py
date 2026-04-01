"""Callback — Risk Contribution: snapshot table + rolling chart."""

import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State, no_update

from theme import FONT, get_theme
from data import parse_tickers, risk_contrib, rolling_risk_contrib
from portfolio import load_transactions, compute_holdings, _resolve_ticker

_COLOURS = [
    "#ff8c00", "#4296f5", "#00d26a", "#ff3333", "#a855f7",
    "#e91e8f", "#06b6d4", "#eab308", "#6366f1", "#14b8a6",
    "#f97316", "#8b5cf6", "#22d3ee", "#84cc16", "#fb7185",
]


def _parse_weights(raw):
    """Parse a comma-separated string of numbers into a list of floats."""
    if not raw:
        return []
    import re
    parts = re.split(r"[\s,;]+", raw.strip())
    out = []
    for p in parts:
        try:
            out.append(float(p))
        except ValueError:
            pass
    return out


def _download_returns(tickers, period="3y"):
    """Download daily close prices and return a returns DataFrame."""
    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if raw is None or raw.empty:
        return None

    if isinstance(raw.columns, pd.MultiIndex):
        price_df = raw.get("Close")
    else:
        price_df = raw

    if isinstance(price_df, pd.Series):
        price_df = price_df.to_frame(name=tickers[0])

    return price_df.pct_change().dropna(how="all")


def register_callbacks(app):

    # ── Load tickers + weights from Portfolio blotter ──────────────────
    @app.callback(
        Output("risk-tickers", "value"),
        Output("risk-weights", "value"),
        Output("risk-load-port-status", "children"),
        Input("risk-load-port", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_portfolio_into_risk(n):
        try:
            txns = load_transactions()
            if txns.empty:
                return no_update, no_update, "No transactions found."
            hdf, _ = compute_holdings(txns)
            active = hdf[hdf["shares"] > 0].copy()
            if active.empty:
                return no_update, no_update, "No active holdings."
            # Resolve to Yahoo tickers for downstream yfinance calls
            yf_tickers = []
            for t in active["ticker"]:
                yf_t, _ = _resolve_ticker(t)
                yf_tickers.append(yf_t)
            tickers_str = ", ".join(yf_tickers)
            weights_str = ", ".join(f"{w / 100:.4f}" for w in active["weight_pct"])
            n_stocks = len(yf_tickers)
            return tickers_str, weights_str, f"Loaded {n_stocks} holdings."
        except Exception as exc:
            return no_update, no_update, f"Error: {exc}"

    @app.callback(
        Output("risk-snapshot-table", "children"),
        Output("risk-rolling-chart",  "children"),
        Output("risk-status",         "children"),
        Input("risk-run", "n_clicks"),
        State("risk-tickers",   "value"),
        State("risk-weights",   "value"),
        State("risk-benchmark", "value"),
        State("risk-window",    "value"),
        State("risk-history",   "value"),
        State("theme-store",    "data"),
        prevent_initial_call=True,
    )
    def compute_risk(n, raw_tickers, raw_weights, raw_bench, window, history, theme_mode):
        c = get_theme(theme_mode or "dark")

        tickers = parse_tickers(raw_tickers)
        weights = _parse_weights(raw_weights)

        if len(tickers) < 1:
            return html.Div(), html.Div(), "Enter at least one ticker."
        if len(weights) == 0:
            # Equal-weight fallback
            weights = [1.0 / len(tickers)] * len(tickers)
        if len(weights) != len(tickers):
            return html.Div(), html.Div(), (
                f"Mismatch: {len(tickers)} tickers but {len(weights)} weights."
            )

        weights_s = pd.Series(weights, index=tickers)
        weights_s = weights_s / weights_s.sum()   # normalise

        # Determine benchmark
        benchmark = parse_tickers(raw_bench)
        all_tickers = list(tickers)
        bench_ticker = None
        if benchmark:
            bench_ticker = benchmark[0]
            if bench_ticker not in all_tickers:
                all_tickers.append(bench_ticker)

        # Download
        returns_df = _download_returns(all_tickers, period=history or "3y")
        if returns_df is None or returns_df.empty:
            return html.Div(), html.Div(), "No return data available — check tickers."

        # If benchmark, compute active (excess) returns
        if bench_ticker and bench_ticker in returns_df.columns:
            bench_ret = returns_df[bench_ticker]
            for t in tickers:
                if t in returns_df.columns:
                    returns_df[t] = returns_df[t] - bench_ret
            # Drop the benchmark column from the returns used for risk decomposition
            returns_df = returns_df[[t for t in tickers if t in returns_df.columns]]
        else:
            returns_df = returns_df[[t for t in tickers if t in returns_df.columns]]

        available = list(returns_df.columns)
        weights_s = weights_s.reindex(available).dropna()
        if weights_s.empty:
            return html.Div(), html.Div(), "No overlapping data for tickers + weights."
        weights_s = weights_s / weights_s.sum()

        window = int(window) if window else 63

        # ── Snapshot table ────────────────────────────────────────────────
        snap, port_vol = risk_contrib(returns_df, weights_s)
        ann_factor = (252 ** 0.5)
        ann_vol = port_vol * ann_factor

        vol_label = "Tracking Error" if bench_ticker else "Portfolio Volatility"

        th_style = {
            "padding": "0.35rem 0.6rem", "fontSize": "0.62rem",
            "textTransform": "uppercase", "letterSpacing": "0.06em",
            "fontWeight": "700", "whiteSpace": "nowrap",
            "borderBottom": f"2px solid {c['border']}",
            "fontFamily": FONT, "color": c["muted"],
        }
        td_style = {
            "padding": "0.35rem 0.6rem", "fontSize": "0.78rem",
            "fontFamily": FONT, "color": c["text"],
            "borderBottom": f"1px solid {c['border']}",
            "whiteSpace": "nowrap",
        }

        header = html.Thead(html.Tr([
            html.Th("Ticker",   style={**th_style, "textAlign": "left"}),
            html.Th("Weight",   style={**th_style, "textAlign": "right"}),
            html.Th("MCR",      style={**th_style, "textAlign": "right"}),
            html.Th("Risk Cont", style={**th_style, "textAlign": "right"}),
            html.Th("% of TE" if bench_ticker else "% of Vol",
                     style={**th_style, "textAlign": "right"}),
        ]))

        rows = []
        for ticker in snap.index:
            r = snap.loc[ticker]
            pct_val = r["pct_RC"] * 100
            colour = c["red"] if pct_val > 15 else (c["green"] if pct_val < 5 else c["text"])
            rows.append(html.Tr([
                html.Td(ticker, style={**td_style, "textAlign": "left",
                                        "fontWeight": "700", "color": c["accent"]}),
                html.Td(f"{r['weight']:.1%}", style={**td_style, "textAlign": "right"}),
                html.Td(f"{r['MCR']*ann_factor:.4f}", style={**td_style, "textAlign": "right"}),
                html.Td(f"{r['RC']*ann_factor:.4f}", style={**td_style, "textAlign": "right"}),
                html.Td(f"{pct_val:.1f}%",
                         style={**td_style, "textAlign": "right", "color": colour,
                                "fontWeight": "700"}),
            ]))

        # Totals row
        rows.append(html.Tr([
            html.Td("Total", style={**td_style, "textAlign": "left",
                                     "fontWeight": "700", "color": c["blue"]}),
            html.Td(f"{snap['weight'].sum():.1%}", style={**td_style, "textAlign": "right",
                                                           "fontWeight": "700"}),
            html.Td("", style=td_style),
            html.Td(f"{ann_vol:.4f}", style={**td_style, "textAlign": "right",
                                              "fontWeight": "700"}),
            html.Td("100.0%", style={**td_style, "textAlign": "right", "fontWeight": "700"}),
        ]))

        summary = (f"Annualised {vol_label}: {ann_vol:.4f}  "
                   f"({ann_vol*100:.2f}%)  •  Daily σ: {port_vol:.6f}")

        table = html.Table(
            [header, html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        )

        # ── Rolling chart ─────────────────────────────────────────────────
        pct_RC_df, port_vol_s = rolling_risk_contrib(returns_df, weights_s, window=window)

        # Pick top 20 by latest absolute contribution
        latest = pct_RC_df.iloc[-1].abs().sort_values(ascending=False)
        top = list(latest.index[:20])

        fig = go.Figure()
        for i, ticker in enumerate(top):
            colour = _COLOURS[i % len(_COLOURS)]
            fig.add_trace(go.Scatter(
                x=pct_RC_df.index,
                y=(pct_RC_df[ticker] * 100).values,
                mode="lines",
                name=ticker,
                line={"color": colour, "width": 1.5},
                hovertemplate=f"{ticker}: " + "%{y:.1f}%<extra></extra>",
            ))

        win_labels = {21: "1M", 63: "3M", 126: "6M", 252: "1Y"}
        win_lbl = win_labels.get(window, f"{window}d")

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": FONT, "color": c["text"], "size": 11},
            margin={"l": 50, "r": 15, "t": 35, "b": 40},
            height=400,
            yaxis={"title": "% Contribution to TE" if bench_ticker else "% Contribution to Vol",
                   "gridcolor": c["border"], "zerolinecolor": c["muted"],
                   "ticksuffix": "%"},
            xaxis={"gridcolor": c["border"]},
            legend={"orientation": "h", "y": -0.18, "x": 0.5, "xanchor": "center",
                    "font": {"size": 10}},
                 title={"text": f"Rolling {win_lbl} % Risk Contribution (Top 20)",
                   "font": {"size": 13}, "x": 0.5},
        )

        status = (f"{summary}  •  Rolling window: {win_lbl}"
                  + (f"  •  Benchmark: {bench_ticker}" if bench_ticker else ""))

        return table, dcc.Graph(figure=fig, config={"displayModeBar": False}), status
