"""
Data helpers — every function that fetches, transforms, or renders market data.
No Dash app reference here; pure functions that return DataFrames or Dash components.
"""

import datetime
import re

import feedparser
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from dash import dcc, html

from theme import (
    C, FONT, LBL, PANEL,
    INDICES, SCREENER_UNIVERSE,
)

# ─────────────────────────────────────────────────────────────────────────────
# Ticker parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_tickers(raw):
    if not raw:
        return []
    return [t for t in re.split(r"[\s,;]+", raw.upper().strip()) if t]


# ─────────────────────────────────────────────────────────────────────────────
# Market data fetchers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_earnings(tickers):
    rows = []
    today  = datetime.date.today()
    cutoff = today + datetime.timedelta(days=30)
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
            if ts:
                dt = datetime.date.fromtimestamp(ts)
                if today <= dt <= cutoff:
                    rows.append({"Ticker": ticker,
                                 "Earnings Date": dt.strftime("%d %b %Y"),
                                 "Days Away": (dt - today).days,
                                 "_date": dt})
        except Exception:
            pass
    if not rows:
        return pd.DataFrame(columns=["Ticker", "Earnings Date", "Days Away"])
    df = pd.DataFrame(rows).sort_values("_date")
    return df.drop(columns=["_date"]).reset_index(drop=True)


def fetch_prices(tickers):
    rows = []
    for ticker in tickers:
        try:
            fi    = yf.Ticker(ticker).fast_info
            price = round(fi.last_price, 2)
            prev  = round(fi.previous_close, 2)
            chg   = round(price - prev, 2)
            pct   = round((chg / prev) * 100, 2) if prev else 0
            mc    = fi.market_cap
            cap   = (f"${mc/1e9:.1f}B" if mc and mc >= 1e9
                     else f"${mc/1e6:.1f}M" if mc else "—")
            rows.append({"Ticker": ticker,
                         "Price":   f"${price:,.2f}",
                         "Change":  f"{'+' if chg>=0 else ''}{chg:.2f}",
                         "Chg %":   f"{'+' if pct>=0 else ''}{pct:.2f}%",
                         "Mkt Cap": cap,
                         "_chg":    chg})
        except Exception:
            rows.append({"Ticker": ticker, "Price": "—", "Change": "—",
                         "Chg %": "—", "Mkt Cap": "—", "_chg": 0})
    return pd.DataFrame(rows)


def fetch_index_data():
    results = []
    for name, sym in INDICES.items():
        try:
            fi  = yf.Ticker(sym).fast_info
            p   = fi.last_price
            prv = fi.previous_close
            chg = p - prv
            pct = (chg / prv) * 100 if prv else 0
            results.append({"name": name, "price": p, "chg": chg, "pct": pct})
        except Exception:
            results.append({"name": name, "price": None, "chg": 0, "pct": 0})
    return results


def fetch_news(tickers, max_per=3):
    articles = []
    for ticker in tickers:
        url = (f"https://feeds.finance.yahoo.com/rss/2.0/headline"
               f"?s={ticker}&region=US&lang=en-US")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per]:
                articles.append({"ticker":    ticker,
                                  "title":     entry.get("title", ""),
                                  "link":      entry.get("link", "#"),
                                  "published": entry.get("published", "")})
        except Exception:
            pass
    return articles


# ─────────────────────────────────────────────────────────────────────────────
# Screener
# ─────────────────────────────────────────────────────────────────────────────

