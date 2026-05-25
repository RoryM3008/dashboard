"""Callbacks — Earnings & Revisions page."""

import io
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, html, dcc, no_update, ALL
from dash.exceptions import PreventUpdate

from theme import get_theme, FONT
from snowflake_data import search_tickers, _resolve_ids, fetch_earnings_package


# ── Colour palette for revision lines ────────────────────────────────────────
_REV_COLOURS = ["#ff8c00", "#4296f5", "#00d26a", "#a855f7", "#e91e8f"]


def _offline_banner():
    return html.Div([
        html.Div("📡", style={"fontSize": "2.5rem", "marginBottom": "0.5rem"}),
        html.Div("Offline Mode", style={"fontWeight": "800", "fontSize": "1.1rem",
                                        "color": "#ff8c00", "marginBottom": "0.4rem"}),
        html.Div("This page requires a Snowflake / FactSet connection.",
                 style={"color": "#888", "fontSize": "0.82rem"}),
    ], style={"textAlign": "center", "padding": "3rem 2rem",
              "fontFamily": "'Inter', sans-serif"})


def _empty_fig(c, msg="No data"):
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=c["subtext"]),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(text=msg, showarrow=False,
                          font=dict(size=13, color=c["muted"], family=FONT))],
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


def _fmt_val(v, item):
    """Format a number for display in the summary table."""
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    if item in ("SALES", "EBITDA", "EBIT"):
        if abs(v) >= 1e6:
            return f"{v/1e6:,.1f}T"
        if abs(v) >= 1e3:
            return f"{v/1e3:,.1f}B"
        return f"{v:,.0f}M"
    return f"{v:.2f}"


# ── Scorecard / chart helpers (called from the main load callback) ────────────

def _compute_revision_scorecard(revisions_df, surprise_df, consensus_fwd_df,
                                 cur_price, item, c):
    """Return the revision scorecard chip strip (html.Div)."""

    def _chip(label, value_str, color):
        return html.Div([
            html.Div(label, style={"color": c["muted"], "fontSize": "0.58rem",
                                   "textTransform": "uppercase", "letterSpacing": "0.05em",
                                   "fontFamily": FONT}),
            html.Div(value_str, style={"color": color, "fontWeight": "800",
                                       "fontSize": "0.82rem", "fontFamily": FONT,
                                       "marginTop": "0.1rem"}),
        ], style={
            "padding": "0.4rem 0.9rem",
            "border": f"1px solid {color}55",
            "borderRadius": "8px",
            "backgroundColor": f"{color}13",
            "textAlign": "center",
            "minWidth": "76px",
        })

    chips = []

    # ── 4W / 13W / 52W revision % for NTM FY ─────────────────────────────
    if not revisions_df.empty:
        rev = revisions_df.copy()
        rev["CONS_END_DATE"] = pd.to_datetime(rev["CONS_END_DATE"], errors="coerce")
        rev["FE_FP_END"]     = pd.to_datetime(rev["FE_FP_END"],     errors="coerce")
        rev = rev.dropna(subset=["CONS_END_DATE", "FE_FP_END", "FE_MEAN"])
        future_fy = rev[rev["FE_FP_END"] >= pd.Timestamp.now()]
        if not future_fy.empty:
            ntm_fy = future_fy["FE_FP_END"].min()
            ntm = rev[rev["FE_FP_END"] == ntm_fy].sort_values("CONS_END_DATE")
            if len(ntm) >= 2:
                latest_date = ntm["CONS_END_DATE"].max()
                latest_mean = float(ntm.loc[ntm["CONS_END_DATE"] == latest_date,
                                            "FE_MEAN"].iloc[0])
                for weeks, lbl in [(4, "4W Rev"), (13, "13W Rev"), (52, "52W Rev")]:
                    cutoff = latest_date - pd.Timedelta(weeks=weeks)
                    prior  = ntm[ntm["CONS_END_DATE"] <= cutoff]
                    if not prior.empty:
                        prior_mean = float(prior.iloc[-1]["FE_MEAN"])
                        if prior_mean != 0:
                            pct = (latest_mean - prior_mean) / abs(prior_mean) * 100
                            col = "#00d26a" if pct >= 0 else "#ff3333"
                            chips.append(_chip(lbl, f"{'+' if pct>=0 else ''}{pct:.1f}%", col))

    # ── Estimate dispersion ───────────────────────────────────────────────
    if not consensus_fwd_df.empty:
        fwd = consensus_fwd_df.dropna(subset=["FE_MEAN", "FE_HIGH", "FE_LOW"])
        if not fwd.empty:
            r = fwd.iloc[0]
            mean_v = float(r["FE_MEAN"])
            if mean_v != 0:
                disp = (float(r["FE_HIGH"]) - float(r["FE_LOW"])) / abs(mean_v) * 100
                dcol = "#ff8c00" if disp > 15 else c["axis"]
                chips.append(_chip("Dispersion", f"{disp:.1f}%", dcol))

    # ── Beat / miss streak ────────────────────────────────────────────────
    if not surprise_df.empty:
        sur = surprise_df.copy()
        sur["FE_FP_END"] = pd.to_datetime(sur["FE_FP_END"], errors="coerce")
        sur = sur.dropna(subset=["FE_FP_END", "ACTUAL_VALUE", "CONS_MEAN"])\
                 .sort_values("FE_FP_END", ascending=False)
        streak, direction = 0, None
        for _, row in sur.iterrows():
            try:
                beat = float(row["ACTUAL_VALUE"]) >= float(row["CONS_MEAN"])
            except (TypeError, ValueError):
                break
            cur_dir = "beat" if beat else "miss"
            if direction is None:
                direction, streak = cur_dir, 1
            elif cur_dir == direction:
                streak += 1
            else:
                break
        if direction and streak > 0:
            scol  = "#00d26a" if direction == "beat" else "#ff3333"
            slbl  = f"✅ {streak}Q" if direction == "beat" else f"❌ {streak}Q"
            chips.append(_chip("Streak", slbl, scol))

    # ── NTM P/E (only meaningful when metric = EPS) ───────────────────────
    cur_px = cur_price.get("price")
    if cur_px and item == "EPS" and not consensus_fwd_df.empty:
        fwd_eps = consensus_fwd_df.dropna(subset=["FE_MEAN"])
        if not fwd_eps.empty:
            ntm_eps = float(fwd_eps.iloc[0]["FE_MEAN"])
            if ntm_eps > 0:
                chips.append(_chip("NTM P/E", f"{cur_px / ntm_eps:.1f}x", c["blue"]))

    if not chips:
        return html.Div()

    return html.Div([
        html.Div(f"Revision Scorecard — {item} (NTM consensus)",
                 style={"color": c["muted"], "fontSize": "0.58rem", "fontFamily": FONT,
                        "textTransform": "uppercase", "letterSpacing": "0.06em",
                        "marginBottom": "0.4rem"}),
        html.Div(chips, style={"display": "flex", "flexWrap": "wrap", "gap": "0.4rem"}),
    ], style={
        "backgroundColor": c["panel"], "border": f"1px solid {c['border']}",
        "borderRadius": "10px", "padding": "0.7rem 1.2rem", "marginTop": "0.5rem",
    })


