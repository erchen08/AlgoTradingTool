/**
 * AlgoTradingTool - 前端交互逻辑
 */

// ============================================================
// 页面初始化
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('stock-input');
    const btn = document.getElementById('analyze-btn');

    // 回车触发分析
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            runAnalysis();
        }
    });

    // 自动聚焦
    input.focus();
});

// ============================================================
// 核心分析流程
// ============================================================
async function runAnalysis() {
    const input = document.getElementById('stock-input');
    const stockName = input.value.trim();

    if (!stockName) {
        input.focus();
        input.style.borderColor = '#ff4757';
        setTimeout(() => { input.style.borderColor = ''; }, 1500);
        return;
    }

    // 显示加载动画
    showLoading(true);

    // 隐藏旧结果
    const resultContainer = document.getElementById('result-container');
    resultContainer.classList.add('hidden');

    try {
        // 模拟加载步骤
        const loadingSteps = [
            '获取实时交易数据...',
            '抓取多平台新闻...',
            '正在执行 SnowNLP 情感分析...',
            '计算综合评分...',
            '生成可视化报告...',
        ];
        const detailEl = document.getElementById('loading-detail');

        // 开始请求
        const fetchPromise = fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stock_name: stockName }),
        });

        // 动画加载步骤
        let stepIndex = 0;
        const stepInterval = setInterval(() => {
            if (stepIndex < loadingSteps.length) {
                detailEl.textContent = loadingSteps[stepIndex];
                stepIndex++;
            }
        }, 600);

        const response = await fetchPromise;
        clearInterval(stepInterval);

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || '分析失败');
        }

        const data = await response.json();
        showLoading(false);

        // 1. 先显示容器
        resultContainer.classList.remove('hidden');

        // 2. 先渲染非图表内容（推荐横幅、评分卡片、新闻）
        renderRecommendation(data);
        renderScoreCards(data.scores);
        renderNewsList(data.news);

        // 3. 等浏览器完成布局后再初始化图表
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                try { renderRadarChart(data.radar); } catch(e) { console.error('Radar error:', e); }
                try { renderSourcePieChart(data.source_distribution); } catch(e) { console.error('Pie error:', e); }
            });
        });

        // 滚动到结果区域
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        showLoading(false);
        alert('分析失败: ' + error.message);
        console.error(error);
    }
}

// ============================================================
// 加载动画切换
// ============================================================
function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// ============================================================
// 渲染分析结果
// ============================================================
function renderResults(data) {
    renderRecommendation(data);
    renderScoreCards(data.scores);
    renderNewsList(data.news);
    // 图表在主流程中通过 requestAnimationFrame 延迟渲染
}

// ============================================================
// 渲染推荐横幅
// ============================================================
function renderRecommendation(data) {
    var stock = data.stock;
    var rec = data.recommendation;
    var summary = data.summary;
    var scores = data.scores;

    // 推荐徽章：显示推荐指数
    var badge = document.getElementById('rec-badge');
    var title = document.getElementById('rec-title');
    var summaryEl = document.getElementById('rec-summary');

    badge.className = 'rec-badge';
    title.className = 'rec-title';

    var recIndex = rec.index || scores.overall;
    var recText = rec.text || '';
    var recStars = rec.stars || '';

    if (recIndex >= 65) {
        badge.classList.add('buy');
        title.style.color = '#00ff88';
    } else if (recIndex >= 40) {
        badge.classList.add('hold');
        title.style.color = '#ffc107';
    } else {
        badge.classList.add('avoid');
        title.style.color = '#ff4757';
    }

    badge.textContent = recIndex;
    title.textContent = recStars + ' ' + recText + '（推荐指数 ' + recIndex + '）';

    summaryEl.textContent = summary;

    // 股票信息
    document.querySelector('.stock-name-large').textContent = stock.name;
    document.querySelector('.stock-price-large').textContent = stock.price.toFixed(2);

    var changeEl = document.querySelector('.stock-change-large');
    var changePct = stock.change_pct || 0;
    changeEl.textContent = (changePct >= 0 ? '+' : '') + changePct.toFixed(2) + '%';
    changeEl.className = 'stock-change-large ' + (changePct >= 0 ? 'up' : 'down');

    document.title = recText + ' | ' + stock.name + ' - AlgoTradingTool';
}

// ============================================================
// 渲染评分卡片
// ============================================================
function renderScoreCards(scores) {
    const keys = [
        { id: 'financial', el: 'score-financial', bar: 'bar-financial' },
        { id: 'sentiment', el: 'score-sentiment', bar: 'bar-sentiment' },
        { id: 'risk', el: 'score-risk', bar: 'bar-risk' },
        { id: 'confidence', el: 'score-confidence', bar: 'bar-confidence' },
    ];

    keys.forEach(({ id, el, bar }) => {
        const value = scores[id] || 0;
        const elScore = document.getElementById(el);
        const elBar = document.getElementById(bar);

        // 数字动画
        animateNumber(elScore, 0, value, 800);

        // 进度条动画
        setTimeout(() => {
            elBar.style.width = value + '%';
        }, 200);
    });

    // 综合评分显示在推荐横幅中，这里暂不额外显示
}

/**
 * 数字滚动动画
 */
function animateNumber(element, start, end, duration) {
    if (!element) return;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // ease-out
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * eased;
        element.textContent = current.toFixed(1);
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// ============================================================
// 渲染新闻列表
// ============================================================
function renderNewsList(newsItems) {
    const container = document.getElementById('news-list');
    const countEl = document.getElementById('news-count');

    if (!container) return;

    countEl.textContent = `共 ${newsItems.length} 条`;
    container.innerHTML = '';

    if (newsItems.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:40px;color:#5a6080;">暂无相关新闻</div>';
        return;
    }

    newsItems.forEach(item => {
        const sentiment = item.sentiment || 50;
        let sentimentClass = 'neutral';
        let sentimentLabel = '中性';
        if (sentiment >= 55) {
            sentimentClass = 'positive';
            sentimentLabel = '正面';
        } else if (sentiment <= 45) {
            sentimentClass = 'negative';
            sentimentLabel = '负面';
        }

        var sourceCat = item.source_category || '主流媒体';
        var sourceDotClass = sourceCat === '官方媒体' ? 'official'
            : sourceCat === '主流媒体' ? 'mainstream'
            : 'self';

        const card = document.createElement('div');
        card.className = `news-card ${sentimentClass}`;
        card.innerHTML = `
            <div class="news-card-title">${escapeHtml(item.title)}</div>
            <div class="news-card-summary">${escapeHtml(item.summary)}</div>
            <div class="news-card-meta">
                <div class="news-card-source">
                    <span class="source-dot ${sourceDotClass}"></span>
                    ${escapeHtml(sourceCat)} · ${escapeHtml(item.source)}
                </div>
                <span class="news-card-sentiment ${sentimentClass}">
                    ${sentimentLabel} ${sentiment.toFixed(0)}%
                </span>
            </div>
        `;

        // 如果有 URL，添加点击跳转
        if (item.url) {
            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                window.open(item.url, '_blank');
            });
        }

        container.appendChild(card);
    });
}

// ============================================================
// 工具函数
// ============================================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
