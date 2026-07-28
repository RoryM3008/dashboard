"""Callbacks — Stock Moves page (regional quadrant + movers table)."""

import datetime as _dt

import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import dash
from dash import Input, Output, State, dcc, html

from theme import (
    FONT,
    FTSE100_TICKERS,
    EUROSTOXX50_TICKERS,
    SP500_TICKERS,
    get_theme,
)
from snowflake_data import fetch_movers_sf, fetch_msci_constituents


ASIA_TICKERS = [
    "7203-JP", "6758-JP", "9984-JP", "9983-JP", "8306-JP",
    "0700-HK", "9988-HK", "1299-HK", "0941-HK", "2318-HK",
    "005930-KR", "000660-KR", "035420-KR", "005380-KR", "051910-KR",
    "RELIANCE-IN", "TCS-IN", "HDFCBANK-IN", "INFY-IN", "ICICIBANK-IN",
    "BHP-AU", "CBA-AU", "WBC-AU", "NAB-AU", "CSL-AU",
]

# Nasdaq-100 proxy constituent list (kept in Yahoo/simple ticker format then converted)
NASDAQ100_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "AVGO", "COST", "TSLA",
    "NFLX", "TMUS", "ASML", "ADBE", "AMD", "CSCO", "PEP", "INTU", "QCOM", "TXN",
    "AMGN", "HON", "INTC", "AMAT", "BKNG", "PDD", "ISRG", "CMCSA", "GILD", "ADP",
    "VRTX", "LRCX", "MU", "PANW", "REGN", "MDLZ", "KLAC", "SNPS", "CRWD", "MELI",
    "ABNB", "MAR", "FTNT", "ORLY", "CDNS", "PYPL", "CTAS", "SBUX", "MSTR", "ADSK",
    "CSX", "AEP", "DXCM", "NXPI", "ROP", "WDAY", "KDP", "MNST", "AXON", "EXC",
    "FAST", "ROST", "IDXX", "CPRT", "PAYX", "FANG", "PCAR", "ODFL", "CHTR", "CCEP",
    "BKR", "TEAM", "DDOG", "KHC", "LULU", "XEL", "DASH", "GEHC", "EA", "ZS",
    "GFS", "TTD", "ANSS", "ON", "KMB", "MRVL", "BIIB", "DLTR", "MCHP", "WBD",
    "ILMN", "CSGP", "VRSK", "TTWO", "ARM", "MDB", "SPLK", "SIRI", "CDW", "ALGN",
]

DOW30_TICKERS = [
    "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "GS",
    "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT",
    "NKE", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT", "AMZN", "NVDA",
]

# DAX 40 (FactSet region format)
DAX_TICKERS = [
    "ADS-DE", "AIR-DE", "ALV-DE", "BAS-DE", "BAYN-DE", "BEI-DE", "BMW-DE", "BNR-DE", "CBK-DE", "CON-DE",
    "1COV-DE", "DTG-DE", "DB1-DE", "DBK-DE", "DHL-DE", "DTE-DE", "EOAN-DE", "FRE-DE", "FME-DE", "HEI-DE",
    "HEN3-DE", "IFX-DE", "MBG-DE", "MRK-DE", "MTX-DE", "MUV2-DE", "P911-DE", "PAH3-DE", "PUM-DE", "QIA-DE",
    "RHM-DE", "RWE-DE", "SAP-DE", "SRT3-DE", "SIE-DE", "ENR-DE", "SHL-DE", "SY1-DE", "VOW3-DE", "ZAL-DE",
]

# FTSE 250 proxy (Yahoo format). Used when user selects FTSE250 specifically.
FTSE250_PROXY_YF = [
    "BAB.L", "BBOX.L", "BTRW.L", "CTEC.L", "DOM.L", "DRX.L", "EMG.L", "ENQ.L", "GFRD.L", "HOC.L",
    "IGG.L", "JDW.L", "JUST.L", "LMP.L", "MGAM.L", "ONT.L", "OSB.L", "PLUS.L", "QQ.L", "RHIM.L",
    "SBRY.L", "SDR.L", "SMIN.L", "SXS.L", "TW.L", "UTG.L", "WEIR.L", "WIZZ.L",
]

# Nikkei 225 proxy (top constituents, Yahoo format)
NIKKEI225_YF = [
    "7203.T", "6758.T", "9984.T", "9983.T", "8306.T", "6861.T", "6902.T", "4063.T",
    "6501.T", "7741.T", "6367.T", "8035.T", "9433.T", "6098.T", "4502.T",
    "6954.T", "7267.T", "4568.T", "6273.T", "3382.T", "8001.T", "2914.T",
    "6503.T", "7974.T", "4901.T", "7751.T", "8058.T", "9432.T", "6762.T", "5108.T",
]

# KOSPI proxy (top constituents, Yahoo format)
KOSPI_YF = [
    "005930.KS", "000660.KS", "035420.KS", "005380.KS", "051910.KS",
    "006400.KS", "035720.KS", "003550.KS", "105560.KS", "055550.KS",
    "068270.KS", "028260.KS", "012330.KS", "066570.KS", "096770.KS",
    "015760.KS", "034730.KS", "003490.KS", "032830.KS", "009150.KS",
]

# Hang Seng proxy (top constituents, Yahoo format)
HANGSENG_YF = [
    "0700.HK", "9988.HK", "1299.HK", "0941.HK", "2318.HK",
    "0005.HK", "1398.HK", "0388.HK", "2628.HK", "0011.HK",
    "0016.HK", "0001.HK", "0003.HK", "0027.HK", "1109.HK",
    "0883.HK", "0386.HK", "1928.HK", "0017.HK", "0066.HK",
]

# S&P/ASX 200 proxy (top constituents, Yahoo format)
ASX200_YF = [
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "MQG.AX",
    "WES.AX", "WOW.AX", "FMG.AX", "TLS.AX", "RIO.AX", "ALL.AX", "GMG.AX",
    "TCL.AX", "WDS.AX", "STO.AX", "COL.AX", "QBE.AX", "SUN.AX",
    "REA.AX", "XRO.AX", "JHX.AX", "IAG.AX", "ORG.AX",
]

# Nifty 50 proxy (top constituents, Yahoo format)
NIFTY50_YF = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "TITAN.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
    "ADANIENT.NS", "HCLTECH.NS", "BAJAJFINSV.NS", "POWERGRID.NS", "NTPC.NS",
]

# CAC 40 proxy (Yahoo format)
CAC40_YF = [
    "MC.PA", "OR.PA", "RMS.PA", "AI.PA", "SU.PA", "AIR.PA", "SAN.PA",
    "BNP.PA", "CS.PA", "DG.PA", "RI.PA", "CAP.PA", "SGO.PA", "BN.PA",
    "EN.PA", "KER.PA", "SAF.PA", "VIV.PA", "ORA.PA", "ACA.PA",
    "ML.PA", "DSY.PA", "STM.PA", "PUB.PA", "GLE.PA",
]

# FTSE MIB proxy (Yahoo format)
FTSEMIB_YF = [
    "ISP.MI", "ENEL.MI", "ENI.MI", "UCG.MI", "STLAM.MI", "RACE.MI",
    "G.MI", "TEN.MI", "SRG.MI", "CPR.MI", "BAMI.MI", "PST.MI",
    "MB.MI", "MONC.MI", "PRY.MI", "AMP.MI", "A2A.MI", "BGN.MI",
    "LDO.MI", "SPM.MI",
]

# IBEX 35 proxy (Yahoo format)
IBEX35_YF = [
    "IBE.MC", "SAN.MC", "BBVA.MC", "ITX.MC", "TEF.MC", "REP.MC",
    "AMS.MC", "CABK.MC", "FER.MC", "ACS.MC", "GRF.MC", "MAP.MC",
    "ENG.MC", "RED.MC", "IAG.MC", "CLNX.MC", "ELE.MC", "MEL.MC",
    "COL.MC", "ACX.MC",
]

