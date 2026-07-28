"""Callbacks - Style Analytics (Factor Tilt) page."""
import traceback
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, html, dcc, no_update
from dash.exceptions import PreventUpdate

from snowflake_data import fetch_portfolio_factor_snapshot, GEMLTL_STYLE_FACTORS
from portfolio import load_transactions, compute_holdings, get_isin_map, set_isin, delete_isin
from theme import SP500_TICKERS, FTSE100_TICKERS, EUROSTOXX50_TICKERS

# Style bucket definitions
STYLE_BUCKETS = {
    "Value":      ["GEMLT_BTOP", "GEMLT_EARNYILD", "GEMLT_DIVYILD"],
    "Quality":    ["GEMLT_PROFIT", "GEMLT_EARNQLTY", "GEMLT_INVSQLTY"],
    "Growth":     ["GEMLT_GROWTH"],
    "Momentum":   ["GEMLT_MOMENTUM", "GEMLT_LTREVRSL"],
    "Size":       ["GEMLT_SIZE", "GEMLT_MIDCAP"],
    "Risk":       ["GEMLT_RESVOL", "GEMLT_BETA", "GEMLT_LEVERAGE", "GEMLT_LIQUIDTY", "GEMLT_EARNVAR"],
}

BUCKET_COLOUR = {
    "Value":    "#3b82f6",
    "Quality":  "#22c55e",
    "Growth":   "#a855f7",
    "Momentum": "#f97316",
    "Size":     "#06b6d4",
    "Risk":     "#ef4444",
}

FACTOR_DISPLAY = {
    "GEMLT_BTOP":     "Book-to-Price",
    "GEMLT_EARNYILD": "Earnings Yield",
    "GEMLT_DIVYILD":  "Dividend Yield",
    "GEMLT_PROFIT":   "Profitability",
    "GEMLT_EARNQLTY": "Earnings Quality",
    "GEMLT_INVSQLTY": "Investment Quality",
    "GEMLT_GROWTH":   "Growth",
    "GEMLT_MOMENTUM": "Momentum",
    "GEMLT_LTREVRSL": "Long-Term Reversal",
    "GEMLT_SIZE":     "Size",
    "GEMLT_MIDCAP":   "Mid Cap",
    "GEMLT_RESVOL":   "Residual Volatility",
    "GEMLT_BETA":     "Beta",
    "GEMLT_LEVERAGE": "Leverage",
    "GEMLT_LIQUIDTY": "Liquidity",
    "GEMLT_EARNVAR":  "Earnings Variability",
}


def _compute_bucket_scores(df):
    scores = {}
    for bucket, factors in STYLE_BUCKETS.items():
        sub = df[df["FACTOR"].isin(factors)]
        scores[bucket] = float(sub["PORTFOLIO_SCORE"].mean()) if not sub.empty else 0.0
    return scores


def _build_radar(bucket_scores, font, C):
    cats = list(bucket_scores.keys())
    vals = [round(bucket_scores[c], 3) for c in cats]
    scaled = [max(0, min(1, (v + 2) / 4)) for v in vals]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scaled + [scaled[0]],
        theta=cats + [cats[0]],
        fill="toself",
        fillcolor="rgba(250,190,0,0.15)",
        line=dict(color="#fabc00", width=2),
        customdata=vals + [vals[0]],
        hovertemplate="<b>%{theta}</b><br>Score: %{customdata:.3f}<extra></extra>",
        name="Portfolio",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=C.get("panel", "#1a1a1a"),
            angularaxis=dict(tickfont=dict(size=11, color=C.get("text", "#fff"), family=font),
                             linecolor=C.get("border", "#333"), gridcolor=C.get("border", "#333")),
            radialaxis=dict(visible=False, range=[0, 1]),
        ),
        paper_bgcolor=C.get("panel", "#1a1a1a"),
        plot_bgcolor=C.get("panel", "#1a1a1a"),
        margin=dict(l=60, r=60, t=40, b=40),
        font=dict(family=font, color=C.get("text", "#fff")),
        showlegend=False, height=320,
    )
    return fig


def _build_style_map(bucket_scores, font, C):
    x = bucket_scores.get("Value", 0)
    y = bucket_scores.get("Growth", 0)
    q = bucket_scores.get("Quality", 0)
    m = bucket_scores.get("Momentum", 0)
    s = bucket_scores.get("Size", 0)
    r = bucket_scores.get("Risk", 0)
    fig = go.Figure()
    fig.add_hline(y=0, line=dict(color=C.get("border", "#333"), width=1, dash="dot"))
    fig.add_vline(x=0, line=dict(color=C.get("border", "#333"), width=1, dash="dot"))
    for qx, qy, label in [(-1.5, 1.2, "Growth / Quality"), (0.8, 1.2, "Value / Quality"),
                           (-1.5, -1.5, "Growth / Spec."),  (0.8, -1.5, "Value / Spec.")]:
        fig.add_annotation(x=qx, y=qy, text=label,
            font=dict(size=9, color=C.get("muted", "#888"), family=font),
            showarrow=False, xref="x", yref="y")
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="markers+text",
        marker=dict(size=22, color="#fabc00", line=dict(color="#000", width=1.5)),
        text=["Portfolio"], textposition="top center",
        textfont=dict(size=10, color=C.get("text", "#fff"), family=font),
        hovertemplate=(
            f"<b>Portfolio</b><br>Value: {x:+.3f}<br>Growth: {y:+.3f}<br>"
            f"Quality: {q:+.3f}<br>Momentum: {m:+.3f}<br>"
            f"Size: {s:+.3f}<br>Risk: {r:+.3f}<extra></extra>"
        ),
    ))
    fig.update_layout(
        xaxis=dict(title=dict(text="Value", font=dict(size=10, color=C.get("muted", "#888"), family=font)),
                   range=[-2.2, 2.2], zeroline=False, showgrid=False,
                   tickfont=dict(size=10, color=C.get("muted", "#888"), family=font)),
        yaxis=dict(title=dict(text="Growth", font=dict(size=10, color=C.get("muted", "#888"), family=font)),
                   range=[-2.2, 2.2], zeroline=False, showgrid=False,
                   tickfont=dict(size=10, color=C.get("muted", "#888"), family=font)),
        paper_bgcolor=C.get("panel", "#1a1a1a"),
        plot_bgcolor=C.get("panel", "#1a1a1a"),
        margin=dict(l=50, r=30, t=30, b=50),
        font=dict(family=font, color=C.get("text", "#fff")),
        showlegend=False, height=320,
    )
    return fig


