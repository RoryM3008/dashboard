"""Callback — Portfolio Performance chart + weights table."""

import re
import datetime
import io
import pandas as pd
import yfinance as yf

import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from dash import dcc, html, Input, Output, State

from theme import FONT, get_theme
from data import parse_tickers, build_portfolio_performance_data


def register_callbacks(app):

    @app.callback(
        Output("perf-chart", "children"),
        Output("perf-benchmark-chart", "children"),
        Output("perf-weights-table", "children"),
        Output("perf-export-store", "data"),
        Output("perf-status", "children"),
        Input("perf-run", "n_clicks"),
        State("perf-tickers", "value"),
        State("perf-weights", "value"),
        State("perf-frequency", "value"),
        State("perf-start-date", "date"),
        State("perf-benchmarks", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def calculate_portfolio_performance(n, raw_tickers, raw_weights, frequency, start_date, raw_benchmarks, theme_mode):
        c = get_theme(theme_mode or "dark")
        is_dark = (theme_mode or "dark") == "dark"
        hover_bg = "#1a1a1a" if is_dark else "#ffffff"
        hover_fg = "#f2f2f2" if is_dark else "#1a1a1a"
        tickers = parse_tickers(raw_tickers)
        if len(tickers) < 1:
            return html.Div(), html.Div(), html.Div(), None, "Enter at least one ticker."

        weight_tokens = [w for w in re.split(r"[\s,;]+", (raw_weights or "").strip()) if w]
        if len(weight_tokens) != len(tickers):
            msg = "Provide exactly one weight per ticker (same order)."
            return html.Div(), html.Div(), html.Div(), None, msg

        weights = []
        for token in weight_tokens:
            try:
                weights.append(float(token.replace("%", "")))
            except Exception:
                msg = "Weights must be numeric (e.g. 25, 25, 25, 25)."
                return html.Div(), html.Div(), html.Div(), None, msg

        if any(w > 1 for w in weights):
            weights = [w / 100 for w in weights]

        if sum(weights) <= 0:
            return html.Div(), html.Div(), html.Div(), None, "Total weight must be greater than zero."

        port_index, component_index, used_weights, raw_prices = build_portfolio_performance_data(
            tickers, weights, frequency or "weekly"
        )
        if port_index is None or component_index is None or used_weights is None:
            return html.Div(), html.Div(), html.Div(), None, "No usable price history found for these inputs."

        # Optional: start from a selected date and rebase to 100 from that point
        if start_date:
            try:
                start_dt = pd.Timestamp(start_date).normalize()
                component_cut = component_index[component_index.index >= start_dt]
                if component_cut.empty:
                    return html.Div(), html.Div(), html.Div(), None, "Selected start date is after available data."
                component_index = component_cut.divide(component_cut.iloc[0]).mul(100)
                port_index = component_index.mul(used_weights, axis=1).sum(axis=1)
            except Exception:
                return html.Div(), html.Div(), html.Div(), None, "Invalid start date selection."

        fig = go.Figure()

        # Colour component lines by performance rank: best = dark green, worst = dark red
        end_vals = component_index.iloc[-1]
        rank = end_vals.rank(method="min")
        n_rank = max(len(rank) - 1, 1)
        perf_scale = [
            [0.0, "#7f1d1d"],  # dark red
            [0.5, "#4a3f2a"],  # muted midpoint
            [1.0, "#14532d"],  # dark green
        ]

        for ticker in component_index.columns:
            score = (rank[ticker] - 1) / n_rank  # 0 = worst, 1 = best
            line_col = sample_colorscale(perf_scale, [float(score)])[0]
            fig.add_trace(go.Scatter(
                x=component_index.index,
                y=component_index[ticker],
                mode="lines",
                line={"width": 1.6, "color": line_col},
                opacity=0.9,
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
            hovermode="closest",
            hoverlabel={
                "bgcolor": hover_bg,
                "bordercolor": c["border"],
                "font": {"family": FONT, "color": hover_fg, "size": 11},
            },
            height=390,
        )

        # Fallback at trace level (some themes/templates can override unified hover colors)
        fig.update_traces(hoverlabel={
            "bgcolor": hover_bg,
            "bordercolor": c["border"],
            "font": {"family": FONT, "color": hover_fg, "size": 11},
        })

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

        # ── Benchmark comparison chart ────────────────────────────────
        bench_chart = html.Div()
        bench_tickers = parse_tickers(raw_benchmarks) if raw_benchmarks else []
        if bench_tickers:
            _resample = {"daily": None, "weekly": "W-FRI", "monthly": "ME"}
            rule = _resample.get(frequency or "weekly")

            fig_b = go.Figure()
            # Add portfolio line first
            fig_b.add_trace(go.Scatter(
                x=port_index.index, y=port_index, mode="lines",
                line={"width": 3, "color": c["accent"]},
                name="Portfolio",
                hovertemplate="Portfolio: %{y:.2f}<extra></extra>",
            ))

            import numpy as np

            bench_colors = ["#42a5f5", "#ab47bc", "#ef5350", "#66bb6a",
                            "#ffa726", "#26c6da", "#8d6e63", "#78909c"]
            first_bench_rebased = None  # keep first benchmark for tracking error
            for i, bt in enumerate(bench_tickers):
                try:
                    print(f"[BENCH] Fetching {bt}...")
                    bh = yf.Ticker(bt).history(period="max", auto_adjust=True)
                    if bh.empty:
                        print(f"[BENCH] {bt}: empty history")
                        continue
                    bs = bh["Close"]
                    bs.index = bs.index.tz_localize(None)
                    if rule:
                        bs = bs.resample(rule).last().dropna()
                    # Align to portfolio date range using nearest/forward-fill
                    common = port_index.index.intersection(bs.index)
                    print(f"[BENCH] {bt}: {len(bs)} pts, {len(common)} common with portfolio")
                    if len(common) < 2:
                        bs = bs.reindex(port_index.index, method="ffill").dropna()
                        print(f"[BENCH] {bt}: after ffill reindex: {len(bs)} pts")
                    else:
                        bs = bs.loc[common]
                    if len(bs) < 2:
                        print(f"[BENCH] {bt}: skipping, < 2 pts")
                        continue
                    # Rebase to 100
                    bs = (bs / bs.iloc[0]) * 100
                    if first_bench_rebased is None:
                        first_bench_rebased = bs.copy()
                    clr = bench_colors[i % len(bench_colors)]
                    fig_b.add_trace(go.Scatter(
                        x=bs.index, y=bs, mode="lines",
                        line={"width": 2, "color": clr},
                        name=bt,
                        hovertemplate=f"{bt}: %{{y:.2f}}<extra></extra>",
                    ))
                    print(f"[BENCH] {bt}: added trace OK, last val={bs.iloc[-1]:.2f}")
                except Exception as exc:
                    print(f"[BENCH] {bt}: ERROR {exc}")
                    continue

            # Rolling tracking error vs first benchmark (on secondary y-axis)
            if bench_tickers:
                bt0 = bench_tickers[0]
                try:
                    # Download benchmark as DAILY data (don't resample independently)
                    bh_raw = yf.Ticker(bt0).history(period="max", auto_adjust=True)
                    if not bh_raw.empty:
                        bs_daily = bh_raw["Close"]
                        bs_daily.index = bs_daily.index.tz_localize(None).normalize()

                        # Get the portfolio's actual dates
                        port_s = port_index.copy()
                        port_s.index = port_s.index.normalize()

                        # Reindex benchmark to portfolio dates using last available daily close
                        # This ensures both series are on identical dates
                        bs_aligned = bs_daily.reindex(port_s.index, method="ffill").dropna()

                        # Only keep dates present in both
                        common = port_s.index.intersection(bs_aligned.index)
                        port_s = port_s.loc[common]
                        bs_aligned = bs_aligned.loc[common]

                        print(f"[TE] {len(common)} common dates, port dates: {common[:3].tolist()}")

                        if len(common) > 10:
                            # Period returns
                            p_ret = port_s.pct_change().dropna() * 100
                            b_ret = bs_aligned.pct_change().dropna() * 100
                            diff = p_ret - b_ret

                            ann_factor = {"daily": 252, "weekly": 52, "monthly": 12}.get(frequency or "weekly", 52)
                            win = max(10, ann_factor)

                            full_te = diff.std() * np.sqrt(ann_factor)
                            print(f"[TE] std(P-B)={diff.std():.4f}% | annualised TE={full_te:.2f}%")
                            print(f"[TE] first 5 diffs: {diff.head().tolist()}")

                            te_rolling = diff.rolling(win, min_periods=max(win // 2, 5)).std() * np.sqrt(ann_factor)
                            te_rolling = te_rolling.dropna()

                            if not te_rolling.empty:
                                print(f"[TE] latest rolling TE = {te_rolling.iloc[-1]:.2f}%")
                                fig_b.add_trace(go.Scatter(
                                    x=te_rolling.index, y=te_rolling, mode="lines",
                                    line={"width": 1.8, "color": "#ffa726", "dash": "dot"},
                                    name=f"Tracking Error vs {bt0}",
                                    yaxis="y2",
                                    hovertemplate="TE: %{y:.2f}%<extra></extra>",
                                ))
                except Exception as exc:
                    print(f"[TE] error: {exc}")

            fig_b.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"family": FONT, "color": c["text"], "size": 11},
                margin={"l": 0, "r": 50, "t": 10, "b": 0},
                xaxis={"showgrid": False, "color": c["muted"], "linecolor": c["border"]},
                yaxis={"showgrid": True, "gridcolor": c["border"], "color": c["subtext"],
                       "title": "Indexed (100)"},
                yaxis2={"overlaying": "y", "side": "right", "showgrid": False,
                        "zeroline": False, "title": "Tracking Error (%)",
                        "tickfont": {"size": 9}, "color": "#ffa726"},
                legend={"orientation": "h", "y": 1.02, "x": 0},
                hovermode="x unified",
                hoverlabel={
                    "bgcolor": hover_bg, "bordercolor": c["border"],
                    "font": {"family": FONT, "color": hover_fg, "size": 11},
                },
                height=340,
            )
            # Add 100 baseline
            fig_b.add_hline(y=100, line_dash="dot", line_width=0.8,
                            line_color="rgba(255,255,255,0.25)")
            bench_chart = dcc.Graph(figure=fig_b, config={"displayModeBar": False})

        # ── Build export DataFrames (two tabs: Prices + Index) ────────
        prices_df = raw_prices.copy()
        prices_df.index.name = "Date"

        index_df = pd.DataFrame(index=port_index.index)
        index_df["Portfolio"] = port_index
        for t in used_weights.index:
            index_df[t] = component_index[t]
        index_df.index.name = "Date"

        # Add benchmark data to both tabs
        bench_tickers_list = parse_tickers(raw_benchmarks) if raw_benchmarks else []
        for bt in bench_tickers_list:
            try:
                bh = yf.Ticker(bt).history(period="max", auto_adjust=True)
                if bh.empty:
                    continue
                bs = bh["Close"]
                bs.index = bs.index.tz_localize(None).normalize()
                bs_aligned = bs.reindex(prices_df.index, method="ffill").dropna()
                prices_df[bt] = bs_aligned
                index_df[bt] = (bs_aligned / bs_aligned.iloc[0]) * 100
            except Exception:
                continue

        export_json = {
            "prices": prices_df.reset_index().to_json(date_format="iso", orient="split"),
            "index": index_df.reset_index().to_json(date_format="iso", orient="split"),
        }
        import json
        export_store = json.dumps(export_json)

        total_return = ((float(port_index.iloc[-1]) / float(port_index.iloc[0])) - 1) * 100
        freq_label = (frequency or "weekly").capitalize()
        start_txt = f" From {pd.Timestamp(start_date).strftime('%d-%b-%Y')}." if start_date else ""
        status = (
            f"{freq_label} portfolio performance across {len(used_weights)} ticker(s). "
            f"Total return over shown period: {total_return:+.2f}%.{start_txt}"
        )

        return dcc.Graph(figure=fig, config={"displayModeBar": False}), bench_chart, weights_table, export_store, status

    @app.callback(
        Output("perf-export-download", "data"),
        Input("perf-export-btn", "n_clicks"),
        State("perf-export-store", "data"),
        prevent_initial_call=True,
    )
    def export_performance(n, store_data):
        if not store_data:
            return None
        import json
        data = json.loads(store_data)
        prices_df = pd.read_json(data["prices"], orient="split")
        index_df = pd.read_json(data["index"], orient="split")

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            index_df.to_excel(writer, sheet_name="Index", index=False)
            prices_df.to_excel(writer, sheet_name="Prices", index=False)
        buf.seek(0)

        now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return dcc.send_bytes(buf.getvalue(), f"performance_{now}.xlsx")
