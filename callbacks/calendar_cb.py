"""Callbacks — Earnings Calendar page."""

import datetime
import pandas as pd
import dash
from dash import Input, Output, State, html, dcc, no_update
from dash.exceptions import PreventUpdate

from theme import get_theme, FONT
from snowflake_data import fetch_earnings_calendar


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_val(v, is_sales=False):
    """Format a consensus number nicely."""
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    if is_sales:
        if abs(v) >= 1_000:
            return f"{v/1_000:.1f}B"
        return f"{v:.0f}M"
    return f"{v:.2f}"


def _market_time_badge(timing, c):
    colour_map = {
        "Pre-Market":  "#3399ff",
        "After Close": "#ff9900",
        "Time TBC":    c["muted"],
    }
    colour = colour_map.get(timing, c["muted"])
    return html.Span(timing, style={
        "backgroundColor": colour + "22",
        "color": colour,
        "border": f"1px solid {colour}44",
        "borderRadius": "4px",
        "padding": "0.1rem 0.45rem",
        "fontSize": "0.62rem",
        "fontFamily": FONT,
        "fontWeight": "600",
        "whiteSpace": "nowrap",
    })


def _confirmed_badge(confirmed, c):
    if confirmed:
        return html.Span("Confirmed", style={
            "color": c["green"], "fontSize": "0.6rem",
            "fontFamily": FONT, "fontWeight": "600",
        })
    return html.Span("Est.", style={
        "color": c["muted"], "fontSize": "0.6rem",
        "fontFamily": FONT, "fontStyle": "italic",
    })


