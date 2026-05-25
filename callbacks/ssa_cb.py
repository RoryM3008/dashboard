"""Callback — Single Stock Analysis (FactSet / Snowflake)."""

import pandas as pd
import numpy as np
import dash
from dash import Input, Output, State, html, dash_table, dcc, no_update, ALL
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from theme import get_theme, FONT, BBG_ESTIMATES
from snowflake_data import (
    download_ohlcv, _resolve_ids, fetch_company_profile,
    fetch_key_ratios, fetch_eps_consensus, fetch_recommendations,
    fetch_ratio_history,
    fetch_latest_price, fetch_sec_filings, fetch_news_headlines,
    fetch_transcripts_list, fetch_financial_statements, search_tickers,
    fetch_estimate_actuals, fetch_consensus_estimates, fetch_shares_outstanding,
)


def _offline_banner():
    return html.Div([
        html.Div("📡", style={"fontSize": "2.5rem", "marginBottom": "0.5rem"}),
        html.Div("Offline Mode", style={"fontWeight": "800", "fontSize": "1.1rem",
                                        "color": "#ff8c00", "marginBottom": "0.4rem"}),
        html.Div("This page requires a Snowflake / FactSet connection.",
                 style={"color": "#888", "fontSize": "0.82rem", "marginBottom": "0.3rem"}),
        html.Div("Toggle 🔌 SF → 📡 YF in the top bar to switch to offline mode, or reconnect to the office network.",
                 style={"color": "#666", "fontSize": "0.75rem"}),
    ], style={"textAlign": "center", "padding": "3rem 2rem",
              "fontFamily": "'Inter', sans-serif"})

BBG = BBG_ESTIMATES

ESTIMATE_MEASURES = {
    "EPS": {"label": "EPS", "kind": "number", "item": "EPS", "decimals": 2},
    "SALES": {"label": "Sales", "kind": "money", "item": "SALES", "decimals": 0},
    "CFPS": {"label": "CFPS", "kind": "number", "item": "CFPS", "decimals": 2},
    "DPS": {"label": "DPS", "kind": "number", "item": "DPS", "decimals": 2},
    "PE": {"label": "P/E", "kind": "multiple", "item": "EPS", "derived": "price_over_item", "decimals": 1},
    "PSALES": {"label": "P/S", "kind": "multiple", "item": "SALES", "derived": "marketcap_over_item", "decimals": 1},
    "PCF": {"label": "P/CF", "kind": "multiple", "item": "CFPS", "derived": "price_over_item", "decimals": 1},
    "GROSS_MARGIN": {"label": "Gross Margin", "kind": "percent", "statement": "gross_margin", "decimals": 1},
    "EBIT_MARGIN": {"label": "EBIT Margin", "kind": "percent", "statement": "ebit_margin", "decimals": 1},
}


