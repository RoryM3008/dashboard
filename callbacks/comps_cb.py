"""Callbacks — Comps Table page.

Builds a comparable-companies table for one or more preset peer groups
(plus optional custom tickers). Each group renders as its own block with
a group-name header row and a group-median summary row at the bottom.
"""

import re
import numpy as np
import pandas as pd
from dash import Input, Output, State, html, no_update

from theme import get_theme, FONT
from snowflake_data import _resolve_ids, _get_connection, SF_WAREHOUSE, fetch_comps_table
from pages.comps_page import PEER_GROUPS, DEFAULT_GROUPS


# ─────────────────────────────────────────────────────────────────────────────
# Column definitions
#   Each entry: (label, key in df, fmt, header-group)
# ─────────────────────────────────────────────────────────────────────────────
COLUMNS = [
    ("Company",        "NAME",            "name",      "Identity"),
    ("Mkt Cap (USD mn)", "MKT_CAP_USD_M", "intk",      "Size"),
    ("EV (USD mn)",      "EV_USD_M",      "intk",      "Size"),
    ("P/E LTM",        "PE_LTM",          "mult",      "P/E"),
    ("P/E 1BF",        "PE_FY1",          "mult",      "P/E"),
    ("P/E 2BF",        "PE_FY2",          "mult",      "P/E"),
    ("P/B LTM",        "PB_LTM",          "mult",      "P/B"),
    ("P/B 1BF",        "PB_FY1",          "mult",      "P/B"),
    ("P/B 2BF",        "PB_FY2",          "mult",      "P/B"),
    ("EV/EBITDA LTM",  "EV_EBITDA_LTM",   "mult",      "EV/EBITDA"),
    ("EV/EBITDA 1BF",  "EV_EBITDA_FY1",   "mult",      "EV/EBITDA"),
    ("EV/EBITDA 2BF",  "EV_EBITDA_FY2",   "mult",      "EV/EBITDA"),
    ("ROE LTM",        "ROE_LTM",         "pct1",      "ROE"),
    ("ROE 1BF",        "ROE_FY1",         "pct1",      "ROE"),
    ("ROE 2BF",        "ROE_FY2",         "pct1",      "ROE"),
    ("PEG FY1-2",      "PEG",             "mult",      "Growth"),
    ("EPS Gr FY1-2",   "EPS_GR_FY12",     "pct1",      "Growth"),
    ("OPM LTM",        "OPM_LTM",         "pct1",      "Margin"),
    ("OPM 1BF",        "OPM_FY1",         "pct1",      "Margin"),
    ("Div Yld LTM",    "DIV_YLD_LTM",     "pct1",      "Yield"),
    ("Div Yld 1BF",    "DIV_YLD_FY1",     "pct1",      "Yield"),
]

# Header band colour per metric group
HEADER_BAND = {
    "Identity":   "#1f1f1f",
    "Size":       "#16243a",
    "P/E":        "#1d2a16",
    "P/B":        "#1d2a16",
    "EV/EBITDA":  "#1d2a16",
    "ROE":        "#2a221a",
    "Growth":     "#2a1a2a",
    "Margin":     "#2a221a",
    "Yield":      "#1a2a2a",
}


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(val, kind):
    if val is None or (isinstance(val, float) and (pd.isna(val) or np.isinf(val))):
        return "n.a."
    try:
        v = float(val)
    except Exception:
        return str(val)
    if kind == "intk":      # integer with thousands sep
        return f"{v:,.0f}"
    if kind == "mult":      # ratio with x suffix
        return f"{v:.1f}x"
    if kind == "pct1":      # percent already in %
        return f"{v:.1f}%"
    if kind == "pct2":
        return f"{v:.2f}%"
    return f"{v:.2f}"


def _short_ticker(tkr):
    if not tkr:
        return ""
    return tkr.split("-")[0] if "-" in tkr else tkr


def _company_label(row):
    name = row.get("NAME")
    tkr  = row.get("TICKER")
    if name:
        return name
    return _short_ticker(tkr) or "—"


# ─────────────────────────────────────────────────────────────────────────────
# Table renderer
# ─────────────────────────────────────────────────────────────────────────────

