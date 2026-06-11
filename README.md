# AlgoTradingTool — A 股量化分析工具

> 基于 Flask + akshare + SnowNLP + ECharts 的 A 股市场情绪量化分析平台

**GitHub 仓库**: https://github.com/erchen08/AlgoTradingTool

---

## 一、项目背景

### 选题初衷

A 股市场信息高度碎片化——实时行情、财报数据、财经新闻、投资者讨论分散在不同平台。普通投资者在面对一只股票时，往往需要手动翻阅多个网站，难以在短时间内形成全面的判断。

本工具旨在**一键聚合多维度信息**，通过量化模型自动给出参考评分，帮助投资者快速了解目标股票的市场情绪与基本面状况。

### 解决的问题

| 痛点 | 解决方案 |
|------|---------|
| 多平台数据分散 | 自动抓取东方财富、雪球等平台新闻与行情 |
| 舆论难以量化 | SnowNLP 中文情感分析，将文本情感转为数值 |
| 来源可靠性混杂 | 官方媒体/主流媒体/自媒体三分类，加权计算置信度 |
| 评分维度过少 | 六维雷达图覆盖财务、市场、竞争、技术、经营、政策 |
| 缺乏直观结论 | 推荐指数(0-100) + 星级评定，一句话概括 |

---

## 二、核心算法与技术

### 课程知识点应用

| 知识点 | 应用位置 | 说明 |
|--------|---------|------|
| **贝叶斯分类** | `analysis/sentiment.py` | SnowNLP 基于朴素贝叶斯的中文情感分类模型，对每条新闻给出 0~1 情感得分 |
| **加权评分模型** | `analysis/scorer.py` | 财务评分×0.4 + 情感评分×0.4 + (100-风险分)×0.2，多因子加权融合 |
| **关键词匹配 + 规则分类** | `analysis/classifier.py` | 六维雷达维度分类（市场竞争、财务表现等）使用关键词词典匹配；来源三分类结合规则引擎与内容信号检测 |
| **Jaccard 相似度** | `utils/helpers.py` | 标题 n-gram Jaccard 系数用于新闻去重（`compute_title_similarity`） |
| **RESTful API 设计** | `app.py` | Flask 路由设计，POST `/api/analyze` 接收股票名返回 JSON，GET `/api/search` 提供搜索建议 |
| **代理 / 网络容错** | `data/stock_fetcher.py` | 多数据源回退策略（新浪搜索 + 腾讯K线），动态代理配置 |
| **缓存策略** | `data/stock_fetcher.py` | 5527 只 A 股列表启动时一次性拉取并缓存为 Python list，避免重复网络请求 |
| **Unicode 规范化** | `data/stock_fetcher.py` | `unicodedata.normalize('NFC', ...)` 处理中文编码跨平台一致性问题 |
| **数据可视化** | `static/js/charts.js` | ECharts 雷达图（六维） + 饼图（三分类），响应式布局 |

### 评分体系公式

```
推荐指数 = 财务评分 × 0.4 + 情感评分 × 0.4 + (100 − 风险评分) × 0.2
```

- **财务评分**：PE/PB 估值合理性、ROE 水平、营收增速、近期涨跌幅加权
- **情感评分**：SnowNLP 所有新闻情感得分均值 × 100
- **风险评分**：情感标准差归一化 + 极化指标 + 新闻量不足惩罚

### 置信度计算

```
置信度 = Σ(每条新闻来源权重) / 新闻总数 × 数量惩罚系数
```

来源权重：官方媒体 1.0 > 主流媒体 0.75 > 自媒体 0.35

---

## 三、运行指南

### 环境要求

- Python 3.9+
- 网络代理（用于访问新浪股票列表接口）

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/erchen08/AlgoTradingTool.git
cd AlgoTradingTool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置代理端口（编辑 src/config.py 第 115 行）
PROXY_PORT = 6518  # 改为你自己的代理端口

# 4. 启动应用
python src/app.py

# 5. 浏览器访问
# http://127.0.0.1:18000
```

### 使用步骤

1. 浏览器打开 `http://127.0.0.1:18000`
2. 在搜索框输入 A 股名称（如"贵州茅台"、"宁德时代"）
3. 点击"开始分析"，等待 5~10 秒
4. 查看推荐指数、六维雷达图、来源饼图、新闻摘要

---

## 四、技术架构

```
用户输入 → akshare 数据抓取 → SnowNLP 情感分析 → 综合评分引擎 → ECharts 可视化
```

| 环节 | 技术选型 |
|------|---------|
| 后端框架 | Flask（Python） |
| 行情数据 | akshare（新浪 + 腾讯双源回退） |
| 新闻抓取 | 东方财富 API |
| 中文分词 | jieba |
| 情感分析 | SnowNLP（朴素贝叶斯） |
| 图表渲染 | ECharts 5.x（浏览器端） |

---

## 五、界面预览

