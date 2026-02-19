import { MbtistatsDashboard } from './dashboard-class.mjs';

function _renderTraitPies() {
    const initTraitChart = (cfg) => {
        let chart;
        switch (cfg.id) {
            case 'chart-ei': chart = this.eiChart; break;
            case 'chart-ns': chart = this.nsChart; break;
            case 'chart-tf': chart = this.tfChart; break;
            case 'chart-jp': chart = this.jpChart; break;
            default: return;
        }

        const trait1 = cfg.traits[0];
        const trait2 = cfg.traits[1];
        const traitX = cfg.traits[2];

        const data1 = { count: this.traitRawData[cfg.rawKey][trait1] || 0 };
        const data2 = { count: this.traitRawData[cfg.rawKey][trait2] || 0 };
        const dataX = { count: this.traitRawData[cfg.rawKey][traitX] || 0 };

        const pieData = [
            {
                value: data1.count,
                name: cfg.labels[0],
                itemStyle: { color: cfg.colors[0] },
                label: { formatter: `${cfg.labels[0]}`, color: '#fff', fontSize: 16, fontWeight: 'bold', lineHeight: 20 },
            },
            {
                value: data2.count,
                name: cfg.labels[1],
                itemStyle: { color: cfg.colors[1] },
                label: { formatter: `${cfg.labels[1]}`, color: '#fff', fontSize: 16, fontWeight: 'bold', lineHeight: 20 },
            },
            {
                value: dataX.count,
                name: cfg.labels[2],
                itemStyle: { color: cfg.colors[2] },
                label: { formatter: `${cfg.labels[2]}`, color: '#fff', fontSize: 14, fontWeight: 'bold', lineHeight: 18 },
            },
        ];
        if (dataX.count === 0) pieData.pop();

        chart.setOption({
            title: { text: cfg.rawKey, left: 'center', textStyle: { fontSize: 14, fontWeight: 'bold' } },
            textStyle: { fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif' },
            tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
            series: [
                {
                    name: 'Distribution',
                    type: 'pie',
                    radius: ['30%', '90%'],
                    center: ['50%', '50%'],
                    avoidLabelOverlap: true,
                    itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
                    label: {
                        show: true,
                        position: 'inside',
                        formatter: '{b}',
                        fontSize: 16,
                        fontWeight: 'bold',
                        color: '#fff',
                        lineHeight: 20,
                        align: 'center',
                        verticalAlign: 'middle',
                    },
                    labelLine: { show: false },
                    emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
                    data: pieData,
                },
            ],
        });
    };

    this.traitConfig.forEach(cfg => initTraitChart(cfg));
}
MbtistatsDashboard.prototype.renderTraitPies = _renderTraitPies;