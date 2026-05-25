"""Callback — Snowflake price viewer (FactSet data)."""

import pandas as pd
import dash
from dash import Input, Output, State, html, dash_table, no_update
import plotly.graph_objects as go

from theme import get_theme, FONT
from snowflake_data import download_prices


def register_callbacks(app):

    @app.callback(
        Output("sf-chart", "figure"),
        Output("sf-table-container", "children"),
        Output("sf-status", "children"),
        Input("sf-load-btn", "n_clicks"),
        State("sf-tickers", "value"),
        State("sf-period", "value"),
        State("sf-display", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def load_snowflake_prices(n_clicks, tickers_raw, period, display_mode, theme_mode):
        if not tickers_raw or not tickers_raw.strip():
            return no_update, no_update, "⚠️ Enter at least one ticker."

        c = get_theme(theme_mode or "dark")
        tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]

        try:
            df = download_prices(tickers, period=period)
        except Exception as e:
            empty = go.Figure()
            empty.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=c["subtext"]),
                annotations=[dict(text=f"Error: {e}", showarrow=False,
                                  font=dict(size=14, color="#ff6b6b"))]
            )
            return empty, html.Div(), f"❌ {e}"

        if df.empty:
            empty = go.Figure()
            empty.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=c["subtext"]),
                annotations=[dict(text="No data returned", showarrow=False,
                                  font=dict(size=14, color=c["muted"]))]
            )
            return empty, html.Div(), "No data found."

        # ── Build chart ──────────────────────────────────────────────────
        plot_df = df.copy()
        if display_mode == "rebased":
            first = plot_df.iloc[0].replace(0, float("nan"))
            plot_df = (plot_df / first) * 100

        fig = go.Figure()
        colours = ["#58a6ff", "#3fb950", "#ff8c00", "#f85149",
                    "#bc8cff", "#39d2c0", "#ffdf5d", "#ff7eb6"]
        for i, col in enumerate(plot_df.columns):
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df[col],
                mode="lines", name=col,
                line=dict(color=colours[i % len(colours)], width=2),
            ))

        y_prefix = "$" if display_mode == "raw" else ""
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["subtext"], size=11),
            margin=dict(l=0, r=48, t=10, b=0),
            legend=dict(orientation="h", y=1.06, x=0),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#1e1e2f", font_size=12,
                            font_family=FONT, font_color="#e6e6e6"),
            xaxis=dict(showgrid=False, color=c["muted"], linecolor=c["border"]),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["subtext"],
                       tickprefix=y_prefix, side="right", autorange=True),
        )

        # ── Build last-20-rows table ─────────────────────────────────────
        recent = df.tail(20).sort_index(ascending=False).round(2)
        recent = recent.reset_index()
        recent.columns = ["Date"] + list(recent.columns[1:])
        recent["Date"] = pd.to_datetime(recent["Date"]).dt.strftime("%Y-%m-%d")

        table = dash_table.DataTable(
            columns=[{"name": col, "id": col} for col in recent.columns],
            data=recent.to_dict("records"),
            page_action="none",
            style_table={"overflowX": "auto", "borderRadius": "8px",
                         "maxHeight": "400px", "overflowY": "auto"},
            style_header={
                "backgroundColor": c["panel"],
                "color": c["text"],
                "fontWeight": "700",
                "fontFamily": FONT,
                "fontSize": "0.75rem",
                "borderBottom": f"1px solid {c['border']}",
                "position": "sticky", "top": 0,
            },
            style_cell={
                "backgroundColor": c["bg"],
                "color": c["text"],
                "fontFamily": FONT,
                "fontSize": "0.75rem",
                "padding": "6px 10px",
                "borderBottom": f"1px solid {c['border']}",
                "textAlign": "right",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": c["panel"]},
                {"if": {"column_id": "Date"}, "textAlign": "left"},
            ],
        )

        status = f"✅ {len(df)} trading days • {len(df.columns)} tickers • Source: FactSet/Snowflake"
        return fig, table, status
