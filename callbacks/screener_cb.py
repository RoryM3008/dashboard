"""Callbacks — Stock Screener: run screen + CSV download."""

import base64
import datetime
import io
import re

import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State, ctx

from theme import FONT, get_theme
from data import parse_tickers, run_screener


def _is_blank(value):
    if value is None:
        return True
    txt = str(value).strip()
    return txt == "" or txt.lower() in {"nan", "none", "nat"}


def _clean_header_piece(value):
    if _is_blank(value):
        return ""
    cleaned = re.sub(r"\s+", " ", str(value).strip())
    if cleaned.lower().startswith("unnamed"):
        return ""
    return cleaned


def _looks_like_year_piece(value):
    if _is_blank(value):
        return False
    text = str(value).strip().upper()
    return bool(re.match(r"^(19|20)\d{2}$", text) or re.match(r"^(FY|CY)\s*\d{2,4}$", text))


def _dedupe_columns(columns):
    seen = {}
    out = []
    for i, col in enumerate(columns):
        base = col or f"Column {i + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        out.append(base if count == 0 else f"{base}_{count + 1}")
    return out


def _normalize_uploaded_dataframe(raw_df):
    raw_df = raw_df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if raw_df.empty:
        return pd.DataFrame()

    raw_df = raw_df.reset_index(drop=True)
    if len(raw_df) == 1:
        headers = [_clean_header_piece(v) for v in raw_df.iloc[0].tolist()]
        return pd.DataFrame(columns=_dedupe_columns(headers))

    top = raw_df.iloc[0].ffill()
    bottom = raw_df.iloc[1]

    top_labels = [_clean_header_piece(v) for v in top.tolist()]
    bottom_labels = [_clean_header_piece(v) for v in bottom.tolist()]

    top_non_empty = sum(1 for x in top_labels if x)
    bottom_non_empty = sum(1 for x in bottom_labels if x)
    year_hits = sum(1 for x in bottom.tolist() if _looks_like_year_piece(x))
    top_values = [x for x in top_labels if x]
    has_grouped_top = len(top_values) > len(set(top_values))

    use_two_row_header = bottom_non_empty >= 3 and (year_hits >= 2 or has_grouped_top)

    if use_two_row_header:
        cols = []
        for t, b in zip(top_labels, bottom_labels):
            if b and t and b.lower() != t.lower():
                cols.append(f"{t} {b}".strip())
            else:
                cols.append((b or t).strip())
        data = raw_df.iloc[2:].copy()
    else:
        cols = top_labels
        data = raw_df.iloc[1:].copy()

    cols = _dedupe_columns(cols)
    data.columns = cols
    data = data.dropna(axis=0, how="all").reset_index(drop=True)

    for col in data.columns:
        if data[col].dtype == object:
            data[col] = data[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

        non_null = data[col].notna().sum()
        if non_null == 0:
            continue

        numeric_candidate = pd.to_numeric(
            data[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False),
            errors="coerce",
        )
        if numeric_candidate.notna().sum() >= max(3, int(non_null * 0.7)):
            data[col] = numeric_candidate

    return data


def _parse_uploaded_screener(contents, filename):
    _, content_string = contents.split(",", 1)
    raw_bytes = base64.b64decode(content_string)
    lower_name = (filename or "").lower()

    if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        raw_df = pd.read_excel(io.BytesIO(raw_bytes), header=None)
    elif lower_name.endswith(".csv") or not lower_name:
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = raw_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                text = None
        if text is None:
            raise ValueError("Could not decode CSV. Try UTF-8 or Latin-1 encoding.")
        raw_df = pd.read_csv(io.StringIO(text), header=None)
    else:
        raise ValueError("Unsupported file type. Upload CSV or XLSX.")

    return _normalize_uploaded_dataframe(raw_df)


def _render_uploaded_table(df, c):
    columns = []
    for col in df.columns:
        col_type = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else "text"
        columns.append({"name": col, "id": col, "type": col_type})

    def _group_key(col_name):
        # Normalize names like "ReturnonEquity(%) 2025(Cal.)" into a metric group key.
        clean = re.sub(r"\s+", " ", str(col_name)).strip()
        clean = re.sub(r"\(Cal\.\)$", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"\b(FY|CY)?\s*(19|20)\d{2}$", "", clean, flags=re.IGNORECASE).strip()
        return clean

    # Count how many columns share each group key
    group_counts: dict = {}
    for col in df.columns:
        key = _group_key(col)
        group_counts[key] = group_counts.get(key, 0) + 1

    # Build ordered list of multi-column groups by first appearance
    seen_multi_groups: list = []
    for col in df.columns:
        key = _group_key(col)
        if group_counts[key] >= 2 and key not in seen_multi_groups:
            seen_multi_groups.append(key)

    dark_mode = str(c.get("bg", "")).lower() in {"#000", "#000000"}
    if dark_mode:
        neutral = {"header": "#2d2d2d", "cell": "#222222"}
        palette = [
            {"header": "#1e3a52", "cell": "#172d40"},  # blue
            {"header": "#1a4a30", "cell": "#123822"},  # green
            {"header": "#52321a", "cell": "#3d2512"},  # orange
            {"header": "#3d2b52", "cell": "#2e2040"},  # purple
            {"header": "#4a2a2a", "cell": "#381e1e"},  # red/maroon
            {"header": "#2a3d4a", "cell": "#1e3038"},  # teal
        ]
    else:
        neutral = {"header": "#e8eaed", "cell": "#f5f6f8"}
        palette = [
            {"header": "#c8dff7", "cell": "#e4f0fc"},  # blue
            {"header": "#c2ecd4", "cell": "#ddf5e8"},  # green
            {"header": "#fcd8b0", "cell": "#feecd8"},  # orange
            {"header": "#ddd0f7", "cell": "#eee8fc"},  # purple
            {"header": "#f7c8c8", "cell": "#fce2e2"},  # red/rose
            {"header": "#b8eaf0", "cell": "#d8f5f8"},  # teal
        ]

    group_color_map = {key: palette[i % len(palette)] for i, key in enumerate(seen_multi_groups)}

    # Build per-column styling — applies to both header and data cells
    cell_conditional = []
    for col in df.columns:
        key = _group_key(col)
        colors = group_color_map.get(key, neutral)
        cell_conditional.append({
            "if": {"column_id": col},
            "backgroundColor": colors["cell"],
            "color": c["text"],
        })

    # Separate header colours (slightly darker than cells)
    header_conditional = []
    for col in df.columns:
        key = _group_key(col)
        colors = group_color_map.get(key, neutral)
        header_conditional.append({
            "if": {"column_id": col},
            "backgroundColor": colors["header"],
            "color": c["text"],
        })

    # Debug: print group assignments so we can verify
    for col in df.columns:
        key = _group_key(col)
        grp = "GROUPED" if key in group_color_map else "SINGULAR"
        print(f"  [{grp}] '{col}' -> group key: '{key}'")

    return dash_table.DataTable(
        id="screener-upload-table",
        columns=columns,
        data=df.where(df.notna(), None).to_dict("records"),
        sort_action="native",
        filter_action="native",
        page_action="none",
        style_table={"overflowX": "auto", "overflowY": "auto",
                     "maxHeight": "calc(100vh - 220px)"},
        style_header={
            "padding": "0.38rem 0.6rem",
            "fontSize": "0.62rem",
            "textTransform": "uppercase",
            "letterSpacing": "0.06em",
            "fontWeight": "700",
            "whiteSpace": "nowrap",
            "borderBottom": "2px solid " + c["border"],
            "fontFamily": FONT,
            "position": "sticky",
            "top": "0",
            "zIndex": "1",
        },
        style_header_conditional=header_conditional,
        style_cell={
            "padding": "0.4rem 0.6rem",
            "borderBottom": "1px solid " + c["border"],
            "fontSize": "0.78rem",
            "fontFamily": FONT,
            "textAlign": "left",
            "whiteSpace": "nowrap",
            "minWidth": "80px",
        },
        style_data_conditional=cell_conditional,
        style_filter={"backgroundColor": c["bg"], "color": c["text"], "border": "none"},
        css=[{"selector": ".dash-header", "rule": "position: sticky; top: 0; z-index: 1;"}],
    )


def register_callbacks(app):

    @app.callback(
        Output("screener-results",    "children"),
        Output("screener-status",     "children"),
        Output("screener-data-store", "data"),
        Input("screener-run",  "n_clicks"),
        Input("screener-raw-upload", "contents"),
        State("screener-extra",    "value"),
        State("screener-raw-upload", "filename"),
        State("f-pe-max",          "value"),
        State("f-ev-max",          "value"),
        State("f-margin-min",      "value"),
        State("f-revgrowth-min",   "value"),
        State("f-div-min",         "value"),
        State("f-de-max",          "value"),
        State("f-sector",          "value"),
        State("theme-store",       "data"),
        prevent_initial_call=True,
    )
    def run_screen(n, upload_contents, extra_raw, upload_filename,
                   pe_max, ev_max, margin_min, revgrowth_min, div_min, de_max,
                   sector, theme_mode):
        c = get_theme(theme_mode or "dark")

        if ctx.triggered_id == "screener-raw-upload":
            if not upload_contents:
                return html.Div(), "", None
            try:
                uploaded_df = _parse_uploaded_screener(upload_contents, upload_filename)
            except Exception as exc:
                return html.Div(), f"Upload failed: {exc}", None

            if uploaded_df.empty:
                return html.Div("Uploaded file has no usable rows.",
                                style={"color": c["muted"], "fontFamily": FONT}), "", None

            table = _render_uploaded_table(uploaded_df, c)
            status = (
                f"Loaded {len(uploaded_df)} row{'s' if len(uploaded_df) != 1 else ''} "
                f"from {upload_filename or 'uploaded file'} · sortable + filterable"
            )
            store_data = uploaded_df.to_json(date_format="iso", orient="split")
            return table, status, store_data

        if not n:
            return html.Div(), "", None
        extra = parse_tickers(extra_raw) if extra_raw else []
        df    = run_screener(extra)
        if df.empty:
            return html.Div("No data returned.", style={"color": c["muted"], "fontFamily": FONT}), "", None

        if sector and sector != "All":
            df = df[df["Sector"] == sector]
        if pe_max is not None:
            df = df[df["P/E"].isna() | (df["P/E"] <= float(pe_max))]
        if ev_max is not None:
            df = df[df["EV/EBITDA"].isna() | (df["EV/EBITDA"] <= float(ev_max))]
        if margin_min is not None:
            df = df[df["Profit Margin Raw"].isna() | (df["Profit Margin Raw"] >= float(margin_min)/100)]
        if revgrowth_min is not None:
            df = df[df["Rev Growth Raw"].isna() | (df["Rev Growth Raw"] >= float(revgrowth_min)/100)]
        if div_min is not None:
            df = df[df["Div Yield Raw"].isna() | (df["Div Yield Raw"] >= float(div_min)/100)]
        if de_max is not None:
            df = df[df["Debt/Equity"].isna() | (df["Debt/Equity"] <= float(de_max))]

        if df.empty:
            return html.Div("No stocks matched your filters.", style={"color": c["muted"], "fontFamily": FONT}), "0 results", None

        df = df.sort_values("Mkt Cap Raw", ascending=False).reset_index(drop=True)
        status = f"{len(df)} stock{'s' if len(df)!=1 else ''} matched \u00b7 sorted by Market Cap"
        display_cols = ["Ticker","Name","Sector","Price","Mkt Cap","P/E","EV/EBITDA",
                        "Rev Growth","Profit Margin","Div Yield","52w Chg %","Debt/Equity","Day Chg %"]

        th_s = {
            "padding": "0.38rem 0.6rem", "fontSize": "0.62rem", "textTransform": "uppercase",
            "letterSpacing": "0.06em", "fontWeight": "700", "whiteSpace": "nowrap",
            "borderBottom": "2px solid " + c["border"], "fontFamily": FONT, "color": c["muted"],
        }
        header = html.Thead(html.Tr(
            [html.Th(col, style={**th_s, "textAlign": "right" if i > 2 else "left"})
             for i, col in enumerate(display_cols)]
        ))

        def cell_color(col, val):
            if col in ("Day Chg %", "52w Chg %", "Rev Growth"):
                try:
                    nv = float(str(val).replace("%","").replace("+",""))
                    return c["green"] if nv > 0 else (c["red"] if nv < 0 else c["subtext"])
                except Exception:
                    return c["subtext"]
            if col == "Profit Margin":
                try:
                    nv = float(str(val).replace("%",""))
                    return c["green"] if nv >= 15 else (c["accent"] if nv >= 5 else c["red"])
                except Exception:
                    return c["subtext"]
            return c["text"]

        body_rows = []
        for _, row in df.iterrows():
            cells = []
            for i, col in enumerate(display_cols):
                val = row.get(col, "\u2014")
                val = "\u2014" if (val is None or (isinstance(val, float) and pd.isna(val))) else val
                is_right = i > 2
                color = cell_color(col, val) if i > 2 else (c["accent"] if col == "Ticker" else c["text"])
                fw = "700" if col == "Ticker" else ("600" if i > 2 else "400")
                cells.append(html.Td(str(val), style={
                    "color": color, "fontWeight": fw,
                    "padding": "0.4rem 0.6rem",
                    "borderBottom": "1px solid " + c["border"],
                    "fontSize": "0.78rem", "fontFamily": FONT,
                    "textAlign": "right" if is_right else "left",
                    "whiteSpace": "nowrap",
                }))
            body_rows.append(html.Tr(cells))

        table = html.Div(
            html.Table([header, html.Tbody(body_rows)],
                       style={"width": "100%", "borderCollapse": "collapse"}),
            style={"overflowX": "auto", "maxHeight": "520px", "overflowY": "auto"},
        )
        csv_df = df[display_cols].copy()
        store_data = csv_df.to_json(date_format="iso", orient="split")
        return table, status, store_data

    @app.callback(
        Output("screener-download", "data"),
        Input("screener-download-btn", "n_clicks"),
        State("screener-data-store",   "data"),
        prevent_initial_call=True,
    )
    def download_csv(n, store_data):
        if not store_data:
            return None
        df  = pd.read_json(store_data, orient="split")
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return dcc.send_data_frame(df.to_csv, f"screener_{now}.csv", index=False)
