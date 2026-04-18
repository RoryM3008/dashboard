"""
Data helpers — every function that fetches, transforms, or renders market data.
No Dash app reference here; pure functions that return DataFrames or Dash components.
"""

import datetime
import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import feedparser
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from dash import dcc, html

# ─────────────────────────────────────────────────────────────────────────────
# TTL cache — avoids re-fetching the same data within a short window
# ─────────────────────────────────────────────────────────────────────────────
_CACHE = {}
_DISK_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
os.makedirs(_DISK_CACHE_DIR, exist_ok=True)


def _disk_save(key, data):
    """Persist data to a JSON file on disk."""
    try:
        path = os.path.join(_DISK_CACHE_DIR, f"{key}.json")
        with open(path, "w") as f:
            json.dump({"ts": time.time(), "val": data}, f)
    except Exception:
        pass


def _disk_load(key, max_age=86400):
    """Load data from disk cache. Returns None if missing or too old."""
    try:
        path = os.path.join(_DISK_CACHE_DIR, f"{key}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            blob = json.load(f)
        if time.time() - blob["ts"] > max_age:
            return None
        return blob["val"]
    except Exception:
        return None


def _cached(key, ttl_seconds, func, *args, **kwargs):
    """Return cached result if fresh, otherwise call func and cache it."""
    now = time.time()
    entry = _CACHE.get(key)
    if entry and (now - entry["ts"]) < ttl_seconds:
        return entry["val"]
    val = func(*args, **kwargs)
    _CACHE[key] = {"val": val, "ts": now}
    return val

from theme import (
    C, FONT, LBL, PANEL,
    INDICES, SCREENER_UNIVERSE,
    FX_PAIRS, BONDS, COMMODITIES, SECTOR_ETFS,
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
    today  = datetime.date.today()
    cutoff = today + datetime.timedelta(days=30)

    def _one(ticker):
        try:
            info = yf.Ticker(ticker).info
            ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
            if ts:
                dt = datetime.date.fromtimestamp(ts)
                if today <= dt <= cutoff:
                    exp_eps = info.get("earningsEstimate") or info.get("forwardEps")
                    last_eps = info.get("trailingEps")
                    sector = info.get("sector", "—")
                    return {"Ticker": ticker,
                            "Sector": sector or "—",
                            "Earnings Date": dt.strftime("%d %b %Y"),
                            "Days Away": (dt - today).days,
                            "Est EPS": round(float(exp_eps), 2) if exp_eps is not None else None,
                            "Last EPS": round(float(last_eps), 2) if last_eps is not None else None,
                            "_date": dt}
        except Exception:
            pass
        return None

    rows = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for result in pool.map(_one, tickers):
            if result:
                rows.append(result)
    if not rows:
        return pd.DataFrame(columns=["Ticker", "Sector", "Earnings Date", "Days Away", "Est EPS", "Last EPS"])
    df = pd.DataFrame(rows).sort_values("_date")
    return df.drop(columns=["_date"]).reset_index(drop=True)


def fetch_prices(tickers):
    def _one(ticker):
        try:
            fi    = yf.Ticker(ticker).fast_info
            price = round(fi.last_price, 2)
            prev  = round(fi.previous_close, 2)
            chg   = round(price - prev, 2)
            pct   = round((chg / prev) * 100, 2) if prev else 0
            mc    = fi.market_cap
            cap   = (f"${mc/1e9:.1f}B" if mc and mc >= 1e9
                     else f"${mc/1e6:.1f}M" if mc else "—")
            return {"Ticker": ticker,
                    "Price":   f"${price:,.2f}",
                    "Change":  f"{'+' if chg>=0 else ''}{chg:.2f}",
                    "Chg %":   f"{'+' if pct>=0 else ''}{pct:.2f}%",
                    "Mkt Cap": cap,
                    "_chg":    chg}
        except Exception:
            return {"Ticker": ticker, "Price": "—", "Change": "—",
                    "Chg %": "—", "Mkt Cap": "—", "_chg": 0}

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(_one, tickers))
    return pd.DataFrame(results)


# ─────────────────────────────────────────────────────────────────────────────
# S&P 500 top movers
# ─────────────────────────────────────────────────────────────────────────────

_SP500_CACHE = {"tickers": None, "ts": None}

# Full S&P 500 constituents (as of April 2026) — used as fallback when
# the Wikipedia scrape fails (corporate proxy / SSL / rate-limit).
_SP500_HARDCODED = [
    "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","A","APD","ABNB",
    "AKAM","ALB","ARE","ALGN","ALLE","LNT","ALL","GOOGL","GOOG","MO","AMZN",
    "AMCR","AEE","AAL","AEP","AXP","AIG","AMT","AWK","AMP","AME","AMGN","APH",
    "ADI","ANSS","AON","APA","AAPL","AMAT","APTV","ACGL","ADM","ANET","AJG",
    "AIZ","T","ATO","ADSK","ADP","AZO","AVB","AVY","AXON","BKR","BALL","BAC",
    "BK","BBWI","BAX","BDX","BRK-B","BBY","BIO","TECH","BIIB","BLK","BA","BKNG",
    "BWA","BSX","BMY","AVGO","BR","BRO","BF-B","BLDR","BG","CDNS","CZR","CPT",
    "CPB","COF","CAH","KMX","CCL","CARR","CTLT","CAT","CBOE","CBRE","CDW","CE",
    "COR","CNC","CNP","CF","CHRW","CRL","SCHW","CHTR","CVX","CMG","CB","CHD",
    "CI","CINF","CTAS","CSCO","C","CFG","CLX","CME","CMS","KO","CTSH","CL",
    "CMCSA","CAG","COP","ED","STZ","CEG","COO","CPRT","GLW","CPAY","CTVA",
    "CSGP","COST","CTRA","CRWD","CCI","CSX","CMI","CVS","DHR","DRI","DVA",
    "DAY","DECK","DE","DAL","DVN","DXCM","FANG","DLR","DFS","DG","DLTR","D",
    "DPZ","DOV","DOW","DHI","DTE","DUK","DD","EMN","ETN","EBAY","ECL","EIX",
    "EW","EA","ELV","EMR","ENPH","ETR","EOG","EPAM","EQT","EFX","EQIX","EQR",
    "ERIE","ESS","EL","ETSY","EG","EVRG","ES","EXC","EXPE","EXPD","EXR","XOM",
    "FFIV","FDS","FICO","FAST","FRT","FDX","FIS","FITB","FSLR","FE","FI",
    "FMC","F","FTNT","FTV","FOXA","FOX","BEN","FCX","GRMN","IT","GE","GEHC",
    "GEN","GNRC","GD","GIS","GM","GPC","GILD","GPN","GL","GDDY","GS","HAL",
    "HIG","HAS","HCA","DOC","HSIC","HSY","HES","HPE","HLT","HOLX","HD","HON",
    "HRL","HST","HWM","HPQ","HUBB","HUM","HBAN","HII","IBM","IEX","IDXX","ITW",
    "ILMN","INCY","IR","PODD","INTC","ICE","IFF","IP","IPG","INTU","ISRG","IVZ",
    "INVH","IQV","IRM","JBHT","JBL","JKHY","J","JNJ","JCI","JPM","JNPR","K",
    "KVUE","KDP","KEY","KEYS","KMB","KIM","KMI","KKR","KLAC","KHC","KR","LHX",
    "LH","LRCX","LW","LVS","LDOS","LEN","LLY","LIN","LYV","LKQ","LMT","L",
    "LOW","LULU","LYB","MTB","MRO","MPC","MKTX","MAR","MMC","MLM","MAS","MA",
    "MTCH","MKC","MCD","MCK","MDT","MRK","META","MCHP","MU","MSFT","MAA","MRNA",
    "MHK","MOH","TAP","MDLZ","MPWR","MNST","MCO","MS","MOS","MSI","MSCI","NDAQ",
    "NTAP","NFLX","NEM","NWSA","NWS","NEE","NKE","NI","NDSN","NSC","NTRS","NOC",
    "NCLH","NRG","NUE","NVDA","NVR","NXPI","ORLY","OXY","ODFL","OMC","ON","OKE",
    "ORCL","OTIS","PCAR","PKG","PANW","PARA","PH","PAYX","PAYC","PYPL","PNR",
    "PEP","PFE","PCG","PM","PSX","PNW","PXD","PNC","POOL","PPG","PPL","PFG",
    "PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","QRVO","PWR","QCOM","DGX",
    "RL","RJF","RTX","O","REG","REGN","RF","RSG","RMD","RVTY","RHI","ROK","ROL",
    "ROP","ROST","RCL","SPGI","CRM","SBAC","SLB","STX","SRE","NOW","SHW","SPG",
    "SWKS","SJM","SW","SNA","SOLV","SO","LUV","SWK","SBUX","STT","STLD","STE",
    "SYK","SMCI","SYF","SNPS","SYY","TMUS","TROW","TTWO","TPR","TRGP","TGT",
    "TEL","TDY","TFX","TER","TSLA","TXN","TXT","TMO","TJX","TSCO","TT","TDG",
    "TRV","TRMB","TFC","TYL","TSN","USB","UBER","UDR","ULTA","UNP","UAL","UPS",
    "URI","UNH","UHS","VLO","VTR","VLTO","VRSN","VRSK","VZ","VRTX","VTRS","VICI",
    "V","VMC","WRB","GWW","WAB","WBA","WMT","DIS","WBD","WM","WAT","WEC","WFC",
    "WELL","WST","WDC","WRK","WY","WMB","WTW","WYNN","XEL","XYL","YUM","ZBRA",
    "ZBH","ZTS",
]


def _get_sp500_tickers():
    """Return list of S&P 500 tickers.
    Tries Wikipedia first (via requests to bypass SSL issues),
    falls back to the hardcoded list above.  Cached for 24 h.
    """
    now = time.time()
    if _SP500_CACHE["tickers"] and _SP500_CACHE["ts"] and now - _SP500_CACHE["ts"] < 86400:
        return _SP500_CACHE["tickers"]
    try:
        import requests
        from io import StringIO
        r = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "stock-dashboard/1.0"},
            verify=False, timeout=10,
        )
        r.raise_for_status()
        tables = pd.read_html(StringIO(r.text), flavor="lxml")
        table = next(t for t in tables if "Symbol" in t.columns)
        ticks = table["Symbol"].str.replace(".", "-", regex=False).tolist()
        if len(ticks) > 400:   # sanity check
            _SP500_CACHE["tickers"] = ticks
            _SP500_CACHE["ts"] = now
            return ticks
    except Exception:
        pass
    # Fallback — hardcoded full list
    _SP500_CACHE["tickers"] = list(_SP500_HARDCODED)
    _SP500_CACHE["ts"] = now
    return _SP500_CACHE["tickers"]


