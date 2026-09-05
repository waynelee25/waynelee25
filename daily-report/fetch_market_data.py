#!/usr/bin/env python3
"""
每日金融數據抓取腳本
產出 market_data.json 供每日投資報告使用

安裝依賴：pip install yfinance pandas requests
執行方式：python fetch_market_data.py
"""

import json
import requests
import warnings
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("❌ 請先執行：pip install yfinance pandas requests")
    exit(1)

TW_TZ = ZoneInfo("Asia/Taipei")
NOW = datetime.now(TW_TZ)
TODAY_STR = NOW.strftime("%Y/%m/%d")
OUTPUT_FILE = "market_data.json"
PORTFOLIO_FILE = "portfolio.json"

# ── 讀取 portfolio.json 動態決定標的
with open(PORTFOLIO_FILE, encoding="utf-8") as _f:
    _portfolio = json.load(_f)

_tw_holdings = {s["ticker"]: s["name"] for s in _portfolio.get("taiwan_stocks", [])}
_us_holdings = [s["ticker"] for s in _portfolio.get("us_stocks", [])]
_watchlist_tw = _portfolio.get("watchlist_tw", [])   # e.g. ["台積電(2330)", ...]
_watchlist_us = _portfolio.get("watchlist_us", [])   # e.g. ["GOOGL", "NVDA", ...]

def _parse_tw_watchlist(items):
    """把 '台積電(2330)' 解析成 {'2330': '台積電'}"""
    out = {}
    for item in items:
        if "(" in item and item.endswith(")"):
            name, code = item[:-1].rsplit("(", 1)
            out[code.strip()] = name.strip()
    return out

_watchlist_tw_dict = _parse_tw_watchlist(_watchlist_tw)

print(f"📊 開始抓取市場數據 — {TODAY_STR}")

# ──────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────

def safe_round(val, digits=2):
    try:
        return round(float(val), digits) if val is not None else None
    except Exception:
        return None

def pct(val):
    return safe_round(val * 100) if val is not None else None

def get_price_data(ticker_symbol, period="6mo"):
    """取得個股/指數歷史價格與技術指標"""
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period=period)
        if hist.empty:
            return {"error": f"無法取得 {ticker_symbol} 數據"}

        # yfinance 有時會在當日附加一筆 Close=NaN 的佔位列（僅有成交量，
        # 收盤價尚未更新，常見於台股）。技術指標仍用乾淨數據計算，
        # 但 last_close 視為無效，讓呼叫端觸發 TWSE 官方 API 備援。
        has_valid_latest_bar = not pd.isna(hist["Close"].iloc[-1])
        hist = hist[hist["Close"].notna()]
        if hist.empty:
            return {"error": f"無法取得 {ticker_symbol} 數據"}

        close = hist["Close"]
        volume = hist["Volume"]
        last_close = safe_round(close.iloc[-1]) if has_valid_latest_bar else None
        prev_close = safe_round(close.iloc[-2]) if len(close) > 1 else close.iloc[-1]
        change = safe_round(last_close - prev_close) if last_close is not None else None
        change_pct = safe_round((last_close - prev_close) / prev_close * 100) if (last_close is not None and prev_close) else None

        # 均線
        def ma(n):
            return safe_round(close.rolling(n).mean().iloc[-1]) if len(close) >= n else None

        # RSI(14) — Wilder 平滑（標準算法）
        def rsi(n=14):
            delta = close.diff()
            gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
            rs = gain / loss
            r = 100 - (100 / (1 + rs))
            return safe_round(r.iloc[-1]) if len(close) >= n else None

        # MACD(12,26,9)
        def macd():
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            m = ema12 - ema26
            signal = m.ewm(span=9).mean()
            hist_macd = m - signal
            return {
                "macd": safe_round(m.iloc[-1]),
                "signal": safe_round(signal.iloc[-1]),
                "histogram": safe_round(hist_macd.iloc[-1]),
                "cross": "golden" if m.iloc[-1] > signal.iloc[-1] else "dead"
            }

        # KD(9)
        def kd(n=9):
            low_n = hist["Low"].rolling(n).min()
            high_n = hist["High"].rolling(n).max()
            rsv = (hist["Close"] - low_n) / (high_n - low_n) * 100
            k = rsv.ewm(com=2).mean()
            d = k.ewm(com=2).mean()
            return {"K": safe_round(k.iloc[-1]), "D": safe_round(d.iloc[-1])}

        # 52週高低
        hist_1y = tk.history(period="1y")
        week52_high = safe_round(hist_1y["High"].max()) if not hist_1y.empty else None
        week52_low = safe_round(hist_1y["Low"].min()) if not hist_1y.empty else None

        # 成交量比較（5日均量）
        avg_vol_5 = safe_round(volume.rolling(5).mean().iloc[-1])
        last_vol = int(volume.iloc[-1]) if not pd.isna(volume.iloc[-1]) else None
        vol_ratio = safe_round(last_vol / avg_vol_5) if avg_vol_5 and last_vol else None

        return {
            "last_close": last_close,
            "prev_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "volume": last_vol,
            "avg_volume_5d": safe_round(avg_vol_5),
            "volume_ratio": vol_ratio,
            "52w_high": week52_high,
            "52w_low": week52_low,
            "ma5": ma(5),
            "ma10": ma(10),
            "ma20": ma(20),
            "ma60": ma(60),
            "ma120": ma(120),
            "rsi14": rsi(),
            "macd": macd(),
            "kd": kd(),
        }
    except Exception as e:
        return {"error": str(e)}