def _build_group_table(df_group: pd.DataFrame, group_label: str, c: dict):
    """Render a comps table for a single peer group with median summary row."""
    if df_group.empty:
        return html.Div(
            f"No data for {group_label}.",
            style={"color": c["muted"], "fontFamily": FONT, "fontSize": "0.78rem",
                   "padding": "0.6rem"},
        )

    # ── Header rows: metric-group band on row 1, column label on row 2 ──
    # Build grouped header (colspan-based)
    header_groups = []
    last_group = None
    span = 0
    for _, _, _, g in COLUMNS:
        if last_group is None:
            last_group, span = g, 1
        elif g == last_group:
            span += 1
        else:
            header_groups.append((last_group, span))
            last_group, span = g, 1
    header_groups.append((last_group, span))

    band_cells = []
    for g, sp in header_groups:
        band_cells.append(html.Th(
            g, colSpan=sp,
            style={
                "backgroundColor": HEADER_BAND.get(g, "#1a1a1a"),
                "color": c["muted"], "fontFamily": FONT,
                "fontSize": "0.62rem", "fontWeight": "700",
                "textTransform": "uppercase", "letterSpacing": "0.05em",
                "padding": "0.25rem 0.55rem",
                "borderBottom": f"1px solid {c['border']}",
                "textAlign": "center",
            },
        ))

    col_cells = []
    for i, (label, _, _, g) in enumerate(COLUMNS):
        col_cells.append(html.Th(
            label,
            style={
                "color": c["accent"] if i == 0 else c["text"],
                "fontFamily": FONT, "fontSize": "0.68rem",
                "fontWeight": "700",
                "padding": "0.35rem 0.55rem",
                "borderBottom": f"1px solid {c['border']}",
                "textAlign": "left" if i == 0 else "right",
                "backgroundColor": "#0e0e0e",
                "whiteSpace": "nowrap",
            },
        ))

    # ── Body rows ───────────────────────────────────────────────────────
    body_rows = []
    for _, r in df_group.iterrows():
        tds = []
        for i, (label, key, kind, _) in enumerate(COLUMNS):
            if i == 0:
                txt = _company_label(r)
                style = {
                    "color": c["text"], "fontFamily": FONT,
                    "fontSize": "0.74rem", "fontWeight": "600",
                    "padding": "0.32rem 0.55rem",
                    "borderBottom": f"1px solid {c['border']}",
                    "textAlign": "left",
                    "whiteSpace": "nowrap",
                }
            else:
                val = r.get(key)
                txt = _fmt(val, kind)
                style = {
                    "color": c["muted"] if txt == "n.a." else c["text"],
                    "fontFamily": FONT, "fontSize": "0.74rem",
                    "padding": "0.32rem 0.55rem",
                    "borderBottom": f"1px solid {c['border']}",
                    "textAlign": "right",
                    "whiteSpace": "nowrap",
                }
            tds.append(html.Td(txt, style=style))
        body_rows.append(html.Tr(tds))

    # ── Group-median summary row ────────────────────────────────────────
    summary_tds = []
    for i, (label, key, kind, _) in enumerate(COLUMNS):
        if i == 0:
            txt = group_label
            style = {
                "color": c["accent"], "fontFamily": FONT,
                "fontSize": "0.74rem", "fontWeight": "800",
                "padding": "0.4rem 0.55rem",
                "borderTop": f"2px solid {c['accent']}",
                "borderBottom": f"1px solid {c['border']}",
                "backgroundColor": "#0c0c0c",
                "textAlign": "left", "whiteSpace": "nowrap",
            }
        else:
            try:
                series = pd.to_numeric(df_group[key], errors="coerce")
                # Use median for ratios/percents; sum for sizes
                if kind == "intk":
                    val = series.dropna().sum() if not series.dropna().empty else None
                else:
                    val = series.dropna().median() if not series.dropna().empty else None
            except Exception:
                val = None
            txt = _fmt(val, kind)
            style = {
                "color": c["text"], "fontFamily": FONT,
                "fontSize": "0.74rem", "fontWeight": "800",
                "padding": "0.4rem 0.55rem",
                "borderTop": f"2px solid {c['accent']}",
                "borderBottom": f"1px solid {c['border']}",
                "backgroundColor": "#0c0c0c",
                "textAlign": "right", "whiteSpace": "nowrap",
            }
        summary_tds.append(html.Td(txt, style=style))
    body_rows.append(html.Tr(summary_tds))

    table = html.Table([
        html.Thead([
            html.Tr(band_cells),
            html.Tr(col_cells),
        ]),
        html.Tbody(body_rows),
    ], style={
        "width": "100%", "borderCollapse": "collapse",
        "tableLayout": "auto",
    })

    return html.Div([
        html.Div(group_label, style={
            "color": c["accent"], "fontFamily": FONT,
            "fontSize": "0.8rem", "fontWeight": "800",
            "letterSpacing": "0.05em", "textTransform": "uppercase",
            "marginTop": "0.8rem", "marginBottom": "0.4rem",
        }),
        html.Div(table, style={"overflowX": "auto"}),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — resolve custom tickers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_tickers_to_fsym(tickers):
    """Resolve a list of FactSet TICKER-REGION strings to FSYM_IDs.

    Uses a single batch SQL query for speed + reliability.
    Falls back to one-by-one _resolve_ids if batch fails.
    """
    tickers = [(t or "").strip().upper() for t in tickers if (t or "").strip()]
    if not tickers:
        return {}

    # ── Attempt batch resolution (single query) ──────────────────────────
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(f"USE WAREHOUSE {SF_WAREHOUSE}")
        ph = ", ".join(f"'{t}'" for t in tickers)
        cur.execute(f"""
            SELECT tr.TICKER_REGION, tr.FSYM_ID
            FROM FACTSET.SYM_V1.SYM_TICKER_REGION tr
            JOIN FACTSET.SYM_V1.SYM_COVERAGE sc ON sc.FSYM_ID = tr.FSYM_ID
            WHERE tr.TICKER_REGION IN ({ph})
              AND sc.UNIVERSE_TYPE = 'EQ'
              AND sc.REGIONAL_FLAG = TRUE
        """)
        rows = cur.fetchall()
        out = {}
        for tr, fsym_id in rows:
            out[tr.upper()] = fsym_id
        # Return what was found
        if out:
            return out
    except Exception:
        pass

    # ── Fallback: one-by-one ─────────────────────────────────────────────
    out = {}
    for t in tickers:
        try:
            ids = _resolve_ids(t)
        except Exception:
            ids = None
        if ids and ids.get("fsym_id"):
            out[t] = ids["fsym_id"]
    return out


def _parse_custom_input(raw):
    if not raw:
        return []
    return [t.strip().upper() for t in re.split(r"[,;\s]+", raw) if t.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Register callbacks
# ─────────────────────────────────────────────────────────────────────────────

def register_callbacks(app):

    @app.callback(
        Output("comps-output", "children"),
        Output("comps-status", "children"),
        Input("comps-load-btn",     "n_clicks"),
        Input("comps-load-all-btn", "n_clicks"),
        State("comps-groups",        "value"),
        State("comps-custom-input",  "value"),
        State("theme-store",         "data"),
        State("datasource",          "data"),
        prevent_initial_call=True,
    )
    def render_comps(n_load, n_all, group_codes, custom_raw, theme, datasource):
        c = get_theme(theme or "dark")

        if datasource == "yf":
            return (
                html.Div("Comps Table requires Snowflake/FactSet data.",
                         style={"color": c["muted"], "fontFamily": FONT,
                                "fontSize": "0.85rem", "padding": "1.5rem"}),
                "⚠️ Offline mode — switch back to Snowflake.",
            )

        import dash
        ctx = dash.callback_context
        trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""

        # ── Build list of (group_label, [tickers]) ──────────────────────
        groups_to_show = []
        if trigger == "comps-load-all-btn":
            for code in DEFAULT_GROUPS:
                meta = PEER_GROUPS[code]
                groups_to_show.append((meta["label"], meta["tickers"]))
        else:
            for code in (group_codes or []):
                if code in PEER_GROUPS:
                    meta = PEER_GROUPS[code]
                    groups_to_show.append((meta["label"], meta["tickers"]))

        custom = _parse_custom_input(custom_raw or "")
        if custom:
            groups_to_show.append(("Custom Group", custom))

        if not groups_to_show:
            return (
                html.Div("Pick at least one peer group or add custom tickers.",
                         style={"color": c["muted"], "fontFamily": FONT,
                                "fontSize": "0.85rem", "padding": "1rem"}),
                "",
            )

        # ── Resolve all tickers → FSYM_IDs (batch query) ────────────────
        all_tickers = []
        for _, ts in groups_to_show:
            all_tickers.extend(ts)
        unique_tickers = sorted(set(all_tickers))

        try:
            resolved = _resolve_tickers_to_fsym(unique_tickers)
        except Exception as e:
            return (
                html.Div(f"Ticker resolution error: {e}",
                         style={"color": "#ff6b6b", "fontFamily": FONT,
                                "fontSize": "0.85rem", "padding": "1rem"}),
                f"❌ Resolution error: {e}",
            )

        if not resolved:
            return (
                html.Div([
                    html.Div("Could not resolve any tickers to FactSet IDs.",
                             style={"fontWeight": "700", "marginBottom": "0.4rem"}),
                    html.Div(f"Attempted: {', '.join(unique_tickers[:20])}…"
                             if len(unique_tickers) > 20
                             else f"Attempted: {', '.join(unique_tickers)}",
                             style={"fontSize": "0.75rem", "color": c["muted"]}),
                    html.Div("Check Snowflake connection (🔌 SF button) and ensure "
                             "you are on VPN / office network.",
                             style={"fontSize": "0.75rem", "color": c["muted"],
                                    "marginTop": "0.3rem"}),
                ], style={"color": "#ff6b6b", "fontFamily": FONT,
                          "fontSize": "0.85rem", "padding": "1rem"}),
                "❌ No tickers resolved. Check Snowflake connectivity.",
            )

        unresolved = [t for t in unique_tickers if t not in resolved]

        # ── Single batch query for all FSYM_IDs ─────────────────────────
        try:
            df_all = fetch_comps_table(list(resolved.values()))
        except Exception as e:
            return (
                html.Div(f"Error fetching data: {e}",
                         style={"color": "#ff6b6b", "fontFamily": FONT,
                                "fontSize": "0.85rem", "padding": "1rem"}),
                "❌ Snowflake error.",
            )

        if df_all is None or df_all.empty:
            return (
                html.Div("No data returned from FactSet for the given tickers.",
                         style={"color": c["muted"], "fontFamily": FONT,
                                "fontSize": "0.85rem", "padding": "1rem"}),
                "No rows returned.",
            )

        # FSYM_ID → ticker (preserve user order within group)
        fsym_to_ticker = {v: k for k, v in resolved.items()}

        # Build a per-group dataframe view
        blocks = []
        for group_label, ts in groups_to_show:
            ordered_fsyms = [resolved[t] for t in ts if t in resolved]
            if not ordered_fsyms:
                blocks.append(html.Div(
                    f"{group_label}: no tickers resolved.",
                    style={"color": c["muted"], "fontFamily": FONT,
                           "fontSize": "0.78rem", "marginTop": "0.6rem"},
                ))
                continue
            df_g = df_all[df_all["FSYM_ID"].isin(ordered_fsyms)].copy()
            # Preserve user-supplied order
            df_g["__order"] = df_g["FSYM_ID"].map(
                {f: i for i, f in enumerate(ordered_fsyms)}
            )
            df_g = df_g.sort_values("__order").drop(columns="__order")
            blocks.append(_build_group_table(df_g, group_label, c))

        status_bits = [f"✅ Loaded {len(resolved)} companies across {len(groups_to_show)} group(s)."]
        if unresolved:
            status_bits.append(f"⚠️ Unresolved: {', '.join(unresolved)}")
        status = "  ·  ".join(status_bits)

        return html.Div(blocks), status