# ─────────────────────────────────────────────────────────────────────────────
# Generic movers engine — shared by S&P 500 / FTSE 100 / Euro Stoxx 50
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_movers_generic(tickers, n, cache_key, prefix="$"):
    """Download daily + intraday data for a ticker list, return (gainers, losers).
    Uses parallel bulk downloads and persists results to disk."""

    def _dl_daily():
        try:
            return yf.download(tickers, period="5d", interval="1d",
                               group_by="ticker", threads=True, progress=False)
        except Exception:
            return None

    def _dl_intra():
        try:
            return yf.download(tickers, period="1d", interval="5m",
                               group_by="ticker", threads=True, progress=False)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_daily = pool.submit(_dl_daily)
        fut_intra = pool.submit(_dl_intra)
    daily = fut_daily.result()
    intra = fut_intra.result()

    if daily is None or daily.empty:
        return pd.DataFrame(), pd.DataFrame()

    has_intraday = (intra is not None and not intra.empty)

    rows = []
    for t in tickers:
        try:
            d_close = daily[t]["Close"].dropna()
            if len(d_close) < 2:
                continue

            if has_intraday:
                prev = float(d_close.iloc[-2])
                live = None
                try:
                    i_close = intra[t]["Close"].dropna()
                    if not i_close.empty:
                        live = float(i_close.iloc[-1])
                except Exception:
                    pass
                if live is None:
                    live = float(d_close.iloc[-1])
            else:
                prev = float(d_close.iloc[-2])
                live = float(d_close.iloc[-1])

            if prev == 0:
                continue

            pct = (live / prev - 1) * 100
            rows.append({"Ticker": t, "Price": f"{prefix}{live:,.2f}",
                         "Chg %": f"{'+'if pct >= 0 else ''}{pct:.2f}%",
                         "_chg": pct})
        except Exception:
            continue

    if not rows:
        return pd.DataFrame(), pd.DataFrame()
    result = pd.DataFrame(rows).sort_values("_chg", ascending=False)
    gainers = result.head(n).reset_index(drop=True)
    losers = result.tail(n).sort_values("_chg").reset_index(drop=True)

    try:
        _disk_save(f"{cache_key}_{n}", {
            "gainers": gainers.to_dict(orient="records"),
            "losers":  losers.to_dict(orient="records"),
        })
    except Exception:
        pass

    return gainers, losers