def get_info(ticker_symbol):
    """取得基本面資訊"""
    try:
        tk = yf.Ticker(ticker_symbol)
        info = tk.info
        return {
            "name": info.get("longName") or info.get("shortName"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": safe_round(info.get("trailingPE")),
            "forward_pe": safe_round(info.get("forwardPE")),
            "eps_ttm": safe_round(info.get("trailingEps")),
            "eps_forward": safe_round(info.get("forwardEps")),
            "price_to_book": safe_round(info.get("priceToBook")),
            "revenue_growth": pct(info.get("revenueGrowth")),
            "gross_margin": pct(info.get("grossMargins")),
            "operating_margin": pct(info.get("operatingMargins")),
            "net_margin": pct(info.get("profitMargins")),
            "dividend_yield": pct(info.get("dividendYield")),
            "beta": safe_round(info.get("beta")),
            "short_ratio": safe_round(info.get("shortRatio")),
            "analyst_target": safe_round(info.get("targetMeanPrice")),
            "analyst_low": safe_round(info.get("targetLowPrice")),
            "analyst_high": safe_round(info.get("targetHighPrice")),
            "recommendation": info.get("recommendationKey"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception as e:
        return {"error": str(e)}

def get_twse_stock_price(stock_id):
    """從 TWSE MI_INDEX 抓台股收盤價（適用上市股票）"""
    for days_ago in range(0, 5):
        date = (NOW - timedelta(days=days_ago)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date={date}&type=ALLBUT0999"
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            d = r.json()
            if d.get("stat") != "OK":
                continue
            for table in d.get("tables", []):
                for row in table.get("data", []):
                    if str(row[0]).strip() == stock_id:
                        def parse_num(s):
                            try: return float(str(s).replace(",", ""))
                            except: return None
                        close = parse_num(row[8])
                        # row[9] 是漲跌方向的 HTML（color:red=漲, color:green=跌），row[10] 是漲跌價差絕對值
                        direction_html = str(row[9]) if len(row) > 9 else ""
                        change_abs = parse_num(row[10]) if len(row) > 10 else None
                        if change_abs is None:
                            change = None
                        elif "green" in direction_html:
                            change = -change_abs
                        elif "red" in direction_html:
                            change = change_abs
                        else:
                            change = 0.0
                        change_pct = safe_round(change / (close - change) * 100) if close and change else None
                        vol = parse_num(row[2]) if len(row) > 2 else None
                        return {
                            "last_close": close,
                            "change": change,
                            "change_pct": change_pct,
                            "volume": vol,
                            "date": date,
                            "source": "TWSE_MI_INDEX"
                        }
        except Exception as e:
            continue
    return {"error": f"無法取得 {stock_id} 收盤價"}

def get_twse_taiex_latest():
    """從 TWSE FMTQIK 抓大盤加權指數官方最新收盤（yfinance ^TWII 常常慢一個交易日）"""
    for days_ago in range(0, 40, 30):
        d = NOW - timedelta(days=days_ago)
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?response=json&date={d.strftime('%Y%m%d')}"
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()
            if data.get("stat") != "OK" or not data.get("data"):
                continue
            rows = data["data"]
            last = rows[-1]
            prev = rows[-2] if len(rows) > 1 else last

            def parse_num(s):
                try: return float(str(s).replace(",", ""))
                except: return None

            def roc_to_west(roc_date):
                # "115/08/18" -> "2026-08-18"
                y, m, dd = roc_date.split("/")
                return f"{int(y) + 1911}-{m}-{dd}"

            close = parse_num(last[4])
            change = parse_num(last[5])
            prev_close = parse_num(prev[4])
            change_pct = safe_round(change / prev_close * 100) if change is not None and prev_close else None
            return {
                "last_close": close,
                "prev_close": prev_close,
                "change": change,
                "change_pct": change_pct,
                "volume": parse_num(last[1]),
                "date": roc_to_west(last[0]),
                "source": "TWSE_FMTQIK",
            }
        except Exception:
            continue
    return None

def get_twse_institutional(stock_id):
    """台股三大法人買賣超（TWSE 開放資料）"""
    try:
        date_str = NOW.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=ALL"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        if data.get("stat") != "OK":
            # 嘗試前一個交易日
            prev = (NOW - timedelta(days=1)).strftime("%Y%m%d")
            url2 = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={prev}&selectType=ALL"
            r = requests.get(url2, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()

        if data.get("stat") != "OK":
            return {"error": "TWSE API 無數據"}

        fields = data.get("fields", [])
        rows = data.get("data", [])
        for row in rows:
            if row[0] == stock_id:
                def parse(val):
                    try:
                        return int(val.replace(",", "").replace("+", ""))
                    except Exception:
                        return None
                return {
                    "foreign_net": parse(row[4]),   # 外資買賣超
                    "invest_net": parse(row[10]),    # 投信買賣超
                    "dealer_net": parse(row[13]),    # 自營商買賣超（合計）
                    "total_net": parse(row[14]),     # 三大法人合計
                    "date": data.get("date", ""),
                }
        return {"error": f"找不到 {stock_id}"}
    except Exception as e:
        return {"error": str(e)}

def get_twse_margin(stock_id):
    """台股融資融券餘額"""
    try:
        date_str = NOW.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json&date={date_str}&selectType=ALL"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        if data.get("stat") != "OK":
            prev = (NOW - timedelta(days=1)).strftime("%Y%m%d")
            url2 = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json&date={prev}&selectType=ALL"
            r = requests.get(url2, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()

        # 找到第一個 table（融資）
        tables = data.get("tables", [])
        for table in tables:
            for row in table.get("data", []):
                if row[0] == stock_id:
                    def parse(val):
                        try:
                            return int(val.replace(",", ""))
                        except Exception:
                            return None
                    return {
                        "margin_balance": parse(row[3]),     # 融資餘額
                        "margin_change": parse(row[4]),      # 融資增減
                        "short_balance": parse(row[8]),      # 融券餘額
                        "short_change": parse(row[9]),       # 融券增減
                    }
        return {"error": f"找不到 {stock_id} 融資融券"}
    except Exception as e:
        return {"error": str(e)}

# ──────────────────────────────────────────────
# 開始抓取數據
# ──────────────────────────────────────────────

result = {
    "generated_at": NOW.isoformat(),
    "date": TODAY_STR,
    "us_markets": {},
    "tw_markets": {},
    "currencies": {},
    "bonds": {},
    "commodities": {},
    "my_portfolio": {},
}

# ── 美股指數
print("  📈 美股指數...")
indices_us = {
    "sp500":    "^GSPC",
    "nasdaq":   "^IXIC",
    "dow":      "^DJI",
    "russell":  "^RUT",
    "sox":      "^SOX",
    "vix":      "^VIX",
}
for name, sym in indices_us.items():
    result["us_markets"][name] = get_price_data(sym, period="3mo")

# ── 美股科技股（watchlist_us + 持倉，去重）
print("  💻 美股科技股（動態從 portfolio.json）...")
tech_us = list(dict.fromkeys(_watchlist_us + _us_holdings))
for sym in tech_us:
    result["us_markets"][sym] = get_price_data(sym, period="6mo")

# ── 美股基本面（持倉 + NVDA/MU 指標股）
print("  📋 基本面數據...")
info_tickers = list(dict.fromkeys(_us_holdings + ["NVDA", "MU"]))
for sym in info_tickers:
    result["us_markets"][f"{sym}_info"] = get_info(sym)

# ── 台股指數
print("  🇹🇼 台股指數...")
result["tw_markets"]["taiex"] = get_price_data("^TWII", period="3mo")
# yfinance ^TWII 常慢一個交易日（無佔位列，直接缺最新一天），
# 用 TWSE 官方每日成交量值表覆蓋 last_close/prev_close/change，
# 技術指標（MA/RSI/MACD/KD）保留 yfinance 計算結果。
taiex_official = get_twse_taiex_latest()
if taiex_official and taiex_official.get("last_close"):
    yf_taiex_last = result["tw_markets"]["taiex"].get("last_close")
    if yf_taiex_last is None or abs(yf_taiex_last - taiex_official["last_close"]) > 0.01:
        result["tw_markets"]["taiex"]["last_close"] = taiex_official["last_close"]
        result["tw_markets"]["taiex"]["prev_close"] = taiex_official["prev_close"]
        result["tw_markets"]["taiex"]["change"] = taiex_official["change"]
        result["tw_markets"]["taiex"]["change_pct"] = taiex_official["change_pct"]
        result["tw_markets"]["taiex"]["official_date"] = taiex_official["date"]
        result["tw_markets"]["taiex"]["note"] = "last_close/change 來自 TWSE 官方數據（yfinance 落後一日）；技術指標仍為 yfinance 計算"

# ── 台股個股（watchlist_tw + 持倉，動態從 portfolio.json）
print("  🏢 台股個股（動態從 portfolio.json）...")
tw_stocks = {}
for code, name in {**_watchlist_tw_dict, **_tw_holdings}.items():
    tw_stocks[code] = (f"{code}.TW", name)
for stock_id, (sym, name) in tw_stocks.items():
    # 先試 yfinance（有完整技術指標）
    yf_data = get_price_data(sym, period="6mo")
    if yf_data.get("last_close"):
        result["tw_markets"][stock_id] = yf_data
        result["tw_markets"][stock_id]["name"] = name
    else:
        # 備援：TWSE 官方 API（只有當日收盤）
        twse_data = get_twse_stock_price(stock_id)
        twse_data["name"] = name
        twse_data["note"] = "yfinance 無數據，使用 TWSE API 備援（無技術指標）"
        result["tw_markets"][stock_id] = twse_data

# ── 台股法人籌碼（持倉 + 台積電、聯發科）
print("  🏦 台股三大法人...")
inst_ids = list(dict.fromkeys(list(_tw_holdings.keys()) + ["2330", "2454"]))
for stock_id in inst_ids:
    result["tw_markets"][f"{stock_id}_institutional"] = get_twse_institutional(stock_id)

# ── 台股融資融券（持倉標的）
print("  💳 台股融資融券...")
for stock_id in list(_tw_holdings.keys()):
    result["tw_markets"][f"{stock_id}_margin"] = get_twse_margin(stock_id)

# ── 匯率
print("  💱 匯率...")
fx = {
    "usd_dxy":   "DX-Y.NYB",
    "usd_twd":   "TWD=X",
    "usd_jpy":   "JPY=X",
    "usd_cny":   "CNY=X",
    "eur_usd":   "EURUSD=X",
}
for name, sym in fx.items():
    result["currencies"][name] = get_price_data(sym, period="3mo")

# ── 美國公債殖利率
print("  📉 公債殖利率...")
bonds = {
    "us_2y":   "^IRX",
    "us_10y":  "^TNX",
    "us_30y":  "^TYX",
}
for name, sym in bonds.items():
    result["bonds"][name] = get_price_data(sym, period="3mo")

# ── 商品
print("  🛢️  商品...")
commodities = {
    "gold":          "GC=F",
    "oil_wti":       "CL=F",
    "oil_brent":     "BZ=F",
    "copper":        "HG=F",
    "natural_gas":   "NG=F",
    "uranium_ura":   "URA",
    "uranium_urnm":  "URNM",
    "copper_copx":   "COPX",
    "copper_cper":   "CPER",
}
for name, sym in commodities.items():
    result["commodities"][name] = get_price_data(sym, period="6mo")

# ── 我的持倉摘要（完全從 portfolio.json 動態決定）
print("  💼 持倉摘要（動態從 portfolio.json）...")
for s in _portfolio.get("us_stocks", []):
    sym = s["ticker"]
    pd_data = get_price_data(sym, period="6mo")
    result["my_portfolio"][sym] = {
        "price_data": pd_data,
        "market": "us",
        "fundamentals": get_info(sym),
    }
for s in _portfolio.get("taiwan_stocks", []):
    code = s["ticker"]
    sym = f"{code}.TW"
    pd_data = get_price_data(sym, period="6mo")
    if not pd_data.get("last_close"):
        pd_data = get_twse_stock_price(code)
        pd_data["note"] = "yfinance 無數據，使用 TWSE API 備援"
    result["my_portfolio"][f"{code}_TW"] = {
        "price_data": pd_data,
        "market": "tw",
    }

# ── 寫出 JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

print(f"\n✅ 完成！數據已儲存至：{OUTPUT_FILE}")
print(f"   總大小：{len(json.dumps(result)):,} 字元")
print(f"   台股法人：{'✅' if 'foreign_net' in str(result['tw_markets'].get('1603_institutional', {})) else '⚠️  需確認'}")
print(f"   美股指數：{'✅' if result['us_markets']['sp500'].get('last_close') else '⚠️'}")
print(f"   持倉 AVGO：{'✅' if result['my_portfolio']['AVGO']['price_data'].get('last_close') else '⚠️'}")