```
┌─────────────────────────────────────────┐
│  [ 54 ]  ★★★  推荐买入（推荐指数 54）   │  ← 推荐指数徽章
│  市场情绪喜忧参半...                     │
│  贵州茅台  1275.88  +1.58%               │
├──────┬──────┬──────┬───────────────────┤
│ 财务 │ 情感 │ 风险 │ 置信度            │  ← 四维卡片
├─────────────────────┬─────────────────┤
│  六维雷达图         │  信息来源饼图    │  ← 全宽堆叠
│  (900px)           │  (900px)        │
├─────────────────────┴─────────────────┤
│  📰 近期重要新闻 (10 条)               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ 新闻卡片 │ │ 新闻卡片 │ │ 新闻卡片 │  │
│  └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────┘
```

---

## 六、AI 工具使用声明

本项目在开发过程中使用了 **Anthropic Claude（Claude Code）** 作为 AI 辅助编程工具。具体分工如下：

| 模块 | AI 辅助程度 | 说明 |
|------|-----------|------|
| 项目架构设计 | 人机协作 | AI 协助设计了评分公式框架、数据流和模块划分；用户做出关键技术选型决策 |
| `src/config.py` | AI 生成 | 关键词词典、评分权重等参数由 AI 草拟，用户审核调整 |
| `src/data/stock_fetcher.py` | 人机协作 | 数据源选择和代理策略由用户决策，AI 完成代码实现和调试 |
| `src/data/news_fetcher.py` | AI 生成 | 多平台新闻抓取逻辑和去重算法由 AI 实现 |
| `src/analysis/*.py` | AI 生成 | 情感分析封装、分类器、评分引擎、雷达图计算均由 AI 实现 |
| `src/app.py` | AI 生成 | Flask 路由和 API 设计由 AI 完成 |
| `src/templates/index.html` | AI 生成 | 前端页面结构由 AI 设计 |
| `src/static/css/style.css` | AI 生成 | 深色科技风主题样式由 AI 编写 |
| `src/static/js/charts.js` | AI 生成 | ECharts 雷达图和饼图配置由 AI 实现 |
| `src/static/js/main.js` | AI 生成 | 前端交互逻辑由 AI 实现 |
| 评分算法核心逻辑 | 人机协作 | 用户提出"推荐指数 + 星级"需求，AI 实现了多因子加权模型 |
| 网络调试（代理/SSL/端口） | 人机协作 | 用户提供代理端口，AI 排查并修复了 SSL 证书路径、端口僵尸进程等问题 |
| `README.md` | AI 生成 | 项目文档由 AI 编写 |

**自主贡献说明**：用户独立完成了项目需求定义、技术选型（Flask + akshare + SnowNLP）、UI 风格要求（深色科技风）、评分维度设计（六维雷达）、来源分类方案（三分类）、以及全程的测试验证与反馈迭代。

---

## 七、项目结构

```
AlgoTradingTool/
├── src/
│   ├── app.py                  # Flask 主入口
│   ├── config.py               # 配置（评分权重、关键词词典、代理等）
│   ├── data/
│   │   ├── __init__.py          # SSL 证书修复
│   │   ├── stock_fetcher.py     # 股票搜索 + 行情 + K线
│   │   └── news_fetcher.py      # 多平台新闻抓取
│   ├── analysis/
│   │   ├── sentiment.py         # SnowNLP 情感分析
│   │   ├── classifier.py        # 来源分级 + 六维雷达分类
│   │   ├── scorer.py            # 综合评分引擎
│   │   └── radar.py             # 雷达图得分计算
│   ├── utils/
│   │   └── helpers.py           # 工具函数
│   ├── templates/
│   │   └── index.html           # 前端页面
│   └── static/
│       ├── css/style.css        # 深色科技风样式
│       └── js/
│           ├── charts.js        # ECharts 图表渲染
│           └── main.js          # 前端交互逻辑
├── docs/                        # 文档与附件
│   └── 主文档.md                # 作业主文档
├── tests/                       # 测试用例
├── requirements.txt             # Python 依赖
├── LICENSE                      # MIT 协议
└── README.md                    # 本文件
```

---

## 八、依赖清单

```
flask>=3.0
akshare>=1.14
snownlp>=0.12.3
pandas>=2.0
numpy>=1.24
jieba>=0.42
requests>=2.31
```

---

## 九、参考文献与开源组件

| 组件 | 用途 | 链接 |
|------|------|------|
| akshare | A 股数据接口 | https://github.com/akshare/akshare |
| SnowNLP | 中文情感分析 | https://github.com/isnowfy/snownlp |
| ECharts | 数据可视化 | https://echarts.apache.org/ |
| Flask | Web 框架 | https://flask.palletsprojects.com/ |
| jieba | 中文分词 | https://github.com/fxsjy/jieba |

---

## 十、免责声明

本工具仅供学习研究使用，**不构成任何投资建议**。股市有风险，投资需谨慎。

数据来源：akshare（新浪财经、腾讯证券、东方财富）

## License

MIT License
