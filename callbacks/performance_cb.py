"""Callback — Portfolio Performance chart + weights table."""

import re

import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State

from theme import FONT, get_theme
from data import parse_tickers, build_portfolio_performance_data


def register_callbacks(app):

    @app.callback(
        Output("perf-chart", "children"),
        Output("perf-weights-table", "children"),
        Output("perf-status", "children"),
        Input("perf-run", "n_clicks"),
        State("perf-tickers", "value"),
        State("perf-weights", "value"),
        State("perf-frequency", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def calculate_portfolio_performance(n, raw_tickers, raw_weights, frequency, theme_mode):
        c = get_theme(theme_mode or "dark")
        tickers = parse_tickers(raw_tickers)
        if len(tickers) < 1:
            return html.Div(), html.Div(), "Enter at least one ticker."

        weight_tokens = [w for w in re.split(r"[\s,;]+", (raw_weights or "").strip()) if w]
        if len(weight_tokens) != len(tickers):
            msg = "Provide exactly one weight per ticker (same order)."
            return html.Div(), html.Div(), msg

        weights = []
        for token in weight_tokens:
            try:
                weights.append(float(token.replace("%", "")))
            except Exception:
                msg = "Weights must be numeric (e.g. 25, 25, 25, 25)."
                return html.Div(), html.Div(), msg

        if any(w > 1 for w in weights):
            weights = [w / 100 for w in weights]

        if sum(weights) <= 0:
            return html.Div(), html.Div(), "Total weight must be greater than zero."

        port_index, component_index, used_weights = build_portfolio_performance_data(
            tickers, weights, frequency or "weekly"
        )
        if port_index is None or component_index is None or used_weights is None:
            return html.Div(), html.Div(), "No usable price history found for these inputs."

        fig = go.Figure()
        for ticker in component_index.columns:
            fig.add_trace(go.Scatter(
                x=component_index.index,
                y=component_index[ticker],
                mode="lines",
                line={"width": 1.2, "color": c["muted"]},
                opacity=0.5,
                name=ticker,
                hovertemplate=f"{ticker}: %{{y:.2f}}<extra></extra>",
            ))

        fig.add_trace(go.Scatter(
            x=port_index.index,
            y=port_index,
            mode="lines",
            line={"width": 3, "color": c["accent"]},
            name="Portfolio",
            hovertemplate="Portfolio: %{y:.2f}<extra></extra>",
        ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": FONT, "color": c["text"], "size": 11},
            margin={"l": 0, "r": 0, "t": 10, "b": 0},
            xaxis={"showgrid": False, "color": c["muted"], "linecolor": c["border"]},
            yaxis={"showgrid": True, "gridcolor": c["border"], "color": c["subtext"]},
            legend={"orientation": "h", "y": 1.02, "x": 0},
            hovermode="x unified",
            height=390,
        )

        rows = []
        for ticker, weight in used_weights.items():
            rows.append(html.Tr([
                html.Td(ticker, style={
                    "padding": "0.4rem 0.7rem", "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.8rem", "fontFamily": FONT, "color": c["accent"], "fontWeight": "700",
                }),
                html.Td(f"{weight * 100:.2f}%", style={
                    "padding": "0.4rem 0.7rem", "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.8rem", "fontFamily": FONT, "color": c["text"], "textAlign": "right",
                }),
            ]))

        weights_table = html.Div(
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Ticker", style={
                        "padding": "0.35rem 0.7rem", "fontSize": "0.62rem", "textTransform": "uppercase",
                        "letterSpacing": "0.06em", "fontWeight": "700", "borderBottom": "2px solid " + c["border"],
                        "fontFamily": FONT, "color": c["muted"], "textAlign": "left",
                    }),
                    html.Th("Weight", style={
                        "padding": "0.35rem 0.7rem", "fontSize": "0.62rem", "textTransform": "uppercase",
                        "letterSpacing": "0.06em", "fontWeight": "700", "borderBottom": "2px solid " + c["border"],
                        "fontFamily": FONT, "color": c["muted"], "textAlign": "right",
                    }),
                ])),
                html.Tbody(rows),
            ], style={"width": "100%", "borderCollapse": "collapse", "maxWidth": "420px"}),
            style={"overflowX": "auto"},
        )

        total_return = ((float(port_index.iloc[-1]) / float(port_index.iloc[0])) - 1) * 100
        freq_label = (frequency or "weekly").capitalize()
        status = (
            f"{freq_label} portfolio performance across {len(used_weights)} ticker(s). "
            f"Total return over shown period: {total_return:+.2f}%"
        )

        return dcc.Graph(figure=fig, config={"displayModeBar": False}), weights_table, status