def _build_price_reaction_chart(surprise_df, price_reaction_prices, c):
    """Bar chart: day-of stock return for each earnings release."""
    fig = go.Figure()
    if surprise_df.empty or price_reaction_prices.empty:
        return _empty_fig(c, "No price reaction data")

    sur = surprise_df.copy()
    sur["REPORT_DATE"] = pd.to_datetime(sur["REPORT_DATE"], errors="coerce")
    sur["FE_FP_END"]   = pd.to_datetime(sur["FE_FP_END"],   errors="coerce")
    sur = sur.dropna(subset=["REPORT_DATE", "FE_FP_END"]).sort_values("FE_FP_END")

    prices = price_reaction_prices.copy()
    prices["P_DATE"] = pd.to_datetime(prices["P_DATE"], errors="coerce")
    prices = prices.dropna(subset=["P_DATE", "P_PRICE"]).sort_values("P_DATE")

    reactions = []
    for _, row in sur.iterrows():
        rdate    = pd.Timestamp(row["REPORT_DATE"])
        on_day   = prices[prices["P_DATE"] >= rdate]
        before   = prices[prices["P_DATE"] <  rdate]
        if on_day.empty or before.empty:
            continue
        px_after  = float(on_day.iloc[0]["P_PRICE"])
        px_before = float(before.iloc[-1]["P_PRICE"])
        if px_before == 0:
            continue
        ret  = (px_after / px_before - 1) * 100
        beat = None
        surp = None
        try:
            if pd.notna(row.get("CONS_MEAN")):
                cons_v = float(row["CONS_MEAN"])
                act_v  = float(row["ACTUAL_VALUE"])
                beat   = act_v >= cons_v
                if cons_v != 0:
                    surp = (act_v - cons_v) / abs(cons_v) * 100
        except (TypeError, ValueError):
            pass
        reactions.append({"period": pd.Timestamp(row["FE_FP_END"]).strftime("%b '%y"),
                           "ret": ret, "beat": beat, "surp": surp})

    if not reactions:
        return _empty_fig(c, "Could not match prices to report dates")

    colours = ["#00d26a" if r["beat"] is True else
               "#ff3333" if r["beat"] is False else c["accent"]
               for r in reactions]
    hover   = [f"Period: {r['period']}<br>Day return: {r['ret']:+.1f}%"
               + (f"<br>EPS surprise: {r['surp']:+.1f}%" if r["surp"] is not None else "")
               for r in reactions]

    fig.add_trace(go.Bar(
        x=[r["period"] for r in reactions],
        y=[r["ret"]    for r in reactions],
        marker_color=colours,
        text=[f"{r['ret']:+.1f}%" for r in reactions],
        textposition="outside",
        textfont=dict(size=9, color=c["axis"]),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
        name="Day Return",
    ))
    fig.add_hline(y=0, line_color=c["border"], line_width=1)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=c["axis"], size=11),
        margin=dict(l=45, r=10, t=20, b=55),
        xaxis=dict(showgrid=False, color=c["axis"], tickangle=-40),
        yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                   title="Price Return %", ticksuffix="%"),
        showlegend=False,
    )
    return fig


def _build_ntm_pe_chart(price_hist_df, revisions_df, c):
    """Monthly NTM P/E implied from price history ÷ consensus NTM EPS."""
    fig = go.Figure()
    if price_hist_df.empty or revisions_df.empty:
        return _empty_fig(c, "Select EPS metric and reload for NTM P/E chart")

    ph = price_hist_df.copy()
    ph["P_DATE"] = pd.to_datetime(ph["P_DATE"], errors="coerce")
    ph = ph.dropna(subset=["P_DATE", "P_PRICE"]).sort_values("P_DATE")

    rev = revisions_df.copy()
    rev["CONS_END_DATE"] = pd.to_datetime(rev["CONS_END_DATE"], errors="coerce")
    rev["FE_FP_END"]     = pd.to_datetime(rev["FE_FP_END"],     errors="coerce")
    rev = rev.dropna(subset=["CONS_END_DATE", "FE_FP_END", "FE_MEAN"])
    rev["FE_MEAN"] = pd.to_numeric(rev["FE_MEAN"], errors="coerce")
    rev = rev[rev["FE_MEAN"] > 0]

    pe_rows = []
    for _, price_row in ph.iterrows():
        pdate = price_row["P_DATE"]
        px    = float(price_row["P_PRICE"])
        future = rev[rev["FE_FP_END"] > pdate].sort_values("FE_FP_END")
        if future.empty:
            continue
        ntm_fy = future["FE_FP_END"].iloc[0]
        snaps  = rev[(rev["FE_FP_END"] == ntm_fy) & (rev["CONS_END_DATE"] <= pdate)]
        if snaps.empty:
            continue
        ntm_eps = float(snaps.sort_values("CONS_END_DATE").iloc[-1]["FE_MEAN"])
        if ntm_eps <= 0:
            continue
        pe = px / ntm_eps
        if 0 < pe <= 150:
            pe_rows.append({"date": pdate, "pe": pe})

    if not pe_rows:
        return _empty_fig(c, "Select EPS metric and reload for NTM P/E chart")

    pe_df  = pd.DataFrame(pe_rows).sort_values("date")
    avg_pe = float(pe_df["pe"].mean())

    fig.add_trace(go.Scatter(
        x=pe_df["date"], y=pe_df["pe"],
        mode="lines", name="NTM P/E",
        line=dict(color=c["blue"], width=2),
        fill="tozeroy", fillcolor="rgba(66,150,245,0.07)",
        hovertemplate="%{x|%b %Y}  NTM P/E: %{y:.1f}x<extra></extra>",
    ))
    fig.add_hline(y=avg_pe, line_dash="dot", line_color=c["accent"],
                  annotation_text=f"3Y avg {avg_pe:.1f}x",
                  annotation_font_color=c["accent"], annotation_font_size=10)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=c["axis"], size=11),
        margin=dict(l=50, r=10, t=20, b=40),
        xaxis=dict(showgrid=False, color=c["axis"]),
        yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                   title="NTM P/E (x)", ticksuffix="x"),
        showlegend=False,
    )
    return fig


