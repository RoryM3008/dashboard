"""
Shared theme constants — colours, fonts, style dicts, ticker lists.
Imported by every other module so the look-and-feel lives in one place.

Two palettes are available: DARK and LIGHT.
Use ``get_theme(mode)`` to get the right colour dict for the active mode.
The module-level ``C`` dict defaults to dark so that layout builders that
run at import time still work.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Colour palettes
# ─────────────────────────────────────────────────────────────────────────────
DARK = {
    "bg":      "#000000",
    "panel":   "#1a1a1a",
    "border":  "#333333",
    "accent":  "#ff8c00",
    "green":   "#00d26a",
    "red":     "#ff3333",
    "blue":    "#4296f5",
    "muted":   "#555555",
    "text":    "#f5f5f5",
    "subtext": "#999999",
}

LIGHT = {
    "bg":      "#f6f8fa",
    "panel":   "#ffffff",
    "border":  "#d0d7de",
    "accent":  "#d4940a",
    "green":   "#1a7f37",
    "red":     "#cf222e",
    "blue":    "#0969da",
    "muted":   "#8c959f",
    "text":    "#1c1e21",
    "subtext": "#57606a",
}

# Default for import-time layout code
C = dict(DARK)


def get_theme(mode: str = "dark") -> dict:
    """Return the colour palette for the given mode ('dark' or 'light')."""
    return dict(LIGHT) if mode == "light" else dict(DARK)


FONT = "'Nunito Sans', 'Segoe UI', sans-serif"

# ─────────────────────────────────────────────────────────────────────────────
# Style-dict builders (take a colour dict so callbacks can pass the live theme)
# ─────────────────────────────────────────────────────────────────────────────

def _panel(c):
    return {
        "backgroundColor": c["panel"],
        "border": f"1px solid {c['border']}",
        "borderRadius": "10px",
        "padding": "1.25rem",
        "marginBottom": "1.25rem",
    }

def _lbl(c):
    return {
        "fontFamily": FONT,
        "fontWeight": "700",
        "fontSize": "0.65rem",
        "letterSpacing": "0.08em",
        "textTransform": "uppercase",
        "color": c["subtext"],
        "marginBottom": "0.6rem",
    }

def _nav_btn(c):
    return {
        "backgroundColor": "transparent",
        "border": f"1px solid {c['border']}",
        "borderRadius": "6px",
        "color": c["subtext"],
        "padding": "0.45rem 1rem",
        "fontFamily": FONT,
        "fontSize": "0.82rem",
        "cursor": "pointer",
        "fontWeight": "600",
    }

def _nav_btn_active(c):
    base = _nav_btn(c)
    return {**base, "backgroundColor": c["accent"], "color": "#000",
            "border": f"1px solid {c['accent']}"}

def _main_menu_btn(c):
    return {
        "width": "100%",
        "textAlign": "left",
        "backgroundColor": "transparent",
        "border": f"1px solid {c['border']}",
        "borderRadius": "8px",
        "color": c["subtext"],
        "padding": "0.6rem 0.85rem",
        "fontFamily": FONT,
        "fontSize": "0.82rem",
        "fontWeight": "700",
        "cursor": "pointer",
    }

def _main_menu_btn_active(c):
    base = _main_menu_btn(c)
    return {**base, "backgroundColor": c["accent"], "color": "#000",
            "border": f"1px solid {c['accent']}"}


# Static defaults (dark) — used by layout code that runs at import time
PANEL = _panel(C)
LBL   = _lbl(C)
NAV_BTN        = _nav_btn(C)
NAV_BTN_ACTIVE = _nav_btn_active(C)
MAIN_MENU_BTN        = _main_menu_btn(C)
MAIN_MENU_BTN_ACTIVE = _main_menu_btn_active(C)

# ─────────────────────────────────────────────────────────────────────────────
# Market constants
# ─────────────────────────────────────────────────────────────────────────────
INDICES = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX"}
PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

# ─────────────────────────────────────────────────────────────────────────────
# Screener universe — Full S&P 500 + International ADRs (~540 stocks)
# ─────────────────────────────────────────────────────────────────────────────
_RAW_UNIVERSE = [
    # ── S&P 500 constituents (alphabetical) ──────────────────────────────
    "A","AAPL","ABBV","ABNB","ABT","ACGL","ACN","ADBE","ADI","ADM",
    "ADP","ADSK","AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM",
    "ALB","ALGN","ALL","ALLE","AMAT","AMCR","AMD","AME","AMGN","AMZN",
    "AMT","ANET","ANSS","AON","AOS","APA","APD","APH","APO","APTV",
    "ARE","ARM","ATO","AVGO","AVB","AVY","AWK","AXON","AXP","AZO",
    "BA","BAC","BALL","BAX","BBY","BDX","BEN","BG","BIIB","BK",
    "BKNG","BKR","BLK","BLDR","BMY","BR","BRK-B","BRO","BSX","BX","BXP",
    "C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE","CCI","CCL",
    "CDNS","CDW","CE","CF","CFG","CHD","CHRW","CHTR","CI","CINF",
    "CL","CLX","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF",
    "COO","COP","COR","COST","CPAY","CPB","CPRT","CPT","CRL","CRM",
    "CRWD","CSGP","CSCO","CSX","CTAS","CTRA","CTSH","CTVA","CVS","CVX","CZR",
    "D","DAL","DAY","DD","DDOG","DE","DECK","DELL","DFS","DG",
    "DGX","DHI","DHR","DIS","DLR","DLTR","DOC","DOV","DOW","DPZ",
    "DRI","DT","DVA","DVN","DXCM",
    "EA","EBAY","ECL","ED","EFX","EG","EIX","EL","ELV","EMN",
    "EMR","ENPH","EOG","EPAM","EQIX","EQR","EQT","ERIE","ES","ESS",
    "ETN","ETR","EW","EVRG","EXC","EXPD","EXPE","EXR",
    "F","FANG","FAST","FCNCA","FCX","FDS","FDX","FE","FFIV","FI",
    "FICO","FIS","FITB","FOX","FOXA","FRT","FSLR","FTNT","FTV",
    "GD","GDDY","GE","GEHC","GEN","GEV","GILD","GIS","GL","GLW",
    "GM","GNRC","GOOG","GOOGL","GPC","GPN","GRMN","GS","GWW",
    "HAL","HAS","HBAN","HCA","HD","HOLX","HON","HPE","HPQ","HRL",
    "HSIC","HST","HSY","HUBB","HUM","HWM",
    "IBM","ICE","IDXX","IEX","IFF","INCY","INTC","INTU","INVH","IP",
    "IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ",
    "J","JBHT","JBL","JCI","JKHY","JNJ","JNPR","JPM",
    "K","KDP","KEY","KEYS","KHC","KIM","KKR","KLAC","KMB","KMI",
    "KMX","KO","KR","KVUE",
    "L","LDOS","LEN","LH","LHX","LII","LIN","LKQ","LLY","LMT",
    "LNT","LOW","LRCX","LULU","LUV","LVS","LW","LYB","LYV",
    "MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT",
    "MET","META","MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MNST",
    "MO","MOH","MOS","MPC","MPWR","MRK","MRNA","MS","MSCI","MSFT",
    "MSI","MTB","MTCH","MTD","MU",
    "NCLH","NDAQ","NDSN","NEE","NEM","NFLX","NI","NKE","NOC","NOW",
    "NRG","NSC","NTAP","NTRS","NTRA","NUE","NVDA","NVR","NWS","NWSA","NXPI",
    "O","ODFL","OKE","OMC","ON","ORCL","ORLY","OTIS","OXY",
    "PANW","PARA","PAYC","PAYX","PCAR","PCG","PEG","PEP","PFE","PFG",
    "PG","PGR","PH","PHM","PKG","PLD","PLTR","PM","PNC","PNR",
    "PNW","PODD","POOL","PPG","PPL","PRU","PSA","PSX","PTC","PYPL",
    "QCOM","QRVO",
    "RCL","REG","REGN","RF","RJF","RL","RMD","ROK","ROL","ROP",
    "ROST","RSG","RTX","RVTY",
    "SBAC","SBUX","SCHW","SHW","SJM","SLB","SMCI","SNA","SNPS","SO",
    "SOLV","SPG","SPGI","SRE","STE","STLD","STT","STX","STZ","SW",
    "SWK","SWKS","SYF","SYK","SYY",
    "T","TAP","TDG","TDY","TECH","TEL","TER","TFC","TGT","TJX",
    "TKO","TMO","TMUS","TOST","TPG","TPL","TPR","TRGP","TRMB","TROW",
    "TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL",
    "UAL","UBER","UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB",
    "V","VEEV","VICI","VLO","VLTO","VMC","VRSK","VRSN","VRTX","VST",
    "VTR","VTRS",
    "WAB","WAT","WBA","WBD","WDAY","WDC","WEC","WELL","WFC","WM",
    "WMB","WMT","WRB","WSM","WST","WTW","WY","WYNN",
    "XEL","XOM","XYL",
    "YUM",
    "ZBH","ZBRA","ZTS",
    # ── International ADRs ───────────────────────────────────────────────
    "ASML","TSM","BABA","JD","PDD","BIDU","NIO","XPEV","TCEHY",
    "SONY","SNY","NVS","RHHBY","AZN","GSK","BP","SHEL",
    "HSBC","UBS","DB","BCS","SAN","ING",
    "SAP","SHOP","ENB","TD","RY","BNS","BMO","CM","MFC",
    "INFY","WIT","HDB","IBN","VALE","ITUB","NU",
    "RIO","BHP","GLEN",
]
_seen_u = set()
SCREENER_UNIVERSE = [t for t in _RAW_UNIVERSE if not (t in _seen_u or _seen_u.add(t))]
