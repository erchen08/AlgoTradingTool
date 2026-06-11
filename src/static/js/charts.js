/**
 * AlgoTradingTool - ECharts 图表渲染
 */
const CHART_THEME = {
    textColor: '#8890b5',
    axisColor: '#2a2f50',
    splitColor: 'rgba(42, 47, 80, 0.4)',
};

window.radarChartInstance = null;
window.pieChartInstance = null;

function renderRadarChart(radarData) {
    var container = document.getElementById('radar-chart');
    if (!container) return;

    // 强制显示并获取实际尺寸
    container.style.display = 'block';
    var w = container.clientWidth || container.offsetWidth || 1200;
    var h = container.clientHeight || container.offsetHeight || 800;

    if (window.radarChartInstance) {
        window.radarChartInstance.dispose();
    }

    window.radarChartInstance = echarts.init(container, null, {
        width: w,
        height: h,
        devicePixelRatio: window.devicePixelRatio || 1,
    });

    var dimensions = ['财务表现','资本市场','市场竞争','产品技术','公司经营','行业政策'];
    var values = dimensions.map(function(d) { return radarData[d] || 50; });

    window.radarChartInstance.setOption({
        tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(17, 22, 64, 0.95)',
            borderColor: '#2a2f50',
            textStyle: { color: '#e0e6f0', fontSize: 14 },
            formatter: function(p) {
                var s = p.value >= 70 ? '积极' : p.value >= 40 ? '中性' : '消极';
                return '<b>' + p.name + '</b><br/>' + p.value.toFixed(1) + ' / 100<br/>' + s;
            },
        },
        legend: {
            bottom: 10,
            textStyle: { color: CHART_THEME.textColor, fontSize: 14 },
            data: ['当前评分'],
        },
        radar: {
            center: ['50%', '46%'],
            radius: '72%',
            indicator: dimensions.map(function(d) { return { name: d, max: 100 }; }),
            axisName: { color: CHART_THEME.textColor, fontSize: 14, borderRadius: 3, padding: [3, 5] },
            shape: 'polygon',
            splitNumber: 4,
            axisLine: { lineStyle: { color: CHART_THEME.axisColor } },
            splitLine: { lineStyle: { color: CHART_THEME.splitColor } },
            splitArea: { areaStyle: { color: ['rgba(0,212,255,0.02)', 'rgba(0,212,255,0.04)'] } },
        },
        series: [{
            name: '当前评分', type: 'radar',
            data: [{ value: values, name: '当前评分' }],
            symbol: 'circle', symbolSize: 8,
            lineStyle: { color: '#00d4ff', width: 3, shadowBlur: 12, shadowColor: 'rgba(0,212,255,0.5)' },
            areaStyle: { color: { type: 'radial', x: 0.5, y: 0.5, r: 0.5, colorStops: [{ offset: 0, color: 'rgba(0,212,255,0.3)' }, { offset: 1, color: 'rgba(0,212,255,0.02)' }] } },
            itemStyle: { color: '#00d4ff', borderColor: '#fff', borderWidth: 2 },
            label: { show: true, formatter: '{c}', color: '#e0e6f0', fontSize: 14, fontWeight: 'bold' },
        }],
    });
}

function renderSourcePieChart(sourceData) {
    var container = document.getElementById('source-pie-chart');
    if (!container) return;

    // DEBUG: 在标题旁边显示数据，确认函数被调用且数据正确
    var title = document.querySelector('#source-pie-chart').parentElement.querySelector('.chart-title');
    if (title && sourceData && sourceData.items) {
        var debugText = sourceData.items.map(function(i) { return i.name + ':' + i.value; }).join(' ');
        title.setAttribute('data-debug', debugText);
        title.textContent = '信息来源分布 [' + sourceData.total + '条] ' + debugText;
    }

    container.style.display = 'block';
    var w = container.clientWidth || container.offsetWidth || 800;
    var h = container.clientHeight || container.offsetHeight || 800;

    if (window.pieChartInstance) {
        window.pieChartInstance.dispose();
    }

    window.pieChartInstance = echarts.init(container, null, {
        width: w,
        height: h,
        devicePixelRatio: window.devicePixelRatio || 1,
    });

    var total = sourceData.total || 1;
    // 使用后端传来的 items 数组（避免中文键名编码问题）
    var pieData = (sourceData.items || []).map(function(item) {
        return { name: item.name, value: item.value, itemStyle: { color: item.color } };
    });
    // DEBUG: 如果 pieData 为空，用默认数据
    if (pieData.length === 0) {
        pieData = [
            { name: '官方媒体', value: 3, itemStyle: { color: '#ffd700' } },
            { name: '主流媒体', value: 5, itemStyle: { color: '#00d4ff' } },
            { name: '自媒体', value: 2, itemStyle: { color: '#5a6080' } },
        ];
    }

    window.pieChartInstance.setOption({
        tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(17, 22, 64, 0.95)',
            borderColor: '#2a2f50',
            textStyle: { color: '#e0e6f0', fontSize: 14 },
            formatter: function(p) { return '<b>' + p.name + '</b><br/>' + p.value + ' 条<br/>' + p.percent + '%'; },
        },
        legend: {
            orient: 'vertical', right: '8%', top: 'center',
            textStyle: { color: CHART_THEME.textColor, fontSize: 15 }, itemGap: 20,
        },
        series: [{
            name: '信息来源', type: 'pie',
            radius: ['48%', '78%'], center: ['38%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 8, borderColor: '#0a0e27', borderWidth: 4 },
            label: { show: true, position: 'inside', formatter: '{d}%', color: '#fff', fontSize: 16, fontWeight: 'bold' },
            emphasis: { label: { fontSize: 22, fontWeight: 'bold' }, scaleSize: 10 },
            data: pieData,
        }],
        graphic: [{
            type: 'text', left: '28%', top: '43%',
            style: { text: total + '\n条', textAlign: 'center', fill: '#e0e6f0', fontSize: 20, fontWeight: 'bold', lineHeight: 26 },
        }],
    });
}

// resize on window change
window.addEventListener('resize', function() {
    if (window.radarChartInstance) window.radarChartInstance.resize();
    if (window.pieChartInstance) window.pieChartInstance.resize();
});