# SMI (Swiss Market Index) proxy (Yahoo format)
SMI_YF = [
    "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "CSGN.SW", "ABBN.SW",
    "ZURN.SW", "SIKA.SW", "GIVN.SW", "LONN.SW", "GEBN.SW", "CFR.SW",
    "PGHN.SW", "SLHN.SW", "SCMN.SW", "SREN.SW", "HOLN.SW", "BAER.SW",
    "SOON.SW", "LOGN.SW",
]

# Russell 2000 proxy (top small-cap names, Yahoo format)
RUSSELL2000_YF = [
    "SMCI", "CELH", "CVNA", "DUOL", "EXAS", "FND", "HALO", "KNSL",
    "LNTH", "MGNI", "NOVT", "OII", "PCVX", "QLYS", "RMBS", "SFM",
    "TMDX", "UPST", "VRNS", "WFRD", "XPEL", "YELP", "ZETA", "ACIW",
    "BOOT", "CARG", "DFH", "ENSG", "FORM", "GMS",
]

# S&P/TSX 60 proxy (Yahoo format)
TSX60_YF = [
    "RY.TO", "TD.TO", "ENB.TO", "CNR.TO", "BN.TO", "BMO.TO", "CP.TO",
    "SHOP.TO", "CSU.TO", "ATD.TO", "MFC.TO", "SU.TO", "TRI.TO", "ABX.TO",
    "BCE.TO", "CM.TO", "NTR.TO", "QSR.TO", "WCN.TO", "T.TO",
    "FNV.TO", "GIB-A.TO", "DOL.TO", "IFC.TO", "BAM.TO",
]

# MSCI ACWI proxy (top global holdings across regions)
MSCI_ACWI_YF = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "JPM", "V", "UNH",
    "ASML.AS", "MC.PA", "NESN.SW", "NOVN.SW", "SAP.DE", "AZN.L", "SHEL.L",
    "7203.T", "005930.KS", "0700.HK", "RELIANCE.NS", "BHP.AX", "RY.TO",
    "NOVO-B.CO", "ROG.SW", "OR.PA", "TCS.NS", "9984.T", "9988.HK", "CSL.AX",
]

# ── MSCI Index Codes (Snowflake constituents lookup) ──────────────────────────
# Key = dropdown value, Value = MSCI numeric index code
MSCI_INDEX_CODES = {
    # Broad
    "MSCI_ACWI": 892400,
    "MSCI_WORLD": 990100,
    "MSCI_EM": 891800,
    "MSCI_EAFE": 990300,
    # Regional
    "MSCI_NORTH_AMERICA": 990200,
    "MSCI_EUROPE": 990500,
    "MSCI_PACIFIC": 990800,
    "MSCI_EM_ASIA": 899700,
    "MSCI_NORDIC": 990700,
    # Country – Developed
    "MSCI_USA": 984000,
    "MSCI_JAPAN": 939200,
    "MSCI_UK": 982600,
    "MSCI_GERMANY": 928000,
    "MSCI_FRANCE": 925000,
    "MSCI_SWITZERLAND": 975600,
    "MSCI_CANADA": 912400,
    "MSCI_AUSTRALIA": 903600,
    "MSCI_ITALY": 938000,
    "MSCI_SPAIN": 972400,
    "MSCI_NETHERLANDS": 952800,
    "MSCI_SWEDEN": 975200,
    "MSCI_DENMARK": 920800,
    "MSCI_HONG_KONG": 934400,
    "MSCI_ISRAEL": 300400,
    # Country – Emerging
    "MSCI_CHINA": 302400,
    "MSCI_KOREA": 941000,
    "MSCI_INDIA": 935600,
    "MSCI_TAIWAN": 915800,
    "MSCI_BRAZIL": 907600,
    "MSCI_MEXICO": 848400,
    "MSCI_SOUTH_AFRICA": 971000,
    "MSCI_INDONESIA": 105767,
    "MSCI_SAUDI_ARABIA": 705405,
    # Sector (World) – stored as (parent_code, gics_sector_code)
    # These don't exist as standalone codes; derived from MSCI World (990100) + GICS sector filter
    "MSCI_ENERGY": (990100, 10),
    "MSCI_MATERIALS": (990100, 15),
    "MSCI_INDUSTRIALS": (990100, 20),
    "MSCI_CONS_DISC": (990100, 25),
    "MSCI_CONS_STAPLES": (990100, 30),
    "MSCI_HEALTH_CARE": (990100, 35),
    "MSCI_FINANCIALS": (990100, 40),
    "MSCI_INFO_TECH": (990100, 45),
    "MSCI_COMM_SERVICES": (990100, 50),
    "MSCI_UTILITIES": (990100, 55),
    "MSCI_REAL_ESTATE": (990100, 60),
}