def _build_rolling_revision_chart(revisions_df, weeks, c):
    """Rolling N-week revision % for each forward FY, charted over time.

    For every consensus snapshot date in the revision history, we look back
    `weeks` weeks and compute  (current_mean - prior_mean) / |prior_mean| * 100.
    One line per forward FY so you can see which year is being revised most.
    """
    fig = go.Figure()
    if revisions_df.empty:
        return _empty_fig(c, f"No revision data for {weeks}W chart")

    rev = revisions_df.copy()
    rev["CONS_END_DATE"] = pd.to_datetime(rev["CONS_END_DATE"], errors="coerce")
    rev["FE_FP_END"]     = pd.to_datetime(rev["FE_FP_END"],     errors="coerce")
    rev["FE_MEAN"]       = pd.to_numeric(rev["FE_MEAN"],        errors="coerce")
    rev = rev.dropna(subset=["CONS_END_DATE", "FE_FP_END", "FE_MEAN"])

    future_fys = sorted([fy for fy in rev["FE_FP_END"].unique()
                         if pd.Timestamp(fy) >= pd.Timestamp.now()])[:4]
    if not future_fys:
        return _empty_fig(c, "No forward FY data for rolling revision chart")

    any_data = False
    for i, fy in enumerate(future_fys):
        grp = rev[rev["FE_FP_END"] == fy].sort_values("CONS_END_DATE")
        if len(grp) < 2:
            continue
        rows = []
        for _, row in grp.iterrows():
            cur_date = row["CONS_END_DATE"]
            cur_mean = float(row["FE_MEAN"])
            lookback = cur_date - pd.Timedelta(weeks=weeks)
            prior = grp[grp["CONS_END_DATE"] <= lookback]
            if prior.empty:
                continue
            prior_mean = float(prior.iloc[-1]["FE_MEAN"])
            if prior_mean == 0:
                continue
            pct = (cur_mean - prior_mean) / abs(prior_mean) * 100
            rows.append({"date": cur_date, "rev_pct": pct})

        if not rows:
            continue
        any_data = True
        df_r   = pd.DataFrame(rows)
        colour = _REV_COLOURS[i % len(_REV_COLOURS)]
        fy_lbl = f"FY {pd.Timestamp(fy).year}"
        fig.add_trace(go.Scatter(
            x=df_r["date"], y=df_r["rev_pct"],
            mode="lines+markers",
            name=fy_lbl,
            line=dict(color=colour, width=2),
            marker=dict(size=4, color=colour),
            hovertemplate=f"{fy_lbl}  %{{x|%b %Y}}<br>{weeks}W Rev: %{{y:+.1f}}%<extra></extra>",
        ))

    if not any_data:
        return _empty_fig(c, f"Not enough history for {weeks}W rolling revision")

    fig.add_hline(y=0, line_color=c["border"], line_width=1)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=c["axis"], size=11),
        margin=dict(l=50, r=10, t=20, b=40),
        legend=dict(orientation="h", y=1.08, font=dict(size=10)),
        xaxis=dict(showgrid=False, color=c["axis"]),
        yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                   title=f"{weeks}W Revision %", ticksuffix="%"),
    )
    return fig


