"""Callback — Correlation matrix heatmap + table."""

import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State

from theme import FONT, get_theme
from data import parse_tickers, build_correlation_data


def register_callbacks(app):

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
