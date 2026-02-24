import * as echarts from 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.esm.min.js';

export class MbtistatsDashboard {
    constructor(data) {
        this.echarts = echarts;
        this.typeRawData = data.typeRawData ?? [];
        this.traitRawData = data.traitRawData ?? {};
        this.typeHistoryData = this.normalizeHistoryData(data.typeHistoryData ?? []);
        this.traitHistoryData = this.normalizeHistoryData(data.traitHistoryData ?? []);

        this.pieChart = echarts.init(document.getElementById('pie-chart-container'));
        this.barChart = echarts.init(document.getElementById('bar-chart-container'));

        this.trendWindowsDom = document.getElementById('trend-windows-container');
        this.trendWindowRefs = {
            week: {
                card: document.getElementById('trend-window-week'),
                type16Dom: document.getElementById('trend-week-type16'),
                type4Dom: document.getElementById('trend-week-type4'),
            },
            month: {
                card: document.getElementById('trend-window-month'),
                type16Dom: document.getElementById('trend-month-type16'),
                type4Dom: document.getElementById('trend-month-type4'),
            },
            year: {
                card: document.getElementById('trend-window-year'),
                type16Dom: document.getElementById('trend-year-type16'),
                type4Dom: document.getElementById('trend-year-type4'),
            },
            all: {
                card: document.getElementById('trend-window-all'),
                type16Dom: document.getElementById('trend-all-type16'),
                type4Dom: document.getElementById('trend-all-type4'),
            },
        };

        this.eiChart = echarts.init(document.getElementById('chart-ei'));
        this.nsChart = echarts.init(document.getElementById('chart-ns'));
        this.tfChart = echarts.init(document.getElementById('chart-tf'));
        this.jpChart = echarts.init(document.getElementById('chart-jp'));

        this.tableContainer = document.getElementById('history-table-container');
        this.traitTableContainer = document.getElementById('trait-history-table-container');

        this.mbtiConfig = [
            // NT分析家 (紫色系)
            { type: "INTP", color: "#E8D9FF" }, { type: "ENTP", color: "#D469FF" },
            { type: "INTJ", color: "#C79FF3" }, { type: "ENTJ", color: "#A14BFF" },
            // NF外交家 (绿色系)
            { type: "INFP", color: "#A9D18E" }, { type: "ENFP", color: "#70AD47" },
            { type: "INFJ", color: "#548235" }, { type: "ENFJ", color: "#385723" },
            // SJ守护者 (蓝色系)
            { type: "ISTJ", color: "#2E75B6" }, { type: "ESTJ", color: "#9DC3E6" },
            { type: "ISFJ", color: "#BDD7EE" }, { type: "ESFJ", color: "#DEEBF7" },
            // SP探险家 (黄色系)
            { type: "ISTP", color: "#BF9000" }, { type: "ESTP", color: "#FFD356" },
            { type: "ISFP", color: "#FB9800" }, { type: "ESFP", color: "#FFB703" },
        ];
        this.colorMap = this.mbtiConfig.reduce((acc, item) => {
            acc[item.type] = item.color;
            return acc;
        }, {});
        this.defaultColor = '#cccccc';

        this.traitConfig = [
            { id: 'chart-ei', rawKey: 'EI', traits: ['I', 'E', 'X'], labels: ['I', 'E', '未知'], colors: ['#EEAB7E', '#8EBBE6', '#ccc'] },
            { id: 'chart-ns', rawKey: 'SN', traits: ['N', 'S', 'X'], labels: ['N', 'S', '未知'], colors: ['#89D18B', '#FFD863', '#ccc'] },
            { id: 'chart-tf', rawKey: 'TF', traits: ['F', 'T', 'X'], labels: ['F', 'T', '未知'], colors: ['#d4a5a5', '#9e9ac8', '#ccc'] },
            { id: 'chart-jp', rawKey: 'JP', traits: ['P', 'J', 'X'], labels: ['P', 'J', '未知'], colors: ['#80b1d3', '#fdb462', '#ccc'] },
        ];
    }

    normalizeHistoryData(data) {
        if (!Array.isArray(data)) return [];
        return data
            .filter(item => item && Number.isFinite(item.timestamp))
            .slice()
            .sort((a, b) => a.timestamp - b.timestamp);
    }

    renderTimestamp() {
        const date = new Date();
        document.getElementById('timestamp').textContent =
            `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${date.toLocaleTimeString()}`;
    }

    renderTypeHistoryTable() {
        if (!this.typeHistoryData || this.typeHistoryData.length === 0) return;

        let tableHTML = '<table>';
        tableHTML += '<thead><tr><th>日期</th>';

        const allTypes = [...new Set(this.typeHistoryData.flatMap(record =>
            record.data.filter(item => item.value > 0).map(item => item.name)
        ))].sort();

        allTypes.forEach(type => {
            tableHTML += `<th>${type}</th>`;
        });
        tableHTML += '</tr></thead><tbody>';

        this.typeHistoryData.toReversed().forEach(record => {
            const d = new Date(record.timestamp);
            const dateStr = `${d.getMonth() + 1}-${d.getDate()}`;
            tableHTML += `<tr><td>${dateStr}</td>`;
            allTypes.forEach(type => {
                const item = record.data.find(x => x.name === type);
                tableHTML += `<td>${item ? item.value : 0}</td>`;
            });
            tableHTML += '</tr>';
        });
        tableHTML += '</tbody></table>';
        this.tableContainer.innerHTML = tableHTML;
    }

    renderTraitHistoryTable() {
        if (!this.traitHistoryData || this.traitHistoryData.length === 0) return;

        let tableHTML = '<table>';
        tableHTML += '<thead><tr><th>日期</th>';

        const allDimensions = ['EI', 'SN', 'TF', 'JP'];
        const allTraits = {
            EI: ['E', 'I', 'X'],
            SN: ['S', 'N', 'X'],
            TF: ['T', 'F', 'X'],
            JP: ['J', 'P', 'X'],
        };

        allDimensions.forEach(dim => {
            allTraits[dim].forEach(trait => {
                tableHTML += `<th>${dim}-${trait}</th>`;
            });
        });
        tableHTML += '</tr></thead><tbody>';

        this.traitHistoryData.toReversed().forEach(record => {
            const d = new Date(record.timestamp);
            const dateStr = `${d.getMonth() + 1}-${d.getDate()}`;
            tableHTML += `<tr><td>${dateStr}</td>`;
            allDimensions.forEach(dim => {
                const dimData = record.data[dim] || {};
                allTraits[dim].forEach(trait => {
                    tableHTML += `<td>${dimData[trait] || 0}</td>`;
                });
            });
            tableHTML += '</tr>';
        });

        tableHTML += '</tbody></table>';
        this.traitTableContainer.innerHTML = tableHTML;
    }

    setupAll() {
        this.renderTimestamp();
        this.renderTopPersonality();
        this.renderTypeSummary();
        this.renderTrendCharts();
        this.renderTraitPies();
        this.renderTypeHistoryTable();
        this.renderTraitHistoryTable();
    }
}