def _build_factor_bars(df, font, C):
    rows = []
    for bucket, factors in STYLE_BUCKETS.items():
        for fcode in factors:
            sub = df[df["FACTOR"] == fcode]
            if sub.empty:
                continue
            score = float(sub["PORTFOLIO_SCORE"].iloc[0])
            rows.append({"bucket": bucket, "factor": FACTOR_DISPLAY.get(fcode, fcode),
                         "score": score, "colour": BUCKET_COLOUR[bucket]})
    if not rows:
        return go.Figure()
    fdf = pd.DataFrame(rows)
    fdf = fdf.sort_values(["bucket", "score"], ascending=[True, False])
    fig = go.Figure()
    for bucket in STYLE_BUCKETS:
        sub = fdf[fdf["bucket"] == bucket]
        if sub.empty:
            continue
        colour = BUCKET_COLOUR[bucket]
        bar_colours = [colour if v >= 0 else "rgba(150,150,150,0.4)" for v in sub["score"]]
        fig.add_trace(go.Bar(
            y=sub["factor"].tolist(), x=sub["score"].tolist(),
            orientation="h", name=bucket,
            marker_color=bar_colours, marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>",
            legendgroup=bucket,
        ))
    fig.add_vline(x=0, line=dict(color=C.get("text", "#fff"), width=1))
    fig.update_layout(
        barmode="relative",
        xaxis=dict(title=dict(text="Factor Z-Score", font=dict(size=10, color=C.get("muted", "#888"), family=font)),
                   showgrid=True, gridcolor=C.get("border", "#333"),
                   zeroline=False,
                   tickfont=dict(size=10, color=C.get("muted", "#888"), family=font)),
        yaxis=dict(showgrid=False, autorange="reversed",
                   tickfont=dict(size=10.5, color=C.get("text", "#fff"), family=font)),
        paper_bgcolor=C.get("panel", "#1a1a1a"),
        plot_bgcolor=C.get("panel", "#1a1a1a"),
        margin=dict(l=160, r=30, t=20, b=40),
        font=dict(family=font, color=C.get("text", "#fff")),
        legend=dict(orientation="h", x=0, y=-0.08,
                    font=dict(size=10, color=C.get("text", "#fff"), family=font),
                    bgcolor="rgba(0,0,0,0)"),
        height=max(380, len(rows) * 26 + 80),
    )
    return fig


def _build_bucket_cards(bucket_scores, C, font):
    cards = []
    for bucket, score in bucket_scores.items():
        colour = BUCKET_COLOUR[bucket]
        bar_w = min(100, abs(score) / 2 * 100)
        bar_col = colour if score >= 0 else "rgba(150,150,150,0.55)"
        cards.append(html.Div([
            html.Div(bucket, style={"fontSize": "0.65rem", "color": C.get("muted", "#888"),
                                    "fontFamily": font, "fontWeight": "700",
                                    "textTransform": "uppercase", "letterSpacing": "0.06em"}),
            html.Div(f"{score:+.3f}", style={"fontSize": "1.35rem",
                                              "color": colour if score >= 0 else C.get("text", "#fff"),
                                              "fontFamily": font, "fontWeight": "700",
                                              "lineHeight": "1.3"}),
            html.Div(style={"height": "4px", "borderRadius": "2px",
                            "backgroundColor": C.get("border", "#333"), "marginTop": "4px"}),
            html.Div(style={"height": "4px", "borderRadius": "2px",
                            "backgroundColor": bar_col, "width": f"{bar_w}%",
                            "marginTop": "-4px"}),
        ], style={"backgroundColor": C.get("bg", "#111"),
                  "border": f"1px solid {C.get('border', '#333')}",
                  "borderRadius": "8px", "padding": "0.65rem 0.85rem",
                  "flex": "1 1 120px", "minWidth": "100px"}))
    return html.Div(cards, style={"display": "flex", "gap": "0.5rem", "flexWrap": "wrap"})


def _overview_layout(df, bucket_scores, font, C):
    radar_fig = _build_radar(bucket_scores, font, C)
    map_fig   = _build_style_map(bucket_scores, font, C)
    panel_style = {"backgroundColor": C.get("panel", "#1a1a1a"),
                   "border": f"1px solid {C.get('border', '#333')}",
                   "borderRadius": "8px", "padding": "0.75rem"}
    label_style = {"color": C.get("muted", "#888"), "fontSize": "0.7rem", "fontFamily": font,
                   "fontWeight": "600", "textTransform": "uppercase",
                   "letterSpacing": "0.05em", "marginBottom": "0.5rem"}
    return html.Div([
        html.Div([
            html.Div([html.Div("Style Shape", style=label_style),
                      dcc.Graph(figure=radar_fig, config={"displayModeBar": False}, style={"height": "320px"})],
                     style={**panel_style, "flex": "0 0 48%"}),
            html.Div([html.Div("Style Map - Value vs Growth", style=label_style),
                      dcc.Graph(figure=map_fig, config={"displayModeBar": False}, style={"height": "320px"})],
                     style={**panel_style, "flex": "0 0 48%"}),
        ], style={"display": "flex", "gap": "1rem", "flexWrap": "wrap", "marginBottom": "1rem"}),
        html.Div([
            html.Div("Composite Style Scores", style=label_style),
            _build_bucket_cards(bucket_scores, C, font),
        ], style={**panel_style, "marginBottom": "1rem"}),
    ])