def _fetch_movers_cached(cache_key, n, impl_fn):
    """Generic cached movers: in-memory → disk → fresh fetch."""
    key = f"{cache_key}_{n}"

    # 1. In-memory cache (15-min TTL)
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < 900:
        return entry["val"]

    # 2. Disk cache (up to 24h old — serve immediately, refresh in background)
    disk = _disk_load(key, max_age=86400)
    if disk:
        gainers = pd.DataFrame(disk["gainers"])
        losers  = pd.DataFrame(disk["losers"])
        _CACHE[key] = {"val": (gainers, losers), "ts": time.time() - 600}
        threading.Thread(
            target=lambda: _cached(key, 900, impl_fn, n),
            daemon=True,
        ).start()
        return gainers, losers

    # 3. Cold start
    return _cached(key, 900, impl_fn, n)


# ─────────────────────────────────────────────────────────────────────────────
# S&P 500 movers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_sp500_movers_impl(n=10):
    """S&P 500 gainers & losers."""
    return _fetch_movers_generic(_get_sp500_tickers(), n, "sp500_movers")


def fetch_sp500_movers(n=10):
    """S&P 500 movers with disk cache + background refresh."""
    return _fetch_movers_cached("sp500_movers", n, _fetch_sp500_movers_impl)


# ─────────────────────────────────────────────────────────────────────────────
# FTSE 100 movers
# ─────────────────────────────────────────────────────────────────────────────

