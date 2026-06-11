"""
综合评分引擎模块
融合财务数据评分和新闻情感分析，输出最终推荐
"""
from config import (
    SCORING_WEIGHTS,
    RECOMMENDATION_THRESHOLDS,
    FINANCIAL_SCORE_PARAMS,
    SOURCE_CATEGORY_WEIGHTS,
    get_star_rating,
)


def compute_financial_score(stock: dict, financial: dict, history: dict) -> float:
    """
    计算财务技术评分（0-100）
    综合 PE、PB、ROE、营收增速、近期涨跌幅等指标
    """
    if not stock:
        return 50.0

    params = FINANCIAL_SCORE_PARAMS
    scores = []
    weights = []

    # 1. PE 合理性（25%权重）
    pe = stock.get("pe")
    if pe is not None and pe > 0 and pe < params["pe_max"]:
        pe_ideal = params["pe_ideal"]
        if pe <= pe_ideal:
            pe_score = 70 + min(30, (1 - pe / pe_ideal) * 30)
        elif pe <= 50:
            pe_score = 70 - (pe - pe_ideal) / (50 - pe_ideal) * 30
        elif pe <= 100:
            pe_score = 40 - (pe - 50) / 50 * 20
        else:
            pe_score = max(10, 20 - (pe - 100) / 100 * 10)
    elif pe is not None and pe < 0:
        pe_score = 15  # 亏损
    else:
        pe_score = 50  # 无数据取中性
    scores.append(pe_score)
    weights.append(0.25)

    # 2. PB 合理性（15%权重）
    pb = stock.get("pb")
    if pb is not None and pb > 0 and pb < params["pb_max"]:
        pb_ideal = params["pb_ideal"]
        if pb <= pb_ideal:
            pb_score = 70 + min(30, (1 - pb / pb_ideal) * 30)
        elif pb <= 10:
            pb_score = 70 - (pb - pb_ideal) / (10 - pb_ideal) * 40
        else:
            pb_score = max(10, 30 - (pb - 10) / 20 * 20)
    else:
        pb_score = 50
    scores.append(pb_score)
    weights.append(0.15)

    # 3. ROE（20%权重）
    if financial:
        roe = financial.get("roe")
        if roe is not None:
            roe_score = min(100, max(10, (roe / params["roe_ideal"]) * 50 + 30))
            scores.append(roe_score)
            weights.append(0.20)
        else:
            # 无ROE数据，权重分配给其他项
            for i in range(len(weights)):
                weights[i] += 0.20 / len(weights)

    # 4. 营收增速（15%权重）
    if financial:
        rev_growth = financial.get("revenue_growth")
        if rev_growth is not None:
            rev_score = min(100, max(10, (rev_growth / params["revenue_growth_ideal"]) * 50 + 30))
            scores.append(rev_score)
            weights.append(0.15)
        else:
            for i in range(len(weights)):
                weights[i] += 0.15 / len(weights)

    # 5. 近期涨跌幅（15%权重）
    if history:
        month_change = history.get("month_change", 0)
        if abs(month_change) > 30:
            mc_score = 30
        elif abs(month_change) > 20:
            mc_score = 40
        elif abs(month_change) > 10:
            mc_score = 55
        elif month_change > 0:
            mc_score = 70
        else:
            mc_score = 50
        scores.append(mc_score)
        weights.append(0.15)

    # 6. 振幅（10%权重）
    amplitude = stock.get("amplitude", 0)
    if amplitude:
        if amplitude < 3:
            amp_score = 60
        elif amplitude < 6:
            amp_score = 70
        elif amplitude < 9:
            amp_score = 55
        else:
            amp_score = 35
        scores.append(amp_score)
        weights.append(0.10)

    # 归一化权重
    if not scores:
        return 50.0
    total_w = sum(weights)
    if total_w > 0:
        weights = [w / total_w for w in weights]

    return round(sum(s * w for s, w in zip(scores, weights)), 1)