def run_screener(extra_tickers=None):
    universe = list(SCREENER_UNIVERSE)
    if extra_tickers:
        for t in extra_tickers:
            if t not in universe:
                universe.append(t)

    def fmt_money(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        return f"${v/1e9:.2f}B" if v >= 1e9 else (f"${v/1e6:.1f}M" if v >= 1e6 else f"${v:,.0f}")

    def fmt_pct(v, signed=True):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        sign = "+" if signed and float(v) > 0 else ""
        return f"{sign}{float(v) * 100:.2f}%"

    rows = []
    for ticker in universe:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            fi = t.fast_info

            price = getattr(fi, "last_price", None)
            prev = getattr(fi, "previous_close", None)
            day_pct = ((price - prev) / prev) if (price is not None and prev) else None

            mkt_cap = info.get("marketCap") or getattr(fi, "market_cap", None)
            pe = info.get("trailingPE")
            ev_ebitda = info.get("enterpriseToEbitda")
            rev_growth = info.get("revenueGrowth")
            profit_margin = info.get("profitMargins")
            div_yield = info.get("dividendYield")
            debt_equity = info.get("debtToEquity")
            chg_52w = info.get("52WeekChange")

            rows.append({
                "Ticker": ticker,
                "Name": info.get("shortName") or info.get("longName") or ticker,
                "Sector": info.get("sector") or "Unknown",
                "Price": f"${price:,.2f}" if price is not None else "—",
                "Mkt Cap": fmt_money(mkt_cap),
                "P/E": round(float(pe), 2) if pe is not None else None,
                "EV/EBITDA": round(float(ev_ebitda), 2) if ev_ebitda is not None else None,
                "Rev Growth": fmt_pct(rev_growth, signed=True),
                "Profit Margin": fmt_pct(profit_margin, signed=False),
                "Div Yield": fmt_pct(div_yield, signed=False),
                "52w Chg %": fmt_pct(chg_52w, signed=True),
                "Debt/Equity": round(float(debt_equity), 2) if debt_equity is not None else None,
                "Day Chg %": fmt_pct(day_pct, signed=True),
                "Mkt Cap Raw": mkt_cap,
                "Profit Margin Raw": profit_margin,
                "Rev Growth Raw": rev_growth,
                "Div Yield Raw": div_yield,
            })
        except Exception:
            continue

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Correlation / portfolio performance
# ─────────────────────────────────────────────────────────────────────────────

def build_correlation_data(tickers, frequency):
    freq_map = {
        "daily":   {"interval": "1d",  "period": "1y"},
        "weekly":  {"interval": "1wk", "period": "5y"},
        "monthly": {"interval": "1mo", "period": "10y"},
    }
    cfg = freq_map.get(frequency, freq_map["daily"])

    close = yf.download(
        tickers=tickers,
        period=cfg["period"],
        interval=cfg["interval"],
        auto_adjust=True,
        progress=False,
    )

    if close is None or close.empty:
        return None, []

    if isinstance(close.columns, pd.MultiIndex):
        price_df = close.get("Close")
    else:
        price_df = close

    if isinstance(price_df, pd.Series):
        price_df = price_df.to_frame(name=tickers[0])

    available = [t for t in tickers if t in price_df.columns]
    if not available:
        return None, []

    price_df = price_df[available].dropna(how="all")
    returns = price_df.pct_change().dropna(how="all")
    if returns.empty:
        return None, available

    corr = returns.corr().round(3)
    return corr, available


def build_portfolio_performance_data(tickers, weights, frequency):
    freq_map = {
        "daily":   {"interval": "1d",  "period": "1y"},
        "weekly":  {"interval": "1wk", "period": "5y"},
        "monthly": {"interval": "1mo", "period": "10y"},
    }
    cfg = freq_map.get(frequency, freq_map["weekly"])

    close = yf.download(
        tickers=tickers,
        period=cfg["period"],
        interval=cfg["interval"],
        auto_adjust=True,
        progress=False,
    )

    if close is None or close.empty:
        return None, None, None

    if isinstance(close.columns, pd.MultiIndex):
        price_df = close.get("Close")
    else:
        price_df = close

    if isinstance(price_df, pd.Series):
        price_df = price_df.to_frame(name=tickers[0])

    available = [t for t in tickers if t in price_df.columns]
    if not available:
        return None, None, None

    weight_series = pd.Series(weights, index=tickers)
    weight_series = weight_series.reindex(available).dropna()
    if weight_series.empty or weight_series.sum() <= 0:
        return None, None, None

    weight_series = weight_series / weight_series.sum()

    aligned_prices = price_df[weight_series.index].dropna(how="any")
    if aligned_prices.empty:
        return None, None, None

    rebased_components = aligned_prices.divide(aligned_prices.iloc[0]).mul(100)
    portfolio_index = rebased_components.mul(weight_series, axis=1).sum(axis=1)
    return portfolio_index, rebased_components, weight_series


# ─────────────────────────────────────────────────────────────────────────────
# Price chart
# ─────────────────────────────────────────────────────────────────────────────

def build_price_chart(ticker, period="6mo", c=None):
    if c is None:
        c = C
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty:
            return go.Figure()
        color    = c["green"] if df["Close"].iloc[-1] >= df["Close"].iloc[0] else c["red"]
        rgb      = "63,185,80" if color == c["green"] else "248,81,73"
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=f"rgba({rgb},0.07)",
            name="Price",
            hovertemplate="$%{y:.2f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"],
            name="Volume",
            marker_color="rgba(88,166,255,0.2)",
            yaxis="y2",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, color=c["subtext"], size=11),
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False, color=c["muted"], linecolor=c["border"]),
            yaxis=dict(showgrid=True, gridcolor=c["border"], color=c["subtext"],
                       tickprefix="$", side="right"),
            yaxis2=dict(overlaying="y", side="left", showgrid=False,
                        showticklabels=False,
                        range=[0, df["Volume"].max() * 6]),
            legend=dict(orientation="h", yanchor="bottom", y=1,
                        font=dict(size=10, family=FONT)),
            hovermode="x unified",
        )
        return fig
    except Exception:
        return go.Figure()