_FTSE100 = [
    "AAF.L","AAL.L","ABF.L","ADM.L","AHT.L","ANTO.L","AUTO.L","AV.L","AZN.L",
    "BA.L","BARC.L","BATS.L","BDEV.L","BEZ.L","BKG.L","BME.L","BNZL.L","BP.L",
    "BRBY.L","BT-A.L","CCH.L","CNA.L","CPG.L","CRDA.L","CRH.L","CTEC.L",
    "DARK.L","DCC.L","DGE.L","DPH.L","EDV.L","ENT.L","EXPN.L","EZJ.L","FCIT.L",
    "FLTR.L","FRAS.L","FRES.L","GLEN.L","GSK.L","HIK.L","HLMA.L","HLN.L",
    "HSBA.L","IAG.L","ICG.L","IHG.L","III.L","IMB.L","INF.L","ITRK.L","JD.L",
    "KGF.L","LAND.L","LGEN.L","LLOY.L","LSEG.L","MKS.L","MNDI.L","MNG.L",
    "MRO.L","NG.L","NWG.L","NXT.L","PHNX.L","PRU.L","PSH.L","PSN.L","PSON.L",
    "REL.L","RIO.L","RKT.L","RMV.L","RR.L","RTO.L","SBRY.L","SDR.L","SGE.L",
    "SGRO.L","SHEL.L","SKG.L","SMDS.L","SMIN.L","SMT.L","SN.L","SPX.L",
    "SSE.L","STAN.L","SVT.L","TSCO.L","TW.L","ULVR.L","UTG.L","UU.L","VOD.L",
    "VTY.L","WEIR.L","WPP.L","WTB.L",
]


def _fetch_ftse100_movers_impl(n=10):
    return _fetch_movers_generic(_FTSE100, n, "ftse100_movers", prefix="£")


def fetch_ftse100_movers(n=10):
    """FTSE 100 movers with disk cache + background refresh."""
    return _fetch_movers_cached("ftse100_movers", n, _fetch_ftse100_movers_impl)


# ─────────────────────────────────────────────────────────────────────────────
# Euro Stoxx 50 movers
# ─────────────────────────────────────────────────────────────────────────────

_EUROSTOXX50 = [
    "ABI.BR","AD.AS","ADY.DE","AI.PA","AIR.PA","ALV.DE","ASML.AS","AXA.PA",
    "BAS.DE","BAYN.DE","BBVA.MC","BMW.DE","BN.PA","BNP.PA","CRG.IR","CS.PA",
    "DHL.DE","DTE.DE","ENEL.MI","ENGI.PA","ENI.MI","EL.PA","FLO.MC","GLE.PA",
    "IBE.MC","IFX.DE","ISP.MI","ITX.MC","KER.PA","KN.PA","LIN.DE","MC.PA",
    "MBG.DE","MRK.DE","MUV2.DE","NOKIA.HE","OR.PA","ORA.PA","PHIA.AS",
    "RMS.PA","SAF.PA","SAN.PA","SAN.MC","SAP.DE","SIE.DE","SU.PA","TTE.PA",
    "UCG.MI","UMG.AS","VOW3.DE",
]