def register_callbacks(app):

    # ── Ticker autocomplete ───────────────────────────────────────────────────
    @app.callback(
        Output("earn-ticker-suggestions", "children"),
        Input("earn-ticker", "value"),
        prevent_initial_call=True,
    )
    def earn_ticker_suggestions(search):
        if not search or len(search.strip()) < 2:
            return []
        if "-" in search and len(search) >= 5:
            return []
        try:
            results = search_tickers(search, limit=20)
        except Exception:
            return []
        cards = []
        for r in results[:8]:
            region = f" · {r['region']}" if r.get("region") else ""
            cards.append(html.Button(
                [html.Span(f"{r['ticker']}{region}", style={"fontWeight": "700"}),
                 html.Span(f"  {r['name']}", style={"marginLeft": "0.35rem"})],
                id={"type": "earn-ticker-sug", "index": r["ticker_region"]},
                n_clicks=0,
                style={"backgroundColor": "#0b0b0b", "border": "1px solid #2a2a2a",
                       "color": "#e6e6e6", "padding": "0.45rem 0.65rem",
                       "textAlign": "left", "fontFamily": FONT,
                       "fontSize": "0.76rem", "cursor": "pointer"},
            ))
        return cards

    @app.callback(
        Output("earn-ticker", "value", allow_duplicate=True),
        Output("earn-ticker-suggestions", "children", allow_duplicate=True),
        Input({"type": "earn-ticker-sug", "index": ALL}, "n_clicks"),
        State({"type": "earn-ticker-sug", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def pick_earn_suggestion(clicks, ids):
        if not clicks or not any(clicks):
            return no_update, no_update
        for n, item in zip(clicks, ids):
            if n:
                return item["index"], []
        return no_update, no_update

    # ── Metric toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("earn-item-store", "data"),
        Output("earn-item-EPS",    "style"),
        Output("earn-item-SALES",  "style"),
        Output("earn-item-EBITDA", "style"),
        Output("earn-item-EBIT",   "style"),
        Output("earn-item-DPS",    "style"),
        Input("earn-item-EPS",    "n_clicks"),
        Input("earn-item-SALES",  "n_clicks"),
        Input("earn-item-EBITDA", "n_clicks"),
        Input("earn-item-EBIT",   "n_clicks"),
        Input("earn-item-DPS",    "n_clicks"),
        State("earn-item-store", "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_item(n1, n2, n3, n4, n5, current, theme_mode):
        import dash
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        item_map = {
            "earn-item-EPS":    "EPS",
            "earn-item-SALES":  "SALES",
            "earn-item-EBITDA": "EBITDA",
            "earn-item-EBIT":   "EBIT",
            "earn-item-DPS":    "DPS",
        }
        new_item = item_map.get(trigger, current)
        c = get_theme(theme_mode or "dark")
        styles = []
        for btn_id in ["earn-item-EPS", "earn-item-SALES", "earn-item-EBITDA",
                        "earn-item-EBIT", "earn-item-DPS"]:
            active = (item_map[btn_id] == new_item)
            styles.append({
                "backgroundColor": c["accent"] if active else c["panel"],
                "color": "#000" if active else c["text"],
                "border": f"1px solid {c['border']}",
                "borderRadius": "6px", "padding": "0.4rem 0.75rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.75rem", "cursor": "pointer",
            })
        return new_item, *styles

    # ── Period toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("earn-period-store", "data"),
        Output("earn-period-q", "style"),
        Output("earn-period-a", "style"),
        Input("earn-period-q", "n_clicks"),
        Input("earn-period-a", "n_clicks"),
        State("earn-period-store", "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_period(nq, na, current, theme_mode):
        import dash
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        new_period = "quarterly" if trigger == "earn-period-q" else "annual"
        c = get_theme(theme_mode or "dark")
        def _btn(active):
            return {
                "backgroundColor": c["accent"] if active else c["panel"],
                "color": "#000" if active else c["text"],
                "border": f"1px solid {c['border']}",
                "borderRadius": "6px", "padding": "0.4rem 0.75rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.75rem", "cursor": "pointer",
            }
        return new_period, _btn(new_period == "quarterly"), _btn(new_period == "annual")

    # ── Main load callback ────────────────────────────────────────────────────
    @app.callback(
        Output("earn-actuals-chart",        "figure"),
        Output("earn-forward-chart",        "figure"),
        Output("earn-revisions-chart",      "figure"),
        Output("earn-recs-chart",           "figure"),
        Output("earn-pt-chart",             "figure"),
        Output("earn-recs-history-chart",   "figure"),
        Output("earn-price-reaction-chart", "figure"),
        Output("earn-ntm-pe-chart",         "figure"),
        Output("earn-ntm-panel-title",      "children"),
        Output("earn-ntm-panel-subtitle",   "children"),
        Output("earn-fwd-table",            "children"),
        Output("earn-header-strip",         "children"),
        Output("earn-revision-scorecard",   "children"),
        Output("earn-actuals-title",        "children"),
        Output("earn-status",               "children"),
        Output("earn-data-store",           "data"),
        Input("earn-load-btn",    "n_clicks"),
        Input("earn-item-store",  "data"),
        Input("earn-period-store","data"),
        State("earn-ticker",      "value"),
        State("theme-store",      "data"),
        State("datasource",       "data"),
        prevent_initial_call=True,
    )
    def load_earnings(n_clicks, item, period, ticker_raw, theme_mode, datasource):
        c = get_theme(theme_mode or "dark")
        empty = _empty_fig(c)
        _e8 = (empty,) * 8

        if datasource == "yf":
            return _e8 + ("—", "", _offline_banner(), html.Div(), html.Div(), "—", "⚠️ Offline mode", {})

        if not ticker_raw or not ticker_raw.strip():
            return _e8 + ("—", "", html.Div(), html.Div(), html.Div(), "—", "", {})

        # Resolve ticker
        try:
            ids = _resolve_ids(ticker_raw.strip().upper())
        except Exception as e:
            return _e8 + ("—", "", html.Div(), html.Div(), html.Div(), "—", f"❌ {e}", {})

        if not ids or not ids.get("fsym_id"):
            return _e8 + ("—", "", html.Div(), html.Div(), html.Div(), "—",
                f"❌ Ticker '{ticker_raw.strip().upper()}' not found", {})

        fsym_id   = ids["fsym_id"]
        comp_name = ids.get("name") or ticker_raw.strip().upper()

        try:
            pkg = fetch_earnings_package(fsym_id, item)
        except Exception as e:
            return _e8 + ("—", "", html.Div(), html.Div(), html.Div(), "—", f"❌ {e}", {})

        # ── Chart 1: Actuals (+ Beat/Miss) ───────────────────────────────
        actuals_title = f"{comp_name} — {item} {'Quarterly' if period == 'quarterly' else 'Annual'} Actuals vs Consensus"

        act_df = pkg["actuals_q"] if period == "quarterly" else pkg["actuals_a"]
        sur_df = pkg["surprise_q"] if period == "quarterly" else pd.DataFrame()

        fig_act = go.Figure()

        if not act_df.empty:
            act_df = act_df.copy()
            act_df["FE_FP_END"] = pd.to_datetime(act_df["FE_FP_END"], errors="coerce")
            act_df = act_df.dropna(subset=["FE_FP_END"]).sort_values("FE_FP_END")

            # Beat/miss colours
            if not sur_df.empty:
                sur_df = sur_df.copy()
                sur_df["FE_FP_END"] = pd.to_datetime(sur_df["FE_FP_END"], errors="coerce")
                cons_map = dict(zip(sur_df["FE_FP_END"], sur_df["CONS_MEAN"]))

                colours = []
                surprise_pct = []
                for fp in act_df["FE_FP_END"]:
                    cons = cons_map.get(fp)
                    act  = act_df.loc[act_df["FE_FP_END"] == fp, "ACTUAL_VALUE"]
                    if cons is not None and not act.empty and float(cons) != 0:
                        actual_val = float(act.iloc[0])
                        pct = (actual_val - float(cons)) / abs(float(cons)) * 100
                        colours.append("#00d26a" if actual_val >= float(cons) else "#ff3333")
                        surprise_pct.append(f"{'+' if pct >= 0 else ''}{pct:.1f}%")
                    elif cons is not None and not act.empty:
                        colours.append("#00d26a" if float(act.iloc[0]) >= float(cons) else "#ff3333")
                        surprise_pct.append("")
                    else:
                        colours.append(c["accent"])
                        surprise_pct.append("")

                # Consensus line
                sur_sorted = sur_df.dropna(subset=["FE_FP_END", "CONS_MEAN"]).sort_values("FE_FP_END")
                fig_act.add_trace(go.Scatter(
                    x=sur_sorted["FE_FP_END"],
                    y=sur_sorted["CONS_MEAN"],
                    mode="lines+markers",
                    name="Consensus (at report)",
                    line=dict(color=c["blue"], width=1.5, dash="dot"),
                    marker=dict(size=5, color=c["blue"]),
                    hovertemplate="Consensus: %{y:.2f}<extra></extra>",
                ))
            else:
                colours = [c["accent"]] * len(act_df)
                surprise_pct = [""] * len(act_df)

            labels = act_df["FE_FP_END"].dt.strftime(
                "%b '%y" if period == "quarterly" else "%Y"
            )
            fig_act.add_trace(go.Bar(
                x=act_df["FE_FP_END"],
                y=act_df["ACTUAL_VALUE"],
                name="Actual",
                marker_color=colours,
                text=surprise_pct,
                textposition="outside",
                textfont=dict(size=9, color=c["subtext"]),
                hovertemplate="Period: %{customdata}<br>Actual: %{y:.2f}<br>Surprise: %{text}<extra></extra>",
                customdata=labels,
            ))

        fig_act.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["axis"], size=11),
            margin=dict(l=40, r=10, t=20, b=40),
            legend=dict(orientation="h", y=1.08, font=dict(size=10)),
            xaxis=dict(showgrid=False, color=c["axis"]),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                       title=item),
            barmode="group",
        )

        # ── Chart 2: Forward Consensus ────────────────────────────────────
        fwd_df = pkg["consensus_fwd"]
        fig_fwd = go.Figure()

        if not fwd_df.empty:
            fwd_df = fwd_df.copy()
            fwd_df["FE_FP_END"] = pd.to_datetime(fwd_df["FE_FP_END"], errors="coerce")
            fwd_df = fwd_df.dropna(subset=["FE_FP_END"]).sort_values("FE_FP_END")
            fy_labels = fwd_df["FE_FP_END"].dt.strftime("FY %Y")

            # High/Low range
            fig_fwd.add_trace(go.Bar(
                x=fy_labels,
                y=(fwd_df["FE_HIGH"] - fwd_df["FE_LOW"]),
                base=fwd_df["FE_LOW"],
                name="High–Low Range",
                marker_color=c["border"],
                marker_opacity=0.6,
                hovertemplate="Low: %{base:.2f}  High: %{y:.2f}<extra></extra>",
            ))
            # Mean
            fig_fwd.add_trace(go.Scatter(
                x=fy_labels,
                y=fwd_df["FE_MEAN"],
                mode="markers+text",
                name="Consensus Mean",
                marker=dict(size=14, color=c["accent"], symbol="diamond"),
                text=[f"{v:.2f}" for v in fwd_df["FE_MEAN"]],
                textposition="top center",
                textfont=dict(size=11, color=c["accent"]),
                hovertemplate="Mean: %{y:.2f}<extra></extra>",
            ))
            # Median
            fig_fwd.add_trace(go.Scatter(
                x=fy_labels,
                y=fwd_df["FE_MEDIAN"],
                mode="markers",
                name="Median",
                marker=dict(size=8, color=c["blue"], symbol="circle"),
                hovertemplate="Median: %{y:.2f}<extra></extra>",
            ))

        fig_fwd.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["axis"], size=11),
            margin=dict(l=40, r=10, t=20, b=40),
            legend=dict(orientation="h", y=1.08, font=dict(size=10)),
            xaxis=dict(showgrid=False, color=c["axis"]),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                       title=item),
            barmode="overlay",
        )

        # ── Chart 3: Revision History ─────────────────────────────────────
        rev_df = pkg["revisions"]
        fig_rev = go.Figure()

        if not rev_df.empty:
            rev_df = rev_df.copy()
            rev_df["CONS_END_DATE"] = pd.to_datetime(rev_df["CONS_END_DATE"], errors="coerce")
            rev_df["FE_FP_END"]     = pd.to_datetime(rev_df["FE_FP_END"],     errors="coerce")
            rev_df = rev_df.dropna(subset=["CONS_END_DATE", "FE_FP_END", "FE_MEAN"])

            for i, (fy, grp) in enumerate(rev_df.groupby("FE_FP_END")):
                grp = grp.sort_values("CONS_END_DATE")
                colour = _REV_COLOURS[i % len(_REV_COLOURS)]
                fig_rev.add_trace(go.Scatter(
                    x=grp["CONS_END_DATE"],
                    y=grp["FE_MEAN"],
                    mode="lines+markers",
                    name=f"FY {pd.Timestamp(fy).year}",
                    line=dict(color=colour, width=2),
                    marker=dict(size=5, color=colour),
                    hovertemplate=f"FY {pd.Timestamp(fy).year}<br>%{{x|%b %Y}}<br>{item}: %{{y:.2f}}<extra></extra>",
                ))

        fig_rev.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["axis"], size=11),
            margin=dict(l=40, r=10, t=20, b=40),
            legend=dict(orientation="h", y=1.08, font=dict(size=10)),
            xaxis=dict(showgrid=False, color=c["axis"]),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                       title=f"{item} Consensus"),
        )

        # ── Chart 4: Analyst Recommendations ─────────────────────────────
        recs_df = pkg["recommendations"]
        fig_recs = go.Figure()

        if not recs_df.empty:
            recs_df = recs_df.copy()
            recs_df["CONS_END_DATE"] = pd.to_datetime(recs_df["CONS_END_DATE"], errors="coerce")
            recs_df = recs_df.dropna(subset=["CONS_END_DATE"]).sort_values("CONS_END_DATE")

            # Latest snapshot for donut
            latest = recs_df.iloc[-1]
            labels = ["Buy", "Overweight", "Hold", "Underweight", "Sell"]
            values = [latest.get("FE_BUY", 0) or 0,
                      latest.get("FE_OVER", 0) or 0,
                      latest.get("FE_HOLD", 0) or 0,
                      latest.get("FE_UNDER", 0) or 0,
                      latest.get("FE_SELL", 0) or 0]
            colours_recs = ["#00d26a", "#7ec87e", "#888888", "#e07070", "#ff3333"]

            fig_recs.add_trace(go.Pie(
                labels=labels,
                values=values,
                hole=0.52,
                marker_colors=colours_recs,
                textinfo="label+percent",
                textfont=dict(size=11, family=FONT),
                hovertemplate="%{label}: %{value} analysts (%{percent})<extra></extra>",
            ))

            total = int(latest.get("FE_TOTAL", sum(values)) or sum(values))
            snap  = pd.Timestamp(latest["CONS_END_DATE"]).strftime("%b %Y")
            fig_recs.update_layout(
                annotations=[dict(
                    text=f"<b>{total}</b><br>analysts<br><span style='font-size:9px'>{snap}</span>",
                    x=0.5, y=0.5, font=dict(size=13, family=FONT, color=c["text"]),
                    showarrow=False,
                )],
            )

        fig_recs.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["axis"], size=11),
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=10)),
            showlegend=True,
        )

        # ── Chart 5: Price Target History ─────────────────────────────────
        pt_df = pkg["price_target_hist"]
        cur_price = pkg["current_price"]
        fig_pt = go.Figure()

        if not pt_df.empty:
            pt_df = pt_df.copy()
            pt_df["CONS_END_DATE"] = pd.to_datetime(pt_df["CONS_END_DATE"], errors="coerce")
            pt_df = pt_df.dropna(subset=["CONS_END_DATE", "FE_MEAN"]).sort_values("CONS_END_DATE")

            # High/Low shaded band
            fig_pt.add_trace(go.Scatter(
                x=pd.concat([pt_df["CONS_END_DATE"], pt_df["CONS_END_DATE"][::-1]]),
                y=pd.concat([pt_df["FE_HIGH"], pt_df["FE_LOW"][::-1]]),
                fill="toself",
                fillcolor="rgba(255,140,0,0.12)",
                line=dict(color="rgba(255,140,0,0)"),
                name="PT High–Low Band",
                hoverinfo="skip",
            ))
            # PT mean line
            fig_pt.add_trace(go.Scatter(
                x=pt_df["CONS_END_DATE"],
                y=pt_df["FE_MEAN"],
                mode="lines+markers",
                name="Consensus PT",
                line=dict(color="#ff8c00", width=2),
                marker=dict(size=4, color="#ff8c00"),
                hovertemplate="%{x|%b %Y}  PT: %{y:.2f}<extra></extra>",
            ))

            # Current price horizontal line
            if cur_price.get("price"):
                px_val = cur_price["price"]
                fig_pt.add_hline(
                    y=px_val,
                    line_dash="dot",
                    line_color=c["blue"],
                    annotation_text=f"Price {px_val:.2f}",
                    annotation_font_color=c["blue"],
                    annotation_font_size=10,
                )
                # Upside annotation on latest PT
                latest_pt = float(pt_df["FE_MEAN"].iloc[-1])
                upside = (latest_pt / px_val - 1) * 100
                upside_colour = "#00d26a" if upside >= 0 else "#ff3333"
                fig_pt.add_annotation(
                    x=pt_df["CONS_END_DATE"].iloc[-1],
                    y=latest_pt,
                    text=f"<b>{'+' if upside >= 0 else ''}{upside:.1f}% upside</b>",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=upside_colour,
                    font=dict(color=upside_colour, size=11, family=FONT),
                    bgcolor="rgba(0,0,0,0.5)",
                    bordercolor=upside_colour,
                    borderpad=4,
                )

        fig_pt.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["axis"], size=11),
            margin=dict(l=40, r=10, t=30, b=40),
            legend=dict(orientation="h", y=1.08, font=dict(size=10)),
            xaxis=dict(showgrid=False, color=c["axis"]),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                       title="Price Target"),
        )

        # ── Chart 6: Recommendation History (stacked bar, 24 months) ──────
        recs_hist_df = pkg["recommendations"]
        fig_recs_hist = go.Figure()

        if not recs_hist_df.empty:
            rh = recs_hist_df.copy()
            rh["CONS_END_DATE"] = pd.to_datetime(rh["CONS_END_DATE"], errors="coerce")
            rh = rh.dropna(subset=["CONS_END_DATE"]).sort_values("CONS_END_DATE")
            x_dates = rh["CONS_END_DATE"].dt.strftime("%b %Y")

            _recs_config = [
                ("Buy",         "FE_BUY",   "#00d26a"),
                ("Overweight",  "FE_OVER",  "#7ec87e"),
                ("Hold",        "FE_HOLD",  "#888888"),
                ("Underweight", "FE_UNDER", "#e07070"),
                ("Sell",        "FE_SELL",  "#ff3333"),
            ]
            for label, col, colour in _recs_config:
                vals = rh[col].fillna(0).tolist() if col in rh.columns else [0] * len(rh)
                fig_recs_hist.add_trace(go.Bar(
                    x=x_dates,
                    y=vals,
                    name=label,
                    marker_color=colour,
                    hovertemplate=f"{label}: %{{y}} analysts (%{{x}})<extra></extra>",
                ))

        fig_recs_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["axis"], size=11),
            margin=dict(l=40, r=10, t=20, b=60),
            legend=dict(orientation="h", y=1.08, font=dict(size=10)),
            xaxis=dict(showgrid=False, color=c["axis"], tickangle=-45),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["axis"],
                       title="# Analysts"),
            barmode="stack",
        )

        # ── Chart 7: Price Reaction on Earnings Day ───────────────────────
        fig_price_react = _build_price_reaction_chart(
            pkg["surprise_q"], pkg["price_reaction_prices"], c
        )

        # ── Chart 8: NTM P/E time series (EPS only) ─────────────────────
        fig_ntm_pe = _build_ntm_pe_chart(
            pkg["price_hist"], pkg["revisions"], c
        ) if item == "EPS" else _empty_fig(c, "Select EPS metric for NTM P/E chart")

        # ── Company header strip ──────────────────────────────────────────
        cur_px   = cur_price.get("price")
        cur_ccy  = cur_price.get("currency") or ""
        # Latest PT upside
        upside_str = "—"
        if not pt_df.empty and cur_px:
            lpt = float(pt_df["FE_MEAN"].iloc[-1])
            up  = (lpt / cur_px - 1) * 100
            upside_str = f"{'+' if up >= 0 else ''}{up:.1f}%"
            upside_col = "#00d26a" if up >= 0 else "#ff3333"
        else:
            upside_col = c["muted"]
        # Latest recommendation skew
        recs_skew = "—"
        recs_col  = c["muted"]
        if not recs_hist_df.empty:
            lat = recs_hist_df.iloc[-1]
            buy_ow  = (lat.get("FE_BUY") or 0) + (lat.get("FE_OVER") or 0)
            sell_uw = (lat.get("FE_SELL") or 0) + (lat.get("FE_UNDER") or 0)
            total_r = lat.get("FE_TOTAL") or (buy_ow + sell_uw + (lat.get("FE_HOLD") or 0))
            if total_r:
                buy_pct = buy_ow / total_r * 100
                recs_skew = f"{buy_pct:.0f}% Buy/OW  ({int(total_r)} analysts)"
                recs_col = "#00d26a" if buy_pct >= 60 else ("#ff3333" if buy_pct < 40 else c["muted"])

        def _kpi(label, value, value_color=None):
            return html.Div([
                html.Div(label, style={"color": c["muted"], "fontSize": "0.6rem",
                                       "fontFamily": FONT, "marginBottom": "0.1rem",
                                       "textTransform": "uppercase", "letterSpacing": "0.05em"}),
                html.Div(value, style={"color": value_color or c["text"], "fontSize": "0.88rem",
                                       "fontFamily": FONT, "fontWeight": "700"}),
            ], style={"padding": "0.5rem 1.2rem", "borderRight": f"1px solid {c['border']}"})

        px_label        = f"{cur_px:,.2f} {cur_ccy}" if cur_px else "—"
        latest_pt_label = f"{float(pt_df['FE_MEAN'].iloc[-1]):,.2f}" if not pt_df.empty else "—"
        num_est_label   = str(int(pt_df["FE_NUM_EST"].iloc[-1])) if not pt_df.empty and pd.notna(pt_df["FE_NUM_EST"].iloc[-1]) else "—"

        # Beat streak for header
        beat_streak_label = "—"
        beat_streak_col   = c["muted"]
        if not pkg["surprise_q"].empty:
            sur_h = pkg["surprise_q"].copy()
            sur_h["FE_FP_END"] = pd.to_datetime(sur_h["FE_FP_END"], errors="coerce")
            sur_h = sur_h.dropna(subset=["FE_FP_END", "ACTUAL_VALUE", "CONS_MEAN"])\
                         .sort_values("FE_FP_END", ascending=False)
            st, di = 0, None
            for _, sr in sur_h.iterrows():
                try:
                    bd = float(sr["ACTUAL_VALUE"]) >= float(sr["CONS_MEAN"])
                except (TypeError, ValueError):
                    break
                cd = "beat" if bd else "miss"
                if di is None:          di, st = cd, 1
                elif cd == di:          st += 1
                else:                   break
            if di:
                _icon = "✅" if di == "beat" else "❌"
                _word = "beats" if di == "beat" else "misses"
                beat_streak_label = f"{_icon} {st}Q {_word}"
                beat_streak_col   = "#00d26a" if di == "beat" else "#ff3333"

        # NTM P/E for header
        ntm_pe_label = "—"
        if cur_px and item == "EPS" and not pkg["consensus_fwd"].empty:
            fwd_e = pkg["consensus_fwd"].dropna(subset=["FE_MEAN"])
            if not fwd_e.empty:
                ne = float(fwd_e.iloc[0]["FE_MEAN"])
                if ne > 0:
                    ntm_pe_label = f"{cur_px / ne:.1f}x"

        header_strip = html.Div([
            _kpi("Company",        comp_name,        c["accent"]),
            _kpi("Current Price",  px_label),
            _kpi("Consensus PT",   latest_pt_label),
            _kpi("Implied Upside", upside_str,       upside_col),
            _kpi("PT Analysts",    num_est_label),
            _kpi("NTM P/E",        ntm_pe_label,     c["blue"]),
            _kpi("Beat Streak",    beat_streak_label, beat_streak_col),
            _kpi("Rec Skew",       recs_skew,         recs_col),
        ], style={
            "display": "flex", "alignItems": "center",
            "backgroundColor": c["panel"],
            "borderRadius": "10px", "border": f"1px solid {c['border']}",
            "padding": "0.3rem 0", "flexWrap": "wrap",
        })

        # ── Revision scorecard ───────────────────────────────────────────────
        revision_scorecard = _compute_revision_scorecard(
            pkg["revisions"], pkg["surprise_q"], pkg["consensus_fwd"],
            pkg["current_price"], item, c
        )

        # ── Forward summary table ─────────────────────────────────────────
        fwd_items_df = pkg["forward_items"]
        table_html = _build_fwd_table(fwd_items_df, c, actuals_a=pkg["actuals_a"])

        # ── Serialise data into store for Excel downloads ─────────────────
        def _ser(df):
            return df.astype(str).to_dict("records") if not df.empty else []

        store_data = {
            "comp_name":             comp_name,
            "item":                  item,
            "period":                period,
            "actuals_q":             _ser(pkg["actuals_q"]),
            "actuals_a":             _ser(pkg["actuals_a"]),
            "surprise_q":            _ser(pkg["surprise_q"]),
            "consensus_fwd":         _ser(pkg["consensus_fwd"]),
            "revisions":             _ser(pkg["revisions"]),
            "recommendations":       _ser(pkg["recommendations"]),
            "forward_items":         _ser(pkg["forward_items"]),
            "price_target_hist":     _ser(pkg["price_target_hist"]),
            "price_reaction_prices": _ser(pkg["price_reaction_prices"]),
            "price_hist":            _ser(pkg["price_hist"]),
        }

        status = f"✅ {comp_name}  ·  {item}  ·  {'Quarterly' if period == 'quarterly' else 'Annual'}"
        return (fig_act, fig_fwd, fig_rev, fig_recs,
                fig_pt, fig_recs_hist,
                fig_price_react, fig_ntm_pe,
                "NTM P/E Time Series",
                "Implied NTM P/E = monthly price ÷ consensus NTM EPS.",
                table_html, header_strip,
                revision_scorecard,
                actuals_title, status, store_data)

    # ── Excel download callbacks ──────────────────────────────────────────────
    _dl_callbacks(app)

    # ── NTM panel dropdown — switches between NTM P/E and rolling rev % ───────
    @app.callback(
        Output("earn-ntm-pe-chart",       "figure",   allow_duplicate=True),
        Output("earn-ntm-panel-title",    "children", allow_duplicate=True),
        Output("earn-ntm-panel-subtitle", "children", allow_duplicate=True),
        Input("earn-ntm-view-dd",  "value"),
        State("earn-data-store",   "data"),
        State("theme-store",       "data"),
        prevent_initial_call=True,
    )
    def update_ntm_panel(view, store, theme_mode):
        c = get_theme(theme_mode or "dark")
        if not store:
            raise PreventUpdate

        _TITLES = {
            "ntm_pe":  ("NTM P/E Time Series",
                        "Implied NTM P/E = monthly price ÷ consensus NTM EPS."),
            "rev_4w":  ("4-Week Revision % (Rolling)",
                        "Rolling 4-week change in NTM consensus, one line per forward FY."),
            "rev_13w": ("13-Week Revision % (Rolling)",
                        "Rolling 13-week change in NTM consensus, one line per forward FY."),
            "rev_52w": ("52-Week Revision % (Rolling)",
                        "Rolling 52-week change in NTM consensus, one line per forward FY."),
        }
        title, subtitle = _TITLES.get(view, ("", ""))

        rev_rows = store.get("revisions", [])
        rev_df   = pd.DataFrame(rev_rows)
        if not rev_df.empty:
            for col in ["FE_MEAN", "FE_NUM_EST"]:
                if col in rev_df.columns:
                    rev_df[col] = pd.to_numeric(rev_df[col], errors="coerce")

        if view == "ntm_pe":
            ph_rows = store.get("price_hist", [])
            ph_df   = pd.DataFrame(ph_rows)
            if not ph_df.empty and "P_PRICE" in ph_df.columns:
                ph_df["P_PRICE"] = pd.to_numeric(ph_df["P_PRICE"], errors="coerce")
            fig = _build_ntm_pe_chart(ph_df, rev_df, c)
        else:
            weeks_map = {"rev_4w": 4, "rev_13w": 13, "rev_52w": 52}
            fig = _build_rolling_revision_chart(rev_df, weeks_map[view], c)

        return fig, title, subtitle