# YF proxy fallback tickers for each MSCI index (used if Snowflake fails)
MSCI_YF_FALLBACK = {
    "MSCI_ACWI": MSCI_ACWI_YF,
    "MSCI_WORLD": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "UNH", "V", "ASML.AS", "SAP.DE", "MC.PA", "NESN.SW", "AZN.L", "SHEL.L", "NOVN.SW", "7203.T", "ROG.SW", "NOVO-B.CO", "RY.TO"],
    "MSCI_EM": ["0700.HK", "9988.HK", "005930.KS", "RELIANCE.NS", "TCS.NS", "2330.TW", "BABA", "PDD", "INFY.NS", "ICICIBANK.NS", "3690.HK", "1211.HK", "VALE3.SA", "ITUB4.SA", "000660.KS", "2317.TW", "2454.TW", "1299.HK", "0941.HK", "2318.HK"],
    "MSCI_EAFE": ["ASML.AS", "SAP.DE", "MC.PA", "NESN.SW", "AZN.L", "SHEL.L", "NOVN.SW", "7203.T", "ROG.SW", "NOVO-B.CO", "OR.PA", "RMS.PA", "BP.L", "ALV.DE", "HSBA.L", "6758.T", "9984.T", "DTE.DE", "SIE.DE", "BHP.AX"],
    "MSCI_NORTH_AMERICA": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "UNH", "V", "TSLA", "XOM", "JNJ", "PG", "HD", "MA", "RY.TO", "TD.TO", "ENB.TO", "BN.TO", "SHOP.TO"],
    "MSCI_EUROPE": ["ASML.AS", "SAP.DE", "MC.PA", "NESN.SW", "AZN.L", "SHEL.L", "NOVN.SW", "NOVO-B.CO", "ROG.SW", "OR.PA", "RMS.PA", "ALV.DE", "DTE.DE", "SIE.DE", "BP.L", "HSBA.L", "BNP.PA", "SAN.PA", "AIR.PA", "IBE.MC"],
    "MSCI_PACIFIC": ["7203.T", "6758.T", "9984.T", "9983.T", "8306.T", "BHP.AX", "CBA.AX", "CSL.AX", "6861.T", "7741.T", "6367.T", "8035.T", "NAB.AX", "WBC.AX", "MQG.AX", "ANZ.AX", "0005.HK", "0016.HK", "0388.HK", "0011.HK"],
    "MSCI_EM_ASIA": ["0700.HK", "9988.HK", "005930.KS", "2330.TW", "RELIANCE.NS", "TCS.NS", "PDD", "INFY.NS", "000660.KS", "2317.TW", "2454.TW", "1299.HK", "0941.HK", "2318.HK", "3690.HK", "1211.HK", "ICICIBANK.NS", "HDFCBANK.NS", "051910.KS", "035420.KS"],
    "MSCI_NORDIC": ["NOVO-B.CO", "VOLV-B.ST", "NESTE.HE", "ATCO-A.ST", "SAND.ST", "ABB.ST", "ERIC-B.ST", "INVE-B.ST", "DNB.OL", "EQNR.OL", "MAERSK-B.CO", "DSV.CO", "SEB-A.ST", "SWED-A.ST", "CARL-B.CO"],
    "MSCI_USA": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "UNH", "V", "TSLA", "XOM", "JNJ", "PG", "HD", "MA", "BAC", "KO", "PFE", "ABBV", "MRK"],
    "MSCI_JAPAN": ["7203.T", "6758.T", "9984.T", "9983.T", "8306.T", "6861.T", "6902.T", "4063.T", "6501.T", "7741.T", "6367.T", "8035.T", "9433.T", "6098.T", "4502.T", "6954.T", "7267.T", "4568.T", "6273.T", "3382.T", "7974.T", "4901.T", "7751.T", "8058.T", "9432.T"],
    "MSCI_UK": ["AZN.L", "SHEL.L", "BP.L", "HSBA.L", "ULVR.L", "RIO.L", "REL.L", "GSK.L", "LSEG.L", "DGE.L", "BA.L", "NG.L", "LLOY.L", "BARC.L", "VOD.L", "PRU.L", "RKT.L", "AAL.L", "ABF.L", "SSE.L"],
    "MSCI_GERMANY": ["SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MBG.DE", "MUV2.DE", "BAS.DE", "IFX.DE", "BMW.DE", "BAYN.DE", "ADS.DE", "DHL.DE", "DBK.DE", "HEN3.DE", "RWE.DE", "VOW3.DE", "EOAN.DE", "FRE.DE", "MTX.DE", "DB1.DE"],
    "MSCI_FRANCE": ["MC.PA", "OR.PA", "RMS.PA", "AI.PA", "SU.PA", "AIR.PA", "SAN.PA", "BNP.PA", "CS.PA", "DG.PA", "RI.PA", "CAP.PA", "SGO.PA", "BN.PA", "EN.PA", "KER.PA", "SAF.PA", "VIV.PA", "ORA.PA", "ACA.PA"],
    "MSCI_SWITZERLAND": ["NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ABBN.SW", "ZURN.SW", "SIKA.SW", "GIVN.SW", "LONN.SW", "GEBN.SW", "CFR.SW", "PGHN.SW", "SLHN.SW", "SCMN.SW", "SREN.SW", "HOLN.SW", "BAER.SW", "SOON.SW", "LOGN.SW", "TEMN.SW"],
    "MSCI_CANADA": ["RY.TO", "TD.TO", "ENB.TO", "CNR.TO", "BN.TO", "BMO.TO", "CP.TO", "SHOP.TO", "CSU.TO", "ATD.TO", "MFC.TO", "SU.TO", "TRI.TO", "ABX.TO", "BCE.TO", "CM.TO", "NTR.TO", "QSR.TO", "WCN.TO", "T.TO"],
    "MSCI_AUSTRALIA": ASX200_YF,
    "MSCI_ITALY": FTSEMIB_YF,
    "MSCI_SPAIN": IBEX35_YF,
    "MSCI_NETHERLANDS": ["ASML.AS", "PHIA.AS", "INGA.AS", "UNA.AS", "ABN.AS", "WKL.AS", "RAND.AS", "HEIA.AS", "AD.AS", "NN.AS", "PRX.AS", "DSM.AS", "AKZA.AS", "KPN.AS", "AGN.AS"],
    "MSCI_SWEDEN": ["VOLV-B.ST", "ATCO-A.ST", "SAND.ST", "ABB.ST", "ERIC-B.ST", "INVE-B.ST", "SEB-A.ST", "SWED-A.ST", "HM-B.ST", "HEXA-B.ST", "ALFA.ST", "ASSA-B.ST", "TEL2-B.ST", "BOL.ST", "SCA-B.ST"],
    "MSCI_DENMARK": ["NOVO-B.CO", "MAERSK-B.CO", "DSV.CO", "CARL-B.CO", "NZYM-B.CO", "VWS.CO", "ORSTED.CO", "COLO-B.CO", "PNDORA.CO", "ISS.CO", "GN.CO", "TRYG.CO", "JYSK.CO", "ROCK-B.CO", "DEMANT.CO"],
    "MSCI_HONG_KONG": HANGSENG_YF,
    "MSCI_ISRAEL": ["NICE.TA", "TEVA.TA", "CHECK.TA", "LUMI.TA", "HARL.TA", "BEZQ.TA", "ICL.TA", "ESLT.TA", "POLI.TA", "AZRG.TA"],
    "MSCI_CHINA": ["0700.HK", "9988.HK", "3690.HK", "1211.HK", "1810.HK", "2331.HK", "0968.HK", "1024.HK", "9618.HK", "9999.HK", "0241.HK", "2269.HK", "0981.HK", "1088.HK", "0001.HK", "BABA", "PDD", "JD", "BIDU", "NIO"],
    "MSCI_KOREA": KOSPI_YF,
    "MSCI_INDIA": NIFTY50_YF,
    "MSCI_TAIWAN": ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2881.TW", "2882.TW", "2303.TW", "1301.TW", "2886.TW", "3711.TW", "2891.TW", "2002.TW", "1303.TW", "2412.TW", "2884.TW", "5871.TW", "3008.TW", "2382.TW", "1326.TW", "6505.TW"],
    "MSCI_BRAZIL": ["VALE3.SA", "ITUB4.SA", "PETR4.SA", "BBDC4.SA", "B3SA3.SA", "ABEV3.SA", "WEGE3.SA", "RENT3.SA", "BBAS3.SA", "SUZB3.SA", "JBSS3.SA", "ELET3.SA", "RADL3.SA", "LREN3.SA", "RAIL3.SA"],
    "MSCI_MEXICO": ["FEMSAUBD.MX", "WALMEX.MX", "GFNORTEO.MX", "AMXB.MX", "CEMEXCPO.MX", "GMEXICOB.MX", "GAPB.MX", "ASURB.MX", "BIMBOA.MX", "KIMBERA.MX"],
    "MSCI_SOUTH_AFRICA": ["NPN.JO", "BTI.JO", "AGL.JO", "PRX.JO", "SOL.JO", "FSR.JO", "SBK.JO", "AMS.JO", "BHP.JO", "ABG.JO", "MTN.JO", "CFR.JO", "GLN.JO", "REM.JO", "SHP.JO"],
    "MSCI_INDONESIA": ["BBCA.JK", "BBRI.JK", "TLKM.JK", "BMRI.JK", "ASII.JK", "UNVR.JK", "BBNI.JK", "TPIA.JK", "ICBP.JK", "KLBF.JK"],
    "MSCI_SAUDI_ARABIA": ["2222.SR", "1180.SR", "2010.SR", "1120.SR", "2350.SR", "1010.SR", "2020.SR", "7010.SR", "1150.SR", "2380.SR"],
    # Sector fallbacks (use SPDR sector ETFs top holdings as proxy)
    "MSCI_ENERGY": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "PXD", "SHEL.L", "BP.L", "TTE.PA", "ENI.MI", "EQNR.OL"],
    "MSCI_MATERIALS": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "DOW", "CTVA", "IFF", "RIO.L", "BHP.AX", "AIR.PA", "BAS.DE", "GLEN.L"],
    "MSCI_INDUSTRIALS": ["GE", "CAT", "UNP", "RTX", "HON", "DE", "BA", "LMT", "UPS", "ADP", "SIE.DE", "AIR.PA", "SAF.PA", "DSV.CO", "RAND.AS"],
    "MSCI_CONS_DISC": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TJX", "LOW", "BKNG", "CMG", "MC.PA", "RMS.PA", "7203.T", "BMW.DE", "MBG.DE"],
    "MSCI_CONS_STAPLES": ["PG", "KO", "PEP", "COST", "WMT", "PM", "MDLZ", "CL", "EL", "KHC", "NESN.SW", "ULVR.L", "DGE.L", "OR.PA", "HEN3.DE"],
    "MSCI_HEALTH_CARE": ["UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "AZN.L", "NOVN.SW", "ROG.SW", "NOVO-B.CO", "GSK.L"],
    "MSCI_FINANCIALS": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "C", "AXP", "CB", "HSBA.L", "BNP.PA", "ALV.DE", "UBSG.SW", "8306.T"],
    "MSCI_INFO_TECH": ["AAPL", "MSFT", "NVDA", "AVGO", "ADBE", "CRM", "AMD", "INTC", "QCOM", "TXN", "ASML.AS", "SAP.DE", "005930.KS", "2330.TW", "IFX.DE"],
    "MSCI_COMM_SERVICES": ["META", "GOOGL", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "DTE.DE", "0700.HK", "VOD.L", "VIV.PA", "9984.T"],
    "MSCI_UTILITIES": ["NEE", "SO", "DUK", "AEP", "D", "SRE", "EXC", "XEL", "WEC", "ED", "IBE.MC", "ENEL.MI", "EOAN.DE", "NG.L", "SSE.L"],
    "MSCI_REAL_ESTATE": ["PLD", "AMT", "EQIX", "CCI", "PSA", "O", "SPG", "WELL", "DLR", "AVB", "SGRO.L", "LAND.L", "VNA.DE", "URW.AS", "GMG.AX"],
}