# ─────────────────────────────────────────────────────────────────────────────
# Valuation table
# ─────────────────────────────────────────────────────────────────────────────

def build_valuation_table(ticker, c=None):
    if c is None:
        c = C
    try:
        info = yf.Ticker(ticker).info
        metrics = {
            "P/E Ratio (TTM)":        info.get("trailingPE"),
            "Forward P/E":            info.get("forwardPE"),
            "PEG Ratio":              info.get("pegRatio"),
            "Price / Book":           info.get("priceToBook"),
            "Price / Sales (TTM)":    info.get("priceToSalesTrailing12Months"),
            "EV / EBITDA":            info.get("enterpriseToEbitda"),
            "EV / Revenue":           info.get("enterpriseToRevenue"),
            "Market Cap":             info.get("marketCap"),
            "Enterprise Value":       info.get("enterpriseValue"),
            "Beta":                   info.get("beta"),
            "52w High":               info.get("fiftyTwoWeekHigh"),
            "52w Low":                info.get("fiftyTwoWeekLow"),
            "Dividend Yield":         info.get("dividendYield"),
            "Return on Equity":       info.get("returnOnEquity"),
            "Return on Assets":       info.get("returnOnAssets"),
            "Profit Margin":          info.get("profitMargins"),
            "Gross Margin":           info.get("grossMargins"),
            "Revenue Growth (YoY)":   info.get("revenueGrowth"),
            "Earnings Growth (YoY)":  info.get("earningsGrowth"),
            "Debt / Equity":          info.get("debtToEquity"),
        }

        pct_keys = {"Dividend Yield", "Return on Equity", "Return on Assets",
                    "Profit Margin", "Gross Margin", "Revenue Growth (YoY)",
                    "Earnings Growth (YoY)"}
        big_keys = {"Market Cap", "Enterprise Value"}

        def fmt(k, v):
            if v is None:
                return "—"
            if k in pct_keys:
                return f"{v*100:.2f}%"
            if k in big_keys:
                return f"${v/1e9:.2f}B" if v >= 1e9 else f"${v/1e6:.1f}M"
            if k in {"52w High", "52w Low"}:
                return f"${v:,.2f}"
            return f"{v:.2f}"

        rows = []
        keys = list(metrics.keys())
        for i in range(0, len(keys), 2):
            cells = []
            for j in range(2):
                if i + j < len(keys):
                    k = keys[i + j]
                    v = fmt(k, metrics[k])
                    cells += [
                        html.Td(k, style={"color": c["subtext"], "padding": "0.42rem 0.75rem",
                                           "borderBottom": f"1px solid {c['border']}",
                                           "fontSize": "0.8rem", "fontFamily": FONT,
                                           "width": "30%"}),
                        html.Td(v, style={"color": c["text"], "fontWeight": "600",
                                           "padding": "0.42rem 0.75rem",
                                           "borderBottom": f"1px solid {c['border']}",
                                           "fontSize": "0.8rem", "textAlign": "right",
                                           "fontFamily": FONT, "width": "20%"}),
                    ]
                else:
                    cells += [html.Td(), html.Td()]
            rows.append(html.Tr(cells))

        return html.Table(html.Tbody(rows),
                          style={"width": "100%", "borderCollapse": "collapse"})
    except Exception as e:
        return html.Div(f"Could not load valuation data: {e}",
                        style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})