def _build_fwd_table(df, c, actuals_a=None):
    """Forward estimates table with derived EBITDA/EBIT margin % and YoY growth % rows."""
    if df.empty:
        return html.Div("No forward estimates available.",
                        style={"color": c["muted"], "fontSize": "0.82rem",
                               "fontFamily": FONT})

    df = df.copy()
    df["FE_FP_END"] = pd.to_datetime(df["FE_FP_END"], errors="coerce")
    df = df.dropna(subset=["FE_FP_END"])
    fy_dates = sorted(df["FE_FP_END"].unique())
    fy_labels = [f"FY {pd.Timestamp(d).year}" for d in fy_dates]

    ITEM_ORDER = ["EPS", "SALES", "EBITDA", "EBIT", "DPS", "CFPS"]
    items_present = [i for i in ITEM_ORDER if i in df["FE_ITEM"].values]

    th_s = {
        "padding": "0.3rem 0.7rem", "fontSize": "0.62rem", "fontWeight": "700",
        "textTransform": "uppercase", "letterSpacing": "0.05em",
        "borderBottom": f"2px solid {c['border']}", "fontFamily": FONT,
        "color": c["muted"], "whiteSpace": "nowrap", "textAlign": "right",
    }
    td_s = {
        "padding": "0.3rem 0.7rem", "fontSize": "0.75rem", "fontFamily": FONT,
        "color": c["text"], "borderBottom": f"1px solid {c['border']}",
        "whiteSpace": "nowrap", "textAlign": "right",
    }
    td_d = {**td_s, "color": c["muted"], "fontSize": "0.7rem",
            "borderBottom": f"1px dashed {c['border']}"}

    header = html.Thead(html.Tr([
        html.Th("Metric", style={**th_s, "textAlign": "left"}),
        *[html.Th(lbl, style=th_s) for lbl in fy_labels],
        html.Th("# Analysts", style=th_s),
    ]))

    rows = []
    fwd_means = {}   # {item: {fy_date: mean_float}}

    # ── Main metric rows ───────────────────────────────────────────────
    for it in items_present:
        sub = df[df["FE_ITEM"] == it]
        fwd_means[it] = {}
        cells = []
        num_est = "—"
        for fy in fy_dates:
            row_d = sub[sub["FE_FP_END"] == fy]
            if row_d.empty:
                cells.append(html.Td("—", style=td_s))
            else:
                r = row_d.iloc[0]
                if pd.notna(r.get("FE_MEAN")):
                    fwd_means[it][fy] = float(r["FE_MEAN"])
                mean_s = _fmt_val(r.get("FE_MEAN"), it)
                hi_s   = _fmt_val(r.get("FE_HIGH"), it)
                lo_s   = _fmt_val(r.get("FE_LOW"),  it)
                num_est = str(int(r["FE_NUM_EST"])) if pd.notna(r.get("FE_NUM_EST")) else "—"
                cells.append(html.Td([
                    html.Span(mean_s, style={"fontWeight": "700"}),
                    html.Br(),
                    html.Span(f"{lo_s} – {hi_s}",
                              style={"color": c["muted"], "fontSize": "0.62rem"}),
                ], style=td_s))
        rows.append(html.Tr([
            html.Td(it, style={**td_s, "textAlign": "left", "color": c["accent"],
                               "fontWeight": "700"}),
            *cells,
            html.Td(num_est, style={**td_s, "color": c["muted"]}),
        ]))

    # ── Derived: EBITDA Margin % and EBIT Margin % ─────────────────────
    for m_label, m_key in [("EBITDA Mgn %", "EBITDA"), ("EBIT Mgn %", "EBIT")]:
        if m_key not in fwd_means or "SALES" not in fwd_means:
            continue
        cells = []
        has_data = False
        for fy in fy_dates:
            n = fwd_means[m_key].get(fy)
            d = fwd_means["SALES"].get(fy)
            if n is not None and d is not None and d != 0:
                cells.append(html.Td(f"{n/d*100:.1f}%", style=td_d))
                has_data = True
            else:
                cells.append(html.Td("—", style=td_d))
        if has_data:
            rows.append(html.Tr([
                html.Td(m_label, style={**td_d, "textAlign": "left",
                                        "fontStyle": "italic"}),
                *cells,
                html.Td("", style=td_d),
            ]))

    # ── Derived: YoY growth % ─────────────────────────────────────────
    for yoy_label, yoy_item in [("EPS YoY %", "EPS"), ("Sales YoY %", "SALES")]:
        if yoy_item not in fwd_means:
            continue
        cells = []
        has_data = False
        for i, fy in enumerate(fy_dates):
            cur_v = fwd_means[yoy_item].get(fy)
            if cur_v is None:
                cells.append(html.Td("—", style=td_d))
                continue
            prior_v = None
            if i == 0:
                # Try last actual annual value
                if actuals_a is not None and not actuals_a.empty:
                    aa = actuals_a.copy()
                    aa["FE_FP_END"] = pd.to_datetime(aa["FE_FP_END"], errors="coerce")
                    prev = aa[aa["FE_FP_END"] < fy].sort_values("FE_FP_END", ascending=False)
                    if not prev.empty and pd.notna(prev.iloc[0]["ACTUAL_VALUE"]):
                        prior_v = float(prev.iloc[0]["ACTUAL_VALUE"])
            else:
                prior_v = fwd_means[yoy_item].get(fy_dates[i - 1])

            if prior_v is not None and prior_v != 0:
                pct = (cur_v / abs(prior_v) - 1) * 100
                col = "#00d26a" if pct >= 0 else "#ff3333"
                cells.append(html.Td(
                    html.Span(f"{'+' if pct>=0 else ''}{pct:.1f}%",
                              style={"color": col, "fontWeight": "700"}),
                    style=td_d,
                ))
                has_data = True
            else:
                cells.append(html.Td("—", style=td_d))

        if has_data:
            rows.append(html.Tr([
                html.Td(yoy_label, style={**td_d, "textAlign": "left",
                                          "fontStyle": "italic"}),
                *cells,
                html.Td("", style=td_d),
            ]))

    return html.Table([header, html.Tbody(rows)],
                      style={"width": "100%", "borderCollapse": "collapse"})