def _detail_layout(df, font, C):
    fig = _build_factor_bars(df, font, C)
    panel_style = {"backgroundColor": C.get("panel", "#1a1a1a"),
                   "border": f"1px solid {C.get('border', '#333')}",
                   "borderRadius": "8px", "padding": "0.75rem"}
    label_style = {"color": C.get("muted", "#888"), "fontSize": "0.7rem", "fontFamily": font,
                   "fontWeight": "600", "textTransform": "uppercase",
                   "letterSpacing": "0.05em", "marginBottom": "0.5rem"}
    return html.Div([
        html.Div("All Factor Exposures", style=label_style),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ], style=panel_style)


def _map_layout(bucket_scores, font, C):
    fig = _build_style_map(bucket_scores, font, C)
    panel_style = {"backgroundColor": C.get("panel", "#1a1a1a"),
                   "border": f"1px solid {C.get('border', '#333')}",
                   "borderRadius": "8px", "padding": "0.75rem"}
    label_style = {"color": C.get("muted", "#888"), "fontSize": "0.7rem", "fontFamily": font,
                   "fontWeight": "600", "textTransform": "uppercase",
                   "letterSpacing": "0.05em", "marginBottom": "0.5rem"}
    return html.Div([
        html.Div("Style Map", style=label_style),
        dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"height": "450px"}),
    ], style=panel_style)


def _parse_custom_holdings(raw_tickers, raw_weights):
    tickers = [t.strip().upper() for t in str(raw_tickers or "").split(",") if t.strip()]
    if not tickers:
        raise ValueError("Enter at least one ticker.")
    tickers = list(dict.fromkeys(tickers))

    if str(raw_weights or "").strip() == "":
        w = 1.0 / len(tickers)
        return {t: w for t in tickers}

    weights = []
    for x in str(raw_weights).split(","):
        x = x.strip()
        if not x:
            continue
        weights.append(float(x))

    if len(weights) != len(tickers):
        raise ValueError("Number of weights must match number of tickers, or leave weights blank for equal weight.")
    if sum(weights) <= 0:
        raise ValueError("Weights must sum to a positive number.")
    total = float(sum(weights))
    return {t: w / total for t, w in zip(tickers, weights) if w > 0}


def _benchmark_holdings(code):
    if code == "sp500_eq":
        items = SP500_TICKERS
        label = "S&P 500 equal-weight proxy"
    elif code == "ftse100_eq":
        items = FTSE100_TICKERS
        label = "FTSE 100 equal-weight proxy"
    elif code == "euro50_eq":
        items = EUROSTOXX50_TICKERS
        label = "Euro Stoxx 50 equal-weight proxy"
    else:
        raise ValueError("Unsupported benchmark.")
    w = 1.0 / len(items)
    return {t: w for t in items}, label


def _build_compare_bucket_chart(port_scores, bench_scores, font, C):
    cats = list(STYLE_BUCKETS.keys())
    p = [port_scores.get(c, 0.0) for c in cats]
    b = [bench_scores.get(c, 0.0) for c in cats]
    a = [pp - bb for pp, bb in zip(p, b)]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Portfolio", x=cats, y=p, marker_color=C.get("accent", "#fabc00")))
    fig.add_trace(go.Bar(name="Benchmark", x=cats, y=b, marker_color=C.get("blue", "#60a5fa")))
    fig.add_trace(go.Bar(name="Active", x=cats, y=a, marker_color=C.get("green", "#22c55e"), opacity=0.65))
    fig.update_layout(
        barmode="group",
        paper_bgcolor=C.get("panel", "#1a1a1a"),
        plot_bgcolor=C.get("panel", "#1a1a1a"),
        margin=dict(l=35, r=20, t=20, b=40),
        font=dict(family=font, color=C.get("text", "#fff")),
        legend=dict(orientation="h", y=1.12, x=0),
        yaxis=dict(gridcolor=C.get("border", "#333"), zeroline=False),
        height=300,
    )
    return fig


def _build_active_factor_compare(df_port, df_bench, font, C):
    merged = pd.merge(
        df_port[["FACTOR", "FACTOR_NAME", "PORTFOLIO_SCORE"]].rename(columns={"PORTFOLIO_SCORE": "PORT"}),
        df_bench[["FACTOR", "FACTOR_NAME", "PORTFOLIO_SCORE"]].rename(columns={"PORTFOLIO_SCORE": "BMK"}),
        on=["FACTOR", "FACTOR_NAME"], how="outer"
    ).fillna(0)
    merged["ACTIVE"] = merged["PORT"] - merged["BMK"]
    m = pd.concat([
        merged.nlargest(5, "ACTIVE"),
        merged.nsmallest(5, "ACTIVE")
    ]).drop_duplicates(subset=["FACTOR"])
    m = m.sort_values("ACTIVE")
    fig = go.Figure(go.Bar(
        x=m["ACTIVE"], y=m["FACTOR_NAME"], orientation="h",
        marker_color=[C.get("green", "#22c55e") if v >= 0 else C.get("red", "#ef4444") for v in m["ACTIVE"]],
        hovertemplate="<b>%{y}</b><br>Active Tilt: %{x:.3f}<extra></extra>",
    ))
    fig.add_vline(x=0, line=dict(color=C.get("text", "#fff"), width=1))
    fig.update_layout(
        paper_bgcolor=C.get("panel", "#1a1a1a"),
        plot_bgcolor=C.get("panel", "#1a1a1a"),
        margin=dict(l=150, r=20, t=20, b=35),
        font=dict(family=font, color=C.get("text", "#fff")),
        xaxis=dict(gridcolor=C.get("border", "#333"), zeroline=False),
        yaxis=dict(autorange="reversed"),
        height=300,
    )
    return fig, merged.sort_values("ACTIVE", ascending=False)


