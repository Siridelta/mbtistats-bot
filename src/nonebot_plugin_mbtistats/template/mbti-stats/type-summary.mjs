import { MbtistatsDashboard } from './dashboard-class.mjs';

MbtistatsDashboard.prototype.renderTypeSummary = function() {
    let pieData = [];

    const typeDataMap = this.typeRawData.reduce((acc, item) => {
        acc[item.name] = item;
        return acc;
    }, {});

    const totalValue = this.typeRawData.reduce((sum, item) => sum + item.value, 0);
    let accumValue = 0;

    const computeDynamicLine = (value, accum) => {
        const percent = (value / totalValue) * 100;
        const midValue = accum + value / 2;
        const angleRaw = 90 - (midValue / totalValue) * 360;
        const angle = (angleRaw + 360) % 360;

        const isTop = angle > 0 && angle < 180;
        let len1;
        let len2;

        if (isTop) {
            len1 = Math.max(15, 50 * Math.exp(-0.08 * percent));
            len2 = Math.max(15, 20 * Math.exp(-0.08 * percent));
        } else {
            len1 = Math.max(15, 20 * Math.exp(-0.5 * percent));
            len2 = Math.max(15, 20 * Math.exp(-0.5 * percent));
        }

        return { length: len1, length2: len2 };
    };

    this.mbtiConfig.forEach(config => {
        const item = typeDataMap[config.type];
        if (!item) return;

        pieData.push({
            ...item,
            itemStyle: { color: config.color },
            labelLine: computeDynamicLine(item.value, accumValue),
        });
        accumValue += item.value;
    });

    this.typeRawData.forEach(item => {
        if (this.colorMap[item.name]) return;
        if (item.value === 0) return;

        pieData.push({
            ...item,
            itemStyle: { color: this.defaultColor },
            labelLine: computeDynamicLine(item.value, accumValue),
        });
        accumValue += item.value;
    });

    this.pieChart.setOption({
        backgroundColor: '#ffffff',
        textStyle: { fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif' },
        title: { text: '类型分布', left: 'center' },
        tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
        series: [
            {
                name: 'MBTI 分布',
                type: 'pie',
                radius: ['35%', '60%'],
                center: ['50%', '52%'],
                avoidLabelOverlap: true,
                itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 },
                label: {
                    show: true,
                    position: 'outside',
                    formatter: function (params) {
                        const percent =
                            params.percent >= 1 ? params.percent.toFixed(0)
                                : params.percent >= 0.1 ? params.percent.toFixed(1)
                                    : params.percent.toFixed(2);
                        return `{title|${params.name}}\n{sub|${percent}%}`;
                    },
                    rich: {
                        title: {
                            color: '#333',
                            fontSize: 12,
                            fontWeight: 'bold',
                            align: 'center',
                            padding: [2, 0],
                        },
                        sub: { color: '#666', fontSize: 10, align: 'center' },
                    },
                    lineHeight: 12,
                    overflow: 'break',
                    width: 60,
                },
                labelLine: {
                    show: true,
                    length: 10,
                    length2: 15,
                    smooth: true,
                },
                data: pieData.filter(item => item.value > 0),
            },
        ],
    });

    const barData = pieData;
    const categories = barData.map(item => item.name);

    this.barChart.setOption({
        backgroundColor: '#ffffff',
        textStyle: { fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif' },
        title: { text: '类型统计', left: 'center' },
        tooltip: { trigger: 'item', formatter: '{b}: {c}人' },
        grid: { left: '8%', right: '15%', top: '10%', bottom: '0%', containLabel: true },
        xAxis: { type: 'value', boundaryGap: [0, 0.01], splitLine: { show: false } },
        yAxis: {
            type: 'category',
            data: categories,
            inverse: true,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { fontSize: 12, fontWeight: 'bold', color: '#333' },
        },
        series: [
            {
                name: '人数统计',
                type: 'bar',
                data: barData,
                label: { show: true, position: 'right', formatter: '{c}人', color: '#666' },
                barWidth: '60%',
                itemStyle: { borderRadius: [5, 5, 5, 5] },
            },
        ],
    });
};