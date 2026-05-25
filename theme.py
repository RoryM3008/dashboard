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
    "muted":   "#8b949e",
    "text":    "#f5f5f5",
    "subtext": "#b8c0cc",
    "axis":    "#b8b8b8",
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
    "axis":    "#505a64",
}

# Default for import-time layout code
C = dict(DARK)


def get_theme(mode: str = "dark") -> dict:
    """Return the colour palette for the given mode ('dark' or 'light')."""
    return dict(LIGHT) if mode == "light" else dict(DARK)


FONT = "'Nunito Sans', 'Segoe UI', sans-serif"

BBG_ESTIMATES = {
    "bg": "#000000",
    "panel": "#0b0b0b",
    "panel_alt": "#101010",
    "control": "#1a1a1a",
    "border": "#2a2a2a",
    "grid": "rgba(55, 55, 55, 0.45)",
    "text": "#e6e6e6",
    "muted": "#a9a9a9",
    "orange": "#ff9900",
    "blue": "#1f5aa6",
    "tab_off": "#2a2a2a",
}

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
INDICES = {"S&P 500": "SPY", "NASDAQ": "QQQ", "DOW": "DIA", "VIX": "VIXY"}
PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

# ── Benchmark options for Performance page ───────────────────────────────────
# ETF benchmarks
ETF_BENCHMARKS = {
    "S&P 500 (SPY)": "SPY",
    "NASDAQ 100 (QQQ)": "QQQ",
    "Dow Jones (DIA)": "DIA",
    "Russell 2000 (IWM)": "IWM",
    "MSCI EAFE ETF (EFA)": "EFA",
    "MSCI EM ETF (EEM)": "EEM",
    "US Agg Bond (AGG)": "AGG",
    "US Treasury 20Y+ (TLT)": "TLT",
    "US Treasury 7-10Y (IEF)": "IEF",
    "Gold (GLD)": "GLD",
    "Crude Oil (USO)": "USO",
    "FTSE 100 (ISF)": "ISF-GB",
    "Euro Stoxx 50 (FEZ)": "FEZ",
}

# MSCI index benchmarks  {display_name: "MSCI:<code>"}
MSCI_BENCHMARKS = {
    # Broad world
    "MSCI World": "MSCI:990100",
    "MSCI ACWI": "MSCI:892400",
    "MSCI World All Cap": "MSCI:144485",
    # Regions
    "MSCI North America": "MSCI:990200",
    "MSCI Europe": "MSCI:990500",
    "MSCI EMU": "MSCI:106400",
    "MSCI Pacific": "MSCI:990800",
    "MSCI EAFE": "MSCI:990300",
    "MSCI Nordic Countries": "MSCI:990700",
    # Emerging
    "MSCI Emerging Markets": "MSCI:891800",
    "MSCI EM Asia": "MSCI:899700",
    "MSCI EM Latin America": "MSCI:892000",
    "MSCI EM EMEA": "MSCI:123163",
    "MSCI Frontier Markets": "MSCI:136614",
    # Countries – Developed
    "MSCI USA": "MSCI:984000",
    "MSCI Canada": "MSCI:912400",
    "MSCI United Kingdom": "MSCI:982600",
    "MSCI Germany": "MSCI:928000",
    "MSCI France": "MSCI:925000",
    "MSCI Switzerland": "MSCI:975600",
    "MSCI Japan": "MSCI:939200",
    "MSCI Australia": "MSCI:903600",
    "MSCI Italy": "MSCI:938000",
    "MSCI Spain": "MSCI:972400",
    "MSCI Netherlands": "MSCI:952800",
    "MSCI Sweden": "MSCI:975200",
    "MSCI Denmark": "MSCI:920800",
    "MSCI Norway": "MSCI:957800",
    "MSCI Finland": "MSCI:924600",
    "MSCI Ireland": "MSCI:937200",
    "MSCI Belgium": "MSCI:905600",
    "MSCI Austria": "MSCI:904000",
    "MSCI Israel": "MSCI:300400",
    "MSCI Hong Kong": "MSCI:934400",
    "MSCI Singapore": "MSCI:998100",
    "MSCI New Zealand": "MSCI:955400",
    # Countries – Emerging
    "MSCI China": "MSCI:302400",
    "MSCI India": "MSCI:935600",
    "MSCI Taiwan": "MSCI:915800",
    "MSCI Korea": "MSCI:941000",
    "MSCI Brazil": "MSCI:907600",
    "MSCI Mexico": "MSCI:848400",
    "MSCI South Africa": "MSCI:971000",
    "MSCI Indonesia": "MSCI:105767",
    "MSCI Thailand": "MSCI:105769",
    "MSCI Malaysia": "MSCI:105768",
    "MSCI Philippines": "MSCI:860800",
    "MSCI Turkey": "MSCI:979200",
    "MSCI Poland": "MSCI:961600",
    "MSCI Saudi Arabia": "MSCI:705405",
    "MSCI Chile": "MSCI:915200",
    "MSCI Colombia": "MSCI:917000",
    "MSCI Peru": "MSCI:960400",
    "MSCI Egypt": "MSCI:105766",
    "MSCI Qatar": "MSCI:133715",
    "MSCI UAE": "MSCI:133717",
    "MSCI Kuwait": "MSCI:133713",
    "MSCI Vietnam": "MSCI:136647",
}

