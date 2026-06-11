"""
中文情感分析模块
基于 SnowNLP 对新闻文本进行情感打分
"""
import numpy as np
from snownlp import SnowNLP
from typing import Optional
from utils.helpers import clean_html


def analyze_single(text: str) -> float:
    """
    对单条文本进行情感分析
    返回 0~1 之间的浮点数，越接近 1 表示越正面
    """
    if not text or len(text.strip()) < 2:
        return 0.5  # 空文本返回中性

    try:
        cleaned = clean_html(text)
        if len(cleaned) < 2:
            return 0.5
        s = SnowNLP(cleaned)
        score = s.sentiments
        # 确保在 0~1 范围内
        return max(0.0, min(1.0, float(score)))
    except Exception as e:
        print(f"[sentiment] 单条分析失败: {e}")
        return 0.5


def analyze_batch(texts: list[str]) -> list[float]:
    """
    批量情感分析
    返回与输入等长的情感得分列表
    """
    if not texts:
        return []
    return [analyze_single(t) for t in texts]


def analyze_news_items(news_list: list[dict]) -> list[dict]:
    """
    对新闻列表进行批量情感分析
    为每条新闻添加 sentiment 字段
    输入: [{title, content, ...}, ...]
    输出: [{title, content, ..., sentiment}, ...]
    """
    if not news_list:
        return []

    # 合并 title + content 作为分析文本
    texts = []
    for item in news_list:
        title = item.get("title", "")
        content = item.get("content", "")
        combined = f"{title}。{content}" if content else title
        texts.append(combined)

    # 批量分析
    scores = analyze_batch(texts)

    # 写入结果
    for i, item in enumerate(news_list):
        item["sentiment"] = scores[i] if i < len(scores) else 0.5

    return news_list


def compute_sentiment_stats(sentiments: list[float]) -> dict:
    """
    计算情感得分的统计指标
    返回: {mean, std, median, positive_ratio, negative_ratio, polarization}
    """
    if not sentiments:
        return {
            "mean": 50.0,
            "std": 0.0,
            "median": 50.0,
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "polarization": 0.0,
            "count": 0,
        }

    arr = np.array(sentiments)
    n = len(arr)

    # 基础统计
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr))
    median_val = float(np.median(arr))

    # 正面/负面比例（>0.55 为正面，<0.45 为负面）
    positive_ratio = float(np.sum(arr > 0.55) / n)
    negative_ratio = float(np.sum(arr < 0.45) / n)

    # 极化指标（双峰检测：标准差越大、正面负面比例越接近 → 越极化）
    # polarization 范围 0~1，越高表示意见越分裂
    balance = 1.0 - abs(positive_ratio - negative_ratio)  # 正负面比例越接近 → 越分裂
    polarization = min(1.0, (std_val * 2 + balance) / 2)

    return {
        "mean": round(mean_val * 100, 1),
        "std": round(std_val, 2),
        "median": round(median_val * 100, 1),
        "positive_ratio": round(positive_ratio * 100, 1),
        "negative_ratio": round(negative_ratio * 100, 1),
        "polarization": round(polarization * 100, 1),
        "count": n,
    }