def compute_sentiment_score(sentiment_stats: dict) -> float:
    """
    计算情感评分（0-100）
    基于 SnowNLP 情感均值，结合正面比例微调
    """
    mean_val = sentiment_stats.get("mean", 50.0)
    pos_ratio = sentiment_stats.get("positive_ratio", 0)
    neg_ratio = sentiment_stats.get("negative_ratio", 0)

    # 基础分 = 情感均值
    base = mean_val

    # 正面比例加成
    if pos_ratio > 60:
        base = min(100, base + 5)
    elif pos_ratio > 40:
        base = min(100, base + 2)

    # 负面比例惩罚
    if neg_ratio > 60:
        base = max(0, base - 5)
    elif neg_ratio > 40:
        base = max(0, base - 2)

    return round(base, 1)


def compute_risk_score(sentiment_stats: dict) -> float:
    """
    计算风险评分（0-100，越高风险越大）
    基于情感标准差的归一化 + 极化指标
    """
    std_val = sentiment_stats.get("std", 0)
    polarization = sentiment_stats.get("polarization", 0)

    # 标准差归一化：std 通常在0~0.5之间，映射到0-100
    std_score = min(100, (std_val / 0.35) * 70)

    # 极化指标加权（30%）
    pol_score = polarization * 0.3

    # 新闻数量惩罚（新闻太少 → 风险增加）
    count = sentiment_stats.get("count", 0)
    if count < 5:
        scarcity_penalty = (5 - count) * 6  # 最多加30分
    else:
        scarcity_penalty = 0

    risk = std_score * 0.7 + pol_score + scarcity_penalty
    return round(min(100, max(0, risk)), 1)


def compute_confidence_score(news_list: list[dict]) -> float:
    """
    计算置信度评分（0-100）
    基于新闻来源可靠性加权
    """
    if not news_list:
        return 0.0

    total_weight = 0
    weighted_sum = 0

    for item in news_list:
        weight = item.get("source_weight", SOURCE_CATEGORY_WEIGHTS["自媒体"])
        weighted_sum += weight
        total_weight += 1

    if total_weight == 0:
        return 0.0

    # 基础置信度 = 平均来源权重 × 100
    base_confidence = (weighted_sum / total_weight) * 100

    # 新闻数量惩罚
    count = len(news_list)
    if count < 5:
        count_factor = count / 5 * 0.6 + 0.4  # 新闻少时打6折
    elif count < 10:
        count_factor = 0.7
    elif count < 20:
        count_factor = 0.85
    else:
        count_factor = 1.0

    return round(base_confidence * count_factor, 1)


def compute_overall_score(financial_score: float, sentiment_score: float,
                          risk_score: float) -> float:
    """
    计算综合推荐分（0-100）
    """
    weights = SCORING_WEIGHTS
    overall = (
        financial_score * weights["financial_score"]
        + sentiment_score * weights["sentiment_score"]
        + (100 - risk_score) * weights["risk_penalty"]
    )
    return round(overall, 1)


def get_recommendation(overall_score: float) -> dict:
    """
    根据综合评分返回推荐建议（文本 + 星级）
    """
    t = RECOMMENDATION_THRESHOLDS
    if overall_score >= t["strong_buy"]:
        text = "强烈推荐"
    elif overall_score >= t["buy"]:
        text = "推荐买入"
    elif overall_score >= t["hold"]:
        text = "谨慎观望"
    else:
        text = "建议回避"

    return {
        "text": text,
        "stars": get_star_rating(overall_score),
        "index": round(overall_score, 1),
    }


def compute_full_analysis(stock: dict, history: dict,
                          financial: dict, news_list: list[dict]) -> dict:
    """
    执行完整分析流程，返回所有评分结果
    """
    from .sentiment import compute_sentiment_stats

    # 收集情感得分
    sentiments = [item.get("sentiment", 0.5) for item in news_list]

    # 计算各项指标
    sentiment_stats = compute_sentiment_stats(sentiments)

    financial_score = compute_financial_score(stock, financial, history)
    sentiment_score = compute_sentiment_score(sentiment_stats)
    risk_score = compute_risk_score(sentiment_stats)
    confidence_score = compute_confidence_score(news_list)
    overall_score = compute_overall_score(financial_score, sentiment_score, risk_score)
    recommendation = get_recommendation(overall_score)

    return {
        "scores": {
            "financial": financial_score,
            "sentiment": sentiment_score,
            "risk": risk_score,
            "confidence": confidence_score,
            "overall": overall_score,
        },
        "recommendation": recommendation,
        "sentiment_stats": sentiment_stats,
    }