def _build_calendar_table(df, c):
    """Build the day-grouped calendar table as Dash HTML."""
    if df.empty:
        return html.Div("No earnings events found for this period.",
                        style={"color": c["muted"], "fontSize": "0.85rem",
                               "fontFamily": FONT, "padding": "2rem",
                               "textAlign": "center"})

    # Header row
    th_style = {
        "padding": "0.45rem 0.75rem",
        "fontFamily": FONT, "fontWeight": "700",
        "fontSize": "0.68rem", "color": c["subtext"],
        "borderBottom": f"2px solid {c['border']}",
        "textAlign": "left", "whiteSpace": "nowrap",
        "backgroundColor": c["panel"],
    }
    header = html.Tr([
        html.Th("Company",          style={**th_style, "minWidth": "180px"}),
        html.Th("Ticker",           style={**th_style, "minWidth": "80px"}),
        html.Th("Mkt Cap",          style={**th_style, "textAlign": "right", "minWidth": "80px"}),
        html.Th("Sector",           style={**th_style, "minWidth": "120px"}),
        html.Th("Industry",         style={**th_style, "minWidth": "120px"}),
        html.Th("Period",           style={**th_style, "minWidth": "80px"}),
        html.Th("Timing",           style={**th_style, "minWidth": "110px"}),
        html.Th("Date Status",      style={**th_style, "minWidth": "90px"}),
        html.Th("Cons. EPS",        style={**th_style, "textAlign": "right", "minWidth": "90px"}),
        html.Th("Cons. Sales",      style={**th_style, "textAlign": "right", "minWidth": "100px"}),
        html.Th("# Analysts",       style={**th_style, "textAlign": "right", "minWidth": "85px"}),
    ])

    td_base = {
        "padding": "0.38rem 0.75rem",
        "fontFamily": FONT,
        "fontSize": "0.78rem",
        "borderBottom": f"1px solid {c['border']}",
        "verticalAlign": "middle",
    }

    rows = []
    last_date = None

    for _, row in df.iterrows():
        ev_date = row["EVENT_DATE"]
        if hasattr(ev_date, "date"):
            ev_date_obj = ev_date.date()
        else:
            ev_date_obj = ev_date

        # Day separator header
        if ev_date_obj != last_date:
            last_date = ev_date_obj
            today = datetime.date.today()
            delta = (ev_date_obj - today).days
            if delta == 0:
                day_label = "Today"
                day_colour = c["accent"]
            elif delta == 1:
                day_label = "Tomorrow"
                day_colour = c["blue"]
            else:
                day_label = ev_date_obj.strftime("%A, %d %b %Y")
                day_colour = c["subtext"]

            rows.append(html.Tr([
                html.Td(
                    day_label,
                    colSpan=11,
                    style={
                        "padding": "0.6rem 0.75rem 0.25rem",
                        "fontFamily": FONT,
                        "fontWeight": "800",
                        "fontSize": "0.72rem",
                        "color": day_colour,
                        "borderTop": f"2px solid {c['border']}",
                        "backgroundColor": c["bg"],
                        "letterSpacing": "0.04em",
                        "textTransform": "uppercase",
                    }
                )
            ]))

        ccy = row.get("CURRENCY") or ""
        eps_str = _fmt_val(row.get("EPS_CONSENSUS"))
        if eps_str != "—" and ccy:
            eps_str = f"{eps_str} {ccy}"
        sales_str = _fmt_val(row.get("SALES_CONSENSUS"), is_sales=True)
        if sales_str != "—" and ccy:
            sales_str = f"{sales_str} {ccy}"

        num_est = row.get("EPS_NUM_EST")
        num_str = str(int(num_est)) if num_est and not pd.isna(num_est) else "—"

        period_str = ""
        if row.get("FISCAL_PERIOD") and row.get("FISCAL_YEAR"):
            period_str = f"Q{row['FISCAL_PERIOD']} {int(row['FISCAL_YEAR'])}"
        elif row.get("FISCAL_YEAR"):
            period_str = str(int(row["FISCAL_YEAR"]))

        # Market cap formatting
        mc = row.get("MKT_CAP_M")
        if mc and not pd.isna(mc):
            mc_val = float(mc)
            if mc_val >= 1_000:
                mc_str = f"${mc_val/1000:.1f}B"
            else:
                mc_str = f"${mc_val:.0f}M"
        else:
            mc_str = "—"

        sector_str = row.get("SECTOR") or "—"
        industry_str = row.get("INDUSTRY") or "—"

        rows.append(html.Tr([
            html.Td(row.get("COMPANY_NAME") or "—",
                    style={**td_base, "color": c["text"], "fontWeight": "600"}),
            html.Td(
                html.Span(row.get("TICKER") or "—",
                          style={"color": c["accent"], "fontWeight": "700",
                                 "cursor": "pointer"},
                          className="clickable-ticker",
                          **{"data-ticker": f"{row.get('TICKER_REGION', '')}"}),
                style=td_base
            ),
            html.Td(mc_str, style={**td_base, "textAlign": "right",
                                   "fontFamily": "'Courier New', monospace",
                                   "color": c["subtext"]}),
            html.Td(sector_str, style={**td_base, "color": c["subtext"],
                                       "fontSize": "0.72rem"}),
            html.Td(industry_str, style={**td_base, "color": c["subtext"],
                                         "fontSize": "0.72rem"}),
            html.Td(period_str, style={**td_base, "color": c["subtext"]}),
            html.Td(_market_time_badge(row.get("TIMING", "Time TBC"), c), style=td_base),
            html.Td(_confirmed_badge(row.get("CONFIRMED", False), c), style=td_base),
            html.Td(eps_str,  style={**td_base, "textAlign": "right",
                                     "fontFamily": "'Courier New', monospace",
                                     "color": c["text"]}),
            html.Td(sales_str, style={**td_base, "textAlign": "right",
                                      "fontFamily": "'Courier New', monospace",
                                      "color": c["text"]}),
            html.Td(num_str,  style={**td_base, "textAlign": "right",
                                     "color": c["subtext"]}),
        ], style={"transition": "background 0.15s"},
           className="hover-row"))

    return html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse", "tableLayout": "auto"}
    )


def _build_summary_strip(df, window, c):
    """KPI chip strip above the table."""
    if df.empty:
        return html.Div()

    total = len(df)
    confirmed = int(df["CONFIRMED"].sum()) if "CONFIRMED" in df.columns else 0
    today = datetime.date.today()
    today_count = int((df["EVENT_DATE"].dt.date == today).sum())

    regions = {}
    if "TICKER_REGION" in df.columns:
        for tr in df["TICKER_REGION"].dropna():
            region = tr.split("-")[1] if "-" in tr else "??"
            regions[region] = regions.get(region, 0) + 1
    top_regions = sorted(regions.items(), key=lambda x: -x[1])[:4]

    def _chip(label, value, colour=None):
        col = colour or c["accent"]
        return html.Div([
            html.Div(str(value), style={
                "fontSize": "1.15rem", "fontWeight": "800",
                "color": col, "fontFamily": FONT, "lineHeight": "1",
            }),
            html.Div(label, style={
                "fontSize": "0.6rem", "color": c["subtext"],
                "fontFamily": FONT, "marginTop": "0.15rem",
                "textTransform": "uppercase", "letterSpacing": "0.04em",
            }),
        ], style={
            "backgroundColor": c["panel"],
            "border": f"1px solid {c['border']}",
            "borderRadius": "8px", "padding": "0.5rem 1rem",
            "minWidth": "80px", "textAlign": "center",
        })

    chips = [
        _chip("Reporting", total),
        _chip("Today", today_count, c["green"] if today_count else c["muted"]),
        _chip("Confirmed", confirmed, c["blue"]),
        _chip("Est. Dates", total - confirmed, c["muted"]),
    ]
    for region, cnt in top_regions:
        chips.append(_chip(region, cnt))

    return html.Div(chips, style={
        "display": "flex", "gap": "0.5rem",
        "flexWrap": "wrap", "marginTop": "0.5rem",
    })


