# Snowflake Data Catalogue
## Available databases, schemas, and key views accessible by RORYMCMULLAN

*Auto-discovered on 2026-04-24*

---

## Connection Details
- **Account:** `ja91996.west-europe.privatelink`
- **User:** `RORY.MCMULLAN@MEDIOLANUM.IE`
- **Warehouse:** `PROD_EDW_LOAD`
- **Role:** `PROD_MED_BUSINESS_ANALYST`
- **Auth:** `externalbrowser` (SSO)

---

## Databases
| Database | Description |
|---|---|
| FACTSET | FactSet market data (prices, fundamentals, estimates, events) |
| FACTSET_CUSTOM | Custom FactSet data |
| MSCI | MSCI ESG ratings, index data, Barra analytics |
| PROD_MED_DATAHUB | Internal Mediolanum data (funds, clients, instruments) |
| FINANCE_ECONOMICS | Cybersyn economic data |
| SEC_FILINGS | Cybersyn SEC filings data |
| DEV_MED_AI | Dev AI database |
| USER$RORYMCMULLAN | Personal scratch database |

---

## FACTSET.FP_V2 — Prices & Returns (11 views)
| View | Description | Key Columns |
|---|---|---|
| `FP_BASIC_PRICES` | **Daily OHLCV prices** | FSYM_ID, P_DATE, P_PRICE, P_PRICE_OPEN, P_PRICE_HIGH, P_PRICE_LOW, P_VOLUME |
| `FP_TOTAL_RETURNS_DAILY` | Total return index (price + dividends reinvested) | FSYM_ID, P_DATE |
| `FP_TOTAL_RETURNS_CAGR` | Compound annual growth rates | FSYM_ID |
| `FP_BASIC_DIVIDENDS` | Dividend history (ex-date, amount, frequency) | FSYM_ID |
| `FP_BASIC_SPLITS` | Stock split history | FSYM_ID |
| `FP_BASIC_SHARES_CURRENT` | Current shares outstanding | FSYM_ID |
| `FP_BASIC_SHARES_HIST` | Historical shares outstanding | FSYM_ID |
| `FP_PRICES_LAST_EXCH` | Last exchange price | FSYM_ID |
| `FP_SEC_COVERAGE` | Security coverage metadata | FSYM_ID |
| `FP_SEC_ENTITY` | Security → entity mapping | FSYM_ID, FACTSET_ENTITY_ID |
| `FP_SEC_ENTITY_HIST` | Historical security → entity mapping | FSYM_ID |

## FACTSET.FF_V3 — Fundamentals & Financials (52 views)
| View | Description |
|---|---|
| `FF_BASIC_AF` | **Annual financial statements** (revenue, net income, etc.) |
| `FF_BASIC_QF` | **Quarterly financial statements** |
| `FF_BASIC_SAF` | Semi-annual financials |
| `FF_BASIC_LTM` | **Last twelve months** financials |
| `FF_BASIC_CF` | Cash flow statement |
| `FF_BASIC_DER_AF` | **Derived ratios (annual)** — P/E, EV/EBITDA, ROE, margins |
| `FF_BASIC_DER_QF` | Derived ratios (quarterly) |
| `FF_BASIC_DER_LTM` | Derived ratios (LTM) |
| `FF_BASIC_DER_R_*` | Restated derived ratios (AF, QF, LTM, SAF, YTD) |
| `FF_ADVANCED_*` | Advanced financials (more granular line items) |
| `FF_ENTITY_PROFILES` | **Company profiles** — name, sector, description, country |
| `FF_SEC_COVERAGE` | Coverage metadata |
| `FF_SEC_ENTITY` / `_HIST` | Security ↔ entity mapping |
| `FF_SEC_MAP` | Security mapping |
| `FF_BALANCE_MODEL` | Balance sheet model |
| `FF_SEGBUS_AF` | Business segment data (annual) |
| `FF_SEGREG_AF` | Geographic segment data (annual) |

