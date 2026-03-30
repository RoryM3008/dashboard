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
# Screener universe (~200 major US + International stocks)
# ─────────────────────────────────────────────────────────────────────────────
_RAW_UNIVERSE = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B","JPM","V",
    "XOM","UNH","MA","JNJ","PG","HD","AVGO","MRK","LLY","ABBV",
    "CVX","PEP","KO","COST","WMT","BAC","MCD","CRM","ACN","TMO",
    "CSCO","ABT","NKE","NFLX","ADBE","AMD","QCOM","TXN","DHR","LIN",
    "NEE","PM","RTX","AMGN","SPGI","HON","UPS","INTC","CAT","INTU",
    "IBM","GS","MS","BLK","SCHW","AXP","C","WFC","USB","PNC",
    "DE","MMM","BA","GE","LMT","NOC","GD","PFE","GILD","BIIB",
    "REGN","VRTX","ISRG","SYK","ZTS","BSX","MDT","AMT","PLD","CCI",
    "EQIX","SPG","O","DLR","WELL","PSA","DIS","CMCSA","T","VZ",
    "CVS","CI","HUM","ELV","HCA","F","GM","WM","RSG","ECL",
    "EMR","ETN","PH","ROK","PYPL","SQ","COIN","MELI","SE","GRAB",
    "SBUX","CMG","DRI","SNOW","PLTR","DDOG","NET","CRWD","ZS","PANW",
    "FTNT","OKTA","UBER","LYFT","ABNB","BKNG","EXPE","DASH","RBLX",
    "ORCL","NOW","WDAY","HUBS","TEAM","VEEV","CDNS","SNPS",
    # International ADRs
    "ASML","TSM","BABA","JD","PDD","BIDU","NIO","XPEV","TCEHY",
    "SONY","SNY","NVS","RHHBY","AZN","GSK","BP","SHEL",
    "HSBC","UBS","DB","BCS","SAN","ING",
    "SAP","SHOP","ENB","TD","RY","BNS","BMO","CM","MFC",
    "INFY","WIT","HDB","IBN","VALE","ITUB","NU",
    "RIO","BHP","GLEN",
]
_seen_u = set()
SCREENER_UNIVERSE = [t for t in _RAW_UNIVERSE if not (t in _seen_u or _seen_u.add(t))]