def _fetch_eurostoxx_movers_impl(n=10):
    return _fetch_movers_generic(_EUROSTOXX50, n, "eurostoxx_movers", prefix="€")


def fetch_eurostoxx_movers(n=10):
    """Euro Stoxx 50 movers with disk cache + background refresh."""
    return _fetch_movers_cached("eurostoxx_movers", n, _fetch_eurostoxx_movers_impl)


# ── Pre-warm: kick off background fetches on import ─────────────────────────
for _warm_fn in (fetch_sp500_movers, fetch_ftse100_movers, fetch_eurostoxx_movers):
    threading.Thread(target=lambda fn=_warm_fn: fn(10), daemon=True).start()


def fetch_index_data():
    """Fetch index data in parallel (was serial)."""
    def _one(name, sym):
        try:
            fi  = yf.Ticker(sym).fast_info
            p   = fi.last_price
            prv = fi.previous_close
            chg = p - prv
            pct = (chg / prv) * 100 if prv else 0
            return {"name": name, "symbol": sym, "price": p, "chg": chg, "pct": pct}
        except Exception:
            return {"name": name, "symbol": sym, "price": None, "chg": 0, "pct": 0}

    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(_one, n, s): n for n, s in INDICES.items()}
        for f in as_completed(futs):
            results.append(f.result())
    # Preserve original order
    order = {n: i for i, n in enumerate(INDICES)}
    results.sort(key=lambda r: order.get(r["name"], 999))
    return results


