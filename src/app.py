"""
AlgoTradingTool - Flask 主入口
"""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:6518")
os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:6518")

from flask import Flask, render_template, request, jsonify
from config import FLASK_PORT

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["JSON_AS_ASCII"] = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "请求数据为空"}), 400
        stock_name = data.get("stock_name", "").strip()
        if not stock_name: return jsonify({"error": "请输入股票名称"}), 400

        from data.stock_fetcher import get_full_stock_data
        from data.news_fetcher import fetch_all_news
        from analysis.sentiment import analyze_news_items
        from analysis.classifier import (classify_news_sources, classify_all_news_dimensions,
                                         compute_source_distribution, compute_dimension_scores)
        from analysis.radar import compute_radar_scores
        from analysis.scorer import compute_full_analysis
        from utils.helpers import generate_summary, generate_news_summary

        stock = get_full_stock_data(stock_name)
        if not stock:
            return jsonify({"error": f"未找到与「{stock_name}」匹配的股票"}), 404

        code, name = stock["code"], stock["name"]
        news = fetch_all_news(code, name)
        news = analyze_news_items(news)
        news = classify_news_sources(news)
        news = classify_all_news_dimensions(news)
        dim_scores = compute_dimension_scores(news)
        analysis = compute_full_analysis(stock, stock.get("history"), stock.get("financial"), news)
        radar = compute_radar_scores(stock, stock.get("history"), stock.get("financial"), dim_scores)
        src_dist = compute_source_distribution(news)
        summary = generate_summary(analysis["scores"]["sentiment"], analysis["scores"]["risk"],
                                   analysis["scores"]["financial"], analysis["recommendation"])

        news_items = []
        for item in news:
            st = generate_news_summary(item.get("title",""), item.get("content",""))
            news_items.append({
                "title": item.get("title",""), "summary": st,
                "sentiment": round(item.get("sentiment", 0.5) * 100, 1),
                "source": item.get("source",""),
                "source_category": item.get("source_category", "自媒体"),
                "datetime": item.get("datetime",""), "url": item.get("url",""),
            })

        return jsonify({
            "stock": {"code": code, "name": name, "price": stock["price"],
                      "change_pct": stock["change_pct"], "change_amount": stock.get("change_amount", 0),
                      "pe": stock.get("pe"), "pb": stock.get("pb"),
                      "volume": stock.get("volume", 0), "turnover": stock.get("turnover", 0),
                      "turnover_rate": stock.get("turnover_rate", 0)},
            "recommendation": analysis["recommendation"], "summary": summary,
            "scores": analysis["scores"], "sentiment_stats": analysis["sentiment_stats"],
            "radar": radar,
            "source_distribution": {
                "total": src_dist["total"],
                "items": [
                    {"name": "官方媒体", "value": src_dist.get("官方媒体", 0), "color": "#ffd700"},
                    {"name": "主流媒体", "value": src_dist.get("主流媒体", 0), "color": "#00d4ff"},
                    {"name": "自媒体", "value": src_dist.get("自媒体", 0), "color": "#5a6080"},
                ]
            },
            "news": news_items,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"分析失败: {str(e)}"}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  AlgoTradingTool - A股量化分析工具")
    print(f"  http://127.0.0.1:{FLASK_PORT}")
    print("=" * 50)
    app.run(host="127.0.0.1", port=FLASK_PORT, debug=False)