def register_callbacks(app):

    # ── Ticker search-as-you-type ─────────────────────────────────────
    @app.callback(
        Output("ssa-ticker-suggestions", "children"),
        Input("ssa-ticker", "value"),
        prevent_initial_call=True,
    )
    def update_ticker_options(search):
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
                    id={"type": "ssa-ticker-suggestion", "index": r["ticker_region"]},
                    n_clicks=0,
                    style={
                        "backgroundColor": BBG["panel"],
                        "border": f"1px solid {BBG['border']}",
                        "color": BBG["text"],
                        "padding": "0.45rem 0.65rem",
                        "textAlign": "left",
                        "fontFamily": FONT,
                        "fontSize": "0.76rem",
                        "cursor": "pointer",
                    },
                )
            )
        return cards[:8]

    @app.callback(
        Output("ssa-ticker", "value", allow_duplicate=True),
        Output("ssa-ticker-suggestions", "children", allow_duplicate=True),
        Input({"type": "ssa-ticker-suggestion", "index": ALL}, "n_clicks"),
        State({"type": "ssa-ticker-suggestion", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def choose_ticker_suggestion(clicks, ids):
        if not clicks or not any(clicks):
            return no_update, no_update
        for n, item in zip(clicks, ids):
            if n:
                return item["index"], []
        return no_update, no_update

    # Auto-load: increment the load button when the SSA section becomes visible
    @app.callback(
        Output("ssa-load-btn", "n_clicks"),
        Input("section-ssa", "style"),
        State("ssa-load-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def auto_load_ssa(style, current_clicks):
        if style and style.get("display") != "none" and (current_clicks or 0) == 0:
            return 1
        return dash.no_update

    # Preset period buttons → set start/end date inputs
    @app.callback(
        Output("ssa-chart-start", "value", allow_duplicate=True),
        Output("ssa-chart-end", "value", allow_duplicate=True),
        [Input(f"ssa-preset-{p}", "n_clicks") for p in ["1d", "5d", "1m", "3m", "ytd", "1y", "5y", "max"]],
        prevent_initial_call=True,
    )
    def set_chart_dates(*clicks):
        import datetime as dt
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update
        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
        preset = btn_id.replace("ssa-preset-", "").upper()
        today = dt.date.today()
        end = today.strftime("%Y-%m-%d")
        mapping = {
            "1D": 1, "5D": 5, "1M": 30, "3M": 90, "YTD": None,
            "1Y": 365, "5Y": 1825, "MAX": 9999,
        }
        if preset == "YTD":
            start = dt.date(today.year, 1, 1).strftime("%Y-%m-%d")
        else:
            days = mapping.get(preset, 365)
            start = (today - dt.timedelta(days=days)).strftime("%Y-%m-%d")
        return start, end

    # Separate chart callback — reacts to date changes without reloading all data
    @app.callback(
        Output("ssa-price-chart", "figure"),
        Input("ssa-chart-start", "value"),
        Input("ssa-chart-end", "value"),
        State("ssa-ticker", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def update_price_chart(start_str, end_str, ticker_raw, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not ticker_raw or not ticker_raw.strip():
            return _empty_figure(c)
        ticker, ids = _resolve_ssa_ticker_input(ticker_raw)
        if isinstance(ids, Exception):
            return _empty_figure(c, "Ticker not found")
        if not ticker:
            return _empty_figure(c, "Ticker not found")
        ccy_sym = "$"
        if ids and ids.get("currency"):
            ccy_sym = "$" if ids["currency"] == "USD" else f"{ids['currency']} "
        try:
            ohlcv = download_ohlcv(ticker, start=start_str, end=end_str)
        except Exception:
            ohlcv = pd.DataFrame()
        if ohlcv.empty:
            return _empty_figure(c, "No price data")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ohlcv.index, y=ohlcv["Close"], mode="lines",
            line=dict(color="#1a6dcc", width=1.5),
            fill="tozeroy", fillcolor="rgba(58,130,220,0.12)",
            name="Close",
            hovertemplate=f"{ccy_sym}%{{y:.2f}}<extra></extra>",
        ))
        bbg_grid = "rgba(60,65,75,0.4)"
        bbg_text = "#8a8e96"
        bbg_font = dict(family="Consolas, 'Courier New', monospace", size=10, color=bbg_text)
        ymin, ymax = ohlcv["Close"].min(), ohlcv["Close"].max()
        pad = (ymax - ymin) * 0.05
        fig.update_layout(
            paper_bgcolor="#000000", plot_bgcolor="#0a0a0f", font=bbg_font,
            margin=dict(l=5, r=55, t=8, b=25), showlegend=False,
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#1a1d24", font_size=10,
                            font_family="Consolas, monospace", font_color="#d0d4db",
                            bordercolor="#333"),
            xaxis=dict(showgrid=True, gridcolor=bbg_grid, griddash="dot",
                       gridwidth=0.5, tickfont=bbg_font, color=bbg_text, showline=False),
            yaxis=dict(showgrid=True, gridcolor=bbg_grid, griddash="dot",
                       gridwidth=0.5, side="right", tickprefix=ccy_sym,
                       tickfont=bbg_font, range=[ymin - pad, ymax + pad],
                       zeroline=False, showline=False),
        )
        return fig

    @app.callback(
        Output("ssa-company-header", "children"),
        Output("ssa-metrics-cards", "children"),
        Output("ssa-chart-start", "value"),
        Output("ssa-chart-end", "value"),
        Output("ssa-eps-chart", "figure"),
        Output("ssa-rec-chart", "figure"),
        Output("ssa-est-meta", "data"),
        Output("ssa-est-security-name", "children"),
        Output("ssa-est-currency", "options"),
        Output("ssa-est-currency", "value"),
        Output("ssa-status", "children"),
        Input("ssa-load-btn", "n_clicks"),
        State("ssa-ticker", "value"),
        State("theme-store", "data"),
        State("datasource", "data"),
        prevent_initial_call=True,
    )
    def load_ssa(n_clicks, ticker_raw, theme_mode, datasource):
        import datetime as dt
        if datasource == "yf":
            return (html.Div(_offline_banner(), style={"gridColumn": "1/-1"}),) + (no_update,) * 10
        if not ticker_raw or not ticker_raw.strip():
            return (no_update,) * 11

        c = get_theme(theme_mode or "dark")
        ticker, ids = _resolve_ssa_ticker_input(ticker_raw)
        empty_fig = _empty_figure(c)

        if isinstance(ids, Exception):
            e = ids
            return html.Div(), html.Div(), "", "", empty_fig, empty_fig, {}, "—", [{"label": "USD", "value": "USD"}], "USD", f"❌ {e}"

        if ids is None or not ticker:
            failed = str(ticker_raw).strip().upper()
            return html.Div(), html.Div(), "", "", empty_fig, empty_fig, {}, "—", [{"label": "USD", "value": "USD"}], "USD", f"❌ Ticker '{failed}' not found in FactSet."

        fsym_id = ids["fsym_id"]
        security_id = ids["security_id"]
        entity_id = ids["entity_id"]
        name = ids["name"] or ticker
        currency = ids["currency"] or "USD"
        ccy_sym = "$" if currency == "USD" else f"{currency} "

        # ── Company profile ──────────────────────────────────────────────
        profile = {}
        if entity_id:
            try:
                profile = fetch_company_profile(entity_id)
            except Exception:
                pass

        header = html.Div([
            html.Div([
                html.Span(name, style={"fontFamily": FONT, "fontWeight": "800",
                                       "fontSize": "1.3rem", "color": c["text"]}),
                html.Span(f"  {ticker}", style={"fontFamily": FONT, "fontWeight": "400",
                                                  "fontSize": "0.9rem", "color": c["muted"],
                                                  "marginLeft": "0.5rem"}),
                html.Span(f"  •  {profile.get('sector', '')}  •  {profile.get('industry', '')}",
                          style={"fontFamily": FONT, "fontSize": "0.78rem",
                                 "color": c["muted"], "marginLeft": "0.5rem"}),
            ]),
            html.Div(profile.get("description", ""),
                     style={"fontFamily": FONT, "fontSize": "0.75rem",
                            "color": c["subtext"], "marginTop": "0.3rem"}),
        ], style={"backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
                  "borderRadius": "10px", "padding": "1rem 1.5rem"})

        # ── Key ratios ───────────────────────────────────────────────────
        ratios = {}
        try:
            ratios = fetch_key_ratios(fsym_id)
        except Exception:
            pass

        def _card(label, value, fmt=None):
            if value is None or (isinstance(value, (int, float)) and (np.isnan(value) if isinstance(value, float) else False)) or value == 0:
                display = "—"
            elif fmt == "money":
                v = float(value)
                # FactSet FF values are already in millions
                if abs(v) < 1000:
                    display = f"{ccy_sym}{v:,.0f}M"
                else:
                    display = f"{ccy_sym}{v/1000:,.1f}B"
            elif fmt == "pct":
                display = f"{float(value):.1f}%"
            elif fmt == "ratio":
                display = f"{float(value):.1f}x"
            elif fmt == "eps":
                display = f"{ccy_sym}{float(value):.2f}"
            else:
                display = str(value)

            return html.Div([
                html.Div(label, style={"fontFamily": FONT, "fontSize": "0.6rem",
                                       "fontWeight": "700", "letterSpacing": "0.08em",
                                       "textTransform": "uppercase", "color": c["muted"],
                                       "marginBottom": "0.15rem"}),
                html.Div(display, style={"fontFamily": FONT, "fontSize": "1.1rem",
                                         "fontWeight": "700", "color": c["text"]}),
            ], style={"backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
                      "borderRadius": "8px", "padding": "0.7rem 1rem", "flex": "1",
                      "minWidth": "130px"})

        metrics = html.Div([
            _card("Market Cap", ratios.get("mkt_cap"), "money"),
            _card("P/E (LTM)", ratios.get("pe"), "ratio"),
            _card("EPS (Dil)", ratios.get("eps_diluted"), "eps"),
            _card("Gross Margin", ratios.get("gross_margin"), "pct"),
            _card("Oper Margin", ratios.get("oper_margin"), "pct"),
            _card("Net Margin", ratios.get("net_margin"), "pct"),
            _card("EBITDA", ratios.get("ebitda"), "money"),
            _card("Free Cash Flow", ratios.get("free_cf"), "money"),
        ], style={"display": "flex", "gap": "0.5rem", "flexWrap": "wrap"})

        # ── Default chart dates (1Y) ─────────────────────────────────
        today = dt.date.today()
        chart_end = today.strftime("%Y-%m-%d")
        chart_start = (today - dt.timedelta(days=365)).strftime("%Y-%m-%d")

        # ── EPS revisions chart ──────────────────────────────────────────
        try:
            eps_df = fetch_eps_consensus(fsym_id)
        except Exception:
            eps_df = pd.DataFrame()

        if eps_df.empty:
            eps_fig = _empty_figure(c, "No EPS consensus data")
        else:
            eps_fig = go.Figure()
            colours = ["#58a6ff", "#3fb950", "#ff8c00", "#f85149", "#bc8cff"]
            fy_ends = sorted(eps_df["FE_FP_END"].unique())
            for i, fy in enumerate(fy_ends[-5:]):
                sub = eps_df[eps_df["FE_FP_END"] == fy].sort_values("CONS_END_DATE")
                label = f"FY{fy.strftime('%Y')}" if hasattr(fy, "strftime") else str(fy)
                eps_fig.add_trace(go.Scatter(
                    x=sub["CONS_END_DATE"], y=sub["FE_MEAN"],
                    mode="lines+markers", name=label,
                    line=dict(color=colours[i % len(colours)], width=2),
                    marker=dict(size=4),
                ))
            eps_fig.update_layout(
                **_base_layout(c),
                yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["subtext"],
                           tickprefix=ccy_sym, side="right", autorange=True),
                legend=dict(orientation="h", y=1.08, x=0),
            )

        # ── Recommendations chart ────────────────────────────────────────
        try:
            rec_df = fetch_recommendations(fsym_id)
        except Exception:
            rec_df = pd.DataFrame()

        if rec_df.empty:
            rec_fig = _empty_figure(c, "No recommendation data")
        else:
            # Latest recommendation breakdown as stacked bar
            latest = rec_df.iloc[0]
            cats = ["Buy", "Overweight", "Hold", "Underweight", "Sell"]
            vals = [latest.get("FE_BUY", 0) or 0, latest.get("FE_OVER", 0) or 0,
                    latest.get("FE_HOLD", 0) or 0, latest.get("FE_UNDER", 0) or 0,
                    latest.get("FE_SELL", 0) or 0]
            colours_rec = ["#3fb950", "#58a6ff", "#888", "#ff8c00", "#f85149"]

            rec_fig = go.Figure()
            for cat, val, col in zip(cats, vals, colours_rec):
                rec_fig.add_trace(go.Bar(
                    x=[val], y=["Consensus"], name=cat, orientation="h",
                    marker_color=col,
                    text=[f"{cat}: {int(val)}"], textposition="inside",
                    textfont=dict(size=11, family=FONT),
                ))
            total = sum(vals)
            base = _base_layout(c)
            base["xaxis"] = dict(showgrid=False, showticklabels=False)
            base["margin"] = dict(l=10, r=10, t=10, b=10)
            rec_fig.update_layout(
                **base,
                barmode="stack",
                showlegend=False,
                yaxis=dict(showticklabels=False),
                height=120,
                annotations=[dict(
                    text=f"Total: {int(total)} analysts",
                    xref="paper", yref="paper", x=0.5, y=-0.3,
                    showarrow=False, font=dict(size=12, color=c["subtext"], family=FONT),
                )],
            )

            # Add historical trend below
            if len(rec_df) > 1:
                hist_rec = rec_df.sort_values("CONS_END_DATE")
                for cat, col_name, col_color in [("Buy", "FE_BUY", "#3fb950"),
                                                   ("Hold", "FE_HOLD", "#888"),
                                                   ("Sell", "FE_SELL", "#f85149")]:
                    rec_fig.add_trace(go.Scatter(
                        x=hist_rec["CONS_END_DATE"],
                        y=hist_rec[col_name].fillna(0),
                        mode="lines", name=cat, visible=False,
                        line=dict(color=col_color, width=1.5),
                    ))

        currency_options = [{"label": currency, "value": currency}]
        est_meta = {
            "ticker": ticker,
            "name": name,
            "currency": currency,
            "fsym_id": fsym_id,
            "security_id": security_id,
        }
        status = f"✅ {name} ({ticker}) • Source: FactSet/Snowflake"
        return header, metrics, chart_start, chart_end, eps_fig, rec_fig, est_meta, name, currency_options, currency, status

    @app.callback(
        Output("ssa-est-growth-mode", "data"),
        Output("ssa-est-yoy-btn", "style"),
        Output("ssa-est-pop-btn", "style"),
        Input("ssa-est-yoy-btn", "n_clicks"),
        Input("ssa-est-pop-btn", "n_clicks"),
        State("ssa-est-growth-mode", "data"),
        prevent_initial_call=True,
    )
    def set_est_growth_mode(yoy_clicks, pop_clicks, current_mode):
        ctx = dash.callback_context
        mode = current_mode or "yoy"
        if ctx.triggered:
            btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
            mode = "pop" if btn_id == "ssa-est-pop-btn" else "yoy"
        return mode, _bbg_tab_style(mode == "yoy"), _bbg_tab_style(mode == "pop")

    @app.callback(
        Output("ssa-est-chart-mode", "data"),
        Output("ssa-est-values-chart-btn", "style"),
        Output("ssa-est-growth-chart-btn", "style"),
        Input("ssa-est-values-chart-btn", "n_clicks"),
        Input("ssa-est-growth-chart-btn", "n_clicks"),
        State("ssa-est-chart-mode", "data"),
        prevent_initial_call=True,
    )
    def set_est_chart_mode(values_clicks, growth_clicks, current_mode):
        ctx = dash.callback_context
        mode = current_mode or "values"
        if ctx.triggered:
            btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
            mode = "growth" if btn_id == "ssa-est-growth-chart-btn" else "values"
        return mode, _bbg_tab_style(mode == "values"), _bbg_tab_style(mode == "growth")

    @app.callback(
        Output("ssa-est-values-table", "children"),
        Output("ssa-est-growth-table", "children"),
        Output("ssa-est-chart", "figure"),
        Output("ssa-est-multiples-table", "children"),
        Input("ssa-est-meta", "data"),
        Input("ssa-est-periodicity", "value"),
        Input("ssa-est-source", "value"),
        Input("ssa-est-currency", "value"),
        Input("ssa-est-measure", "value"),
        Input("ssa-est-growth-mode", "data"),
        Input("ssa-est-chart-mode", "data"),
        Input("theme-store", "data"),
        prevent_initial_call=True,
    )
    def render_estimates_screen(meta, periodicity, source, currency, measure, growth_mode, chart_mode, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not meta or not meta.get("fsym_id"):
            empty = html.Div("Load a stock to view estimates.", style={
                "color": BBG_ESTIMATES["muted"], "fontFamily": FONT, "fontSize": "0.75rem"
            })
            return empty, empty, _empty_figure(c, "No estimates loaded"), empty

        dataset = _build_estimate_dataset(
            meta.get("fsym_id"),
            meta.get("security_id"),
            measure or "EPS",
            periodicity or "quarterly",
            currency or meta.get("currency", "USD"),
        )

        values_table = _bbg_matrix_table(dataset.get("values_table"), label_col="Period")
        growth_table = _bbg_matrix_table(
            _compute_growth_table(dataset.get("values_table"), growth_mode or "yoy"),
            label_col="Period",
            is_growth=True,
        )
        chart_fig = _build_estimate_chart(dataset, chart_mode or "values", growth_mode or "yoy", measure or "EPS")
        multiples_table = _bbg_matrix_table(dataset.get("multiples_table"), label_col="Multiple")
        return values_table, growth_table, chart_fig, multiples_table

    # ── On-demand News, Filings & Transcripts callback ──────────────────
    @app.callback(
        Output("ssa-news-feed", "children"),
        Output("ssa-sec-filings", "children"),
        Output("ssa-transcripts", "children"),
        Output("ssa-news-status", "children"),
        Input("ssa-load-news-btn", "n_clicks"),
        State("ssa-ticker", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def load_news_filings(n_clicks, ticker_raw, theme_mode):
        if not ticker_raw or not ticker_raw.strip():
            return no_update, no_update, no_update, "Enter a ticker first."

        c = get_theme(theme_mode or "dark")
        ticker, ids = _resolve_ssa_ticker_input(ticker_raw)
        if isinstance(ids, Exception):
            return html.Div(), html.Div(), html.Div(), f"❌ {ids}"
        if ids is None or not ticker:
            return html.Div(), html.Div(), html.Div(), f"❌ Ticker not found."

        # Resolve company name
        name = ids["name"] or ticker

        # ── News headlines ────────────────────────────────────────────
        try:
            news = fetch_news_headlines(name, limit=25)
        except Exception:
            news = []

        if not news:
            news_feed = html.Div("No recent news found.",
                                 style={"color": c["muted"], "fontSize": "0.78rem", "fontFamily": FONT})
        else:
            news_items = []
            for n_item in news:
                ts = n_item["publish_time"]
                ts_str = ts.strftime("%d-%b-%Y %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
                news_items.append(html.Div([
                    html.Span(ts_str, style={"color": c["muted"], "fontSize": "0.62rem",
                                              "fontFamily": "Consolas, monospace",
                                              "marginRight": "0.5rem", "whiteSpace": "nowrap"}),
                    html.Span(n_item["headline"], style={"color": c["text"], "fontSize": "0.75rem",
                                                          "fontFamily": FONT}),
                ], style={"borderBottom": f"1px solid {c['border']}",
                          "padding": "0.4rem 0", "display": "flex",
                          "alignItems": "flex-start"}))
            news_feed = html.Div(news_items)

        # ── SEC filings ──────────────────────────────────────────────────
        try:
            filings = fetch_sec_filings(name, limit=20)
        except Exception:
            filings = []

        if not filings:
            sec_widget = html.Div("No SEC filings found.",
                                  style={"color": c["muted"], "fontSize": "0.78rem", "fontFamily": FONT})
        else:
            filing_rows = []
            for f in filings:
                d = f["filed_date"]
                d_str = d.strftime("%d-%b-%Y") if hasattr(d, "strftime") else str(d)[:10]
                form = f["form_type"] or ""
                form_color = "#3fb950" if form in ("10-K", "10-K/A") else \
                             "#58a6ff" if form in ("10-Q", "10-Q/A") else \
                             c["muted"]
                row_children = [
                    html.Span(d_str, style={"color": c["muted"], "fontSize": "0.62rem",
                                             "fontFamily": "Consolas, monospace",
                                             "marginRight": "0.5rem", "whiteSpace": "nowrap"}),
                    html.Span(form, style={"color": form_color, "fontSize": "0.75rem",
                                            "fontWeight": "700", "fontFamily": FONT,
                                            "marginRight": "0.4rem", "minWidth": "50px"}),
                ]
                if f.get("url"):
                    row_children.append(html.A("EDGAR ↗", href=f["url"], target="_blank",
                                              style={"color": c["accent"], "fontSize": "0.65rem",
                                                     "fontFamily": FONT, "textDecoration": "none"}))
                filing_rows.append(html.Div(row_children,
                                            style={"borderBottom": f"1px solid {c['border']}",
                                                   "padding": "0.35rem 0", "display": "flex",
                                                   "alignItems": "center"}))
            sec_widget = html.Div(filing_rows)

        # ── Transcripts ──────────────────────────────────────────────────
        try:
            transcripts = fetch_transcripts_list(name, limit=15)
        except Exception:
            transcripts = []

        if not transcripts:
            trans_widget = html.Div("No transcripts found.",
                                    style={"color": c["muted"], "fontSize": "0.78rem", "fontFamily": FONT})
        else:
            trans_rows = []
            for t in transcripts:
                d = t["date"]
                d_str = d.strftime("%d-%b-%Y") if hasattr(d, "strftime") else str(d)[:10]
                trans_rows.append(html.Div([
                    html.Span(d_str, style={"color": c["muted"], "fontSize": "0.62rem",
                                             "fontFamily": "Consolas, monospace",
                                             "marginRight": "0.5rem"}),
                    html.Span("Earnings Call", style={"color": c["text"], "fontSize": "0.75rem",
                                                       "fontFamily": FONT}),
                ], style={"borderBottom": f"1px solid {c['border']}",
                          "padding": "0.35rem 0", "display": "flex",
                          "alignItems": "center"}))
            trans_widget = html.Div(trans_rows)

        n_news = len(news) if news else 0
        n_filings = len(filings) if filings else 0
        n_trans = len(transcripts) if transcripts else 0
        status_txt = f"✅ Loaded {n_news} headlines, {n_filings} filings, {n_trans} transcripts."
        return news_feed, sec_widget, trans_widget, status_txt

    # ── Annual / Quarterly toggle ─────────────────────────────────────
    @app.callback(
        Output("ssa-fin-freq", "data"),
        Output("ssa-fin-annual-btn", "style"),
        Output("ssa-fin-quarterly-btn", "style"),
        Input("ssa-fin-annual-btn", "n_clicks"),
        Input("ssa-fin-quarterly-btn", "n_clicks"),
        State("theme-store", "data"),
    )
    def toggle_fin_freq(n_ann, n_qtr, theme_mode):
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        trig = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
        freq = "quarterly" if trig == "ssa-fin-quarterly-btn" else "annual"

        active = {"backgroundColor": c["accent"], "color": "#000", "border": "none",
                  "borderRadius": "4px 0 0 4px" if freq == "annual" else "0 4px 4px 0",
                  "padding": "0.35rem 0.8rem", "fontFamily": FONT, "fontWeight": "700",
                  "fontSize": "0.7rem", "cursor": "pointer"}
        inactive = {"backgroundColor": c["panel"], "color": c["muted"],
                    "border": f"1px solid {c['border']}",
                    "borderRadius": "0 4px 4px 0" if freq == "annual" else "4px 0 0 4px",
                    "padding": "0.35rem 0.8rem", "fontFamily": FONT, "fontWeight": "700",
                    "fontSize": "0.7rem", "cursor": "pointer"}
        ann_style = active if freq == "annual" else inactive
        qtr_style = active if freq == "quarterly" else inactive
        # Fix border-radius
        ann_style["borderRadius"] = "4px 0 0 4px"
        qtr_style["borderRadius"] = "0 4px 4px 0"
        return freq, ann_style, qtr_style

    # ── Load Financial Statements ─────────────────────────────────────
    @app.callback(
        Output("ssa-income-statement", "children"),
        Output("ssa-balance-sheet", "children"),
        Output("ssa-cash-flow", "children"),
        Output("ssa-financials-status", "children"),
        Input("ssa-load-financials-btn", "n_clicks"),
        State("ssa-ticker", "value"),
        State("ssa-fin-freq", "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def load_financials(n_clicks, ticker_raw, freq, theme_mode):
        if not n_clicks or not ticker_raw:
            return no_update, no_update, no_update, no_update
        c = get_theme(theme_mode or "dark")
        ticker, ids = _resolve_ssa_ticker_input(ticker_raw)
        if isinstance(ids, Exception):
            msg = f"⚠️ Error: {ids}"
            return html.Div(msg), html.Div(msg), html.Div(msg), msg
        if not ids or not ids.get("security_id"):
            msg = f"⚠️ Could not resolve {ticker}."
            return html.Div(msg), html.Div(msg), html.Div(msg), msg

        try:
            data = fetch_financial_statements(ids["security_id"], freq=freq or "annual", years=5)
        except Exception as e:
            msg = f"⚠️ Error: {e}"
            return html.Div(msg), html.Div(msg), html.Div(msg), msg

        ccy = data.get("currency", "")
        dates = data.get("dates", [])
        if not dates:
            msg = "No financial statement data available."
            empty = html.Div(msg, style={"color": c["muted"], "fontSize": "0.75rem", "fontFamily": FONT})
            return empty, empty, empty, msg

        def _build_table(items):
            if not items:
                return html.Div("No data.", style={"color": c["muted"], "fontSize": "0.75rem"})
            # Build a DataFrame: rows = line items, columns = dates
            df_data = []
            for item in items:
                row = {"Item": item["label"]}
                for dt in dates:
                    val = item.get(dt)
                    if val is not None:
                        try:
                            v = float(val)
                            if abs(v) >= 1000:
                                row[dt] = f"{v:,.0f}"
                            else:
                                row[dt] = f"{v:,.2f}"
                        except (ValueError, TypeError):
                            row[dt] = str(val)
                    else:
                        row[dt] = "–"
                df_data.append(row)
            df = pd.DataFrame(df_data)
            return _themed_table(df, c)

        is_table = _build_table(data.get("income_statement", []))
        bs_table = _build_table(data.get("balance_sheet", []))
        cf_table = _build_table(data.get("cash_flow", []))

        label = "Annual" if freq == "annual" else "Quarterly"
        status = f"✅ {label} financials loaded ({ccy}, values in millions)."
        return is_table, bs_table, cf_table, status


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_ssa_ticker_input(raw_value):
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
        (
            r for r in results
            if query in {str(r.get("ticker", "")).upper(), str(r.get("ticker_region", "")).upper(), str(r.get("name", "")).upper()}
        ),
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

def _bbg_tab_style(active):
    return {
        "backgroundColor": BBG["blue"] if active else BBG["tab_off"],
        "color": "#ffffff" if active else BBG["muted"],
        "border": f"1px solid {BBG['border']}",
        "borderRadius": "0",
        "padding": "0.22rem 0.55rem",
        "fontSize": "0.68rem",
        "fontFamily": FONT,
        "cursor": "pointer",
    }


def _build_estimate_dataset(fsym_id, security_id, measure_key, periodicity, currency):
    cfg = ESTIMATE_MEASURES.get(measure_key, ESTIMATE_MEASURES["EPS"])
    try:
        latest_price, _ = fetch_latest_price(fsym_id)
    except Exception:
        latest_price = None
    try:
        shares_out = fetch_shares_outstanding(fsym_id)
    except Exception:
        shares_out = None

    quarterly_df = _get_measure_series(fsym_id, security_id, measure_key, "quarterly", latest_price, shares_out)
    annual_df = _get_measure_series(fsym_id, security_id, measure_key, "annual", latest_price, shares_out)
    numeric_table, values_table = _build_values_matrices(quarterly_df, annual_df, cfg, periodicity, currency)
    multiples_table = _build_multiples_table(fsym_id, security_id, latest_price, shares_out, currency)
    return {
        "cfg": cfg,
        "quarterly": quarterly_df,
        "annual": annual_df,
        "values_numeric": numeric_table,
        "values_table": values_table,
        "multiples_table": multiples_table,
    }


def _get_measure_series(fsym_id, security_id, measure_key, periodicity, latest_price=None, shares_out=None):
    cfg = ESTIMATE_MEASURES.get(measure_key, ESTIMATE_MEASURES["EPS"])
    if cfg.get("statement"):
        return _statement_measure_series(security_id, periodicity, cfg["statement"])

    item = cfg.get("item")
    actual_limit = 28 if periodicity == "quarterly" else 8
    est_limit = 12 if periodicity == "quarterly" else 6
    try:
        actual_df = fetch_estimate_actuals(fsym_id, item=item, periodicity=periodicity, limit=actual_limit)
    except Exception:
        actual_df = pd.DataFrame()
    try:
        est_df = fetch_consensus_estimates(fsym_id, item=item, periodicity=periodicity, limit=est_limit)
    except Exception:
        est_df = pd.DataFrame()

    actual_std = _standardize_measure_df(actual_df, "actual", cfg, latest_price, shares_out)
    est_std = _standardize_measure_df(est_df, "estimate", cfg, latest_price, shares_out)
    frames = [df for df in [actual_std, est_std] if not df.empty]
    if not frames:
        return pd.DataFrame(columns=["period_end", "value", "source", "fiscal_year", "calendar_year", "row_label"])

    series = pd.concat(frames, ignore_index=True)
    series["period_end"] = pd.to_datetime(series["period_end"])
    series["priority"] = series["source"].map({"actual": 0, "estimate": 1}).fillna(9)
    series = series.sort_values(["period_end", "priority"]).drop_duplicates("period_end", keep="first")
    series = series.drop(columns=["priority"]).sort_values("period_end")
    if periodicity == "quarterly":
        series = _annotate_quarterly_series(series)
    else:
        series = _annotate_annual_series(series)
    return series


def _statement_measure_series(security_id, periodicity, statement_key):
    freq = "quarterly" if periodicity == "quarterly" else "annual"
    years = 6 if freq == "annual" else 6
    try:
        stmt = fetch_financial_statements(security_id, freq=freq, years=years)
    except Exception:
        stmt = {}
    dates = [pd.to_datetime(d) for d in stmt.get("dates", [])]
    rows = stmt.get("income_statement", [])
    if not dates or not rows:
        return pd.DataFrame(columns=["period_end", "value", "source", "fiscal_year", "calendar_year", "row_label"])

    row_map = {r.get("label"): r for r in rows}
    revenue = row_map.get("Revenue", {})
    gross_profit = row_map.get("Gross Profit", {})
    operating_income = row_map.get("Operating Income", {})
    values = []
    for dt in dates:
        key = str(dt.date())
        rev = revenue.get(key)
        if statement_key == "gross_margin":
            numerator = gross_profit.get(key)
            value = (float(numerator) / float(rev) * 100) if rev not in [None, 0] and numerator is not None else np.nan
        else:
            numerator = operating_income.get(key)
            value = (float(numerator) / float(rev) * 100) if rev not in [None, 0] and numerator is not None else np.nan
        values.append({"period_end": dt, "value": value, "source": "actual"})
    df = pd.DataFrame(values).sort_values("period_end")
    return _annotate_quarterly_series(df) if periodicity == "quarterly" else _annotate_annual_series(df)


def _standardize_measure_df(df, source, cfg, latest_price=None, shares_out=None):
    if df is None or df.empty:
        return pd.DataFrame(columns=["period_end", "value", "source"])
    work = df.copy()
    period_col = "FE_FP_END"
    value_col = "ACTUAL_VALUE" if "ACTUAL_VALUE" in work.columns else "FE_MEAN"
    work = work[[period_col, value_col]].rename(columns={period_col: "period_end", value_col: "raw_value"})
    work["period_end"] = pd.to_datetime(work["period_end"])
    work["value"] = work["raw_value"].apply(lambda v: _transform_measure_value(v, cfg, latest_price, shares_out))
    work["source"] = source
    return work[["period_end", "value", "source"]].dropna(subset=["period_end"])


def _transform_measure_value(value, cfg, latest_price=None, shares_out=None):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    val = float(value)
    derived = cfg.get("derived")
    if derived == "price_over_item":
        return (float(latest_price) / val) if latest_price and val > 0 else np.nan
    if derived == "marketcap_over_item":
        market_cap_m = (float(latest_price) * float(shares_out) / 1_000_000) if latest_price and shares_out else np.nan
        return (market_cap_m / val) if pd.notna(market_cap_m) and val > 0 else np.nan
    return val


def _annotate_quarterly_series(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["period_end", "value", "source", "fiscal_year", "calendar_year", "quarter_num", "row_label"])
    work = df.copy().sort_values("period_end")
    work["fiscal_year"] = work["period_end"].dt.year.astype(int)
    work["calendar_year"] = work["period_end"].dt.year.astype(int)
    work["quarter_num"] = work.groupby("fiscal_year").cumcount() + 1
    work["row_label"] = "Q" + work["quarter_num"].astype(str) + " " + work["period_end"].dt.strftime("%b")
    work["display_label"] = work["row_label"] + " " + work["fiscal_year"].astype(str)
    return work


def _annotate_annual_series(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["period_end", "value", "source", "fiscal_year", "calendar_year", "row_label"])
    work = df.copy().sort_values("period_end")
    work["fiscal_year"] = work["period_end"].dt.year.astype(int)
    work["calendar_year"] = work["period_end"].dt.year.astype(int)
    work["row_label"] = "Year"
    work["display_label"] = work["fiscal_year"].astype(str)
    return work


def _build_values_matrices(quarterly_df, annual_df, cfg, periodicity, currency):
    fiscal_years = sorted(set(annual_df.get("fiscal_year", pd.Series(dtype=int)).dropna().astype(int).tolist()) |
                          set(quarterly_df.get("fiscal_year", pd.Series(dtype=int)).dropna().astype(int).tolist()))
    if not fiscal_years:
        return pd.DataFrame(columns=["Period"]), pd.DataFrame(columns=["Period"])
    years = fiscal_years[-6:]

    quarter_rows = []
    if quarterly_df is not None and not quarterly_df.empty:
        quarter_rows = (quarterly_df[["quarter_num", "row_label"]]
                        .drop_duplicates()
                        .sort_values("quarter_num")["row_label"].tolist())

    rows_order = ["Year", "Cal Yr"] if periodicity == "annual" else quarter_rows + ["", "Year", "Cal Yr"]
    numeric_rows = []
    for row_label in rows_order:
        record = {"Period": row_label}
        for year in years:
            if row_label == "":
                record[str(year)] = np.nan
            elif row_label == "Year":
                record[str(year)] = _lookup_annual_value(annual_df, year)
            elif row_label == "Cal Yr":
                record[str(year)] = _lookup_calendar_value(quarterly_df, annual_df, year, cfg)
            else:
                record[str(year)] = _lookup_quarter_value(quarterly_df, row_label, year)
        numeric_rows.append(record)

    numeric_df = pd.DataFrame(numeric_rows)
    formatted_df = numeric_df.copy()
    year_cols = [col for col in formatted_df.columns if col != "Period"]
    for col in year_cols:
        formatted_df[col] = formatted_df[col].apply(lambda v: _format_measure(v, cfg, currency))
    formatted_df.loc[formatted_df["Period"] == "", year_cols] = ""
    return numeric_df, formatted_df


def _lookup_quarter_value(quarterly_df, row_label, year):
    if quarterly_df is None or quarterly_df.empty:
        return np.nan
    sub = quarterly_df[(quarterly_df["row_label"] == row_label) & (quarterly_df["fiscal_year"] == year)]
    if sub.empty:
        return np.nan
    return float(sub.iloc[-1]["value"]) if pd.notna(sub.iloc[-1]["value"]) else np.nan


def _lookup_annual_value(annual_df, year):
    if annual_df is None or annual_df.empty:
        return np.nan
    sub = annual_df[annual_df["fiscal_year"] == year]
    if sub.empty:
        return np.nan
    return float(sub.iloc[-1]["value"]) if pd.notna(sub.iloc[-1]["value"]) else np.nan


def _lookup_calendar_value(quarterly_df, annual_df, year, cfg):
    if quarterly_df is None or quarterly_df.empty:
        return _lookup_annual_value(annual_df, year)
    sub = quarterly_df[quarterly_df["calendar_year"] == year]
    if sub.empty:
        return _lookup_annual_value(annual_df, year)
    vals = pd.to_numeric(sub["value"], errors="coerce").dropna()
    if vals.empty:
        return np.nan
    if cfg.get("kind") in {"money", "number"}:
        return float(vals.sum())
    return float(vals.mean())


def _compute_growth_table(numeric_df, mode):
    if numeric_df is None or numeric_df.empty:
        return pd.DataFrame(columns=["Period"])
    years = [col for col in numeric_df.columns if col != "Period"]
    rows = numeric_df["Period"].tolist()
    lookup = {
        (row["Period"], col): row[col]
        for _, row in numeric_df.iterrows()
        for col in years
    }
    quarter_rows = [r for r in rows if isinstance(r, str) and r.startswith("Q")]
    growth_rows = []
    for label in rows:
        rec = {"Period": label}
        for idx, year in enumerate(years):
            if label == "":
                rec[year] = ""
                continue
            val = pd.to_numeric(lookup.get((label, year)), errors="coerce")
            base = np.nan
            if label in {"Year", "Cal Yr"} or mode == "yoy":
                if idx > 0:
                    base = pd.to_numeric(lookup.get((label, years[idx - 1])), errors="coerce")
            elif label in quarter_rows:
                pos = quarter_rows.index(label)
                prev_label = quarter_rows[pos - 1] if pos > 0 else quarter_rows[-1]
                prev_year = year if pos > 0 else years[idx - 1] if idx > 0 else None
                if prev_year is not None:
                    base = pd.to_numeric(lookup.get((prev_label, prev_year)), errors="coerce")
            growth = ((val / base) - 1) * 100 if pd.notna(val) and pd.notna(base) and base not in [0, 0.0] else np.nan
            rec[year] = "—" if pd.isna(growth) else f"{growth:.1f}%"
        growth_rows.append(rec)
    return pd.DataFrame(growth_rows)


def _build_estimate_chart(dataset, chart_mode, growth_mode, measure_key):
    annual_df = dataset.get("annual", pd.DataFrame()).copy()
    quarterly_df = dataset.get("quarterly", pd.DataFrame()).copy()
    cfg = dataset.get("cfg", ESTIMATE_MEASURES["EPS"])

    if chart_mode == "growth":
        annual_df = _growth_series(annual_df, growth_mode, annual=True)
        quarterly_df = _growth_series(quarterly_df, growth_mode, annual=False)
        y_suffix = "%"
        hover_fmt = ".1f"
    else:
        y_suffix = ""
        hover_fmt = ".2f" if cfg.get("kind") in {"number", "multiple"} else ".1f"

    if annual_df.empty and quarterly_df.empty:
        return _empty_figure(get_theme("dark"), "No estimate data")

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16, row_heights=[0.45, 0.55])
    if not annual_df.empty:
        fig.add_trace(go.Scatter(
            x=annual_df["fiscal_year"].astype(str),
            y=annual_df["value"],
            mode="lines+markers",
            line=dict(color=BBG["orange"], width=2),
            marker=dict(size=6, color="#d9d9d9", line=dict(color=BBG["orange"], width=1)),
            hovertemplate=f"%{{x}}<br>%{{y:{hover_fmt}}}{y_suffix}<extra></extra>",
            showlegend=False,
        ), row=1, col=1)

    if not quarterly_df.empty:
        for source, color in [("actual", BBG["orange"]), ("estimate", "#7d7d7d")]:
            sub = quarterly_df[quarterly_df["source"] == source]
            if sub.empty:
                continue
            fig.add_trace(go.Bar(
                x=sub["display_label"],
                y=sub["value"],
                marker_color=color,
                hovertemplate=f"%{{x}}<br>%{{y:{hover_fmt}}}{y_suffix}<extra></extra>",
                showlegend=False,
            ), row=2, col=1)

    fig.update_layout(
        paper_bgcolor=BBG["bg"],
        plot_bgcolor=BBG["panel"],
        margin=dict(l=35, r=20, t=8, b=28),
        font=dict(family=FONT, size=11, color=BBG["text"]),
        barmode="group",
    )
    fig.update_xaxes(showgrid=False, color=BBG["muted"], tickfont=dict(size=10), row=1, col=1)
    fig.update_xaxes(showgrid=False, color=BBG["muted"], tickfont=dict(size=10), row=2, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=BBG["grid"], zeroline=False, color=BBG["muted"], row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=BBG["grid"], zeroline=False, color=BBG["muted"], row=2, col=1)
    return fig


def _growth_series(df, mode, annual=False):
    if df is None or df.empty:
        return pd.DataFrame(columns=getattr(df, "columns", ["value"]))
    work = df.copy().sort_values("period_end")
    lag = 1 if annual or mode == "pop" else 4
    work["value"] = pd.to_numeric(work["value"], errors="coerce").pct_change(lag) * 100
    return work.dropna(subset=["value"])


def _build_multiples_table(fsym_id, security_id, latest_price, shares_out, currency):
    try:
        ratio_df = fetch_ratio_history(fsym_id)
    except Exception:
        ratio_df = pd.DataFrame()

    eps_annual = _get_measure_series(fsym_id, security_id, "EPS", "annual", latest_price, shares_out)
    sales_annual = _get_measure_series(fsym_id, security_id, "SALES", "annual", latest_price, shares_out)
    cfps_annual = _get_measure_series(fsym_id, security_id, "CFPS", "annual", latest_price, shares_out)
    dps_annual = _get_measure_series(fsym_id, security_id, "DPS", "annual", latest_price, shares_out)

    future_years = sorted(eps_annual[eps_annual["source"] == "estimate"]["fiscal_year"].dropna().astype(int).unique().tolist())
    while len(future_years) < 3:
        base = future_years[-1] if future_years else pd.Timestamp.today().year
        future_years.append(base + 1)
    fy_cols = [f"FY {str(year)[-2:]}" for year in future_years[:3]]
    columns = ["Multiple", "Last 4Q", "Next 4Q"] + fy_cols

    latest = ratio_df.sort_values("Date").iloc[-1] if not ratio_df.empty else None
    next_year = future_years[0]
    sales_lookup = {int(r["fiscal_year"]): r["value"] for _, r in sales_annual.iterrows() if pd.notna(r.get("value"))}
    eps_lookup = {int(r["fiscal_year"]): r["value"] for _, r in eps_annual.iterrows() if pd.notna(r.get("value"))}
    cfps_lookup = {int(r["fiscal_year"]): r["value"] for _, r in cfps_annual.iterrows() if pd.notna(r.get("value"))}
    dps_lookup = {int(r["fiscal_year"]): r["value"] for _, r in dps_annual.iterrows() if pd.notna(r.get("value"))}

    def _future_mult(lookup, derived):
        row = {}
        for year, col in zip(future_years[:3], fy_cols):
            row[col] = _format_measure(_derive_multiple_value(lookup.get(year), derived, latest_price, shares_out), {"kind": "multiple", "decimals": 1}, currency)
        row["Next 4Q"] = _format_measure(_derive_multiple_value(lookup.get(next_year), derived, latest_price, shares_out), {"kind": "multiple", "decimals": 1}, currency)
        return row

    def _future_yield(lookup):
        row = {}
        for year, col in zip(future_years[:3], fy_cols):
            row[col] = _format_measure((lookup.get(year) / latest_price * 100) if latest_price and lookup.get(year) not in [None, 0] else np.nan, {"kind": "percent", "decimals": 1}, currency)
        row["Next 4Q"] = _format_measure((lookup.get(next_year) / latest_price * 100) if latest_price and lookup.get(next_year) not in [None, 0] else np.nan, {"kind": "percent", "decimals": 1}, currency)
        return row

    rows = []
    rows.append({
        "Multiple": "P/E",
        "Last 4Q": _format_measure(latest.get("P/E") if latest is not None else np.nan, {"kind": "multiple", "decimals": 1}, currency),
        **_future_mult(eps_lookup, "price_over_item"),
    })
    rows.append({
        "Multiple": "P/S",
        "Last 4Q": _format_measure(latest.get("P/Sales") if latest is not None else np.nan, {"kind": "multiple", "decimals": 1}, currency),
        **_future_mult(sales_lookup, "marketcap_over_item"),
    })
    rows.append({"Multiple": "P/B", "Last 4Q": "—", "Next 4Q": "—", **{col: "—" for col in fy_cols}})
    rows.append({
        "Multiple": "P/CF",
        "Last 4Q": _format_measure(latest.get("P/CF") if latest is not None else np.nan, {"kind": "multiple", "decimals": 1}, currency),
        **_future_mult(cfps_lookup, "price_over_item"),
    })
    rows.append({"Multiple": "", "Last 4Q": "", "Next 4Q": "", **{col: "" for col in fy_cols}})
    rows.append({"Multiple": "EV/Revenue", "Last 4Q": "—", "Next 4Q": "—", **{col: "—" for col in fy_cols}})
    rows.append({"Multiple": "EV/EBITDA", "Last 4Q": "—", "Next 4Q": "—", **{col: "—" for col in fy_cols}})
    rows.append({"Multiple": "EV/EBIT", "Last 4Q": "—", "Next 4Q": "—", **{col: "—" for col in fy_cols}})
    rows.append({"Multiple": "EV/OPP", "Last 4Q": "—", "Next 4Q": "—", **{col: "—" for col in fy_cols}})
    rows.append({"Multiple": "", "Last 4Q": "", "Next 4Q": "", **{col: "" for col in fy_cols}})
    rows.append({
        "Multiple": "Dvd Yield",
        "Last 4Q": _format_measure((max(dps_lookup.values()) / latest_price * 100) if latest_price and dps_lookup else np.nan, {"kind": "percent", "decimals": 1}, currency),
        **_future_yield(dps_lookup),
    })
    return pd.DataFrame(rows, columns=columns)


def _derive_multiple_value(value, derived, latest_price, shares_out):
    if value in [None, 0] or pd.isna(value):
        return np.nan
    if derived == "price_over_item":
        return (latest_price / value) if latest_price else np.nan
    if derived == "marketcap_over_item":
        market_cap_m = (latest_price * shares_out / 1_000_000) if latest_price and shares_out else np.nan
        return (market_cap_m / value) if pd.notna(market_cap_m) else np.nan
    return np.nan


def _format_measure(value, cfg, currency):
    if value is None or pd.isna(value):
        return "—"
    kind = cfg.get("kind")
    decimals = cfg.get("decimals", 1)
    if kind == "multiple":
        return f"{float(value):.{decimals}f}x"
    if kind == "percent":
        return f"{float(value):.{decimals}f}%"
    if kind == "money":
        return f"{float(value):,.{decimals}f}"
    return f"{float(value):,.{decimals}f}"


def _bbg_matrix_table(df, label_col="Period", is_growth=False):
    if df is None or df.empty:
        return html.Div("No data.", style={"color": BBG["muted"], "fontFamily": FONT, "fontSize": "0.72rem"})
    style_conditional = [
        {
            "if": {"column_id": label_col},
            "textAlign": "left",
            "color": BBG["orange"],
            "fontWeight": "700",
        },
        {
            "if": {"filter_query": f'{{{label_col}}} = ""'},
            "backgroundColor": BBG["panel"],
            "borderBottom": f"1px solid {BBG['panel']}",
            "height": "8px",
        },
    ]
    return dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        page_action="none",
        style_table={"overflowX": "auto", "overflowY": "auto", "maxHeight": "295px"},
        style_header={
            "backgroundColor": BBG["panel_alt"],
            "color": BBG["text"],
            "fontFamily": FONT,
            "fontSize": "11px",
            "fontWeight": "700",
            "borderBottom": f"1px solid {BBG['border']}",
            "padding": "4px 6px",
        },
        style_cell={
            "backgroundColor": BBG["panel"],
            "color": BBG["orange"],
            "fontFamily": FONT,
            "fontSize": "11px",
            "padding": "4px 7px",
            "border": "none",
            "borderBottom": f"1px solid {BBG['border']}",
            "textAlign": "right",
            "whiteSpace": "nowrap",
            "fontVariantNumeric": "tabular-nums",
        },
        style_data_conditional=style_conditional,
    )

def _base_layout(c):
    return dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=c["subtext"], size=11),
        margin=dict(l=0, r=48, t=10, b=0),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1e1e2f", font_size=12,
                        font_family=FONT, font_color="#e6e6e6"),
        xaxis=dict(showgrid=False, color=c["muted"], linecolor=c["border"]),
    )


def _empty_figure(c, msg="No data"):
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=c["subtext"]),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(text=msg, showarrow=False,
                          font=dict(size=13, color=c["muted"], family=FONT))],
    )
    return fig


def _themed_table(df, c):
    """Return a dash_table.DataTable styled to the current theme."""
    return dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        page_action="none",
        style_table={"overflowX": "auto", "borderRadius": "8px",
                     "maxHeight": "400px", "overflowY": "auto"},
        style_header={
            "backgroundColor": c["panel"], "color": c["text"],
            "fontWeight": "700", "fontFamily": FONT, "fontSize": "0.72rem",
            "borderBottom": f"1px solid {c['border']}",
            "position": "sticky", "top": 0, "whiteSpace": "nowrap",
        },
        style_cell={
            "backgroundColor": c["bg"], "color": c["text"],
            "fontFamily": FONT, "fontSize": "0.72rem",
            "padding": "5px 8px",
            "borderBottom": f"1px solid {c['border']}",
            "textAlign": "right", "whiteSpace": "nowrap",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": c["panel"]},
            {"if": {"column_id": "Date"}, "textAlign": "left"},
            {"if": {"column_id": "Item"}, "textAlign": "left"},
            {"if": {"column_id": "FY End"}, "textAlign": "left"},
        ],
    )