# Combined sorted list for dropdown
BENCHMARK_OPTIONS = sorted(
    [{"label": k, "value": v} for k, v in {**ETF_BENCHMARKS, **MSCI_BENCHMARKS}.items()],
    key=lambda x: x["label"],
)

FX_PAIRS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X", "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X", "EUR/GBP": "EURGBP=X",
}
BONDS = {
    "US 1-3Y (SHY)":  "SHY",
    "US 7-10Y (IEF)": "IEF",
    "US 20Y+ (TLT)":  "TLT",
}
COMMODITIES = {
    "Gold (GLD)": "GLD", "Silver (SLV)": "SLV", "Crude Oil (USO)": "USO",
    "Nat Gas (UNG)": "UNG", "Copper (CPER)": "CPER",
}
SECTOR_ETFS = {
    "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF",
    "Energy": "XLE", "Consumer Disc.": "XLY", "Consumer Staples": "XLP",
    "Industrials": "XLI", "Materials": "XLB", "Utilities": "XLU",
    "Real Estate": "XLRE", "Comm. Services": "XLC",
}

# ── FTSE 100 tickers (FactSet region format) ────────────────────────────────
FTSE100_TICKERS = [
    "AAF-GB","AAL-GB","ABF-GB","ADM-GB","AHT-GB","ANTO-GB","AUTO-GB","AV-GB","AZN-GB",
    "BA-GB","BARC-GB","BATS-GB","BDEV-GB","BEZ-GB","BKG-GB","BME-GB","BNZL-GB","BP-GB",
    "BRBY-GB","BT.A-GB","CCH-GB","CNA-GB","CPG-GB","CRDA-GB","CRH-GB",
    "DARK-GB","DCC-GB","DGE-GB","DPH-GB","EDV-GB","ENT-GB","EXPN-GB","EZJ-GB",
    "FRAS-GB","FRES-GB","GLEN-GB","GSK-GB","HIK-GB","HLMA-GB","HLN-GB",
    "HSBA-GB","IAG-GB","ICG-GB","IHG-GB","III-GB","IMB-GB","INF-GB","ITRK-GB","JD-GB",
    "KGF-GB","LAND-GB","LGEN-GB","LLOY-GB","LSEG-GB","MKS-GB","MNDI-GB","MNG-GB",
    "NG-GB","NWG-GB","NXT-GB","PHNX-GB","PRU-GB","PSN-GB",
    "REL-GB","RIO-GB","RKT-GB","RR-GB","RTO-GB","SBRY-GB","SDR-GB","SGE-GB",
    "SHEL-GB","SKG-GB","SMIN-GB","SMT-GB","SN-GB","SPX-GB",
    "SSE-GB","STAN-GB","SVT-GB","TSCO-GB","TW-GB","ULVR-GB","UU-GB","VOD-GB",
    "WEIR-GB","WPP-GB","WTB-GB",
]