## FACTSET.FE_V4 — Estimates & Consensus (24 views)
| View | Description |
|---|---|
| `FE_BASIC_CONH_AF` | **Consensus estimates (annual)** — EPS, revenue, EBITDA |
| `FE_BASIC_CONH_QF` | Consensus estimates (quarterly) |
| `FE_BASIC_CONH_SAF` | Consensus estimates (semi-annual) |
| `FE_BASIC_CONH_REC` | **Analyst recommendations** (buy/hold/sell, target price) |
| `FE_BASIC_CONH_LT` | **Long-term growth estimates** |
| `FE_BASIC_ACT_AF` | Actual reported values (annual) |
| `FE_BASIC_ACT_QF` | Actual reported values (quarterly) |
| `FE_BASIC_GUID_AF` | Company guidance (annual) |
| `FE_BASIC_GUID_QF` | Company guidance (quarterly) |
| `FE_ADVANCED_*` | Advanced estimate data (more items) |
| `FE_SEC_COVERAGE` | Estimate coverage metadata |

## FACTSET.SYM_V1 — Security Master / Identifiers (15 views)
| View | Description |
|---|---|
| `SYM_TICKER_REGION` | **Ticker → FSYM_ID mapping** (e.g. AAPL-US → FSYM_ID) |
| `SYM_TICKER_EXCHANGE` | Ticker by exchange |
| `SYM_ENTITY` | Entity master (company name, type) |
| `SYM_ENTITY_SECTOR` | **FactSet sector/industry classification** |
| `SYM_ENTITY_SECTOR_RBICS` | **RBICS industry classification** (more granular) |
| `SYM_ISIN` / `SYM_ISIN_HIST` | ISIN identifiers |
| `SYM_CUSIP` / `SYM_CUSIP_HIST` | CUSIP identifiers |
| `SYM_COVERAGE` | Coverage metadata |
| `SYM_ADDRESS` | Company address/location |
| `SYM_REGION` | Region mapping |
| `SYM_MERGED_ENTITY_ID` | Merged entity tracking (M&A) |
| `SYM_MERGED_FSYM_ID` | Merged security tracking |

## FACTSET.EVT_V1 — Corporate Events (11 views)
| View | Description |
|---|---|
| `CE_EVENTS` | **Upcoming/past events** (earnings calls, AGMs, conferences) |
| `CE_CONFERENCES` | Conference details |
| `CE_PARTICIPANTS` | Event participants |
| `CE_REPORTS` | Event reports |
| `CE_TRANSCRIPT_VERSIONS` | Earnings call transcript versions |
| `CE_REPORT_SLIDES` | Presentation slides |

## FACTSET.SA_V1 — StreetAccount News (11 views)
| View | Description |
|---|---|
| `SA_STORY` | **News stories** |
| `SA_CATEGORY` / `SA_CATEGORY_MAP` | Story categories |
| `SA_COUNTRY` | Country tagging |
| `SA_INDUSTRY` / `SA_INDUSTRY_MAP` | Industry tagging |
| `SA_REF_COMPANY` | Company references in stories |

## FACTSET.REF_V2 — Reference Data (155 views)
Lookup/mapping tables for codes used across FactSet:
- Country, currency, exchange, sector, industry maps
- Financial statement item definitions
- ETF classifications
- M&A deal types
- Calendar dates and holidays

---

## MSCI.ESG — ESG Ratings & Climate (273 views)
| View | Description |
|---|---|
| `ESG_RATINGS_T_SUMMARY_SCORES` | **ESG overall + pillar scores** |
| `ESG_RATINGS_T_DRILL_DOWN` | Key issue scores breakdown |
| `ESG_RATINGS_T_CONTROVERSIES` | Controversy flags |
| `ESG_RATINGS_T_GOVERNANCE_DATA` | Board composition, governance metrics |
| `ESG_RATINGS_T_WORKFORCE_AND_DIVERSITY` | Workforce/diversity metrics |
| `ESG_RATINGS_T_DERIVED_ESG_METRICS` | Derived ESG metrics |
| `CLIMATE_CARBON_EMISSIONS_AND_ENERGY_USE` | **Carbon emissions** (Scope 1, 2) |
| `CLIMATE_CARBON_EMISSIONS_SCOPE_3_ESTIMATES` | Scope 3 estimates |
| `CLIMATE_LOW_CARBON_TRANSITION_SCORES` | Low-carbon transition scores |
| `SCN_ANLYS_CORP_TEMPERATURE_ALIGNMENT` | Implied temperature rise |
| `EU_SUST_FIN_CORP_SFDR` | SFDR PAI indicators |
| `EU_SUST_FIN_CORP_EU_TAXONOMY*` | EU Taxonomy alignment |
| `FUND_RATINGS_*` | Fund-level ESG ratings |
| `GOVERNMENT_RATINGS_*` | Sovereign ESG ratings |

