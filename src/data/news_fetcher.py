"""
多平台新闻抓取模块
东方财富为主要来源，雪球热门讨论为补充
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from config import NEWS_DAYS_RANGE, MAX_NEWS_COUNT
from utils.helpers import clean_html, compute_title_similarity


def _safe_fetch(fn, label: str) -> list[dict]:
    """安全抓取包装"""
    try:
        return fn()
    except Exception as e:
        print(f"[news] {label}: {type(e).__name__}")
        return []


def fetch_eastmoney_news(code: str, days: int = NEWS_DAYS_RANGE) -> list[dict]:
    """从东方财富获取个股新闻（列名：新闻标题, 新闻内容, 发布时间, 文章来源, 新闻链接）"""
    def _do():
        df = ak.stock_news_em(symbol=code)
        if df is None or df.empty:
            return []

        # 列名映射（处理中英文列名）
        col_map = {}
        for c in df.columns:
            cs = str(c)
            if "标题" in cs or "title" in cs.lower():
                col_map["title"] = c
            elif "内容" in cs or "content" in cs.lower():
                col_map["content"] = c
            elif "时间" in cs or "date" in cs.lower() or "time" in cs.lower():
                col_map["time"] = c
            elif "来源" in cs or "source" in cs.lower():
                col_map["source"] = c
            elif "链接" in cs or "url" in cs.lower():
                col_map["url"] = c

        cutoff = datetime.now() - timedelta(days=days)
        news_list = []

        for _, row in df.iterrows():
            try:
                title = str(row.get(col_map.get("title", df.columns[1]), ""))
                content = str(row.get(col_map.get("content", df.columns[2]), title))
                source = str(row.get(col_map.get("source", df.columns[4]), "东方财富"))
                url = str(row.get(col_map.get("url", df.columns[5]), ""))
                pub_str = str(row.get(col_map.get("time", df.columns[3]), ""))

                if not title or title == "nan":
                    continue

                # 时间过滤
                dt_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                try:
                    pub_time = pd.to_datetime(pub_str)
                    if pub_time >= cutoff:
                        dt_str = pub_time.strftime("%Y-%m-%d %H:%M")
                    else:
                        continue
                except:
                    pass

                news_list.append({
                    "title": title.strip(),
                    "content": clean_html(content).strip(),
                    "source": source.strip(),
                    "datetime": dt_str,
                    "url": url.strip(),
                    "platform": "东方财富",
                })
            except:
                continue

        return news_list

    return _safe_fetch(_do, "东方财富新闻")


def fetch_xueqiu_tweets(code: str, days: int = NEWS_DAYS_RANGE) -> list[dict]:
    """从雪球获取热门推文"""
    def _do():
        prefix = "SH" if code.startswith(("6", "9")) else "SZ"
        symbol = f"{prefix}{code}"

        df = ak.stock_hot_tweet_xq(symbol=symbol)
        if df is None or df.empty:
            return []

        cutoff = datetime.now() - timedelta(days=days)
        news_list = []

        for _, row in df.iterrows():
            try:
                # 尝试多种列名
                title = ""
                content = ""
                for c in df.columns:
                    cs = str(c)
                    val = str(row[c]) if pd.notna(row[c]) else ""
                    if "text" in cs.lower() or "title" in cs.lower() or "内容" in cs:
                        content = val
                        title = val[:60]
                    if "time" in cs.lower() or "时间" in cs:
                        try:
                            t = pd.to_datetime(val)
                            if t < cutoff:
                                continue
                        except:
                            pass

                if not title:
                    continue

                news_list.append({
                    "title": title.strip(),
                    "content": clean_html(content).strip(),
                    "source": "雪球",
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "url": "",
                    "platform": "雪球",
                })
            except:
                continue

        return news_list

    return _safe_fetch(_do, "雪球讨论")


def fetch_stock_notices(code: str, days: int = NEWS_DAYS_RANGE) -> list[dict]:
    """获取上市公司公告"""
    def _do():
        df = ak.stock_notice_report(symbol=code)
        if df is None or df.empty:
            return None

        cutoff = datetime.now() - timedelta(days=days)
        news_list = []

        for _, row in df.iterrows():
            try:
                title = ""
                for c in df.columns:
                    cs = str(c)
                    if "标题" in cs or "title" in cs.lower():
                        title = str(row[c])

                if not title or title == "nan":
                    continue

                news_list.append({
                    "title": f"[公告] {title.strip()}",
                    "content": title.strip(),
                    "source": "上市公司公告",
                    "datetime": datetime.now().strftime("%Y-%m-%d"),
                    "url": "",
                    "platform": "公告",
                })
            except:
                continue

        return news_list

    return _safe_fetch(_do, "上市公司公告")


def deduplicate_news(news_list: list[dict], threshold: float = 0.7) -> list[dict]:
    """按标题相似度去重"""
    if not news_list:
        return []
    sorted_news = sorted(news_list, key=lambda x: x.get("datetime", ""), reverse=True)
    unique = []
    for news in sorted_news:
        if not any(compute_title_similarity(news["title"], e["title"]) >= threshold for e in unique):
            unique.append(news)
    return unique


def fetch_all_news(code: str, stock_name: str,
                   days: int = NEWS_DAYS_RANGE,
                   max_count: int = MAX_NEWS_COUNT) -> list[dict]:
    """从所有平台获取新闻并去重"""
    print(f"[news] Fetching news for {stock_name}({code})...")

    all_news = []

    # 东方财富新闻
    em = fetch_eastmoney_news(code, days)
    print(f"  EastMoney: {len(em)} items")
    all_news.extend(em)

    # 雪球讨论
    xq = fetch_xueqiu_tweets(code, days)
    print(f"  Xueqiu: {len(xq)} items")
    all_news.extend(xq)

    # 公告
    notices = fetch_stock_notices(code, days)
    print(f"  Notices: {len(notices)} items")
    all_news.extend(notices)

    # 去重
    before = len(all_news)
    all_news = deduplicate_news(all_news)
    print(f"  After dedup: {len(all_news)} (was {before})")

    if len(all_news) > max_count:
        all_news = all_news[:max_count]

    print(f"[news] Final: {len(all_news)} items")
    return all_news