MARKET_MAP = {
    "AMERICAS": SP500_TICKERS,
    "EUROPE": sorted(set(FTSE100_TICKERS + EUROSTOXX50_TICKERS)),
    "ASIA": ASIA_TICKERS,
    "SP500": SP500_TICKERS,
    "NASDAQ100": NASDAQ100_TICKERS,
    "DOW30": DOW30_TICKERS,
    "EUROSTOXX50": EUROSTOXX50_TICKERS,
    "FTSE100": FTSE100_TICKERS,
    "DAX": DAX_TICKERS,
}

MARKET_MAP_YF_ONLY = {
    "FTSE250": FTSE250_PROXY_YF,
    "NIKKEI225": NIKKEI225_YF,
    "KOSPI": KOSPI_YF,
    "HANGSENG": HANGSENG_YF,
    "ASX200": ASX200_YF,
    "NIFTY50": NIFTY50_YF,
    "CAC40": CAC40_YF,
    "FTSEMIB": FTSEMIB_YF,
    "IBEX35": IBEX35_YF,
    "SMI": SMI_YF,
    "RUSSELL2000": RUSSELL2000_YF,
    "TSX60": TSX60_YF,
    "MSCI_ACWI": MSCI_ACWI_YF,
}

REGION_COLOURS = {
    "AMERICAS": "#58a6ff",
    "EUROPE": "#f0b429",
    "ASIA": "#39d353",
    "SP500": "#3b82f6",
    "NASDAQ100": "#0ea5e9",
    "DOW30": "#2563eb",
    "EUROSTOXX50": "#f59e0b",
    "FTSE100": "#f59e0b",
    "FTSE250": "#fb923c",
    "DAX": "#a78bfa",
    "CAC40": "#e879f9",
    "FTSEMIB": "#34d399",
    "IBEX35": "#f97316",
    "SMI": "#ec4899",
    "NIKKEI225": "#f472b6",
    "KOSPI": "#22d3ee",
    "HANGSENG": "#facc15",
    "ASX200": "#4ade80",
    "NIFTY50": "#fb7185",
    "RUSSELL2000": "#818cf8",
    "TSX60": "#2dd4bf",
    "MSCI_ACWI": "#e2e8f0",
    # MSCI indices
    "MSCI_WORLD": "#cbd5e1",
    "MSCI_EM": "#fbbf24",
    "MSCI_EAFE": "#a3e635",
    "MSCI_NORTH_AMERICA": "#60a5fa",
    "MSCI_EUROPE": "#fcd34d",
    "MSCI_PACIFIC": "#34d399",
    "MSCI_EM_ASIA": "#fb923c",
    "MSCI_NORDIC": "#93c5fd",
    "MSCI_USA": "#3b82f6",
    "MSCI_JAPAN": "#f472b6",
    "MSCI_UK": "#fbbf24",
    "MSCI_GERMANY": "#a78bfa",
    "MSCI_FRANCE": "#e879f9",
    "MSCI_SWITZERLAND": "#ec4899",
    "MSCI_CANADA": "#2dd4bf",
    "MSCI_AUSTRALIA": "#4ade80",
    "MSCI_ITALY": "#34d399",
    "MSCI_SPAIN": "#f97316",
    "MSCI_NETHERLANDS": "#fb923c",
    "MSCI_SWEDEN": "#93c5fd",
    "MSCI_DENMARK": "#67e8f9",
    "MSCI_HONG_KONG": "#facc15",
    "MSCI_ISRAEL": "#a5b4fc",
    "MSCI_CHINA": "#ef4444",
    "MSCI_KOREA": "#22d3ee",
    "MSCI_INDIA": "#fb7185",
    "MSCI_TAIWAN": "#5eead4",
    "MSCI_BRAZIL": "#84cc16",
    "MSCI_MEXICO": "#f97316",
    "MSCI_SOUTH_AFRICA": "#a3e635",
    "MSCI_INDONESIA": "#fde047",
    "MSCI_SAUDI_ARABIA": "#86efac",
    # MSCI Sectors
    "MSCI_ENERGY": "#f97316",
    "MSCI_MATERIALS": "#a78bfa",
    "MSCI_INDUSTRIALS": "#60a5fa",
    "MSCI_CONS_DISC": "#f472b6",
    "MSCI_CONS_STAPLES": "#4ade80",
    "MSCI_HEALTH_CARE": "#22d3ee",
    "MSCI_FINANCIALS": "#fbbf24",
    "MSCI_INFO_TECH": "#818cf8",
    "MSCI_COMM_SERVICES": "#fb923c",
    "MSCI_UTILITIES": "#86efac",
    "MSCI_REAL_ESTATE": "#fde047",
}

DEFAULT_HEADERS = {
    "ret_1d": "1D",
    "ret_5d": "5D",
    "ret_1wk": "1W",
    "ret_1mo": "1M",
    "ret_3mo": "3M",
    "ret_6mo": "6M",
    "ret_1yr": "1Y",
}

_FS_TO_YF_SUFFIX = {
    "US": "",
    "GB": ".L",
    "DE": ".DE",
    "FR": ".PA",
    "NL": ".AS",
    "ES": ".MC",
    "IT": ".MI",
    "FI": ".HE",
    "BE": ".BR",
    "IE": ".IR",
    "CH": ".SW",
    "SE": ".ST",
    "DK": ".CO",
    "JP": ".T",
    "HK": ".HK",
    "KR": ".KS",
    "IN": ".NS",
    "AU": ".AX",
    "CA": ".TO",
}


def _parse_pct(v):
    try:
        return float(str(v).replace("%", "").replace("+", "").strip())
    except Exception:
        return None


def _fs_to_yf_symbol(fs_ticker: str) -> str:
    if not fs_ticker:
        return ""
    if "-" not in fs_ticker:
        return fs_ticker
    base, region = fs_ticker.rsplit("-", 1)
    suf = _FS_TO_YF_SUFFIX.get(region.upper(), "")
    return f"{base}{suf}" if suf is not None else base


def _safe_num(x):
    try:
        if x is None:
            return None
        v = float(x)
        if pd.isna(v):
            return None
        return v
    except Exception:
        return None


def _ret_trading(close: pd.Series, n_days: int):
    if close is None or len(close) <= n_days:
        return None
    prev = _safe_num(close.iloc[-1 - n_days])
    last = _safe_num(close.iloc[-1])
    if prev in (None, 0) or last is None:
        return None
    return (last / prev - 1.0) * 100.0


def _ret_calendar(close: pd.Series, cal_days: int):
    if close is None or len(close) < 2:
        return None
    idx = pd.to_datetime(close.index)
    last_dt = idx[-1]
    target = last_dt - pd.Timedelta(days=int(cal_days))
    sub = close[idx <= target]
    if sub is None or len(sub) == 0:
        return None
    prev = _safe_num(sub.iloc[-1])
    last = _safe_num(close.iloc[-1])
    if prev in (None, 0) or last is None:
        return None
    return (last / prev - 1.0) * 100.0