# ── Excel download helpers ────────────────────────────────────────────────────

def _store_to_excel(store, *sheet_keys):
    """Write one or more DataFrames (keyed by sheet_keys) to an in-memory Excel buffer."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for key, sheet_name in sheet_keys:
            rows = store.get(key, [])
            df = pd.DataFrame(rows)
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    buf.seek(0)
    return buf.getvalue()


def _dl_callbacks(app):
    comp_key = "comp_name"

    _DOWNLOADS = [
        ("earn-dl-actuals-btn",   "earn-dl-actuals",
         [("actuals_q", "Quarterly Actuals"), ("actuals_a", "Annual Actuals"),
          ("surprise_q", "Beat-Miss")],
         "actuals"),
        ("earn-dl-forward-btn",   "earn-dl-forward",
         [("consensus_fwd", "Forward Consensus")],
         "forward_consensus"),
        ("earn-dl-revisions-btn", "earn-dl-revisions",
         [("revisions", "Revision History")],
         "revision_history"),
        ("earn-dl-recs-btn",      "earn-dl-recs",
         [("recommendations", "Recommendations")],
         "recommendations"),
        ("earn-dl-pt-btn",        "earn-dl-pt",
         [("price_target_hist", "Price Target History")],
         "price_targets"),
        ("earn-dl-recs-hist-btn", "earn-dl-recs-hist",
         [("recommendations", "Recommendations")],
         "recommendation_history"),
        ("earn-dl-fwd-table-btn", "earn-dl-fwd-table",
         [("forward_items", "Forward Estimates")],
         "forward_estimates"),
        ("earn-dl-price-react-btn", "earn-dl-price-react",
         [("price_reaction_prices", "Price Reaction"), ("surprise_q", "Beat-Miss")],
         "price_reaction"),
    ]

    for btn_id, dl_id, sheets, suffix in _DOWNLOADS:
        # Capture loop variables in default args
        def _make_cb(_sheets, _suffix):
            @app.callback(
                Output(dl_id, "data"),
                Input(btn_id, "n_clicks"),
                State("earn-data-store", "data"),
                prevent_initial_call=True,
            )
            def _download(_, store, sheets=_sheets, suffix=_suffix):
                if not store:
                    raise PreventUpdate
                comp = (store.get(comp_key) or "data").replace(" ", "_")
                item = store.get("item", "")
                fname = f"{comp}_{item}_{suffix}.xlsx"
                data = _store_to_excel(store, *sheets)
                return dcc.send_bytes(data, fname)
        _make_cb(sheets, suffix)

