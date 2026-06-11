"""
工具函数模块
包含文本清洗、相似度计算、日期处理等通用函数
"""
import re
import html
from datetime import datetime


def clean_html(text: str) -> str:
    """清洗 HTML 标签和实体"""
    if not text:
        return ""
    # 去掉 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 解码 HTML 实体
    text = html.unescape(text)
    # 去掉多余空白
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_title_similarity(title1: str, title2: str) -> float:
    """计算两个标题的相似度（基于字符重合度）"""
    if not title1 or not title2:
        return 0.0

    # 简单 Jaccard 相似度（基于2-gram字符集）
    def char_bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))

    set1 = char_bigrams(title1)
    set2 = char_bigrams(title2)

    if not set1 or not set2:
        return 0.0

    intersection = set1 & set2
    union = set1 | set2

    return len(intersection) / len(union) if union else 0.0


def format_number(num: float, decimals: int = 2) -> str:
    """格式化数字显示"""
    if num is None:
        return "--"
    if abs(num) >= 1e8:
        return f"{num/1e8:.{decimals}f}亿"
    if abs(num) >= 1e4:
        return f"{num/1e4:.{decimals}f}万"
    return f"{num:.{decimals}f}"


def format_percent(num: float, decimals: int = 2) -> str:
    """格式化百分比显示"""
    if num is None:
        return "--"
    sign = "+" if num > 0 else ""
    return f"{sign}{num:.{decimals}f}%"


def safe_float(value, default=0.0) -> float:
    """安全转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def generate_summary(sentiment_score: float, risk_score: float,
                     financial_score: float, recommendation: dict) -> str:
    """根据各项得分生成一句话市场情绪总结"""
    rec_text = recommendation["text"] if isinstance(recommendation, dict) else recommendation
    if "推荐" in rec_text and "强烈" in rec_text:
        return "市场情绪积极乐观，舆论氛围良好，财务基本面支撑强劲，综合判断具备突出的投资价值。"
    elif "推荐" in rec_text:
        return "市场情绪整体偏向正面，财务指标表现稳健，舆论信号偏多，综合判断具备较好的投资价值。"
    elif "回避" in rec_text:
        if risk_score >= 60:
            return "市场情绪存在较大分歧，舆论两极分化严重，不确定性较高，当前建议暂时回避。"
        else:
            return "市场情绪偏向负面，近期舆论不太乐观，财务状况或市场表现存在隐忧，建议等待更明确信号。"
    else:
        return "市场情绪喜忧参半，正面与负面观点并存，缺乏明确方向性信号，建议暂时观望等待趋势明朗。"


def generate_news_summary(title: str, content: str, max_length: int = 80) -> str:
    """为每条新闻生成一句话摘要"""
    # 优先使用内容的前段，如果内容太短则用标题
    text = content if content and len(content) > 20 else title
    text = clean_html(text)

    # 截取合理长度，尽量在句号处断开
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    # 在最后一个句号或逗号处断开
    for sep in ["。", "，", "；", "、", ".", ",", ";"]:
        last_sep = truncated.rfind(sep)
        if last_sep > max_length // 2:
            truncated = truncated[:last_sep + 1]
            break

    return truncated + "…"