# ── Euro Stoxx 50 tickers (FactSet region format) ───────────────────────────
EUROSTOXX50_TICKERS = [
    "ABI-BE","AD-NL","ADY-DE","AI-FR","AIR-FR","ALV-DE","ASML-NL","AXA-FR",
    "BAS-DE","BAYN-DE","BBVA-ES","BMW-DE","BN-FR","BNP-FR","CRG-IE","CS-FR",
    "DHL-DE","DTE-DE","ENEL-IT","ENGI-FR","ENI-IT","EL-FR","GLE-FR",
    "IBE-ES","IFX-DE","ISP-IT","ITX-ES","KER-FR","KN-FR","LIN-DE","MC-FR",
    "MBG-DE","MRK-DE","MUV2-DE","NOKIA-FI","OR-FR","ORA-FR","PHIA-NL",
    "RMS-FR","SAF-FR","SAN-FR","SAN-ES","SAP-DE","SIE-DE","SU-FR","TTE-FR",
    "UCG-IT","UMG-NL","VOW3-DE",
]

# ─────────────────────────────────────────────────────────────────────────────
# Screener universe — Full S&P 500 + International ADRs (~540 stocks)
# ─────────────────────────────────────────────────────────────────────────────
_RAW_UNIVERSE = [
    # ── S&P 500 constituents (alphabetical) ──────────────────────────────
    "A","AAPL","ABBV","ABNB","ABT","ACGL","ACN","ADBE","ADI","ADM",
    "ADP","ADSK","AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM",
    "ALB","ALGN","ALL","ALLE","AMAT","AMCR","AMD","AME","AMGN","AMZN",
    "AMT","ANET","AON","AOS","APA","APD","APH","APO","APTV",
    "ARE","ARM","ATO","AVGO","AVB","AVY","AWK","AXON","AXP","AZO",
    "BA","BAC","BALL","BAX","BBY","BDX","BEN","BG","BIIB","BK",
    "BKNG","BKR","BLK","BLDR","BMY","BR","BRK-B","BRO","BSX","BX","BXP",
    "C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE","CCI","CCL",
    "CDNS","CDW","CE","CF","CFG","CHD","CHRW","CHTR","CI","CINF",
    "CL","CLX","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF",
    "COO","COP","COR","COST","CPAY","CPB","CPRT","CPT","CRL","CRM",
    "CRWD","CSGP","CSCO","CSX","CTAS","CTRA","CTSH","CTVA","CVS","CVX","CZR",
    "D","DAL","DD","DDOG","DE","DECK","DELL","DG",
    "DGX","DHI","DHR","DIS","DLR","DLTR","DOC","DOV","DOW","DPZ",
    "DRI","DT","DVA","DVN","DXCM",
    "EA","EBAY","ECL","ED","EFX","EG","EIX","EL","ELV","EMN",
    "EMR","ENPH","EOG","EPAM","EQIX","EQR","EQT","ERIE","ES","ESS",
    "ETN","ETR","EW","EVRG","EXC","EXPD","EXPE","EXR",
    "F","FANG","FAST","FCNCA","FCX","FDS","FDX","FE","FFIV",
    "FICO","FIS","FITB","FOX","FOXA","FRT","FSLR","FTNT","FTV",
    "GD","GDDY","GE","GEHC","GEN","GEV","GILD","GIS","GL","GLW",
    "GM","GNRC","GOOG","GOOGL","GPC","GPN","GRMN","GS","GWW",
    "HAL","HAS","HBAN","HCA","HD","HOLX","HON","HPE","HPQ","HRL",
    "HSIC","HST","HSY","HUBB","HUM","HWM",
    "IBM","ICE","IDXX","IEX","IFF","INCY","INTC","INTU",
    "INVH","IP","IQV","IR","IRM","ISRG","IT","ITW","IVZ",
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

# S&P 500 only (exclude international ADRs) — first ~503 entries
SP500_TICKERS = [t for t in _RAW_UNIVERSE[:_RAW_UNIVERSE.index("ASML")]]
