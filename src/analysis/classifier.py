"""
新闻分类器模块
- 来源分级：判断新闻属于官方媒体/行业媒体/地方媒体/自媒体
- 维度分类：将新闻归类到六维雷达图的对应维度
"""
from config import (
    OFFICIAL_MEDIA_KEYWORDS,
    MAINSTREAM_MEDIA_KEYWORDS,
    SELF_MEDIA_KEYWORDS,
    RADAR_DIMENSION_KEYWORDS,
    SOURCE_CATEGORY_WEIGHTS,
)


def classify_source(source: str, platform: str = "") -> str:
    """
    根据新闻来源字符串判断媒体级别
    返回: "官方媒体" / "主流媒体" / "自媒体"
    """
    combined = f"{source} {platform}".strip()

    # 1. 官方媒体（最高优先级）
    for kw in OFFICIAL_MEDIA_KEYWORDS:
        if kw in combined:
            return "官方媒体"

    # 2. 自媒体
    for kw in SELF_MEDIA_KEYWORDS:
        if kw in combined:
            return "自媒体"

    # 3. 主流媒体（财经媒体、综合媒体、地方媒体等）
    for kw in MAINSTREAM_MEDIA_KEYWORDS:
        if kw in combined:
            return "主流媒体"

    # 默认：无法判断的归为主流媒体
    return "主流媒体"


def classify_news_sources(news_list: list[dict]) -> list[dict]:
    """
    为每条新闻添加 source_category 和 source_weight。
    先按来源名称分类，再根据标题/内容微调：
    - 含"公告""披露"等关键词 → 官方媒体（转载官方信披）
    - 来源是平台+口语化内容 → 自媒体
    - 其余保来源分类
    """
    for item in news_list:
        source = item.get("source", "")
        platform = item.get("platform", "")
        title = item.get("title", "")
        content = item.get("content", "")
        combined_text = f"{title} {content}"

        # 1. 先按来源名称初判
        base_category = classify_source(source, platform)

        # 2. 根据内容微调
        # 官方公告特征
        official_signals = ["公告", "披露", "报告", "年报", "季报", "招股",
                           "上市公告", "停牌", "复牌", "分红", "预案"]
        # 自媒体特征（口语化、互动性）
        self_media_signals = ["我觉得", "个人认为", "大家怎么看", "你怎么看",
                              "不得不说", "太牛了", "牛逼", "炸裂", "推荐",
                              "关注我", "点赞", "转发", "评论"]


        official_hits = sum(1 for kw in official_signals if kw in combined_text)
        self_hits = sum(1 for kw in self_media_signals if kw in combined_text)

        if official_hits >= 1 and base_category != "自媒体":
            category = "官方媒体"
        elif self_hits >= 2:
            category = "自媒体"
        else:
            category = base_category

        item["source_category"] = category
        item["source_weight"] = SOURCE_CATEGORY_WEIGHTS.get(category, 0.4)
    return news_list


def classify_news_dimension(title: str, content: str) -> list[str]:
    """
    判断一条新闻属于哪些雷达维度
    一条新闻可能属于多个维度
    返回维度名称列表
    """
    text = f"{title} {content}"
    matched_dimensions = []

    for dimension, keywords in RADAR_DIMENSION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score >= 2:  # 至少命中2个关键词才认为相关
            matched_dimensions.append(dimension)

    # 如果没有命中任何维度，默认归入"资本市场"
    if not matched_dimensions:
        matched_dimensions.append("资本市场")

    return matched_dimensions


def classify_all_news_dimensions(news_list: list[dict]) -> list[dict]:
    """
    为新闻列表中的每条新闻添加 dimensions 字段
    """
    for item in news_list:
        title = item.get("title", "")
        content = item.get("content", "")
        item["dimensions"] = classify_news_dimension(title, content)
    return news_list


def compute_source_distribution(news_list: list[dict]) -> dict:
    """
    计算新闻来源分布统计（三分类）
    """
    if not news_list:
        return {"官方媒体": 0, "主流媒体": 0, "自媒体": 0, "total": 0}

    distribution = {"官方媒体": 0, "主流媒体": 0, "自媒体": 0}
    for item in news_list:
        cat = item.get("source_category", "主流媒体")
        if cat in distribution:
            distribution[cat] += 1
        else:
            distribution["主流媒体"] += 1

    distribution["total"] = len(news_list)
    return distribution


def compute_dimension_scores(news_list: list[dict]) -> dict:
    """
    计算各维度的情感得分均值
    返回: {维度名: {"score": float, "count": int}, ...}
    """
    dimension_data = {
        "市场竞争": {"scores": [], "count": 0},
        "财务表现": {"scores": [], "count": 0},
        "产品技术": {"scores": [], "count": 0},
        "公司经营": {"scores": [], "count": 0},
        "行业政策": {"scores": [], "count": 0},
        "资本市场": {"scores": [], "count": 0},
    }

    for item in news_list:
        sentiment = item.get("sentiment", 0.5)
        dims = item.get("dimensions", ["资本市场"])

        for dim in dims:
            if dim in dimension_data:
                dimension_data[dim]["scores"].append(sentiment)
                dimension_data[dim]["count"] += 1

    # 计算各维度均值并转为0-100
    result = {}
    for dim, data in dimension_data.items():
        if data["scores"]:
            mean_score = sum(data["scores"]) / len(data["scores"]) * 100
        else:
            mean_score = 50.0  # 默认中性
        result[dim] = {
            "score": round(mean_score, 1),
            "count": data["count"],
        }

    return result