def _ret_1d_live_vs_prev_close(tk, daily_close=None):
    """Best-effort live 1D return = (last available price / previous close - 1) * 100."""
    last_px = None
    prev_close = None

    # 1) Fast fields (usually quickest)
    try:
        fi = tk.fast_info or {}
        last_px = _safe_num(fi.get("lastPrice") or fi.get("last_price"))
        prev_close = _safe_num(fi.get("previousClose") or fi.get("previous_close"))
    except Exception:
        pass

    # 2) Fallback to info fields
    if last_px is None or prev_close is None:
        try:
            info = tk.info or {}
            if last_px is None:
                last_px = _safe_num(info.get("regularMarketPrice") or info.get("currentPrice"))
            if prev_close is None:
                prev_close = _safe_num(info.get("regularMarketPreviousClose") or info.get("previousClose"))
        except Exception:
            pass

    # 3) Last available trade from intraday bars
    if last_px is None:
        try:
            intraday = tk.history(period="2d", interval="5m", auto_adjust=False, prepost=False)
            if intraday is not None and not intraday.empty and "Close" in intraday.columns:
                close_i = intraday["Close"].dropna()
                if len(close_i) > 0:
                    last_px = _safe_num(close_i.iloc[-1])
        except Exception:
            pass

    # 4) Previous close from daily series if still missing
    if prev_close is None:
        try:
            close_d = daily_close if daily_close is not None else None
            if close_d is None or len(close_d) == 0:
                hist_d = tk.history(period="10d", interval="1d", auto_adjust=False)
                if hist_d is not None and not hist_d.empty and "Close" in hist_d.columns:
                    close_d = hist_d["Close"].dropna()
            if close_d is not None and len(close_d) > 0:
                prev_close = _safe_num(close_d.iloc[-1])
        except Exception:
            pass

    if last_px in (None, 0) or prev_close in (None, 0):
        return None
    return (last_px / prev_close - 1.0) * 100.0


def _last_available_price(tk, daily_close=None):
    """Best-effort latest tradable price (live/intraday, then recent close)."""
    px = None
    try:
        fi = tk.fast_info or {}
        px = _safe_num(fi.get("lastPrice") or fi.get("last_price"))
    except Exception:
        pass

    if px is None:
        try:
            info = tk.info or {}
            px = _safe_num(info.get("regularMarketPrice") or info.get("currentPrice"))
        except Exception:
            pass

    if px is None:
        try:
            intraday = tk.history(period="2d", interval="5m", auto_adjust=False, prepost=False)
            if intraday is not None and not intraday.empty and "Close" in intraday.columns:
                c = intraday["Close"].dropna()
                if len(c) > 0:
                    px = _safe_num(c.iloc[-1])
        except Exception:
            pass

    if px is None and daily_close is not None and len(daily_close) > 0:
        px = _safe_num(daily_close.iloc[-1])
    return px


def _enrich_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "y_symbol" not in df.columns:
        return df

    out = df.copy()
    metrics_by_symbol = {}
    symbols = sorted({s for s in out["y_symbol"].dropna().astype(str).tolist() if s})

    for sym in symbols:
        m = {
            "ret_1d": None, "ret_5d": None, "ret_1wk": None,
            "ret_1mo": None, "ret_3mo": None, "ret_6mo": None, "ret_1yr": None,
            "rel_vol_20d": None,
            "trailing_pe": None, "forward_pe": None, "price_sales": None,
            "stock_name": None, "sector": None, "industry": None, "current_price": None,
        }
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="2y", auto_adjust=False)
            if hist is not None and not hist.empty and "Close" in hist.columns:
                close = hist["Close"].dropna()
                if len(close) >= 2:
                    m["current_price"] = _last_available_price(tk, close)
                    m["ret_1d"] = _ret_1d_live_vs_prev_close(tk, close)
                    if m["ret_1d"] is None:
                        m["ret_1d"] = _ret_trading(close, 1)
                    m["ret_5d"] = _ret_trading(close, 5)
                    m["ret_1wk"] = _ret_calendar(close, 7)
                    m["ret_1mo"] = _ret_calendar(close, 30)
                    m["ret_3mo"] = _ret_calendar(close, 90)
                    m["ret_6mo"] = _ret_calendar(close, 182)
                    m["ret_1yr"] = _ret_calendar(close, 365)

            if hist is not None and not hist.empty and "Volume" in hist.columns:
                vol = hist["Volume"].dropna()
                if len(vol) >= 21:
                    v_last = _safe_num(vol.iloc[-1])
                    v_avg = _safe_num(vol.iloc[-21:-1].mean())
                    if v_last is not None and v_avg not in (None, 0):
                        m["rel_vol_20d"] = v_last / v_avg

            try:
                info = tk.info or {}
            except Exception:
                info = {}
            m["trailing_pe"] = _safe_num(info.get("trailingPE"))
            m["forward_pe"] = _safe_num(info.get("forwardPE"))
            m["price_sales"] = _safe_num(info.get("priceToSalesTrailing12Months"))
            m["stock_name"] = (
                info.get("shortName")
                or info.get("longName")
                or info.get("displayName")
                or sym
            )
            m["sector"] = info.get("sectorDisp") or info.get("sector")
            m["industry"] = info.get("industryDisp") or info.get("industry")
        except Exception:
            pass

        metrics_by_symbol[sym] = m

    for col in ["ret_1d", "ret_5d", "ret_1wk", "ret_1mo", "ret_3mo", "ret_6mo", "ret_1yr",
                "rel_vol_20d", "trailing_pe", "forward_pe", "price_sales",
            "stock_name", "sector", "industry", "current_price"]:
        out[col] = out["y_symbol"].map(lambda s, k=col: metrics_by_symbol.get(s, {}).get(k))

    # Keep 1D mover return from Snowflake as fallback if yfinance does not return 1D.
    # `ret_1d` is intended to be live last available price vs previous close.
    out["ret_1d"] = out["ret_1d"].fillna(out.get("chg"))
    out["stock_name"] = out["stock_name"].fillna(out.get("ticker"))
    out["sector"] = out["sector"].fillna("—")
    out["industry"] = out["industry"].fillna("—")
    return out


