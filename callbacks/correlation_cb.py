"""Callback — Correlation matrix heatmap + table + rolling correlation chart."""

import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State, no_update

from theme import FONT, get_theme
from data import parse_tickers, build_correlation_data
from portfolio import load_transactions, compute_holdings, _resolve_ticker

_ROLL_COLOURS = [
    "#ff8c00", "#4296f5", "#00d26a", "#ff3333", "#a855f7",
    "#e91e8f", "#06b6d4", "#eab308", "#6366f1", "#14b8a6",
]


def register_callbacks(app):

    # ── Load tickers from Portfolio blotter ─────────────────────────────
    @app.callback(
        Output("corr-tickers", "value"),
        Output("corr-load-port-status", "children"),
        Input("corr-load-port", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_portfolio_into_corr(n):
        try:
            txns = load_transactions()
            if txns.empty:
                return no_update, "No transactions found."
            hdf, _ = compute_holdings(txns)
            active = hdf[hdf["shares"] > 0].copy()
            if active.empty:
                return no_update, "No active holdings."
            yf_tickers = []
            for t in active["ticker"]:
                yf_t, _ = _resolve_ticker(t)
                yf_tickers.append(yf_t)
            tickers_str = ", ".join(yf_tickers)
            return tickers_str, f"Loaded {len(yf_tickers)} holdings."
        except Exception as exc:
            return no_update, f"Error: {exc}"

    @app.callback(
        Output("corr-heatmap", "children"),
        Output("corr-table", "children"),
        Output("corr-status", "children"),
        Input("corr-run", "n_clicks"),
        State("corr-tickers", "value"),
        State("corr-frequency", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def calculate_correlation(n, raw_tickers, frequency, theme_mode):
        c = get_theme(theme_mode or "dark")
        tickers = parse_tickers(raw_tickers)
        if len(tickers) < 2:
            msg = "Enter at least 2 tickers to calculate correlations."
            return html.Div(), html.Div(), msg

        corr, available = build_correlation_data(tickers, frequency or "daily")
        if corr is None or corr.empty:
            msg = "No usable return series found for the selected inputs."
            return html.Div(), html.Div(), msg

        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=list(corr.columns),
            y=list(corr.index),
            zmin=-1,
            zmax=1,
            colorscale=[
                [0.0, c["red"]],
                [0.5, c["border"]],
                [1.0, c["green"]],
            ],
            text=corr.values,
            texttemplate="%{text:.2f}",
            hovertemplate="%{y} vs %{x}: %{z:.3f}<extra></extra>",
            colorbar={"title": "Corr"},
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": FONT, "color": c["text"], "size": 11},
            margin={"l": 0, "r": 0, "t": 10, "b": 0},
            xaxis={"side": "top", "tickangle": 0},
            yaxis={"autorange": "reversed"},
            height=max(260, 50 * len(corr.index) + 90),
        )

        header_cells = [
            html.Th("Ticker", style={
                "padding": "0.38rem 0.6rem", "fontSize": "0.62rem", "textTransform": "uppercase",
                "letterSpacing": "0.06em", "fontWeight": "700", "borderBottom": "2px solid " + c["border"],
                "fontFamily": FONT, "color": c["muted"], "textAlign": "left",
            })
        ] + [
            html.Th(col, style={
                "padding": "0.38rem 0.6rem", "fontSize": "0.62rem", "textTransform": "uppercase",
                "letterSpacing": "0.06em", "fontWeight": "700", "borderBottom": "2px solid " + c["border"],
                "fontFamily": FONT, "color": c["muted"], "textAlign": "right",
            })
            for col in corr.columns
        ]

        rows = []
        for row_label in corr.index:
            cells = [html.Td(row_label, style={
                "padding": "0.4rem 0.6rem", "borderBottom": "1px solid " + c["border"],
                "fontSize": "0.78rem", "fontFamily": FONT, "color": c["accent"], "fontWeight": "700",
                "textAlign": "left", "whiteSpace": "nowrap",
            })]

            for col_label in corr.columns:
                val = float(corr.loc[row_label, col_label])
                color = c["green"] if val > 0.4 else (c["red"] if val < -0.4 else c["subtext"])
                cells.append(html.Td(f"{val:.3f}", style={
                    "padding": "0.4rem 0.6rem", "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.78rem", "fontFamily": FONT, "color": color,
                    "textAlign": "right", "whiteSpace": "nowrap",
                }))
            rows.append(html.Tr(cells))

        table = html.Div(
            html.Table([html.Thead(html.Tr(header_cells)), html.Tbody(rows)],
                       style={"width": "100%", "borderCollapse": "collapse"}),
            style={"overflowX": "auto"},
        )

        used = ", ".join(available)
        freq_label = (frequency or "daily").capitalize()
        status = f"Computed {freq_label} return correlations for {len(available)} ticker(s): {used}"

        return dcc.Graph(figure=fig, config={"displayModeBar": False}), table, status

    # ── Rolling correlation chart ─────────────────────────────────────────
    @app.callback(
        Output("rolling-corr-chart",  "children"),
        Output("rolling-corr-status", "children"),
        Input("rolling-corr-run", "n_clicks"),
        State("rolling-corr-base",    "value"),
        State("rolling-corr-others",  "value"),
        State("rolling-corr-window",  "value"),
        State("rolling-corr-history", "value"),
        State("rolling-corr-freq",    "value"),
        State("theme-store",          "data"),
        prevent_initial_call=True,
    )
    def rolling_correlation(n, base_raw, others_raw, window, history, freq, theme_mode):
        c = get_theme(theme_mode or "dark")

        base_tickers = parse_tickers(base_raw)
        other_tickers = parse_tickers(others_raw)

        if not base_tickers or not other_tickers:
            return html.Div(), "Enter a base ticker (A) and at least one comparison ticker (B)."

        base = base_tickers[0]           # single base ticker
        all_tickers = [base] + [t for t in other_tickers if t != base]

        # Download daily close prices (rolling always on daily returns)
        try:
            raw = yf.download(
                tickers=all_tickers,
                period=history or "3y",
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
        except Exception as exc:
            return html.Div(), f"Download error: {exc}"

        if raw is None or raw.empty:
            return html.Div(), "No data returned — check tickers."

        if isinstance(raw.columns, pd.MultiIndex):
            price_df = raw.get("Close")
        else:
            price_df = raw

        if isinstance(price_df, pd.Series):
            price_df = price_df.to_frame(name=all_tickers[0])

        available = [t for t in all_tickers if t in price_df.columns]
        if base not in available:
            return html.Div(), f"No data found for base ticker {base}."

        others_available = [t for t in other_tickers if t in available and t != base]
        if not others_available:
            return html.Div(), "No data for comparison tickers."

        # Resample prices to chosen frequency before computing returns
        freq = freq or "daily"
        _resample_rule = {"weekly": "W-FRI", "monthly": "ME"}
        if freq in _resample_rule:
            price_df = price_df[available].resample(_resample_rule[freq]).last().dropna(how="all")
        returns = price_df[available].pct_change().dropna(how="all")
        window = int(window) if window else 63

        freq_labels = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}
        freq_label = freq_labels.get(freq, "Daily")

        fig = go.Figure()
        for i, other in enumerate(others_available):
            roll = returns[base].rolling(window).corr(returns[other]).dropna()
            colour = _ROLL_COLOURS[i % len(_ROLL_COLOURS)]
            fig.add_trace(go.Scatter(
                x=roll.index, y=roll.values,
                mode="lines",
                name=f"{base} vs {other}",
                line={"color": colour, "width": 1.8},
                hovertemplate=f"{base} vs {other}: " + "%{y:.3f}<extra></extra>",
            ))

        # Reference lines
        for lvl, dash_style in [(0, "solid"), (0.5, "dot"), (-0.5, "dot")]:
            fig.add_hline(y=lvl, line_dash=dash_style,
                          line_color=c["muted"], line_width=0.8,
                          annotation_text=str(lvl) if lvl != 0 else None,
                          annotation_font_size=9, annotation_font_color=c["muted"])

        window_labels = {5: "1W", 10: "2W", 21: "1M", 63: "3M", 126: "6M", 252: "1Y"}
        win_label = window_labels.get(window, f"{window}d")

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": FONT, "color": c["text"], "size": 11},
            margin={"l": 45, "r": 15, "t": 30, "b": 40},
            height=380,
            yaxis={"title": "Correlation", "range": [-1.05, 1.05],
                   "gridcolor": c["border"], "zerolinecolor": c["muted"]},
            xaxis={"gridcolor": c["border"]},
            legend={"orientation": "h", "y": -0.15, "x": 0.5, "xanchor": "center",
                    "font": {"size": 10}},
            title={"text": f"Rolling {win_label} Correlation ({freq_label} Returns)",
                   "font": {"size": 13}, "x": 0.5},
        )

        pairs_str = ", ".join(f"{base} vs {t}" for t in others_available)
        status = f"{win_label} rolling window  •  {freq_label} returns  •  {pairs_str}"

        return dcc.Graph(figure=fig, config={"displayModeBar": False}), status