def _compare_layout(df_port, df_bench, port_scores, bench_scores, custom_holdings, bench_label, font, C):
    bucket_fig = _build_compare_bucket_chart(port_scores, bench_scores, font, C)
    active_fig, merged = _build_active_factor_compare(df_port, df_bench, font, C)

    td = {"padding": "0.28rem 0.45rem", "fontSize": "0.74rem", "fontFamily": font,
          "borderBottom": f"1px solid {C.get('border', '#333')}"}
    th = {"padding": "0.28rem 0.45rem", "fontSize": "0.63rem", "fontFamily": font,
          "color": C.get("muted", "#888"), "textTransform": "uppercase",
          "borderBottom": f"1px solid {C.get('border', '#333')}"}
    rows = [html.Tr([
        html.Td(t, style={**td, "color": C.get("accent", "#fabc00"), "fontWeight": "700"}),
        html.Td(f"{w*100:.1f}%", style={**td, "textAlign": "right", "color": C.get("text", "#fff")}),
    ]) for t, w in custom_holdings.items()]

    top_rows = []
    for _, r in merged.head(8).iterrows():
        col = C.get("green", "#22c55e") if r["ACTIVE"] >= 0 else C.get("red", "#ef4444")
        top_rows.append(html.Tr([
            html.Td(FACTOR_DISPLAY.get(r["FACTOR"], r["FACTOR_NAME"]), style={**td, "color": C.get("text", "#fff")}),
            html.Td(f"{r['PORT']:+.3f}", style={**td, "textAlign": "right", "color": C.get("text", "#fff")}),
            html.Td(f"{r['BMK']:+.3f}", style={**td, "textAlign": "right", "color": C.get("text", "#fff")}),
            html.Td(f"{r['ACTIVE']:+.3f}", style={**td, "textAlign": "right", "color": col, "fontWeight": "700"}),
        ]))

    panel = {"backgroundColor": C.get("panel", "#1a1a1a"), "border": f"1px solid {C.get('border', '#333')}",
             "borderRadius": "8px", "padding": "0.75rem"}
    label = {"color": C.get("muted", "#888"), "fontSize": "0.68rem", "fontFamily": font,
             "fontWeight": "700", "textTransform": "uppercase", "letterSpacing": "0.05em", "marginBottom": "0.35rem"}

    return html.Div([
        html.Div([
            html.Div([
                html.Div("Custom Portfolio", style=label),
                html.Table([
                    html.Thead(html.Tr([html.Th("Ticker", style=th), html.Th("Weight", style={**th, "textAlign": "right"})])),
                    html.Tbody(rows),
                ], style={"width": "100%", "borderCollapse": "collapse"}),
            ], style={**panel, "flex": "0 0 28%"}),
            html.Div([
                html.Div(f"Bucket Comparison vs {bench_label}", style=label),
                dcc.Graph(figure=bucket_fig, config={"displayModeBar": False}, style={"height": "300px"}),
            ], style={**panel, "flex": "1 1 36%"}),
            html.Div([
                html.Div("Largest Active Factor Tilts", style=label),
                dcc.Graph(figure=active_fig, config={"displayModeBar": False}, style={"height": "300px"}),
            ], style={**panel, "flex": "1 1 36%"}),
        ], style={"display": "flex", "gap": "0.75rem", "flexWrap": "wrap", "marginBottom": "0.75rem"}),
        html.Div([
            html.Div("Top Active Factors (Portfolio - Benchmark)", style=label),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Factor", style=th),
                    html.Th("Portfolio", style={**th, "textAlign": "right"}),
                    html.Th("Benchmark", style={**th, "textAlign": "right"}),
                    html.Th("Active", style={**th, "textAlign": "right"}),
                ])),
                html.Tbody(top_rows),
            ], style={"width": "100%", "borderCollapse": "collapse"}),
        ], style=panel),
    ])