def _fetch_yf_fallback(market: str, ticker_list: list, topn: int) -> pd.DataFrame:
    """Fetch movers using yfinance for a list of Yahoo tickers."""
    rows = []
    for t in ticker_list:
        try:
            h = yf.Ticker(t).history(period="5d")
            if h is None or len(h) < 2:
                continue
            live = float(h["Close"].iloc[-1])
            prev = float(h["Close"].iloc[-2])
            if prev == 0:
                continue
            pct = (live / prev - 1.0) * 100.0
            rows.append({"ticker": t.split(".")[0], "chg": pct, "region": market,
                         "fs_ticker": "", "y_symbol": t})
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows).sort_values("chg", ascending=False)
    # If proxy list is small relative to topn, return everything
    if len(d) <= 2 * topn:
        return d.reset_index(drop=True)
    n_each = min(int(topn), len(d) // 2)
    gain = d.head(n_each)
    lose = d.tail(n_each)
    return pd.concat([gain, lose], ignore_index=True)


def _fetch_market_movers(market: str, topn: int, datasource: str) -> pd.DataFrame:
    # ── MSCI index: fetch constituents from Snowflake ──
    msci_code = MSCI_INDEX_CODES.get(market)
    if msci_code and datasource != "yf":
        try:
            # Sector indices are tuples: (parent_code, gics_sector)
            if isinstance(msci_code, tuple):
                parent_code, gics_sector = msci_code
                tickers = fetch_msci_constituents(parent_code, gics_sector=gics_sector)
            else:
                tickers = fetch_msci_constituents(msci_code)
            if tickers:
                prefix_map = {}
                for t in tickers:
                    p = str(t).split("-")[0]
                    if p not in prefix_map:
                        prefix_map[p] = t
                g_df, l_df = fetch_movers_sf(tickers, n=topn, prefix="")
                df = pd.concat([g_df, l_df], ignore_index=True)
                if not df.empty:
                    df["chg"] = df["Chg %"].map(_parse_pct)
                    df["ticker"] = df["Ticker"].astype(str)
                    df["region"] = market
                    df["fs_ticker"] = df["ticker"].map(lambda t: prefix_map.get(str(t), ""))
                    df["y_symbol"] = df["fs_ticker"].map(_fs_to_yf_symbol)
                    return df[["ticker", "chg", "region", "fs_ticker", "y_symbol"]].dropna(subset=["chg"])
        except Exception:
            pass
        # Fall through to yf_only proxy if MSCI SF fails
        yf_only = MSCI_YF_FALLBACK.get(market, [])
        if yf_only:
            return _fetch_yf_fallback(market, yf_only, topn)
        return pd.DataFrame()

    tickers = MARKET_MAP.get(market, [])
    yf_only = MARKET_MAP_YF_ONLY.get(market, [])
    if yf_only:
        tickers = yf_only
    if not tickers:
        return pd.DataFrame()

    # Display ticker prefix -> representative FactSet ticker for yfinance lookups.
    prefix_map = {}
    for t in tickers:
        p = str(t).split("-")[0]
        if p not in prefix_map:
            prefix_map[p] = t

    # Prefer Snowflake/FactSet; fall back to yfinance if user switched datasource.
    use_sf = (datasource != "yf") and (market not in MARKET_MAP_YF_ONLY)
    if use_sf:
        try:
            g_df, l_df = fetch_movers_sf(tickers, n=topn, prefix="")
            df = pd.concat([g_df, l_df], ignore_index=True)
            if df.empty:
                return df
            df["chg"] = df["Chg %"].map(_parse_pct)
            df["ticker"] = df["Ticker"].astype(str)
            df["region"] = market
            df["fs_ticker"] = df["ticker"].map(lambda t: prefix_map.get(str(t), ""))
            df["y_symbol"] = df["fs_ticker"].map(_fs_to_yf_symbol)
            return df[["ticker", "chg", "region", "fs_ticker", "y_symbol"]].dropna(subset=["chg"])
        except Exception:
            pass

    # Offline mode (rough fallback): use Yahoo tickers approximating each region.
    yf_map = {
        "AMERICAS": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "XOM", "UNH", "TSLA", "BRK-B", "V", "MA", "PG", "HD", "JNJ", "PFE", "KO", "BAC", "WMT"],
        "EUROPE": ["AZN.L", "SHEL.L", "BP.L", "HSBA.L", "VOD.L", "DTE.DE", "SAP.DE", "MC.PA", "OR.PA", "SAN.PA", "BNP.PA", "ASML.AS", "RMS.PA", "AIR.PA", "IBE.MC"],
        "ASIA": ["7203.T", "6758.T", "9984.T", "0700.HK", "9988.HK", "005930.KS", "000660.KS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "CBA.AX", "BHP.AX"],
        "SP500": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "XOM", "UNH", "TSLA", "BRK-B", "V", "MA", "PG", "HD", "JNJ", "PFE", "KO", "BAC", "WMT"],
        "NASDAQ100": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO", "TSLA", "NFLX", "ASML", "ADBE", "AMD", "COST", "QCOM", "TXN", "INTU", "AMAT", "BKNG", "MU", "PANW"],
        "DOW30": ["AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT", "AMZN", "NVDA"],
        "EUROSTOXX50": ["ASML.AS", "SAP.DE", "MC.PA", "OR.PA", "RMS.PA", "AIR.PA", "SAN.PA", "BNP.PA", "IBE.MC", "ISP.MI", "ENEL.MI", "SU.PA"],
        "FTSE100": ["AZN.L", "SHEL.L", "BP.L", "HSBA.L", "ULVR.L", "RIO.L", "REL.L", "GSK.L", "LSEG.L", "DGE.L"],
        "DAX": ["ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "DBK.DE", "DHL.DE", "DTE.DE", "IFX.DE", "SAP.DE", "SIE.DE", "VOW3.DE"],
        "FTSE250": FTSE250_PROXY_YF,
        "CAC40": CAC40_YF,
        "FTSEMIB": FTSEMIB_YF,
        "IBEX35": IBEX35_YF,
        "SMI": SMI_YF,
        "NIKKEI225": NIKKEI225_YF,
        "KOSPI": KOSPI_YF,
        "HANGSENG": HANGSENG_YF,
        "ASX200": ASX200_YF,
        "NIFTY50": NIFTY50_YF,
        "RUSSELL2000": RUSSELL2000_YF,
        "TSX60": TSX60_YF,
        "MSCI_ACWI": MSCI_ACWI_YF,
    }
    rows = []
    for t in yf_map.get(market, []):
        try:
            h = yf.Ticker(t).history(period="5d")
            if h is None or len(h) < 2:
                continue
            live = float(h["Close"].iloc[-1])
            prev = float(h["Close"].iloc[-2])
            if prev == 0:
                continue
            pct = (live / prev - 1.0) * 100.0
            rows.append({"ticker": t.split(".")[0], "chg": pct, "region": market,
                         "fs_ticker": "", "y_symbol": t})
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    d = pd.DataFrame(rows).sort_values("chg", ascending=False)
    # If proxy list is small relative to topn, return everything
    if len(d) <= 2 * topn:
        return d.reset_index(drop=True)
    n_each = min(int(topn), len(d) // 2)
    gain = d.head(n_each)
    lose = d.tail(n_each)
    return pd.concat([gain, lose], ignore_index=True)


def _build_quadrant(df: pd.DataFrame, c: dict, y_col: str, y_title: str, hover_metric_name: str, hover_raw_col: str):
    fig = go.Figure()

    if df.empty:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": FONT, "color": c["text"]},
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[{
                "text": "No mover data available.",
                "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                "showarrow": False, "font": {"size": 14, "color": c["muted"]},
            }],
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            height=560,
        )
        return fig

    # Build legend order: all known keys, then any remaining from data
    _ORDERED_KEYS = [
        "MSCI_ACWI", "MSCI_WORLD", "MSCI_EM", "MSCI_EAFE",
        "MSCI_NORTH_AMERICA", "MSCI_EUROPE", "MSCI_PACIFIC", "MSCI_EM_ASIA", "MSCI_NORDIC",
        "MSCI_USA", "MSCI_JAPAN", "MSCI_UK", "MSCI_GERMANY", "MSCI_FRANCE",
        "MSCI_SWITZERLAND", "MSCI_CANADA", "MSCI_AUSTRALIA", "MSCI_ITALY", "MSCI_SPAIN",
        "MSCI_NETHERLANDS", "MSCI_SWEDEN", "MSCI_DENMARK", "MSCI_HONG_KONG", "MSCI_ISRAEL",
        "MSCI_CHINA", "MSCI_KOREA", "MSCI_INDIA", "MSCI_TAIWAN", "MSCI_BRAZIL",
        "MSCI_MEXICO", "MSCI_SOUTH_AFRICA", "MSCI_INDONESIA", "MSCI_SAUDI_ARABIA",
        "MSCI_ENERGY", "MSCI_MATERIALS", "MSCI_INDUSTRIALS", "MSCI_CONS_DISC",
        "MSCI_CONS_STAPLES", "MSCI_HEALTH_CARE", "MSCI_FINANCIALS", "MSCI_INFO_TECH",
        "MSCI_COMM_SERVICES", "MSCI_UTILITIES", "MSCI_REAL_ESTATE",
        "AMERICAS", "EUROPE", "ASIA",
        "SP500", "NASDAQ100", "DOW30", "RUSSELL2000", "TSX60",
        "EUROSTOXX50", "FTSE100", "FTSE250", "DAX", "CAC40", "FTSEMIB", "IBEX35", "SMI",
        "NIKKEI225", "KOSPI", "HANGSENG", "ASX200", "NIFTY50",
    ]
    present = set(df["region"].astype(str))
    group_order = [k for k in _ORDERED_KEYS if k in present]
    # Add any leftover regions not in the ordered list
    group_order += [k for k in sorted(present) if k not in group_order]
    for region in group_order:
        d = df[df["region"] == region]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["chg"],
            y=d[y_col],
            mode="markers+text",
            name=region.title(),
            text=d["ticker"],
            textposition="top center",
            customdata=d[[hover_raw_col]].values,
            marker={
                "size": d["bubble"],
                "color": REGION_COLOURS.get(region, c["blue"]),
                "opacity": 0.75,
                "line": {"width": 1, "color": "#111"},
            },
            hovertemplate="%{text}<br>Return: %{x:.2f}%<br>" + hover_metric_name + ": %{customdata[0]:.2f}<br>Y-axis: %{y:.2f}<extra></extra>",
        ))

    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color=c["border"])
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color=c["border"])

    fig.add_annotation(x=0.99, y=0.96, xref="paper", yref="paper",
                       text="Strong Gainers", showarrow=False,
                       font={"size": 11, "color": c["green"]}, xanchor="right")
    fig.add_annotation(x=0.01, y=0.96, xref="paper", yref="paper",
                       text="Strong Losers", showarrow=False,
                       font={"size": 11, "color": c["red"]}, xanchor="left")
    fig.add_annotation(x=0.99, y=0.04, xref="paper", yref="paper",
                       text="Mild Gainers", showarrow=False,
                       font={"size": 10, "color": c["muted"]}, xanchor="right")
    fig.add_annotation(x=0.01, y=0.04, xref="paper", yref="paper",
                       text="Mild Losers", showarrow=False,
                       font={"size": 10, "color": c["muted"]}, xanchor="left")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT, "color": c["text"]},
        xaxis={
            "title": "1D Return (%)",
            "gridcolor": c["border"],
            "zeroline": False,
        },
        yaxis={
            "title": y_title,
            "gridcolor": c["border"],
            "zeroline": False,
        },
        legend={"orientation": "h", "y": 1.04, "x": 0.0},
        margin={"l": 55, "r": 20, "t": 35, "b": 45},
        height=560,
    )
    return fig