# ── Register Callbacks ───────────────────────────────────────────────────────

def register_callbacks(app):

    # ── Market cap toggle ────────────────────────────────────────────────────
    @app.callback(
        Output("cal-mktcap-store",  "data"),
        Output("cal-mc-all",   "style"),
        Output("cal-mc-mega",  "style"),
        Output("cal-mc-large", "style"),
        Output("cal-mc-mid",   "style"),
        Output("cal-mc-small", "style"),
        Input("cal-mc-all",   "n_clicks"),
        Input("cal-mc-mega",  "n_clicks"),
        Input("cal-mc-large", "n_clicks"),
        Input("cal-mc-mid",   "n_clicks"),
        Input("cal-mc-small", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def set_mktcap(n_all, n_mega, n_large, n_mid, n_small, theme_mode):
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "cal-mc-all"
        mapping = {"cal-mc-all": "ALL", "cal-mc-mega": "MEGA",
                   "cal-mc-large": "LARGE", "cal-mc-mid": "MID", "cal-mc-small": "SMALL"}
        val = mapping.get(triggered, "ALL")
        def _s(active):
            return {
                "backgroundColor": c["accent"] if active else c["panel"],
                "color": "#000" if active else c["text"],
                "border": f"1px solid {c['border']}",
                "borderRadius": "6px", "padding": "0.4rem 0.85rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.75rem", "cursor": "pointer",
            }
        return (val, _s(val=="ALL"), _s(val=="MEGA"),
                _s(val=="LARGE"), _s(val=="MID"), _s(val=="SMALL"))

    # ── Sector dropdown — populated from loaded data ──────────────────────────
    @app.callback(
        Output("cal-sector-dd", "options"),
        Input("cal-raw-store", "data"),
        prevent_initial_call=True,
    )
    def populate_sectors(store_data):
        if not store_data:
            return []
        df = pd.DataFrame(store_data)
        if "SECTOR" not in df.columns:
            return []
        sectors = sorted(df["SECTOR"].dropna().unique().tolist())
        return [{"label": s, "value": s} for s in sectors]

    # ── Industry dropdown — populated from loaded data ────────────────────────
    @app.callback(
        Output("cal-industry-dd", "options"),
        Input("cal-raw-store", "data"),
        prevent_initial_call=True,
    )
    def populate_industries(store_data):
        if not store_data:
            return []
        df = pd.DataFrame(store_data)
        if "INDUSTRY" not in df.columns:
            return []
        industries = sorted(df["INDUSTRY"].dropna().unique().tolist())
        return [{"label": s, "value": s} for s in industries]

    # ── Window toggle buttons ────────────────────────────────────────────────
    @app.callback(
        Output("cal-window-store", "data"),
        Output("cal-w7",  "style"),
        Output("cal-w14", "style"),
        Output("cal-w30", "style"),
        Input("cal-w7",  "n_clicks"),
        Input("cal-w14", "n_clicks"),
        Input("cal-w30", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def set_window(n7, n14, n30, theme_mode):
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "cal-w14"
        mapping = {"cal-w7": 7, "cal-w14": 14, "cal-w30": 30}
        days = mapping.get(triggered, 14)

        def _s(active):
            return {
                "backgroundColor": c["accent"] if active else c["panel"],
                "color": "#000" if active else c["text"],
                "border": f"1px solid {c['border']}",
                "borderRadius": "6px", "padding": "0.4rem 0.85rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.75rem", "cursor": "pointer",
            }
        return days, _s(days == 7), _s(days == 14), _s(days == 30)

    # ── Region toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("cal-region-store", "data"),
        Output("cal-r-all", "style"),
        Output("cal-r-us",  "style"),
        Output("cal-r-eur", "style"),
        Output("cal-r-gb",  "style"),
        Input("cal-r-all", "n_clicks"),
        Input("cal-r-us",  "n_clicks"),
        Input("cal-r-eur", "n_clicks"),
        Input("cal-r-gb",  "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def set_region(n_all, n_us, n_eur, n_gb, theme_mode):
        c = get_theme(theme_mode or "dark")
        ctx = dash.callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "cal-r-all"
        mapping = {"cal-r-all": "ALL", "cal-r-us": "US", "cal-r-eur": "EUR", "cal-r-gb": "GB"}
        region = mapping.get(triggered, "ALL")

        def _s(active):
            return {
                "backgroundColor": c["accent"] if active else c["panel"],
                "color": "#000" if active else c["text"],
                "border": f"1px solid {c['border']}",
                "borderRadius": "6px", "padding": "0.4rem 0.85rem",
                "fontFamily": FONT, "fontWeight": "700",
                "fontSize": "0.75rem", "cursor": "pointer",
            }
        return (region,
                _s(region == "ALL"), _s(region == "US"),
                _s(region == "EUR"), _s(region == "GB"))

    # ── Main load + filter ───────────────────────────────────────────────────
    @app.callback(
        Output("cal-table-content",  "children"),
        Output("cal-summary-strip",  "children"),
        Output("cal-status",         "children"),
        Output("cal-data-store",     "data"),
        Output("cal-raw-store",      "data"),
        Input("cal-load-btn",        "n_clicks"),
        Input("cal-window-store",    "data"),
        Input("cal-region-store",    "data"),
        Input("cal-mktcap-store",    "data"),
        Input("cal-sector-dd",       "value"),
        Input("cal-industry-dd",     "value"),
        State("datasource",          "data"),
        State("theme-store",         "data"),
        prevent_initial_call=True,
    )
    def load_calendar(n_clicks, days, region, mktcap, sectors, industries, datasource, theme_mode):
        c = get_theme(theme_mode or "dark")

        if datasource == "yf":
            msg = html.Div("Earnings Calendar requires a Snowflake connection.",
                           style={"color": "#ff8c00", "fontSize": "0.85rem",
                                  "fontFamily": FONT, "padding": "2rem",
                                  "textAlign": "center"})
            return msg, html.Div(), "Offline mode", {}, {}

        try:
            df = fetch_earnings_calendar(days_ahead=days or 14, region_filter=region or "ALL")
        except Exception as e:
            err = html.Div(f"Error loading calendar: {e}",
                           style={"color": "#ff3333", "fontSize": "0.82rem",
                                  "fontFamily": FONT, "padding": "2rem"})
            return err, html.Div(), f"Error: {e}", {}, {}

        # Serialise raw (unfiltered) data for dropdown population
        raw_data = df.to_dict("records") if not df.empty else []
        for rec in raw_data:
            for k, v in rec.items():
                if hasattr(v, "isoformat"):
                    rec[k] = str(v)
                elif v is not None and not isinstance(v, (str, int, float, bool)):
                    rec[k] = str(v)

        # ── Apply market cap filter ───────────────────────────────────────
        if mktcap and mktcap != "ALL" and "MKT_CAP_M" in df.columns:
            mktcap_ranges = {
                "MEGA":  (100_000, None),
                "LARGE": (10_000,  100_000),
                "MID":   (2_000,   10_000),
                "SMALL": (None,    2_000),
            }
            lo, hi = mktcap_ranges.get(mktcap, (None, None))
            mask = df["MKT_CAP_M"].notna()
            if lo is not None:
                mask &= df["MKT_CAP_M"] >= lo
            if hi is not None:
                mask &= df["MKT_CAP_M"] < hi
            df = df[mask]

        # ── Apply sector filter ───────────────────────────────────────────
        if sectors and "SECTOR" in df.columns:
            df = df[df["SECTOR"].isin(sectors)]

        # ── Apply industry filter ─────────────────────────────────────────
        if industries and "INDUSTRY" in df.columns:
            df = df[df["INDUSTRY"].isin(industries)]

        table = _build_calendar_table(df, c)
        strip = _build_summary_strip(df, days, c)

        now = datetime.datetime.now().strftime("%d %b %Y %H:%M")
        status = f"{len(df)} events · Updated {now}"

        # Serialise filtered data for download
        store_data = df.to_dict("records") if not df.empty else []
        for rec in store_data:
            for k, v in rec.items():
                if hasattr(v, "isoformat"):
                    rec[k] = str(v)
                elif v is not None and not isinstance(v, (str, int, float, bool)):
                    rec[k] = str(v)

        return table, strip, status, store_data, raw_data

    # ── Download ──────────────────────────────────────────────────────────────
    @app.callback(
        Output("cal-dl", "data"),
        Input("cal-dl-btn", "n_clicks"),
        State("cal-data-store", "data"),
        prevent_initial_call=True,
    )
    def download_calendar(n, store_data):
        if not store_data:
            raise PreventUpdate
        df = pd.DataFrame(store_data)
        import io
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Earnings Calendar")
        buf.seek(0)
        return dcc.send_bytes(buf.read(), "earnings_calendar.xlsx")