def register_callbacks(app, C=None, FONT=None):
    if C is None:
        C = {}
    if FONT is None:
        FONT = "Inter, sans-serif"

    def _method_demo_layout():
        # Toy data: 3 stocks, 2 style factors
        demo = pd.DataFrame([
            {"Ticker": "AAA", "W_port": 0.50, "W_bmk": 0.20, "Value": 1.20, "Momentum": -0.40},
            {"Ticker": "BBB", "W_port": 0.30, "W_bmk": 0.50, "Value": -0.30, "Momentum": 0.80},
            {"Ticker": "CCC", "W_port": 0.20, "W_bmk": 0.30, "Value": 0.50, "Momentum": 0.20},
        ])

        p_value = float((demo["W_port"] * demo["Value"]).sum())
        b_value = float((demo["W_bmk"] * demo["Value"]).sum())
        p_mom = float((demo["W_port"] * demo["Momentum"]).sum())
        b_mom = float((demo["W_bmk"] * demo["Momentum"]).sum())
        a_value = p_value - b_value
        a_mom = p_mom - b_mom

        # Compact table
        th = {"padding": "0.25rem 0.4rem", "fontSize": "0.64rem", "color": C.get("muted", "#888"),
              "fontFamily": FONT, "textTransform": "uppercase", "borderBottom": f"1px solid {C.get('border', '#333')}"}
        td = {"padding": "0.28rem 0.4rem", "fontSize": "0.74rem", "color": C.get("text", "#fff"),
              "fontFamily": FONT, "borderBottom": f"1px solid {C.get('border', '#333')}"}
        rows = [html.Tr([
            html.Td(r["Ticker"], style={**td, "fontWeight": "700"}),
            html.Td(f"{r['W_port']*100:.1f}%", style={**td, "textAlign": "right"}),
            html.Td(f"{r['W_bmk']*100:.1f}%", style={**td, "textAlign": "right"}),
            html.Td(f"{r['Value']:+.2f}", style={**td, "textAlign": "right"}),
            html.Td(f"{r['Momentum']:+.2f}", style={**td, "textAlign": "right"}),
        ]) for _, r in demo.iterrows()]

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Portfolio", x=["Value", "Momentum"], y=[p_value, p_mom], marker_color=C.get("accent", "#fabc00")))
        fig.add_trace(go.Bar(name="Benchmark", x=["Value", "Momentum"], y=[b_value, b_mom], marker_color=C.get("blue", "#60a5fa")))
        fig.add_trace(go.Bar(name="Active Tilt", x=["Value", "Momentum"], y=[a_value, a_mom], marker_color=C.get("green", "#22c55e"), opacity=0.65))
        fig.update_layout(
            barmode="group",
            paper_bgcolor=C.get("panel", "#1a1a1a"),
            plot_bgcolor=C.get("panel", "#1a1a1a"),
            margin=dict(l=35, r=20, t=20, b=35),
            height=250,
            font=dict(family=FONT, color=C.get("text", "#fff"), size=10),
            legend=dict(orientation="h", y=1.15, x=0),
            yaxis=dict(gridcolor=C.get("border", "#333"), zeroline=False),
        )

        return html.Div([
            html.Div(
                "Formula: Exposure(factor) = Σ(weight × stock factor exposure)  |  Active Tilt = Portfolio Exposure - Benchmark Exposure",
                style={"color": C.get("muted", "#888"), "fontSize": "0.7rem", "fontFamily": FONT, "marginBottom": "0.45rem"},
            ),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Ticker", style=th),
                    html.Th("Port W", style={**th, "textAlign": "right"}),
                    html.Th("Bmk W", style={**th, "textAlign": "right"}),
                    html.Th("Value Exp", style={**th, "textAlign": "right"}),
                    html.Th("Momentum Exp", style={**th, "textAlign": "right"}),
                ])),
                html.Tbody(rows),
            ], style={"width": "100%", "borderCollapse": "collapse", "marginBottom": "0.55rem"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"height": "250px"}),
            html.Div(
                f"Computed example  Value: Port {p_value:+.3f} vs Bmk {b_value:+.3f} -> Active {a_value:+.3f}   |   Momentum: Port {p_mom:+.3f} vs Bmk {b_mom:+.3f} -> Active {a_mom:+.3f}",
                style={"color": C.get("muted", "#888"), "fontSize": "0.69rem", "fontFamily": FONT, "marginTop": "0.2rem"},
            ),
        ])

    @app.callback(
        Output("ft-method-demo-out", "children"),
        Input("ft-method-demo-btn", "n_clicks"),
        prevent_initial_call=False,
    )
    def render_method_demo(_n):
        return _method_demo_layout()

    @app.callback(
        Output("ft-custom-out", "children"),
        Output("ft-custom-status", "children"),
        Input("ft-custom-run-btn", "n_clicks"),
        State("ft-custom-tickers", "value"),
        State("ft-custom-weights", "value"),
        State("ft-custom-benchmark", "value"),
        prevent_initial_call=True,
    )
    def run_custom_compare(n, raw_tickers, raw_weights, benchmark_code):
        if not n:
            raise PreventUpdate
        try:
            holdings = _parse_custom_holdings(raw_tickers, raw_weights)
            benchmark_holdings, bench_label = _benchmark_holdings(benchmark_code)
            isin_map = get_isin_map()
            factors = list(GEMLTL_STYLE_FACTORS.keys())

            df_port = fetch_portfolio_factor_snapshot(
                holdings_dict=holdings,
                model="GEMLTL",
                factors=factors,
                isin_override=isin_map,
            )
            df_bench = fetch_portfolio_factor_snapshot(
                holdings_dict=benchmark_holdings,
                model="GEMLTL",
                factors=factors,
                isin_override=isin_map,
            )
            if df_port.empty or df_bench.empty:
                return html.Div(), "No factor data returned for the custom portfolio or benchmark."

            port_scores = _compute_bucket_scores(df_port)
            bench_scores = _compute_bucket_scores(df_bench)
            out = _compare_layout(df_port, df_bench, port_scores, bench_scores, holdings, bench_label, FONT, C)

            p_cov = float(df_port["COVERAGE_PCT"].iloc[0]) if "COVERAGE_PCT" in df_port.columns else 0.0
            b_cov = float(df_bench["COVERAGE_PCT"].iloc[0]) if "COVERAGE_PCT" in df_bench.columns else 0.0
            status = (
                f"Compared {len(holdings)} holdings vs {bench_label}. "
                f"Coverage  Portfolio: {p_cov:.1f}%  |  Benchmark: {b_cov:.1f}%."
            )
            return out, status
        except Exception as e:
            return html.Div(), f"Error: {str(e)}"

    @app.callback(
        Output("ft-isin-table", "children"),
        Input("ft-isin-refresh", "data"),
        prevent_initial_call=False,
    )
    def refresh_isin_table(_):
        isin_map = get_isin_map()
        if not isin_map:
            return html.Div("No ISINs saved yet.",
                style={"color": C.get("muted", "#888"), "fontSize": "0.72rem", "fontFamily": FONT})
        rows = [html.Tr([
            html.Th("Ticker", style={"width": "130px"}),
            html.Th("ISIN"),
            html.Th(""),
        ], style={"fontSize": "0.68rem", "color": C.get("muted", "#888"), "textAlign": "left"})]
        for ticker, isin in sorted(isin_map.items()):
            rows.append(html.Tr([
                html.Td(ticker, style={"paddingRight": "1rem", "color": C.get("text", "#fff"),
                                       "fontSize": "0.73rem", "fontFamily": FONT}),
                html.Td(isin, style={"paddingRight": "1rem", "color": C.get("muted", "#888"),
                                     "fontSize": "0.73rem", "fontFamily": "monospace"}),
                html.Td(html.Button("x", id={"type": "ft-del-isin", "ticker": ticker},
                    n_clicks=0, style={"background": "none", "border": "none",
                                       "cursor": "pointer", "color": C.get("red", "#f87171"),
                                       "fontSize": "0.9rem"})),
            ]))
        return html.Table(rows, style={"borderCollapse": "collapse",
                                       "marginBottom": "0.5rem", "width": "100%"})

    @app.callback(
        Output("ft-isin-status", "children"),
        Output("ft-isin-refresh", "data"),
        Input("ft-isin-save-btn", "n_clicks"),
        State("ft-isin-ticker-input", "value"),
        State("ft-isin-value-input", "value"),
        State("ft-isin-refresh", "data"),
        prevent_initial_call=True,
    )
    def save_isin(n, ticker, isin, refresh):
        if not n or not ticker or not isin:
            raise PreventUpdate
        ticker = ticker.strip().upper()
        isin = isin.strip().upper()
        if len(isin) != 12:
            return "ISIN must be 12 characters.", no_update
        set_isin(ticker, isin)
        return f"Saved {ticker} -> {isin}", (refresh or 0) + 1

    @app.callback(
        Output("ft-isin-refresh", "data", allow_duplicate=True),
        Input({"type": "ft-del-isin", "ticker": "*"}, "n_clicks"),
        State("ft-isin-refresh", "data"),
        prevent_initial_call=True,
    )
    def delete_isin_cb(_, refresh):
        from dash import ctx
        if not ctx.triggered_id:
            raise PreventUpdate
        delete_isin(ctx.triggered_id["ticker"])
        return (refresh or 0) + 1

    @app.callback(
        Output("ft-chart-area", "children"),
        Output("ft-coverage-info", "children"),
        Output("ft-status", "children"),
        Output("ft-data-store", "data"),
        Output("ft-holdings-store", "data"),
        Output("ft-whatif-panel", "style"),
        Input("ft-load-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def run_analysis(n):
        if not n:
            raise PreventUpdate
        _hidden = {"display": "none"}
        _visible = {"display": "block"}
        try:
            txns = load_transactions()
            holdings_df, _ = compute_holdings(txns)
            if holdings_df.empty:
                return (html.Div("No portfolio holdings found.",
                    style={"color": C.get("muted", "#888"), "textAlign": "center",
                           "padding": "3rem", "fontFamily": FONT}),
                    "", "No holdings.", {}, [], _hidden)

            total_value = holdings_df["market_value"].sum()
            holdings_dict = {
                row["ticker"]: row["market_value"] / total_value
                for _, row in holdings_df.iterrows() if total_value > 0
            }

            isin_map = get_isin_map()
            factors = list(GEMLTL_STYLE_FACTORS.keys())

            df = fetch_portfolio_factor_snapshot(
                holdings_dict=holdings_dict,
                model="GEMLTL",
                factors=factors,
                isin_override=isin_map,
            )

            if df.empty:
                return (html.Div("No Barra data returned. Check ticker/ISIN mapping.",
                    style={"color": C.get("muted", "#888"), "textAlign": "center",
                           "padding": "3rem", "fontFamily": FONT}),
                    "", "No data.", {}, [], _hidden)

            bucket_scores = _compute_bucket_scores(df)

            matched   = df["MATCHED_TICKERS"].iloc[0]   if "MATCHED_TICKERS"   in df.columns else ""
            unmatched = df["UNMATCHED_TICKERS"].iloc[0] if "UNMATCHED_TICKERS" in df.columns else ""
            cov_pct   = df["COVERAGE_PCT"].iloc[0]      if "COVERAGE_PCT"      in df.columns else 0
            date_str  = str(df["DATE_OF_DATA"].iloc[0]) if "DATE_OF_DATA"      in df.columns else "latest"

            coverage_div = html.Div([
                html.Span(f"Coverage: {cov_pct:.1f}%  ",
                    style={"fontWeight": "700", "color": C.get("accent", "#fabc00")}),
                html.Span(f"Matched: {matched}",
                    style={"color": C.get("text", "#fff"), "marginRight": "1rem"}),
                html.Br(),
                html.Span(f"No Barra ID: {unmatched}" if unmatched else "",
                    style={"color": C.get("muted", "#888")}),
            ])

            store = {
                "factors": df[["FACTOR", "PORTFOLIO_SCORE"]].to_dict("records"),
                "bucket_scores": bucket_scores,
            }
            # Build holdings list for what-if editor (pct weights)
            holdings_list = [
                {"ticker": t, "weight": round(w * 100, 2)}
                for t, w in sorted(holdings_dict.items())
            ]
            chart_area = _overview_layout(df, bucket_scores, FONT, C)
            status = f"Analysis complete  {len(df)} factors  data as of {date_str}"
            return chart_area, coverage_div, status, store, holdings_list, _visible

        except Exception:
            err = traceback.format_exc()
            return (html.Div([
                html.Div("Error:", style={"color": C.get("red", "#f87171"),
                         "fontWeight": "700", "fontFamily": FONT}),
                html.Pre(err, style={"color": C.get("muted", "#888"), "fontSize": "0.65rem",
                         "fontFamily": "monospace", "whiteSpace": "pre-wrap"}),
            ]), "", "Error.", {}, [], {"display": "none"})

    def _btn_style(active):
        return {
            "backgroundColor": C.get("accent", "#fabc00") if active else C.get("panel", "#1e1e1e"),
            "color": "#000" if active else C.get("text", "#fff"),
            "border": f"1px solid {C.get('border', '#333')}",
            "borderRadius": "6px", "padding": "0.32rem 0.7rem",
            "fontFamily": FONT, "fontWeight": "700",
            "fontSize": "0.72rem", "cursor": "pointer",
        }

    @app.callback(
        Output("ft-chart-area", "children", allow_duplicate=True),
        Output("ft-view-overview-btn", "style"),
        Output("ft-view-detail-btn",   "style"),
        Output("ft-view-map-btn",      "style"),
        Input("ft-view-overview-btn", "n_clicks"),
        Input("ft-view-detail-btn",   "n_clicks"),
        Input("ft-view-map-btn",      "n_clicks"),
        State("ft-data-store", "data"),
        prevent_initial_call=True,
    )
    def switch_view(n_ov, n_det, n_map, store):
        from dash import ctx
        if not store or "factors" not in store:
            raise PreventUpdate
        df = pd.DataFrame(store["factors"])
        bucket_scores = store.get("bucket_scores", {})
        triggered = ctx.triggered_id
        if triggered == "ft-view-detail-btn":
            return _detail_layout(df, FONT, C), _btn_style(False), _btn_style(True), _btn_style(False)
        elif triggered == "ft-view-map-btn":
            return _map_layout(bucket_scores, FONT, C), _btn_style(False), _btn_style(False), _btn_style(True)
        else:
            return _overview_layout(df, bucket_scores, FONT, C), _btn_style(True), _btn_style(False), _btn_style(False)

    # ── What-If: populate / add row / reset ──────────────────────────────────

    def _build_holdings_table(holdings, font, C):
        """Render all holdings as a clean HTML table with inline weight inputs."""
        th_style = {
            "color": C.get("muted", "#888"), "fontSize": "0.65rem",
            "fontFamily": font, "fontWeight": "700",
            "textTransform": "uppercase", "letterSpacing": "0.05em",
            "padding": "0 0.5rem 0.4rem 0.5rem", "textAlign": "left",
            "borderBottom": f"1px solid {C.get('border', '#333')}",
        }
        header = html.Tr([
            html.Th("Ticker",  style={**th_style, "width": "100px"}),
            html.Th("Weight",  style={**th_style, "width": "90px", "textAlign": "right"}),
            html.Th("Allocation", style={**th_style}),
            html.Th("",        style={**th_style, "width": "24px"}),
        ])

        max_w = max((h["weight"] for h in holdings), default=1) or 1
        body_rows = []
        for h in holdings:
            ticker = h["ticker"]
            weight = h["weight"]
            bar_pct = weight / max_w * 100
            td_style = {
                "padding": "0.3rem 0.5rem",
                "borderBottom": f"1px solid {C.get('border', '#1a1a1a')}",
                "verticalAlign": "middle",
            }
            body_rows.append(html.Tr([
                html.Td(ticker, style={**td_style,
                    "color": C.get("text", "#fff"),
                    "fontFamily": font, "fontSize": "0.82rem",
                    "fontWeight": "600"}),
                html.Td(
                    html.Div([
                        dcc.Input(
                            id={"type": "ft-wi-weight", "ticker": ticker},
                            type="number", value=round(weight, 2),
                            min=0, max=100, step=0.1,
                            style={
                                "backgroundColor": C.get("bg", "#111"),
                                "border": f"1px solid {C.get('border', '#333')}",
                                "borderRadius": "5px",
                                "color": C.get("text", "#fff"),
                                "padding": "0.2rem 0.4rem",
                                "fontFamily": font, "fontSize": "0.78rem",
                                "width": "60px", "outline": "none",
                                "textAlign": "right",
                            },
                        ),
                        html.Span("%", style={"color": C.get("muted", "#888"),
                                              "fontSize": "0.72rem",
                                              "fontFamily": font,
                                              "marginLeft": "2px"}),
                    ], style={"display": "flex", "alignItems": "center",
                              "justifyContent": "flex-end"}),
                    style={**td_style, "textAlign": "right"}),
                html.Td(
                    html.Div(style={"height": "8px", "borderRadius": "4px",
                                   "backgroundColor": C.get("border", "#333"),
                                   "overflow": "hidden"}, children=[
                        html.Div(style={"height": "8px",
                                        "backgroundColor": C.get("accent", "#fabc00"),
                                        "borderRadius": "4px",
                                        "width": f"{bar_pct:.1f}%",
                                        "transition": "width 0.3s ease"}),
                    ]),
                    style={**td_style, "minWidth": "120px"}),
                html.Td(
                    html.Button("x",
                        id={"type": "ft-wi-del", "ticker": ticker},
                        n_clicks=0,
                        style={"background": "none", "border": "none",
                               "cursor": "pointer",
                               "color": C.get("muted", "#888"),
                               "fontSize": "1rem", "padding": "0",
                               "lineHeight": "1"}),
                    style={**td_style, "textAlign": "center"}),
            ]))

        total = sum(h["weight"] for h in holdings)
        warn = abs(total - 100) > 0.5
        footer = html.Tr([
            html.Td("Total", style={"padding": "0.4rem 0.5rem",
                "color": C.get("muted", "#888"),
                "fontFamily": font, "fontSize": "0.72rem",
                "fontWeight": "700", "borderTop": f"1px solid {C.get('border', '#333')}"}),
            html.Td(
                f"{total:.1f}%" + ("  *" if warn else ""),
                style={"padding": "0.4rem 0.5rem", "textAlign": "right",
                       "fontFamily": font, "fontSize": "0.78rem", "fontWeight": "700",
                       "color": C.get("accent", "#fabc00") if warn else C.get("text", "#fff"),
                       "borderTop": f"1px solid {C.get('border', '#333')}"}),
            html.Td(
                "* will be normalised" if warn else "",
                colSpan=2,
                style={"padding": "0.4rem 0.5rem", "fontSize": "0.68rem",
                       "color": C.get("muted", "#888"), "fontFamily": font,
                       "borderTop": f"1px solid {C.get('border', '#333')}"}),
        ])

        return html.Table(
            [html.Thead(header), html.Tbody(body_rows), html.Tfoot(footer)],
            style={"width": "100%", "borderCollapse": "collapse",
                   "tableLayout": "fixed"},
        )

    @app.callback(
        Output("ft-weight-rows", "children"),
        Output("ft-holdings-store", "data", allow_duplicate=True),
        Input("ft-holdings-store", "data"),
        Input("ft-add-row-btn",    "n_clicks"),
        Input({"type": "ft-wi-del", "ticker": "*"}, "n_clicks"),
        Input("ft-reset-btn",      "n_clicks"),
        State("ft-add-ticker",     "value"),
        State("ft-add-weight",     "value"),
        State({"type": "ft-wi-weight", "ticker": "*"}, "value"),
        State({"type": "ft-wi-weight", "ticker": "*"}, "id"),
        prevent_initial_call=True,
    )
    def update_weight_rows(holdings, _add_n, _del_n, _reset_n,
                           add_ticker, add_weight,
                           current_weights, current_ids):
        from dash import ctx
        tid = ctx.triggered_id

        # On reset, use the stored holdings directly (don't read live inputs)
        if tid == "ft-reset-btn":
            pass  # holdings already has original values from store
        else:
            # Reconstruct current state from live weight inputs
            if current_ids and current_weights:
                holdings = [
                    {"ticker": id_["ticker"], "weight": w or 0}
                    for id_, w in zip(current_ids, current_weights)
                ]

            # Delete row
            if isinstance(tid, dict) and tid.get("type") == "ft-wi-del":
                holdings = [h for h in holdings if h["ticker"] != tid["ticker"]]

            # Add row
            elif tid == "ft-add-row-btn" and add_ticker:
                ticker = add_ticker.strip().upper()
                existing = [h["ticker"] for h in holdings]
                if ticker not in existing:
                    holdings.append({"ticker": ticker, "weight": float(add_weight or 0)})

        try:
            tbl = _build_holdings_table(holdings, FONT, C)
        except Exception as _e:
            import traceback as _tb
            tbl = html.Pre(_tb.format_exc(),
                           style={"color": "red", "fontSize": "0.65rem",
                                  "whiteSpace": "pre-wrap"})
        return tbl, holdings

    @app.callback(
        Output("ft-chart-area",     "children", allow_duplicate=True),
        Output("ft-coverage-info",  "children", allow_duplicate=True),
        Output("ft-status",         "children", allow_duplicate=True),
        Output("ft-data-store",     "data",     allow_duplicate=True),
        Output("ft-whatif-status",  "children"),
        Input("ft-recalc-btn", "n_clicks"),
        State({"type": "ft-wi-weight", "ticker": "*"}, "value"),
        State({"type": "ft-wi-weight", "ticker": "*"}, "id"),
        prevent_initial_call=True,
    )
    def recalculate(n, weights, ids):
        if not n or not ids:
            raise PreventUpdate
        try:
            raw = {id_["ticker"]: float(w or 0) for id_, w in zip(ids, weights)}
            total = sum(raw.values())
            if total <= 0:
                return no_update, no_update, no_update, no_update, "Weights sum to zero."
            holdings_dict = {t: w / total for t, w in raw.items() if w > 0}

            isin_map = get_isin_map()
            factors  = list(GEMLTL_STYLE_FACTORS.keys())

            df = fetch_portfolio_factor_snapshot(
                holdings_dict=holdings_dict,
                model="GEMLTL",
                factors=factors,
                isin_override=isin_map,
            )
            if df.empty:
                return no_update, no_update, no_update, no_update, "No Barra data returned."

            bucket_scores = _compute_bucket_scores(df)
            matched   = df["MATCHED_TICKERS"].iloc[0]   if "MATCHED_TICKERS"   in df.columns else ""
            unmatched = df["UNMATCHED_TICKERS"].iloc[0] if "UNMATCHED_TICKERS" in df.columns else ""
            cov_pct   = df["COVERAGE_PCT"].iloc[0]      if "COVERAGE_PCT"      in df.columns else 0
            date_str  = str(df["DATE_OF_DATA"].iloc[0]) if "DATE_OF_DATA"      in df.columns else "latest"

            coverage_div = html.Div([
                html.Span(f"Coverage: {cov_pct:.1f}%  ",
                    style={"fontWeight": "700", "color": C.get("accent", "#fabc00")}),
                html.Span(f"Matched: {matched}",
                    style={"color": C.get("text", "#fff"), "marginRight": "1rem"}),
                html.Br(),
                html.Span(f"No Barra ID: {unmatched}" if unmatched else "",
                    style={"color": C.get("muted", "#888")}),
            ])
            store = {
                "factors": df[["FACTOR", "PORTFOLIO_SCORE"]].to_dict("records"),
                "bucket_scores": bucket_scores,
            }
            tickers_str = ", ".join(f"{t} {w*100:.1f}%" for t, w in sorted(holdings_dict.items()))
            status = f"What-If result  {len(df)} factors  {date_str}"
            wi_status = f"Recalculated  |  {tickers_str}"
            return _overview_layout(df, bucket_scores, FONT, C), coverage_div, status, store, wi_status

        except Exception:
            err = traceback.format_exc()
            return no_update, no_update, no_update, no_update, f"Error: {err[:120]}"