## MSCI.INDEX — Index Data (39 views)
| View | Description |
|---|---|
| `INDEX_CONSTITUENTS` | **Index membership** (which stocks in which MSCI index) |
| `INDEX_LEVELS` | **Index performance history** |
| `INDEX_MONTH_END` | Month-end index data |
| `INDEX_MONTH_END_PERFORMANCE` | Monthly index returns |
| `INDEX_FACS` | Index factor characteristics |
| `INDEX_ESG_METRICS` | Index-level ESG metrics |
| `SECURITY` | MSCI security master |
| `SECURITY_MONTH_END` | Security month-end data |
| `SECURITY_DIVIDENDS` | Dividend data |
| `SECURITY_EVENTS` | Corporate events |
| `CURRENCY_EXCHANGE_RATES` | FX rates |

## MSCI.ANALYTICS — Barra Risk Models (49 views)
| View | Description |
|---|---|
| `ASSET_EXPOSURES_TS` | **Factor exposures** per security (Barra factors) |
| `ASSET_BETAS_TS` | Security betas |
| `ASSET_SPECIFIC_VOLATILITY_TS` | Idiosyncratic volatility |
| `ASSET_SPECIFIC_RETURN_TS` | Specific returns |
| `ASSET_MARKET_DATA_TS` | Market data for risk model |
| `FACTOR_RETURNS_TS` | **Factor return series** |
| `FACTOR_COVARIANCE_TS` | Factor covariance matrix |
| `FACTOR_PORTFOLIO_TS` | Factor-mimicking portfolios |
| `ASSET_DESCRIPTORS_TS` | Style descriptors |
| `MODELS` | Available risk models |
| `FACTORS` | Factor definitions |

---

## PROD_MED_DATAHUB.DIMENSIONAL_WAREHOUSE — Internal Data (67 tables)
| Table | Description |
|---|---|
| `INSTRUMENT_DIMENSION` | Instrument/fund master |
| `INSTRUMENT_MONTHLY_METRICS` | Monthly fund performance |
| `SUB_FUND_DIMENSION` | Sub-fund master |
| `SUB_FUND_DAILY_METRICS` | Daily sub-fund NAV/returns |
| `SUB_FUND_MONTHLY_METRICS` | Monthly sub-fund metrics |
| `SHARE_CLASS_DIMENSION` | Share class master |
| `SHARE_CLASS_DAILY_METRICS` | Daily share class NAV |
| `SHARE_CLASS_MONTHLY_METRICS` | Monthly share class data |
| `CLIENT_ACCOUNT_*` | Client account data |
| `PORTFOLIO_*` | Portfolio positions and transactions |
| `FAMILY_BANKER_*` | Distributor/banker data |
| `DATE_DIMENSION` | Calendar dimension |
| `COUNTRY_DIMENSION` | Country reference |
| `CURRENCY_DIMENSION` | Currency reference |

---

## FINANCE_ECONOMICS.CYBERSYN — Economic Data
Cybersyn economic indicators, macro data

## SEC_FILINGS.CYBERSYN — SEC Filings
Cybersyn SEC filing data (10-K, 10-Q, 8-K, etc.)

---

## Common Joins
```sql
-- Ticker → FSYM_ID (the key join for all FactSet data)
FACTSET.SYM_V1.SYM_TICKER_REGION  (TICKER_REGION → FSYM_ID)

-- FSYM_ID → Entity (for fundamentals, estimates)
FACTSET.FP_V2.FP_SEC_ENTITY       (FSYM_ID → FACTSET_ENTITY_ID)

-- Entity → Sector
FACTSET.SYM_V1.SYM_ENTITY_SECTOR  (FACTSET_ENTITY_ID → SECTOR)

-- Example: Get AAPL's P/E ratio
SELECT d.* 
FROM FACTSET.SYM_V1.SYM_TICKER_REGION t
JOIN FACTSET.FP_V2.FP_SEC_ENTITY e ON t.FSYM_ID = e.FSYM_ID
JOIN FACTSET.FF_V3.FF_BASIC_DER_AF d ON e.FACTSET_ENTITY_ID = d.FSYM_ID
WHERE t.TICKER_REGION = 'AAPL-US'
ORDER BY d.DATE DESC
LIMIT 5;
```