def fetch_news(tickers, max_per=3):
    """
    Fetch news from multiple RSS sources in parallel.
    Returns a dict: {"stock": [...], "general": [...], "all": [...]}.
    """

    seen_titles = set()
    stock_articles = []
    general_articles = []

    # Build job list: (url, source, ticker_or_None, max_entries)
    jobs = []
    for ticker in tickers:
        jobs.append((
            f"https://feeds.finance.yahoo.com/rss/2.0/headline"
            f"?s={ticker}&region=US&lang=en-US", "Yahoo", ticker, max_per))
        jobs.append((
            f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en",
            "Google", ticker, max_per))

    general_feeds = [
        ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
         "CNBC", None, 5),
        ("https://feeds.marketwatch.com/marketwatch/topstories",
         "MarketWatch", None, 5),
        ("https://feeds.bloomberg.com/markets/news.rss",
         "Bloomberg", None, 5),
        ("https://seekingalpha.com/market_currents.xml",
         "SeekingAlpha", None, 5),
        ("https://www.rss.reuters.com/news/economy",
         "Reuters", None, 5),
    ]
    jobs.extend(general_feeds)

    def _fetch_one(url, source, ticker, limit):
        try:
            feed = feedparser.parse(url)
            results = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                if title:
                    results.append({
                        "ticker":    ticker or "MKT",
                        "title":     title,
                        "link":      entry.get("link", "#"),
                        "published": entry.get("published", ""),
                        "source":    source,
                        "_is_stock": ticker is not None,
                    })
            return results
        except Exception:
            return []

    # Fetch all feeds concurrently (max 20 threads)
    all_results = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_fetch_one, *job): job for job in jobs}
        for future in as_completed(futures):
            all_results.extend(future.result())

    # Deduplicate and split
    for a in all_results:
        if a["title"] not in seen_titles:
            seen_titles.add(a["title"])
            if a["_is_stock"]:
                stock_articles.append(a)
            else:
                general_articles.append(a)

    combined = stock_articles + general_articles
    return {"stock": stock_articles, "general": general_articles, "all": combined}


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
    def _scan_one(ticker):
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

            return {
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
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        for result in pool.map(_scan_one, universe):
            if result:
                rows.append(result)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Risk contribution (component contribution to tracking-error / volatility)
# ─────────────────────────────────────────────────────────────────────────────

def risk_contrib(returns_df, weights_s):
    """
    Decompose portfolio volatility into per-asset contributions.

    Parameters
    ----------
    returns_df : DataFrame  (dates × tickers, decimal returns)
    weights_s  : Series     (tickers → weight, sums to 1)

    Returns
    -------
    DataFrame with columns [weight, MCR, RC, pct_RC]
    port_vol : float  (portfolio volatility, same units as returns)
    """
    # Align weights to columns, drop any that are missing
    tickers = [t for t in returns_df.columns if t in weights_s.index]
    returns_df = returns_df[tickers].dropna(how="all")
    w = weights_s.reindex(tickers).fillna(0)
    if w.sum() > 0:
        w = w / w.sum()

    cov = returns_df.cov()                       # sample covariance Σ
    w_arr = w.values                              # (N,)
    sigma_w = cov.values @ w_arr                  # Σ·w  → (N,)
    port_var = float(w_arr @ sigma_w)             # w'·Σ·w
    port_vol = float(np.sqrt(port_var))

    mcr = sigma_w / port_vol if port_vol > 0 else sigma_w * 0   # marginal
    rc  = w_arr * mcr                                            # component
    pct_rc = rc / port_vol if port_vol > 0 else rc * 0          # pct of vol

    result = pd.DataFrame({
        "weight": w.values,
        "MCR":    mcr,
        "RC":     rc,
        "pct_RC": pct_rc,
    }, index=tickers)

    return result, port_vol


def rolling_risk_contrib(returns_df, weights_s, window=90):
    """
    Rolling component contribution to volatility.

    Returns
    -------
    pct_RC_df  : DataFrame (dates × tickers) of rolling percent risk contributions
    port_vol_s : Series    of rolling portfolio volatility
    """
    tickers = [t for t in returns_df.columns if t in weights_s.index]
    returns_df = returns_df[tickers].dropna(how="all")
    w = weights_s.reindex(tickers).fillna(0)
    if w.sum() > 0:
        w = w / w.sum()
    w_arr = w.values

    dates = returns_df.index[window - 1:]
    pct_rc_rows = []
    vol_rows = []

    for i in range(window, len(returns_df) + 1):
        chunk = returns_df.iloc[i - window:i]
        cov = chunk.cov().values
        sigma_w = cov @ w_arr
        port_var = float(w_arr @ sigma_w)
        port_vol = float(np.sqrt(max(port_var, 0)))

        if port_vol > 0:
            mcr = sigma_w / port_vol
            rc = w_arr * mcr
            pct = rc / port_vol
        else:
            pct = np.zeros(len(tickers))

        pct_rc_rows.append(pct)
        vol_rows.append(port_vol)

    pct_RC_df = pd.DataFrame(pct_rc_rows, index=dates, columns=tickers)
    port_vol_s = pd.Series(vol_rows, index=dates, name="port_vol")

    return pct_RC_df, port_vol_s


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


# ─────────────────────────────────────────────────────────────────────────────
# Bloomberg-style data fetchers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_quote_table(pairs_dict):
    """Fetch price + daily change for a dict of {label: yf_symbol}.
    Returns list of dicts: [{name, price, chg, pct}, ...]."""

    def _one(name, sym):
        try:
            fi = yf.Ticker(sym).fast_info
            p = fi.last_price
            prev = fi.previous_close
            chg = p - prev if (p and prev) else 0
            pct = (chg / prev * 100) if prev else 0
            return {"name": name, "symbol": sym, "price": p, "chg": chg, "pct": pct}
        except Exception:
            return {"name": name, "symbol": sym, "price": None, "chg": 0, "pct": 0}

    results = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(_one, n, s): n for n, s in pairs_dict.items()}
        for f in as_completed(futs):
            results.append(f.result())
    # Preserve insertion order from dict
    order = {n: i for i, n in enumerate(pairs_dict)}
    results.sort(key=lambda r: order.get(r["name"], 999))
    return results


def fetch_sector_performance():
    """Fetch daily % change for sector ETFs. Returns list of dicts."""
    return fetch_quote_table(SECTOR_ETFS)


def fetch_chart_data(symbol="^GSPC", period="5d", interval="15m"):
    """Return a DataFrame (Date, Open, High, Low, Close, Volume) for any ticker."""
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        df = df.reset_index()
        return df
    except Exception:
        return pd.DataFrame()


def fetch_portfolio_history(tickers, period="1mo"):
    """Fetch normalised (base-100) close prices for a list of tickers."""
    if not tickers:
        return pd.DataFrame()
    try:
        df = yf.download(tickers, period=period, auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df = df["Close"]
        elif "Close" in df.columns and len(tickers) == 1:
            df = df[["Close"]].rename(columns={"Close": tickers[0]})
        # Normalise to base 100
        first = df.iloc[0]
        first = first.replace(0, np.nan)
        df = (df / first) * 100
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame()