def _fmt_pct(v):
    x = _safe_num(v)
    if x is None:
        return "—"
    s = "+" if x >= 0 else ""
    return f"{s}{x:.2f}%"


def _fmt_price(v):
    x = _safe_num(v)
    if x is None:
        return "—"
    return f"{x:,.2f}"


_RET_COLS = ["ret_1d", "ret_5d", "ret_1wk", "ret_1mo", "ret_3mo", "ret_6mo", "ret_1yr"]


def _col_bg(val, col_min, col_max, col_med):
    """Cell background: green/red gradient normalised per-column."""
    v = _safe_num(val)
    if v is None:
        return "transparent", "inherit"
    # normalise: scale from 0 to 1 within the column's positive or negative range
    if v >= 0:
        denom = col_max - col_med if col_max != col_med else 1
        intensity = min(1.0, max(0.0, (v - col_med) / denom))
        alpha = 0.12 + intensity * 0.50
        return f"rgba(63,185,80,{alpha:.2f})", "#fff"
    else:
        denom = col_med - col_min if col_med != col_min else 1
        intensity = min(1.0, max(0.0, (col_med - v) / denom))
        alpha = 0.12 + intensity * 0.50
        return f"rgba(248,81,73,{alpha:.2f})", "#fff"


def _build_top_table(df: pd.DataFrame, c: dict, hdr: dict, sort_col: str = "ret_1d", sort_asc: bool = False):
    if df.empty:
        return html.Div()

    s = df.copy()
    s["ret_1d"] = s["ret_1d"].fillna(s["chg"])

    # Sort by chosen column
    if sort_col in s.columns:
        s = s.sort_values(sort_col, ascending=sort_asc, na_position="last").head(40)
    else:
        s = s.sort_values("ret_1d", ascending=False, na_position="last").head(40)

    # Pre-compute per-column stats for conditional formatting
    col_stats = {}
    for rc in _RET_COLS:
        if rc in s.columns:
            vals = s[rc].dropna()
            col_stats[rc] = (
                float(vals.min()) if len(vals) else 0.0,
                float(vals.max()) if len(vals) else 0.0,
                float(vals.median()) if len(vals) else 0.0,
            )
        else:
            col_stats[rc] = (0.0, 0.0, 0.0)

    th_base = {
        "padding": "0.32rem 0.45rem",
        "fontSize": "0.62rem",
        "fontFamily": FONT,
        "textTransform": "uppercase",
        "letterSpacing": "0.05em",
        "borderBottom": f"2px solid {c['border']}",
        "color": c["muted"],
        "textAlign": "left",
        "whiteSpace": "nowrap",
    }
    td = {
        "padding": "0.28rem 0.45rem",
        "fontSize": "0.76rem",
        "fontFamily": FONT,
        "borderBottom": f"1px solid {c['border']}",
    }

    def _sort_icon(rc):
        if rc != sort_col:
            return " ⇅"
        return " ↓" if not sort_asc else " ↑"

    def _th(label, col_key, align="right"):
        active = col_key == sort_col
        style = {
            **th_base,
            "textAlign": align,
            "cursor": "pointer",
            "color": c["accent"] if active else c["muted"],
            "borderBottom": f"2px solid {c['accent'] if active else c['border']}",
            "userSelect": "none",
        }
        return html.Th(
            [label, html.Span(_sort_icon(col_key), style={"opacity": "0.55", "fontSize": "0.58rem"})],
            style=style,
            id={"type": "moves-sort-th", "col": col_key},
            n_clicks=0,
        )

    rows = []
    for _, r in s.iterrows():
        def _cell(rc):
            bg, fg = _col_bg(r.get(rc), *col_stats[rc])
            return html.Td(
                _fmt_pct(r.get(rc)),
                style={**td,
                       "backgroundColor": bg,
                       "color": c["text"],
                       "textAlign": "right",
                       "fontFamily": "'Courier New', monospace",
                       "borderRadius": "3px"},
            )

        rows.append(html.Tr([
            html.Td(r["ticker"], style={**td, "color": c["accent"], "fontWeight": "700"}),
            html.Td(r.get("stock_name", "—"), style={**td, "color": c["text"], "maxWidth": "260px", "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"}),
            html.Td(r["region"], style={**td, "color": c["text"]}),
            html.Td(r.get("sector", "—"), style={**td, "color": c["text"], "opacity": "0.92"}),
            html.Td(r.get("industry", "—"), style={**td, "color": c["text"], "opacity": "0.88", "maxWidth": "280px", "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"}),
            html.Td(_fmt_price(r.get("current_price")), style={**td, "color": c["text"], "textAlign": "right", "fontFamily": "'Courier New', monospace"}),
            _cell("ret_1d"),
            _cell("ret_5d"),
            _cell("ret_1wk"),
            _cell("ret_1mo"),
            _cell("ret_3mo"),
            _cell("ret_6mo"),
            _cell("ret_1yr"),
        ]))

    return html.Div([
        html.Div(
            "Top movers snapshot  ·  click any column header to sort",
            style={"fontFamily": FONT, "fontSize": "0.72rem", "fontWeight": "700",
                   "color": c["muted"], "marginBottom": "0.35rem",
                   "textTransform": "uppercase", "letterSpacing": "0.05em"},
        ),
        html.Table([
            html.Thead(html.Tr([
                html.Th("Ticker", style={**th_base, "cursor": "default"}),
                html.Th("Stock", style={**th_base, "cursor": "default"}),
                html.Th("Market", style={**th_base, "cursor": "default"}),
                html.Th("Sector", style={**th_base, "cursor": "default"}),
                html.Th("Industry", style={**th_base, "cursor": "default"}),
                html.Th("Price", style={**th_base, "cursor": "default", "textAlign": "right"}),
                _th(hdr.get("ret_1d", "1D"),  "ret_1d"),
                _th(hdr.get("ret_5d", "5D"),  "ret_5d"),
                _th(hdr.get("ret_1wk", "1W"), "ret_1wk"),
                _th(hdr.get("ret_1mo", "1M"), "ret_1mo"),
                _th(hdr.get("ret_3mo", "3M"), "ret_3mo"),
                _th(hdr.get("ret_6mo", "6M"), "ret_6mo"),
                _th(hdr.get("ret_1yr", "1Y"), "ret_1yr"),
            ])),
            html.Tbody(rows),
        ], style={"width": "100%", "borderCollapse": "collapse"}),
    ], style={"overflowX": "auto"})


