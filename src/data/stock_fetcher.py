"""
股票数据获取模块
数据源：股票搜索(Sina+代理) + 行情/K线(腾讯直连)
启动时缓存全量股票列表，避免重复下载
"""
import os
import akshare as ak
import pandas as pd
from typing import Optional
from config import HISTORY_DAYS, PROXY_URL

# 模块级缓存（转为纯 Python list，避免 pandas 线程问题）
_stock_list_cache = None


def _ensure_proxy():
    os.environ.setdefault("HTTP_PROXY", PROXY_URL)
    os.environ.setdefault("HTTPS_PROXY", PROXY_URL)


def _safe_float(val, default=0.0):
    if val is None: return default
    try:
        v = float(val)
        return v if pd.notna(v) else default
    except (ValueError, TypeError):
        return default


def _init_stock_cache():
    """启动时初始化股票列表缓存（转为纯 Python list）"""
    global _stock_list_cache
    _ensure_proxy()
    try:
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            # 转为 list of (code, name) 避免 pandas 线程兼容问题
            _stock_list_cache = list(zip(
                df["code"].astype(str).str.strip(),
                df["name"].astype(str).str.strip()
            ))
            print(f"[stock] Cached {len(_stock_list_cache)} stocks")
            return True
    except Exception as e:
        print(f"[stock] Cache init failed: {e}")
    return False


def search_stock(name: str) -> Optional[dict]:
    """根据股票名称搜索股票代码"""
    import unicodedata
    global _stock_list_cache

    if _stock_list_cache is None:
        if not _init_stock_cache():
            return None

    name_norm = unicodedata.normalize('NFC', name.strip())
    name_lower = name_norm.lower()

    for code, sname in _stock_list_cache:
        sname_norm = unicodedata.normalize('NFC', sname)
        if name_norm == sname_norm:
            return {"code": code, "name": sname}

    for code, sname in _stock_list_cache:
        sname_lower = unicodedata.normalize('NFC', sname).lower()
        if name_lower in sname_lower or sname_lower in name_lower:
            return {"code": code, "name": sname}

    for code, sname in _stock_list_cache:
        if name_norm == code:
            return {"code": code, "name": sname}

    return None


def _fetch_tencent_hist(code: str, days: int = 10):
    """从腾讯源获取历史K线"""
    _ensure_proxy()
    market = "sh" if code.startswith(("6", "9")) else "sz"
    symbol = f"{market}{code}"
    end = pd.Timestamp.now().strftime("%Y%m%d")
    start = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d")
    try:
        return ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start, end_date=end, adjust="qfq")
    except Exception as e:
        print(f"[stock] Tencent hist failed: {e}")
        return None


def _get_realtime_from_tx(code: str) -> Optional[dict]:
    """从腾讯K线最新一行提取行情数据"""
    df = _fetch_tencent_hist(code, days=10)
    if df is None or df.empty:
        return None
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    lc = _safe_float(latest["close"])
    pc = _safe_float(prev["close"])
    chg = (lc - pc) / pc * 100 if pc > 0 else 0
    high = _safe_float(latest.get("high", lc))
    low = _safe_float(latest.get("low", lc))
    return {
        "price": lc, "change_pct": round(chg, 2),
        "change_amount": round(lc - pc, 2), "volume": 0,
        "turnover": _safe_float(latest.get("amount", 0)),
        "amplitude": round((high - low) / pc * 100, 2) if pc > 0 else 0,
        "high": high, "low": low,
        "open": _safe_float(latest.get("open", pc)), "prev_close": pc,
        "volume_ratio": 0, "turnover_rate": 0, "pe": None, "pb": None,
    }


def get_stock_history(code: str, days: int = HISTORY_DAYS) -> Optional[dict]:
    """获取个股历史K线"""
    df = _fetch_tencent_hist(code, days=days)
    if df is None or df.empty:
        return None
    closes = df["close"].tolist()
    amounts = df["amount"].tolist()
    n = len(closes)
    return {
        "ma5": round(sum(closes[-5:]) / min(5, n), 2) if closes else 0,
        "ma10": round(sum(closes[-10:]) / min(10, n), 2) if closes else 0,
        "ma20": round(sum(closes[-20:]) / min(20, n), 2) if closes else 0,
        "week_change": round((closes[-1] - closes[-5]) / closes[-5] * 100, 2) if n >= 5 else 0,
        "month_change": round((closes[-1] - closes[-min(20, n)]) / closes[-min(20, n)] * 100, 2) if n >= 5 else 0,
        "vol_ratio_5_20": round((sum(amounts[-5:]) / min(5, n)) / (sum(amounts[-20:]) / min(20, n)), 2) if amounts and n >= 5 else 1,
        "recent_closes": [round(c, 2) for c in closes[-30:]],
    }


def get_financial_data(code: str) -> Optional[dict]:
    """获取个股财务指标"""
    _ensure_proxy()
    try:
        df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
        if df is None or df.empty:
            return None
        r = df.iloc[0]
        return {
            "eps": _safe_float(r.get("基本每股收益"), None),
            "bps": _safe_float(r.get("每股净资产"), None),
            "roe": _safe_float(r.get("净资产收益率"), None),
            "net_profit_growth": _safe_float(r.get("净利润同比增长率"), None),
            "revenue_growth": _safe_float(r.get("营业收入同比增长率"), None),
            "gross_margin": _safe_float(r.get("销售毛利率"), None),
            "net_margin": _safe_float(r.get("销售净利率"), None),
        }
    except Exception as e:
        print(f"[stock] financial failed: {e}")
        return None


def get_full_stock_data(stock_name: str) -> Optional[dict]:
    """获取完整的股票分析数据"""
    import sys
    stock = search_stock(stock_name)
    if not stock:
        print(f"[stock] get_full_stock_data FAILED for '{stock_name}'", file=sys.stderr, flush=True)
        return None
    code = stock["code"]
    name = stock["name"]
    realtime = _get_realtime_from_tx(code)
    if not realtime:
        realtime = {"price": 0, "change_pct": 0, "change_amount": 0,
                    "volume": 0, "turnover": 0, "amplitude": 0,
                    "high": 0, "low": 0, "open": 0, "prev_close": 0,
                    "volume_ratio": 0, "turnover_rate": 0,
                    "pe": None, "pb": None}
    history = get_stock_history(code)
    financial = get_financial_data(code)
    return {
        "code": code, "name": name,
        "price": realtime["price"], "change_pct": realtime["change_pct"],
        "change_amount": realtime.get("change_amount", 0),
        "volume": realtime.get("volume", 0), "turnover": realtime.get("turnover", 0),
        "amplitude": realtime.get("amplitude", 0),
        "high": realtime.get("high", 0), "low": realtime.get("low", 0),
        "open": realtime.get("open", 0), "prev_close": realtime.get("prev_close", 0),
        "volume_ratio": realtime.get("volume_ratio", 0),
        "turnover_rate": realtime.get("turnover_rate", 0),
        "pe": realtime.get("pe"), "pb": realtime.get("pb"),
        "history": history, "financial": financial,
    }