# ─────────────────────────────────────────────────────────────────────────────
# Financial statements + EDGAR helpers
# ─────────────────────────────────────────────────────────────────────────────

INCOME_ORDER = [
    "Total Revenue", "Revenue", "Gross Profit", "Cost Of Revenue",
    "Operating Revenue", "Operating Income", "Operating Expense",
    "Selling General Administrative", "Research And Development",
    "Depreciation Amortization Depletion", "Depreciation And Amortization In Income Statement",
    "Ebit", "Ebitda", "Interest Expense", "Interest Income",
    "Pretax Income", "Tax Provision", "Net Income",
    "Net Income Common Stockholders", "Diluted EPS", "Basic EPS",
    "Diluted Average Shares", "Basic Average Shares",
]

BALANCE_ORDER = [
    "Total Assets", "Current Assets", "Cash And Cash Equivalents",
    "Cash Cash Equivalents And Short Term Investments",
    "Receivables", "Inventory", "Other Current Assets",
    "Non Current Assets", "Net PPE", "Goodwill", "Intangible Assets",
    "Other Non Current Assets",
    "Total Liabilities Net Minority Interest", "Current Liabilities",
    "Accounts Payable", "Current Debt", "Other Current Liabilities",
    "Non Current Liabilities", "Long Term Debt", "Other Non Current Liabilities",
    "Total Equity Gross Minority Interest", "Stockholders Equity",
    "Common Stock", "Retained Earnings",
]

CASHFLOW_ORDER = [
    "Operating Cash Flow", "Cash Flow From Continuing Operating Activities",
    "Net Income From Continuing Operations",
    "Depreciation Amortization Depletion", "Change In Working Capital",
    "Change In Receivables", "Change In Inventory", "Change In Payables",
    "Investing Cash Flow", "Cash Flow From Continuing Investing Activities",
    "Capital Expenditure", "Purchase Of Investment", "Sale Of Investment",
    "Financing Cash Flow", "Cash Flow From Continuing Financing Activities",
    "Repayment Of Debt", "Issuance Of Debt", "Common Stock Issuance",
    "Repurchase Of Capital Stock", "Cash Dividends Paid",
    "Free Cash Flow", "Changes In Cash",
]


def get_edgar_10k_url(ticker):
    """Look up the latest 10-K filing URL on SEC EDGAR."""
    try:
        import requests as req
        r = req.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom"
            f"&startdt=2020-01-01&forms=10-K",
            headers={"User-Agent": "stock-dashboard contact@example.com"},
            timeout=5,
        )
        r2 = req.get(
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company="
            f"&CIK={ticker}&type=10-K&dateb=&owner=include&count=1&search_text=",
            headers={"User-Agent": "stock-dashboard contact@example.com"},
            timeout=5,
        )
        return (f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22"
                f"&forms=10-K&dateRange=custom&startdt=2022-01-01")
    except Exception:
        return None