def register_callbacks(app):

    @app.callback(
        Output("moves-quadrant", "figure"),
        Output("moves-table", "children"),
        Output("moves-status", "children"),
        Output("moves-data-store", "data"),
        Input("moves-refresh", "n_clicks"),
        Input("theme-store", "data"),
        State("moves-markets", "value"),
        State("moves-topn", "value"),
        State("moves-y-metric", "value"),
        State("moves-hdr-1d", "value"),
        State("moves-hdr-5d", "value"),
        State("moves-hdr-1wk", "value"),
        State("moves-hdr-1mo", "value"),
        State("moves-hdr-3mo", "value"),
        State("moves-hdr-6mo", "value"),
        State("moves-hdr-1yr", "value"),
        State("datasource", "data"),
        State("moves-sort-store", "data"),
        prevent_initial_call=True,
    )
    def refresh_moves(_n, theme_mode, market_sel, topn, y_metric,
                      hdr_1d, hdr_5d, hdr_1wk, hdr_1mo, hdr_3mo, hdr_6mo, hdr_1yr,
                      datasource, sort_state):
        c = get_theme(theme_mode or "dark")
        topn = max(1, min(100, int(topn or 20)))
        y_metric = (y_metric or "relvol20").lower()
        hdr = {
            "ret_1d": (hdr_1d or DEFAULT_HEADERS["ret_1d"]).strip(),
            "ret_5d": (hdr_5d or DEFAULT_HEADERS["ret_5d"]).strip(),
            "ret_1wk": (hdr_1wk or DEFAULT_HEADERS["ret_1wk"]).strip(),
            "ret_1mo": (hdr_1mo or DEFAULT_HEADERS["ret_1mo"]).strip(),
            "ret_3mo": (hdr_3mo or DEFAULT_HEADERS["ret_3mo"]).strip(),
            "ret_6mo": (hdr_6mo or DEFAULT_HEADERS["ret_6mo"]).strip(),
            "ret_1yr": (hdr_1yr or DEFAULT_HEADERS["ret_1yr"]).strip(),
        }

        sel = market_sel or ["ALL"]
        if isinstance(sel, str):
            sel = [sel]
        if "ALL" in sel:
            regions = ["AMERICAS", "EUROPE", "ASIA"]
        else:
            valid = list(MARKET_MAP.keys()) + list(MARKET_MAP_YF_ONLY.keys()) + list(MSCI_INDEX_CODES.keys())
            regions = [x for x in sel if x in valid]
        if not regions:
            regions = ["AMERICAS", "EUROPE", "ASIA"]

        all_parts = []
        for r in regions:
            d = _fetch_market_movers(r, topn=topn, datasource=datasource or "sf")
            if not d.empty:
                all_parts.append(d)

        if not all_parts:
            fig = _build_quadrant(pd.DataFrame(), c, "strength", "Move Strength vs Regional Median", "Strength", "strength")
            return fig, html.Div(), "No data available for the selected market(s).", []

        df = pd.concat(all_parts, ignore_index=True)
        df = _enrich_metrics(df)
        # Ensure chart/table 1D uses live last-available vs previous close when available
        df["chg"] = df["ret_1d"].fillna(df["chg"])

        # Move strength = |chg| - regional median |chg| (quadrant Y axis)
        abs_chg = df["chg"].abs()
        df["regional_med"] = df.groupby("region")["chg"].transform(lambda s: s.abs().median())
        df["strength"] = abs_chg - df["regional_med"]
        df["bubble"] = (abs_chg.clip(lower=0.3, upper=12.0) / 12.0) * 24 + 8

        if y_metric == "relvol20":
            raw_col = "rel_vol_20d"
            y_title = "Relative Volume (20D) vs Regional Median"
            metric_name = "Rel Vol (x)"
        elif y_metric == "pe":
            raw_col = "trailing_pe"
            y_title = "Trailing P/E vs Regional Median"
            metric_name = "Trailing P/E"
        elif y_metric == "fpe":
            raw_col = "forward_pe"
            y_title = "Forward P/E vs Regional Median"
            metric_name = "Forward P/E"
        elif y_metric == "ps":
            raw_col = "price_sales"
            y_title = "Price/Sales vs Regional Median"
            metric_name = "Price/Sales"
        else:
            raw_col = "strength"
            y_title = "Move Strength vs Regional Median"
            metric_name = "Strength"

        if raw_col == "strength":
            df["y_value"] = df["strength"]
            df["metric_raw"] = df["strength"]
        else:
            med = df.groupby("region")[raw_col].transform("median")
            df["metric_raw"] = df[raw_col]
            df["y_value"] = df[raw_col] - med

        chart_df = df.dropna(subset=["chg", "y_value", "metric_raw"]).copy()

        sort_state = sort_state or {"col": "ret_1d", "asc": False}
        fig = _build_quadrant(chart_df, c, "y_value", y_title, metric_name, "metric_raw")
        table = _build_top_table(df, c, hdr,
                                  sort_col=sort_state.get("col", "ret_1d"),
                                  sort_asc=sort_state.get("asc", False))

        now = _dt.datetime.now().strftime("%d %b %Y %H:%M")
        status = f"Loaded {len(df)} movers across {len(regions)} market group(s) · Updated {now}"
        if "FTSE250" in regions:
            status += " · FTSE250 uses proxy basket"
        if raw_col != "strength":
            status += f" · Y-axis metric: {metric_name}"
        if (datasource or "sf") == "yf":
            status += " · Offline/yfinance mode"

        cached = df[[
            "ticker", "stock_name", "region", "sector", "industry", "current_price", "chg",
            "ret_1d", "ret_5d", "ret_1wk", "ret_1mo", "ret_3mo", "ret_6mo", "ret_1yr",
        ]].to_dict("records")

        return fig, table, status, cached
    # ── Sort: header click → update sort store → re-render table ─────────────
    @app.callback(
        Output("moves-sort-store", "data"),
        Output("moves-table", "children", allow_duplicate=True),
        Input({"type": "moves-sort-th", "col": dash.ALL}, "n_clicks"),
        State("moves-sort-store", "data"),
        State("moves-data-store", "data"),
        State("moves-hdr-1d",  "value"),
        State("moves-hdr-5d",  "value"),
        State("moves-hdr-1wk", "value"),
        State("moves-hdr-1mo", "value"),
        State("moves-hdr-3mo", "value"),
        State("moves-hdr-6mo", "value"),
        State("moves-hdr-1yr", "value"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def sort_table(n_clicks_list, sort_state, cached_records,
                   hdr_1d, hdr_5d, hdr_1wk, hdr_1mo, hdr_3mo, hdr_6mo, hdr_1yr,
                   theme_mode):
        from dash import no_update
        ctx = dash.callback_context
        if not ctx.triggered or not any(n or 0 for n in (n_clicks_list or [])):
            return no_update, no_update

        import re
        triggered_id = ctx.triggered[0]["prop_id"]
        m = re.search(r'"col":\s*"([^"]+)"', triggered_id)
        clicked_col = m.group(1) if m else "ret_1d"

        sort_state = sort_state or {"col": "ret_1d", "asc": False}
        new_asc = (not sort_state.get("asc", False)) if sort_state.get("col") == clicked_col else False
        new_sort = {"col": clicked_col, "asc": new_asc}

        if not cached_records:
            return new_sort, no_update

        c = get_theme(theme_mode or "dark")
        hdr = {
            "ret_1d":  (hdr_1d  or DEFAULT_HEADERS["ret_1d"]).strip(),
            "ret_5d":  (hdr_5d  or DEFAULT_HEADERS["ret_5d"]).strip(),
            "ret_1wk": (hdr_1wk or DEFAULT_HEADERS["ret_1wk"]).strip(),
            "ret_1mo": (hdr_1mo or DEFAULT_HEADERS["ret_1mo"]).strip(),
            "ret_3mo": (hdr_3mo or DEFAULT_HEADERS["ret_3mo"]).strip(),
            "ret_6mo": (hdr_6mo or DEFAULT_HEADERS["ret_6mo"]).strip(),
            "ret_1yr": (hdr_1yr or DEFAULT_HEADERS["ret_1yr"]).strip(),
        }
        df = pd.DataFrame(cached_records)
        table = _build_top_table(df, c, hdr, sort_col=clicked_col, sort_asc=new_asc)
        return new_sort, table