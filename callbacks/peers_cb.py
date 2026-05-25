import pandas as pd
import dash
from dash import Input, Output, State, html, dcc, dash_table, no_update, ALL, MATCH
import plotly.graph_objects as go

from theme import get_theme, FONT
from snowflake_data import (
    search_tickers, _resolve_ids, fetch_peer_comparison,
    fetch_peers_comparison_metrics,
)


def _offline_banner():
    return html.Div([
        html.Div("📡", style={"fontSize": "2.5rem", "marginBottom": "0.5rem"}),
        html.Div("Offline Mode", style={"fontWeight": "800", "fontSize": "1.1rem",
                                        "color": "#ff8c00", "marginBottom": "0.4rem"}),
        html.Div("This page requires a Snowflake / FactSet connection.",
                 style={"color": "#888", "fontSize": "0.82rem", "marginBottom": "0.3rem"}),
        html.Div("Toggle 🔌 SF → 📡 YF in the top bar to switch to offline mode, or reconnect.",
                 style={"color": "#666", "fontSize": "0.75rem"}),
    ], style={"textAlign": "center", "padding": "3rem 2rem",
              "fontFamily": "'Inter', sans-serif"})


def register_callbacks(app):

    # ── Target ticker autocomplete ───────────────────────────────────────────
    @app.callback(
        Output("peers-ticker-suggestions", "children"),
        Input("peers-ticker", "value"),
        prevent_initial_call=True,
    )
    def update_peer_ticker_options(search):
        if not search or len(search.strip()) < 2:
            return []
        search = search.strip()
        if "-" in search and len(search) >= 5:
            return []
        try:
            results = search_tickers(search, limit=20)
        except Exception:
            return []
        cards = []
        for r in results:
            region = f" · {r['region']}" if r.get("region") else ""
            exch = f" · {r['exchange']}" if r.get("exchange") else ""
            cards.append(
                html.Button(
                    [
                        html.Span(f"{r['ticker']}{region}{exch}", style={"fontWeight": "700"}),
                        html.Span(f"  {r['name']}", style={"marginLeft": "0.35rem"}),
                    ],
                    id={"type": "peers-ticker-suggestion", "index": r["ticker_region"]},
                    n_clicks=0,
                    style={
                        "backgroundColor": "#0b0b0b", "border": "1px solid #2a2a2a",
                        "color": "#e6e6e6", "padding": "0.45rem 0.65rem",
                        "textAlign": "left", "fontFamily": FONT, "fontSize": "0.76rem",
                        "cursor": "pointer",
                    },
                )
            )
        return cards[:8]

    @app.callback(
        Output("peers-ticker", "value", allow_duplicate=True),
        Output("peers-ticker-suggestions", "children", allow_duplicate=True),
        Input({"type": "peers-ticker-suggestion", "index": ALL}, "n_clicks"),
        State({"type": "peers-ticker-suggestion", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def choose_peer_ticker_suggestion(clicks, ids):
        if not clicks or not any(clicks):
            return no_update, no_update
        for n, item in zip(clicks, ids):
            if n:
                return item["index"], []
        return no_update, no_update

    # ── Custom peer typeahead ────────────────────────────────────────────────
    @app.callback(
        Output("peers-custom-suggestions", "children"),
        Input("peers-custom-input", "value"),
        prevent_initial_call=True,
    )
    def update_custom_peer_suggestions(search):
        if not search or len(search.strip()) < 2:
            return []
        search = search.strip()
        if "-" in search and len(search) >= 5:
            return []
        try:
            results = search_tickers(search, limit=12)
        except Exception:
            return []
        cards = []
        for r in results[:6]:
            region = f" · {r['region']}" if r.get("region") else ""
            cards.append(
                html.Button(
                    [
                        html.Span(f"{r['ticker']}{region}", style={"fontWeight": "700"}),
                        html.Span(f"  {r['name']}", style={"marginLeft": "0.3rem",
                                                            "color": "#aaa"}),
                    ],
                    id={"type": "peers-custom-suggestion", "index": r["ticker_region"]},
                    n_clicks=0,
                    style={
                        "backgroundColor": "#0b0b0b", "border": "1px solid #2a2a2a",
                        "color": "#e6e6e6", "padding": "0.4rem 0.6rem",
                        "textAlign": "left", "fontFamily": FONT, "fontSize": "0.74rem",
                        "cursor": "pointer",
                    },
                )
            )
        return cards

    @app.callback(
        Output("peers-custom-input", "value", allow_duplicate=True),
        Output("peers-custom-suggestions", "children", allow_duplicate=True),
        Input({"type": "peers-custom-suggestion", "index": ALL}, "n_clicks"),
        State({"type": "peers-custom-suggestion", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def choose_custom_peer_suggestion(clicks, ids):
        if not clicks or not any(clicks):
            return no_update, no_update
        for n, item in zip(clicks, ids):
            if n:
                return item["index"], []
        return no_update, no_update

    # ── Add custom peer to store ─────────────────────────────────────────────
    @app.callback(
        Output("peers-custom-list", "data"),
        Output("peers-custom-input", "value", allow_duplicate=True),
        Output("peers-custom-error", "children"),
        Input("peers-custom-add-btn", "n_clicks"),
        State("peers-custom-input", "value"),
        State("peers-custom-list", "data"),
        prevent_initial_call=True,
    )
    def add_custom_peer(n_clicks, raw, current_list):
        if not n_clicks or not raw or not raw.strip():
            return no_update, no_update, ""
        ticker = raw.strip().upper()
        current_list = current_list or []
        # Dedup
        existing_tickers = [p["ticker"] for p in current_list]
        if ticker in existing_tickers:
            return no_update, "", f"'{ticker}' already in list."
        # Resolve to get fsym_id + name
        try:
            ids = _resolve_ids(ticker)
        except Exception as e:
            return no_update, "", f"❌ {e}"
        if ids is None:
            return no_update, "", f"❌ '{ticker}' not found in FactSet."
        entry = {
            "ticker": ticker,
            "fsym_id": ids.get("fsym_id"),
            "name": ids.get("name") or ticker,
        }
        return current_list + [entry], "", ""

    # ── Remove custom peer from store ────────────────────────────────────────
    @app.callback(
        Output("peers-custom-list", "data", allow_duplicate=True),
        Input({"type": "peers-remove-chip", "index": ALL}, "n_clicks"),
        State("peers-custom-list", "data"),
        prevent_initial_call=True,
    )
    def remove_custom_peer(clicks, current_list):
        if not clicks or not any(c for c in clicks if c):
            return no_update
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update
        triggered_id = ctx.triggered[0]["prop_id"]
        import json
        try:
            id_dict = json.loads(triggered_id.split(".")[0])
            idx = id_dict["index"]
        except Exception:
            return no_update
        current_list = current_list or []
        return [p for p in current_list if p["ticker"] != idx]

    # ── Render custom peer chips ─────────────────────────────────────────────
    @app.callback(
        Output("peers-custom-chips", "children"),
        Input("peers-custom-list", "data"),
        State("theme-store", "data"),
    )
    def render_custom_chips(peer_list, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not peer_list:
            return [html.Span("No custom peers added yet.",
                              style={"color": c["muted"], "fontSize": "0.72rem",
                                     "fontFamily": FONT, "fontStyle": "italic"})]
        chips = []
        for p in peer_list:
            chips.append(html.Div([
                html.Span(p["ticker"], style={"fontWeight": "700", "marginRight": "0.3rem",
                                              "color": c["accent"]}),
                html.Span(p.get("name", ""), style={"color": c["muted"], "fontSize": "0.7rem",
                                                     "marginRight": "0.4rem"}),
                html.Button("✕", id={"type": "peers-remove-chip", "index": p["ticker"]},
                            n_clicks=0,
                            style={"background": "none", "border": "none",
                                   "color": "#ff6b6b", "cursor": "pointer",
                                   "fontSize": "0.75rem", "padding": "0 0.1rem",
                                   "fontFamily": FONT}),
            ], style={
                "display": "inline-flex", "alignItems": "center",
                "backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
                "borderRadius": "20px", "padding": "0.25rem 0.6rem",
                "fontFamily": FONT, "fontSize": "0.76rem",
            }))
        return chips

    # ── Main load (RBICS table + chart + analysis) ───────────────────────────
    @app.callback(
        Output("peers-summary", "children"),
        Output("peers-table", "children"),
        Output("peers-chart", "figure"),
        Output("peers-status", "children"),
        Output("peers-analysis-div", "children"),
        Input("peers-load-btn", "n_clicks"),
        State("peers-ticker", "value"),
        State("peers-custom-list", "data"),
        State("peers-recovery-store", "data"),
        State("theme-store", "data"),
        State("datasource", "data"),
        prevent_initial_call=True,
    )
    def load_peers(n_clicks, ticker_raw, custom_list, recovery_data, theme_mode, datasource):
        c = get_theme(theme_mode or "dark")
        empty_fig = _empty_figure(c, "No peer data")
        empty_analysis = html.Div()

        if datasource == "yf":
            banner = _offline_banner()
            return banner, html.Div(), empty_fig, "⚠️ Offline mode — Snowflake required", empty_analysis

        if not ticker_raw or not ticker_raw.strip():
            return html.Div(), html.Div(), empty_fig, "", empty_analysis

        ticker, ids = _resolve_peer_ticker_input(ticker_raw)
        if isinstance(ids, Exception):
            return html.Div(), html.Div(), empty_fig, f"❌ {ids}", empty_analysis
        if ids is None or not ids.get("entity_id"):
            failed = str(ticker_raw).strip().upper()
            return html.Div(), html.Div(), empty_fig, f"❌ Ticker '{failed}' not found in FactSet.", empty_analysis

        # ── RBICS peers ──────────────────────────────────────────────────────
        try:
            peers = fetch_peer_comparison(ids["entity_id"], limit=12)
        except Exception as e:
            return html.Div(), html.Div(), empty_fig, f"❌ {e}", empty_analysis

        if not peers:
            msg = "No peers found."
            return html.Div(), html.Div(msg, style={"color": c["muted"], "fontFamily": FONT}), empty_fig, msg, empty_analysis

        df = pd.DataFrame(peers).drop_duplicates(subset=["ticker_region"]).reset_index(drop=True)

        # ── Summary banner ───────────────────────────────────────────────────
        summary = html.Div([
            html.Div([
                html.Span(ids.get("name") or ticker,
                          style={"fontFamily": FONT, "fontWeight": "800",
                                 "fontSize": "1.2rem", "color": c["text"]}),
                html.Span(f"  {ticker}",
                          style={"fontFamily": FONT, "fontSize": "0.9rem",
                                 "color": c["muted"], "marginLeft": "0.4rem"}),
            ]),
            html.Div("Peer set derived from FactSet RBICS industry mapping.",
                     style={"fontFamily": FONT, "fontSize": "0.75rem",
                            "color": c["subtext"], "marginTop": "0.25rem"}),
        ], style={"backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
                  "borderRadius": "10px", "padding": "1rem 1.2rem"})

        # ── Market data table ────────────────────────────────────────────────
        table_df = pd.DataFrame({
            "Ticker": df["ticker"],
            "Name": df["name"],
            "Mkt Cap": df["mkt_cap"].apply(_fmt_money),
            "P/E": df["pe"].apply(_fmt_x),
            "P/S": df["ps"].apply(_fmt_x),
            "P/CF": df["pcf"].apply(_fmt_x),
            "Gross Mgn": df["gross_margin"].apply(_fmt_pct),
            "Oper Mgn": df["oper_margin"].apply(_fmt_pct),
            "Net Mgn": df["net_margin"].apply(_fmt_pct),
            "EBITDA": df["ebitda"].apply(_fmt_money),
            "FCF": df["free_cf"].apply(_fmt_money),
        })
        table_df.insert(0, "Target", df["is_target"].apply(lambda v: "●" if v else ""))

        peer_table = dash_table.DataTable(
            columns=[{"name": col, "id": col} for col in table_df.columns],
            data=table_df.to_dict("records"),
            page_action="none", sort_action="native",
            style_table={"overflowX": "auto", "maxHeight": "380px", "overflowY": "auto"},
            style_header={
                "backgroundColor": c["panel"], "color": c["text"], "fontWeight": "700",
                "fontFamily": FONT, "fontSize": "0.72rem",
                "borderBottom": f"1px solid {c['border']}", "position": "sticky", "top": 0,
                "whiteSpace": "nowrap",
            },
            style_cell={
                "backgroundColor": c["bg"], "color": c["text"], "fontFamily": FONT,
                "fontSize": "0.72rem", "padding": "5px 8px",
                "borderBottom": f"1px solid {c['border']}", "textAlign": "right",
                "whiteSpace": "nowrap",
            },
            style_data_conditional=[
                {"if": {"column_id": "Ticker"}, "textAlign": "left", "color": c["accent"], "fontWeight": "700"},
                {"if": {"column_id": "Name"}, "textAlign": "left"},
                {"if": {"column_id": "Target"}, "color": c["blue"], "textAlign": "center", "fontSize": "0.85rem"},
                {"if": {"filter_query": "{Target} = \"●\""}, "backgroundColor": c["panel"]},
            ],
        )

        # ── Scatter chart ────────────────────────────────────────────────────
        chart_df = df.copy()
        chart_df["pe_plot"] = pd.to_numeric(chart_df["pe"], errors="coerce")
        chart_df["ps_plot"] = pd.to_numeric(chart_df["ps"], errors="coerce")
        chart_df["mkt_plot"] = pd.to_numeric(chart_df["mkt_cap"], errors="coerce")
        chart_df = chart_df.dropna(subset=["pe_plot", "ps_plot"])

        fig = go.Figure()
        if not chart_df.empty:
            fig.add_trace(go.Scatter(
                x=chart_df["ps_plot"], y=chart_df["pe_plot"],
                mode="markers+text", text=chart_df["ticker"], textposition="top center",
                marker=dict(
                    size=chart_df["mkt_plot"].fillna(0).apply(
                        lambda v: 14 if v and v > 50000 else 10 if v and v > 10000 else 8),
                    color=chart_df["is_target"].apply(lambda v: c["blue"] if v else c["accent"]),
                    opacity=0.85, line=dict(color=c["text"], width=0.8),
                ),
                hovertemplate="%{text}<br>P/S: %{x:.1f}x<br>P/E: %{y:.1f}x<extra></extra>",
            ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["subtext"], size=11),
            margin=dict(l=40, r=10, t=10, b=40),
            xaxis=dict(title="P/S", showgrid=True, gridcolor=c["border"], color=c["muted"]),
            yaxis=dict(title="P/E", showgrid=True, gridcolor=c["border"], color=c["muted"]),
        )

        # ── 5-section analysis ───────────────────────────────────────────────
        # Collect fsym_ids: target + custom peers
        custom_list = custom_list or []
        fsym_ids_to_fetch = []
        fsym_label_map = {}  # fsym_id → display label

        target_fsym = ids.get("fsym_id")
        target_name = ids.get("name") or ticker
        if target_fsym:
            fsym_ids_to_fetch.append(target_fsym)
            fsym_label_map[target_fsym] = {
                "label": f"{ticker.split('-')[0]}",
                "name": target_name,
                "is_target": True,
            }

        for cp in custom_list:
            fid = cp.get("fsym_id")
            if fid and fid not in fsym_label_map:
                fsym_ids_to_fetch.append(fid)
                fsym_label_map[fid] = {
                    "label": cp["ticker"].split("-")[0],
                    "name": cp.get("name", cp["ticker"]),
                    "is_target": False,
                }

        analysis_div = empty_analysis
        if len(fsym_ids_to_fetch) >= 1:
            try:
                metrics_df = fetch_peers_comparison_metrics(fsym_ids_to_fetch)
                analysis_div = _build_analysis_sections(
                    metrics_df, fsym_label_map, recovery_data or {}, c
                )
            except Exception as e:
                analysis_div = html.Div(f"⚠️ Analysis error: {e}",
                                        style={"color": "#ff6b6b", "fontFamily": FONT,
                                               "fontSize": "0.8rem", "padding": "1rem"})

        status = f"✅ {len(df)} companies loaded (RBICS) • {len(custom_list)} custom peer(s)"
        return summary, peer_table, fig, status, analysis_div

    # ── Recovery store: editable inputs ─────────────────────────────────────
    @app.callback(
        Output("peers-recovery-store", "data"),
        Input({"type": "peers-recovery-input", "index": ALL}, "value"),
        State({"type": "peers-recovery-input", "index": ALL}, "id"),
        State("peers-recovery-store", "data"),
        prevent_initial_call=True,
    )
    def update_recovery_store(values, input_ids, current_data):
        current_data = current_data or {}
        for val, id_dict in zip(values, input_ids):
            key = id_dict["index"]  # format: "TICKER__field"
            if val is not None:
                current_data[key] = val
        return current_data


def _fmt_x(v):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{float(v):.1f}x"


def _fmt_pct(v):
    return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{float(v):.1f}%"


def _fmt_money(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    v = float(v)
    if abs(v) >= 1000:
        return f"{v/1000:,.1f}B"
    return f"{v:,.0f}M"


def _fmt_val(v, fmt="x", dp=1):
    """Format a value: 'x' for multiple, '%' for percent, 'raw' for plain."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        f = float(v)
    except Exception:
        return "—"
    if fmt == "x":
        return f"{f:.{dp}f}x"
    if fmt == "%":
        return f"{f:.{dp}f}%"
    return f"{f:.{dp}f}"


def _resolve_peer_ticker_input(raw_value):
    if not raw_value or not str(raw_value).strip():
        return None, None

    query = str(raw_value).strip().upper()
    try:
        ids = _resolve_ids(query)
        if ids:
            return query, ids
    except Exception as e:
        direct_error = e
    else:
        direct_error = None

    try:
        results = search_tickers(query, limit=8)
    except Exception as e:
        return query, direct_error or e

    if not results:
        return query, None

    exact = next(
        (r for r in results
         if query in {str(r.get("ticker", "")).upper(),
                      str(r.get("ticker_region", "")).upper(),
                      str(r.get("name", "")).upper()}),
        None,
    )
    chosen = exact or results[0]
    chosen_ticker = chosen.get("ticker_region")
    if not chosen_ticker:
        return query, None

    try:
        ids = _resolve_ids(chosen_ticker)
        return chosen_ticker, ids
    except Exception as e:
        return chosen_ticker, e


def _empty_figure(c, msg="No data"):
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=c["subtext"]),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(text=msg, showarrow=False,
                          font=dict(size=13, color=c["muted"], family=FONT))],
    )
    return fig


# ── Analysis section builder ─────────────────────────────────────────────────

def _build_analysis_sections(metrics_df, fsym_label_map, recovery_data, c):
    """Build 5-section peer comparison tables from metrics DataFrame."""

    # Order: target first, then custom peers
    ordered_fsyms = sorted(
        [fid for fid in fsym_label_map if fid in metrics_df["FSYM_ID"].values],
        key=lambda f: (0 if fsym_label_map[f].get("is_target") else 1,
                       fsym_label_map[f]["label"])
    )

    if not ordered_fsyms:
        return html.Div("No metric data available.", style={"color": c["muted"], "fontFamily": FONT,
                                                            "padding": "1rem"})

    # Build lookup dict
    data = {}
    for _, row in metrics_df.iterrows():
        fid = row["FSYM_ID"]
        if fid in fsym_label_map:
            data[fid] = row

    peer_fsyms = [f for f in ordered_fsyms if not fsym_label_map[f].get("is_target")]
    target_fsym = next((f for f in ordered_fsyms if fsym_label_map[f].get("is_target")), None)

    col_labels = [fsym_label_map[f]["label"] for f in ordered_fsyms]
    col_names  = [fsym_label_map[f]["name"] for f in ordered_fsyms]

    def get(fid, field):
        row = data.get(fid)
        if row is None:
            return None
        v = row.get(field)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)

    def peer_avg(field, fmt="x"):
        vals = [get(f, field) for f in peer_fsyms if get(f, field) is not None]
        return sum(vals) / len(vals) if vals else None

    def vs_avg(target_val, avg_val, fmt="x"):
        if target_val is None or avg_val is None or avg_val == 0:
            return "—"
        if fmt == "%":
            diff = target_val - avg_val
            return f"{'+' if diff > 0 else ''}{diff:.1f}pp"
        # For multiples: premium/discount
        prem = (target_val / avg_val - 1) * 100
        return f"{'+' if prem > 0 else ''}{prem:.0f}%"

    def row_data(metric_label, field, fmt="x", dp=1, recovery_key=None):
        """Build one row dict for the comparison table."""
        row = {"Metric": metric_label}
        for fid, lbl in zip(ordered_fsyms, col_labels):
            if recovery_key and fid == target_fsym:
                # manual entry for target (Recovery section)
                rk = f"{lbl}__{recovery_key}"
                stored = recovery_data.get(rk)
                row[lbl] = _fmt_val(stored, fmt, dp) if stored is not None else "—"
            else:
                row[lbl] = _fmt_val(get(fid, field), fmt, dp)
        avg = peer_avg(field, fmt)
        row["Peer Avg"] = _fmt_val(avg, fmt, dp)
        tgt_val = get(target_fsym, field) if target_fsym else None
        row["vs Peer Avg"] = vs_avg(tgt_val, avg, fmt)
        return row

    def manual_row(metric_label, rk_suffix, fmt="%", dp=1, derived_fn=None):
        """Row with manual input fields (Recovery section)."""
        row = {"Metric": metric_label}
        for fid, lbl in zip(ordered_fsyms, col_labels):
            key = f"{lbl}__{rk_suffix}"
            stored = recovery_data.get(key)
            if derived_fn:
                row[lbl] = derived_fn(fid, lbl, stored)
            else:
                row[lbl] = _fmt_val(stored, fmt, dp) if stored is not None else "—"
        row["Peer Avg"] = "—"
        row["vs Peer Avg"] = "—"
        return row

    # ── Section data ─────────────────────────────────────────────────────────

    # 1. Relative Valuation
    valuation_rows = [
        row_data("EV / Sales NTM",     "EVSALES_NTM",          "x"),
        row_data("EV / EBITDA NTM",    "EVEBITDA_NTM",         "x"),
        row_data("EV / EBIT NTM",      "EVEBIT_NTM",           "x"),
        row_data("P / E NTM",          "PE_NTM",               "x"),
        row_data("FCF Yield NTM",      "FCF_YIELD_NTM",        "%"),
        row_data("Net Debt / EBITDA",  "NET_DEBT_EBITDA_NTM",  "x"),
    ]

    # 2. Growth
    growth_rows = [
        row_data("Sales Growth NTM",   "SALES_GR_NTM",    "%"),
        row_data("EBIT Growth NTM",    "EBIT_GR_NTM",     "%"),
        row_data("EPS Growth NTM",     "EPS_GR_NTM",      "%"),
        # Organic / CC: manual (not available from FactSet standard)
        manual_row("Organic Sales Growth NTM", "organic_growth"),
    ]

    # 3. Profitability
    profit_rows = [
        row_data("Gross Margin",          "GROSS_MARGIN",  "%"),
        row_data("EBITDA Margin",         "EBITDA_MARGIN", "%"),
        row_data("EBIT Margin",           "EBIT_MARGIN",   "%"),
        row_data("Net Income Margin LTM", "NET_MARGIN",    "%"),
        row_data("FCF Margin",            "FCF_MARGIN",    "%"),
    ]

    # 4. Returns / Quality
    returns_rows = [
        row_data("ROIC",           "ROIC",           "%"),
        row_data("ROE",            "ROE",            "%"),
        row_data("Asset Turnover", "ASSET_TURNOVER", "x"),
    ]

    # 5. Recovery (mix of LTM actuals + manual entries)
    def _margin_gap(fid, lbl, stored):
        """Current EBIT Margin - Last Normal Year (stored)."""
        if stored is None:
            return "—"
        current = get(fid, "EBIT_MARGIN")
        if current is None:
            return "—"
        gap = current - float(stored)
        return f"{'+' if gap > 0 else ''}{gap:.1f}pp"

    recovery_rows = [
        manual_row("EBIT Margin (Last Normal Year)", "last_normal_margin"),
        row_data("Current EBIT Margin",              "EBIT_MARGIN", "%"),
        # Margin Gap = current - last normal year
        manual_row("Margin Gap vs Normal", "last_normal_margin",
                   derived_fn=_margin_gap),
        manual_row("Mgmt Mid-Term EBIT Target",      "mgmt_target"),
    ]

    SECTIONS = [
        ("Relative Valuation",  valuation_rows),
        ("Growth",              growth_rows),
        ("Profitability",       profit_rows),
        ("Returns / Quality",   returns_rows),
        ("Recovery",            recovery_rows),
    ]

    all_cols = col_labels + ["Peer Avg", "vs Peer Avg"]
    header_cols = ["Metric"] + all_cols

    divs = []
    for section_title, rows in SECTIONS:
        section_div = _build_section_table(
            section_title, rows, header_cols, col_labels, col_names,
            ordered_fsyms, fsym_label_map, target_fsym, c
        )
        divs.append(section_div)

    # Add Recovery editable hint
    recovery_inputs = _build_recovery_inputs(
        ordered_fsyms, fsym_label_map, recovery_data, c
    )
    divs.append(recovery_inputs)

    return html.Div(divs, style={"display": "flex", "flexDirection": "column", "gap": "0.6rem"})


def _build_section_table(title, rows, header_cols, col_labels, col_names,
                         ordered_fsyms, fsym_label_map, target_fsym, c):
    # Header row with company names (sub-labels)
    PANEL = {
        "backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
        "borderRadius": "10px",
    }

    col_widths = {"Metric": "200px"}
    for lbl in col_labels:
        col_widths[lbl] = "130px"
    col_widths["Peer Avg"] = "110px"
    col_widths["vs Peer Avg"] = "120px"

    # Build company sub-header
    sub_cells = [html.Th("", style=_th_style(c, "200px", left=True))]
    for fid, lbl in zip(ordered_fsyms, col_labels):
        name = fsym_label_map[fid]["name"]
        is_tgt = fsym_label_map[fid].get("is_target")
        sub_cells.append(html.Th(
            [html.Div(lbl, style={"fontWeight": "700", "color": c["accent"] if is_tgt else c["text"],
                                  "fontSize": "0.72rem"}),
             html.Div(name, style={"fontWeight": "400", "color": c["muted"],
                                   "fontSize": "0.65rem", "overflow": "hidden",
                                   "textOverflow": "ellipsis", "whiteSpace": "nowrap",
                                   "maxWidth": "120px"})],
            style=_th_style(c, "130px")
        ))
    sub_cells.append(html.Th("Peer Avg", style=_th_style(c, "110px")))
    sub_cells.append(html.Th("vs Peer Avg", style=_th_style(c, "120px")))

    # Data rows
    tr_rows = []
    for i, row in enumerate(rows):
        tds = [html.Td(row["Metric"],
                       style={**_td_style(c, i), "textAlign": "left", "color": c["text"],
                               "paddingLeft": "0.8rem", "minWidth": "200px"})]
        for lbl in col_labels:
            val_str = row.get(lbl, "—")
            is_tgt_col = any(
                fsym_label_map[f]["label"] == lbl and fsym_label_map[f].get("is_target")
                for f in ordered_fsyms
            )
            tds.append(html.Td(val_str,
                               style={**_td_style(c, i),
                                      "color": c["accent"] if is_tgt_col else c["text"],
                                      "fontWeight": "600" if is_tgt_col else "400",
                                      "minWidth": "100px"}))
        avg_str = row.get("Peer Avg", "—")
        tds.append(html.Td(avg_str, style={**_td_style(c, i), "color": c["subtext"],
                                           "minWidth": "90px"}))
        vs_str = row.get("vs Peer Avg", "—")
        vs_color = _vs_color(vs_str, c)
        tds.append(html.Td(vs_str, style={**_td_style(c, i), "color": vs_color,
                                          "fontWeight": "700", "minWidth": "100px"}))
        tr_rows.append(html.Tr(tds))

    table = html.Table([
        html.Thead(html.Tr(sub_cells)),
        html.Tbody(tr_rows),
    ], style={"borderCollapse": "collapse", "width": "100%"})

    return html.Div([
        html.Div(title, style={
            "fontFamily": FONT, "fontSize": "0.65rem", "fontWeight": "700",
            "color": c["accent"], "letterSpacing": "0.06em", "textTransform": "uppercase",
            "marginBottom": "0.4rem", "padding": "0 0.2rem",
        }),
        html.Div(table, style={"overflowX": "auto"}),
    ], style={**PANEL, "padding": "0.8rem 1rem"})


def _build_recovery_inputs(ordered_fsyms, fsym_label_map, recovery_data, c):
    """Editable inputs for the Recovery section manual fields."""
    PANEL = {
        "backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
        "borderRadius": "10px",
    }
    INPUT_FIELDS = [
        ("last_normal_margin", "Last Normal EBIT Margin (%)"),
        ("mgmt_target",        "Mgmt Mid-Term EBIT Target (%)"),
        ("organic_growth",     "Organic Sales Growth NTM (%)"),
    ]
    rows = []
    for fid, lbl in zip(ordered_fsyms, [fsym_label_map[f]["label"] for f in ordered_fsyms]):
        name = fsym_label_map[fid]["name"]
        fields_div = []
        for rk_suffix, field_label in INPUT_FIELDS:
            key = f"{lbl}__{rk_suffix}"
            stored_val = recovery_data.get(key, "")
            fields_div.append(html.Div([
                html.Div(field_label, style={"color": c["muted"], "fontSize": "0.67rem",
                                             "fontFamily": FONT, "marginBottom": "0.15rem"}),
                dcc.Input(
                    id={"type": "peers-recovery-input", "index": key},
                    type="number", step=0.1,
                    value=stored_val if stored_val != "" else None,
                    placeholder="—",
                    style={
                        "width": "90px", "fontFamily": FONT, "fontSize": "0.78rem",
                        "backgroundColor": c["bg"], "border": f"1px solid {c['border']}",
                        "borderRadius": "6px", "color": c["text"],
                        "padding": "0.3rem 0.5rem", "outline": "none",
                    },
                    debounce=True,
                ),
            ], style={"marginRight": "1.2rem"}))
        rows.append(html.Div([
            html.Div([
                html.Span(lbl, style={"fontWeight": "700", "color": c["accent"],
                                      "fontSize": "0.8rem", "fontFamily": FONT}),
                html.Span(f"  {name}", style={"color": c["muted"], "fontSize": "0.72rem",
                                               "fontFamily": FONT, "marginLeft": "0.3rem"}),
            ], style={"marginBottom": "0.4rem"}),
            html.Div(fields_div, style={"display": "flex", "flexWrap": "wrap"}),
        ], style={"marginBottom": "0.8rem"}))

    if not rows:
        return html.Div()

    return html.Div([
        html.Div("Manual Inputs — Recovery", style={
            "fontFamily": FONT, "fontSize": "0.65rem", "fontWeight": "700",
            "color": c["accent"], "letterSpacing": "0.06em", "textTransform": "uppercase",
            "marginBottom": "0.6rem",
        }),
        html.Div("Enter manual data for the Recovery section. Values persist during the session.",
                 style={"color": c["muted"], "fontSize": "0.72rem", "fontFamily": FONT,
                        "marginBottom": "0.8rem"}),
        *rows,
    ], style={**PANEL, "padding": "0.8rem 1rem"})


def _th_style(c, width="120px", left=False):
    return {
        "backgroundColor": c["panel"], "color": c["text"],
        "fontWeight": "700", "fontFamily": FONT, "fontSize": "0.7rem",
        "borderBottom": f"2px solid {c['border']}",
        "padding": "6px 8px", "textAlign": "left" if left else "right",
        "whiteSpace": "nowrap", "minWidth": width,
    }


def _td_style(c, row_idx):
    bg = c["panel"] if row_idx % 2 == 0 else c["bg"]
    return {
        "backgroundColor": bg, "fontFamily": FONT, "fontSize": "0.72rem",
        "padding": "5px 8px", "borderBottom": f"1px solid {c['border']}",
        "textAlign": "right", "whiteSpace": "nowrap",
    }


def _vs_color(val_str, c):
    if val_str == "—" or not val_str:
        return c["muted"]
    if val_str.startswith("+"):
        return "#ff6b6b"  # trading above peer avg = expensive (red for valuation context)
    if val_str.startswith("-"):
        return "#4caf7d"  # trading below = discount (green)
    return c["text"]