def get_edgar_filing_url(ticker):
    """Return the URL for the most recent 10-K filing viewer on EDGAR."""
    try:
        import requests as req
        url = (f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22"
               f"&forms=10-K")
        r = req.get(
            "https://efts.sec.gov/LATEST/search-index?q="
            f"&forms=10-K&dateRange=custom&startdt=2023-01-01",
            headers={"User-Agent": "stock-dashboard contact@example.com"},
            timeout=4,
        )
        return (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                f"&CIK={ticker}&type=10-K&dateb=&owner=include&count=5")
    except Exception:
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=5"


def fetch_latest_10k_url(ticker):
    """
    Use SEC EDGAR submissions API to get the actual 10-K filing document URL.
    Returns a direct link to the filing index page.
    """
    try:
        import requests as req

        headers = {"User-Agent": "stock-dashboard research@example.com"}

        tickers_json = req.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=headers, timeout=6
        ).json()

        cik = None
        for entry in tickers_json.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                break

        if not cik:
            return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=5"

        subs = req.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers=headers, timeout=6
        ).json()

        filings = subs.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        accNums = filings.get("accessionNumber", [])
        dates   = filings.get("filingDate", [])

        for form, acc, date in zip(forms, accNums, dates):
            if form == "10-K":
                acc_clean = acc.replace("-", "")
                filing_url = (f"https://www.sec.gov/Archives/edgar/data/"
                              f"{int(cik)}/{acc_clean}/{acc}-index.htm")
                return filing_url

        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=include&count=5"

    except Exception:
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=5"


def reorder_df(df, preferred_order):
    """Reorder DataFrame rows to match preferred_order, appending any extras at the end."""
    existing = list(df.index)
    ordered  = [r for r in preferred_order if r in existing]
    extras   = [r for r in existing if r not in ordered]
    return df.loc[ordered + extras]


