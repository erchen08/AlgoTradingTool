"""
雷达图计算模块
计算六维雷达图各维度的最终得分（0-100）
混合数据源：财务数据 + 新闻情感聚合
"""
from config import FINANCIAL_SCORE_PARAMS


def compute_financial_dimension(financial: dict, stock: dict) -> float:
    """
    计算"财务表现"维度得分
    基于 PE、PB、ROE、营收增速等指标
    """
    if not financial:
        return 50.0

    params = FINANCIAL_SCORE_PARAMS
    scores = []
    weights = []

    # ROE 评分（越高越好，理想值15%以上满分）
    roe = financial.get("roe")
    if roe is not None:
        roe_score = min(100, (roe / params["roe_ideal"]) * 50 + 25)
        scores.append(roe_score)
        weights.append(0.3)

    # 营收增速评分
    rev_growth = financial.get("revenue_growth")
    if rev_growth is not None:
        growth_score = min(100, max(10, (rev_growth / params["revenue_growth_ideal"]) * 50 + 25))
        scores.append(growth_score)
        weights.append(0.25)

    # 净利润增速评分
    profit_growth = financial.get("net_profit_growth")
    if profit_growth is not None:
        pg_score = min(100, max(10, (profit_growth / params["revenue_growth_ideal"]) * 50 + 25))
        scores.append(pg_score)
        weights.append(0.25)

    # PE 估值评分（PE越低越好，但也要考虑合理性；PE为负则给低分）
    pe = stock.get("pe")
    if pe is not None and pe > 0:
        # 使用对数函数平滑PE的影响
        pe_ideal = params["pe_ideal"]
        if pe <= pe_ideal:
            pe_score = 60 + (1 - pe / pe_ideal) * 40  # PE很低 → 高评分
        elif pe <= 100:
            pe_score = 60 - (pe - pe_ideal) / (100 - pe_ideal) * 40
        else:
            pe_score = max(10, 20 - (pe - 100) / 100 * 10)
        scores.append(pe_score)
        weights.append(0.2)

    # 如果没有足够数据
    if not scores:
        return 50.0

    # 归一化权重
    total_w = sum(weights)
    weights = [w / total_w for w in weights]

    return round(sum(s * w for s, w in zip(scores, weights)), 1)


def compute_capital_market_dimension(stock: dict, history: dict) -> float:
    """
    计算"资本市场"维度得分
    基于涨跌幅、量比、换手率、均线等交易数据
    """
    if not stock:
        return 50.0

    scores = []
    weights = []

    # 当日涨跌幅评分（适中为佳，大涨大跌都不好）
    change_pct = stock.get("change_pct", 0)
    if abs(change_pct) > 9:
        change_score = 30  # 极端波动 → 高风险
    elif abs(change_pct) > 5:
        change_score = 50
    elif abs(change_pct) > 2:
        change_score = 65
    elif change_pct > 0:
        change_score = 75  # 温和上涨最好
    else:
        change_score = 55  # 温和下跌尚可
    scores.append(change_score)
    weights.append(0.2)

    # 周涨跌幅
    if history and history.get("week_change") is not None:
        wc = history["week_change"]
        if wc > 10:
            w_score = 70
        elif wc > 3:
            w_score = 75
        elif wc > 0:
            w_score = 70
        elif wc > -3:
            w_score = 50
        elif wc > -10:
            w_score = 30
        else:
            w_score = 15
        scores.append(w_score)
        weights.append(0.2)

    # 量比（1左右最好，过大过小都不正常）
    vol_ratio = stock.get("volume_ratio", 1)
    if vol_ratio is None:
        vol_ratio = 1
    if 0.8 <= vol_ratio <= 1.5:
        vr_score = 75
    elif 0.5 <= vol_ratio <= 2.5:
        vr_score = 60
    else:
        vr_score = 40
    scores.append(vr_score)
    weights.append(0.2)

    # 换手率评分（适中为佳）
    turnover = stock.get("turnover_rate", 0)
    if turnover is None:
        turnover = 0
    if 1 <= turnover <= 5:
        to_score = 70
    elif 0.3 <= turnover <= 10:
        to_score = 55
    else:
        to_score = 35
    scores.append(to_score)
    weights.append(0.2)

    # 均线关系（股价相对均线位置）
    if history:
        ma5 = history.get("ma5", 0)
        ma20 = history.get("ma20", 0)
        price = stock.get("price", 0)
        if ma5 > 0 and ma20 > 0 and price > 0:
            if price > ma5 > ma20:
                ma_score = 80  # 多头排列
            elif price > ma20:
                ma_score = 60
            elif price > ma5:
                ma_score = 45
            else:
                ma_score = 30  # 空头排列
            scores.append(ma_score)
            weights.append(0.2)

    if not scores:
        return 50.0

    total_w = sum(weights)
    weights = [w / total_w for w in weights]

    return round(sum(s * w for s, w in zip(scores, weights)), 1)


def compute_radar_scores(stock: dict, history: dict,
                         financial: dict, dimension_scores: dict) -> dict:
    """
    计算最终六维雷达图得分
    财务表现、资本市场 → 来自交易/财务数据
    其余四维 → 来自新闻维度情感聚合
    """
    radar = {}

    # 财务表现：来自财务数据
    radar["财务表现"] = compute_financial_dimension(financial, stock)

    # 资本市场：来自交易数据
    radar["资本市场"] = compute_capital_market_dimension(stock, history)

    # 其余四维：来自新闻分析
    for dim in ["市场竞争", "产品技术", "公司经营", "行业政策"]:
        ds = dimension_scores.get(dim, {})
        score = ds.get("score", 50.0)
        count = ds.get("count", 0)
        # 如果该维度新闻太少，向50分回归
        if count == 0:
            radar[dim] = 50.0
        elif count < 3:
            radar[dim] = round(score * 0.6 + 50 * 0.4, 1)
        else:
            radar[dim] = round(score, 1)

    return radar