def build_financials(ticker, stmt_type="income", c=None):
    if c is None:
        c = C
    try:
        t = yf.Ticker(ticker)
        label_map = {
            "income":   ("Income Statement",     t.financials,   INCOME_ORDER),
            "balance":  ("Balance Sheet",         t.balance_sheet, BALANCE_ORDER),
            "cashflow": ("Cash Flow Statement",   t.cashflow,     CASHFLOW_ORDER),
        }
        title, df, preferred_order = label_map[stmt_type]

        if df is None or df.empty:
            return html.Div("No data available.",
                            style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})

        df   = df.dropna(how="all")
        df   = reorder_df(df, preferred_order)
        cols = [str(col_name)[:10] for col_name in df.columns]

        edgar_url = fetch_latest_10k_url(ticker)
        show_link = stmt_type == "income"

        def fmt_val(v):
            try:
                v = float(v)
                if abs(v) >= 1e9:
                    return f"${v/1e9:.2f}B"
                if abs(v) >= 1e6:
                    return f"${v/1e6:.1f}M"
                return f"${v:,.0f}"
            except Exception:
                return "—"

        th_style = {"padding": "0.35rem 0.75rem", "fontSize": "0.65rem",
                    "textTransform": "uppercase", "letterSpacing": "0.07em",
                    "borderBottom": f"2px solid {c['border']}", "fontFamily": FONT}

        header = html.Thead(html.Tr(
            [html.Th("", style={**th_style, "color": c["muted"]})] +
            [html.Th(c_col,  style={**th_style, "color": c["subtext"], "textAlign": "right"})
             for c_col in cols]
        ))

        LINKABLE_ROWS = {
            "Total Revenue", "Revenue", "Gross Profit", "Net Income",
            "Operating Income", "Ebitda", "Operating Cash Flow", "Free Cash Flow",
            "Total Assets", "Total Liabilities Net Minority Interest",
        }

        body_rows = []
        for idx, row in df.iterrows():
            is_linkable  = str(idx) in LINKABLE_ROWS
            is_highlight = str(idx) in {"Total Revenue", "Revenue", "Gross Profit",
                                         "Net Income", "Operating Income"}

            label_cell = html.Td(
                str(idx),
                style={"color": c["accent"] if is_highlight else c["subtext"],
                       "padding": "0.38rem 0.75rem",
                       "borderBottom": f"1px solid {c['border']}",
                       "fontSize": "0.78rem", "fontFamily": FONT,
                       "whiteSpace": "nowrap",
                       "fontWeight": "700" if is_highlight else "400"},
            )

            value_cells = []
            for v in row:
                formatted = fmt_val(v)
                if is_linkable and edgar_url and formatted != "—":
                    cell = html.Td(
                        html.A(
                            formatted,
                            href=edgar_url,
                            target="_blank",
                            title="Open latest 10-K on SEC EDGAR",
                            style={
                                "color": c["blue"],
                                "textDecoration": "none",
                                "fontWeight": "600",
                                "borderBottom": f"1px dashed {c['blue']}",
                                "cursor": "pointer",
                            },
                        ),
                        style={"padding": "0.38rem 0.75rem", "textAlign": "right",
                               "borderBottom": f"1px solid {c['border']}",
                               "fontSize": "0.78rem", "fontFamily": FONT},
                    )
                else:
                    cell = html.Td(
                        formatted,
                        style={"color": c["text"] if formatted != "\u2014" else c["muted"],
                               "fontWeight": "600" if is_highlight else "400",
                               "padding": "0.38rem 0.75rem", "textAlign": "right",
                               "borderBottom": f"1px solid {c['border']}",
                               "fontSize": "0.78rem", "fontFamily": FONT},
                    )
                value_cells.append(cell)

            body_rows.append(html.Tr(
                [label_cell] + value_cells,
                style={"backgroundColor": "rgba(88,166,255,0.04)" if is_highlight else "transparent"},
            ))

        hint = html.Div(
            [html.Span("🔗 ", style={"fontSize": "0.7rem"}),
             html.Span("Blue figures link directly to the latest 10-K filing on SEC EDGAR.",
                       style={"color": c["muted"], "fontSize": "0.68rem", "fontFamily": FONT})],
            style={"marginBottom": "0.65rem"}
        ) if show_link else html.Div()

        return html.Div([
            html.Div(title, style=LBL),
            hint,
            html.Div(
                html.Table([header, html.Tbody(body_rows)],
                           style={"width": "100%", "borderCollapse": "collapse"}),
                style={"overflowX": "auto"},
            ),
        ])
    except Exception as e:
        return html.Div(f"Could not load data: {e}",
                        style={"color": c["muted"], "fontSize": "0.82rem", "fontFamily": FONT})


# ─────────────────────────────────────────────────────────────────────────────
# Layout helper — index card
# ─────────────────────────────────────────────────────────────────────────────

def index_card(name, price, chg, pct, c=None):
    if c is None:
        c = C
    col  = c["green"] if chg >= 0 else c["red"]
    sign = "▲" if chg >= 0 else "▼"
    ps   = f"{price:,.2f}" if price else "—"
    return html.Div([
        html.Div(name, style={"color": c["subtext"], "fontSize": "0.7rem",
                               "fontFamily": FONT, "marginBottom": "4px"}),
        html.Div(ps,   style={"color": c["text"], "fontSize": "1.2rem",
                               "fontWeight": "700", "fontFamily": FONT}),
        html.Div(f"{sign} {abs(pct):.2f}%",
                 style={"color": col, "fontSize": "0.75rem", "fontFamily": FONT}),
    ], style={"backgroundColor": c["bg"], "border": f"1px solid {c['border']}",
              "borderRadius": "10px", "padding": "1rem",
              "flex": "1", "minWidth": "130px"})
