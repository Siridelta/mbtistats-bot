const date = new Date();
document.getElementById("timestamp").textContent = `
    ${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${date.toLocaleTimeString()}
`;

// 全局变量
var _typeRawData;
var _traitRawData;
var _typeHistoryData;
var _traitHistoryData;
var echarts;

// 注入的数据
const typeRawData = _typeRawData;
const traitRawData = _traitRawData;
const typeHistoryData = _typeHistoryData;
const traitHistoryData = _traitHistoryData;

// 类型统计图表
var pieDom = document.getElementById("pie-chart-container");
var pieChart = echarts.init(pieDom);
var barDom = document.getElementById("bar-chart-container");
var barChart = echarts.init(barDom);
var trendDom = document.getElementById("trend-chart-container");
var trendChart = echarts.init(trendDom);
var tableContainer = document.getElementById("history-table-container");

// 特质统计图表
var eiDom = document.getElementById("chart-ei");
var eiChart = echarts.init(eiDom);
var nsDom = document.getElementById("chart-ns");
var nsChart = echarts.init(nsDom);
var tfDom = document.getElementById("chart-tf");
var tfChart = echarts.init(tfDom);
var jpDom = document.getElementById("chart-jp");
var jpChart = echarts.init(jpDom);
var traitTrendDom = document.getElementById("trait-trend-chart-container");
var traitTrendChart = echarts.init(traitTrendDom);
var traitTableContainer = document.getElementById("trait-history-table-container");

// 1. 定义 MBTI 颜色映射配置表 (保证顺序: 分析家 -> 外交家 -> 守护者 -> 探险家)
// 使用数组形式以保留严格顺序
const mbtiConfig = [
    // 分析家 (紫色系)
    { type: "INTP", color: "#E8D9FF" }, { type: "ENTP", color: "#D469FF" },
    { type: "INTJ", color: "#C79FF3" }, { type: "ENTJ", color: "#A14BFF" },
    // 外交家 (绿色系)
    { type: "INFP", color: "#A9D18E" }, { type: "ENFP", color: "#70AD47" },
    { type: "INFJ", color: "#548235" }, { type: "ENFJ", color: "#385723" },
    // 守护者 (蓝色系)
    { type: "ISTJ", color: "#2E75B6" }, { type: "ESTJ", color: "#9DC3E6" },
    { type: "ISFJ", color: "#BDD7EE" }, { type: "ESFJ", color: "#DEEBF7" },
    // 探险家 (黄色系)
    { type: "ISTP", color: "#BF9000" }, { type: "ESTP", color: "#FFD356" },
    { type: "ISFP", color: "#FB9800" }, { type: "ESFP", color: "#FFB703" },
];

// 生成颜色映射表以便快速查找
// 形如：{"INTJ": "#b59bc4", "INTP": "#9b85c1", "ENTJ": "#715c9d", ...}
const colorMap = mbtiConfig.reduce((acc, item) => {
    acc[item.type] = item.color;
    return acc;
}, {});

// 默认颜色，面向模糊类型
const defaultColor = "#cccccc";



// 动态获取人数最多的人格类型并显示图片和文字说明
function displayTopPersonality() {
    // 获取人数最多的人格类型
    let topPersonality = '';
    let maxCount = 0;
    
    typeRawData.forEach(item => {
        if (item.value > maxCount) {
            maxCount = item.value;
            topPersonality = item.name;
        }
    });
    
    // 更新文字说明
    const textContainer = document.getElementById('top-personality-text');
    textContainer.textContent = `本次统计最多的人格是${topPersonality}`;
    
    // 加载图片
    const imageContainer = document.getElementById('top-personality-image');
    const img = new Image();
    img.src = `../images/${topPersonality}.png`;
    img.alt = `${topPersonality}人格图片`;
    
    // 图片加载成功处理
    img.onload = function() {
        imageContainer.innerHTML = '';
        imageContainer.appendChild(img);
    };
    
    // 图片加载失败处理，显示紫色占位图
    img.onerror = function() {
        imageContainer.innerHTML = '<div class="purple-placeholder"></div>';
    };
}

// 调用函数显示图片和文字说明
displayTopPersonality();

// ==================== 类型统计部分 ====================

// 2. 数据预处理：注入颜色 itemStyle 并排序
// 我们希望饼图扇区按照 mbtiConfig 的逻辑顺序排列 (分析家在一起, etc.)

let pieData = [];

// 2.1 先把原始数据转成 Map 方便查找
// 形如：{"INTP": {"name": "INTP", "value": 15}, "INTJ": {"name": "INTJ", "value": 8}, ...}
const typeDataMap = typeRawData.reduce((acc, item) => {
    acc[item.name] = item;
    return acc;
}, {});

// 2.2 按照 mbtiConfig 的顺序填充数据
// 形如：[{"name": "INTP", "value": 15, "itemStyle": { color: "#9b85c1" }}, {"name": "INTJ", "value": 8, "itemStyle": { color: "#b59bc4" }}, ...]

// 先计算总数以便计算百分比
const totalValue = typeRawData.reduce((sum, item) => sum + item.value, 0);

// 维护当前的累计数值，*状态变量* (用于计算角度)
let accumValue = 0;

const computeDynamicLine = (value, accumValue) => {
    // 计算百分比
    const percent = (value / totalValue) * 100;
    
    // 内部计算角度：
    // 1. 计算当前 item 的中点累计值 (前序总和 + 当前的一半)
    const midValue = accumValue + value / 2;
    // 2. 计算中点角度 (ECharts startAngle=90, 顺时针为减)
    const _angle = 90 - (midValue / totalValue) * 360;
    const angle = (_angle + 360) % 360;
    
    // 动态线长策略 (连续算法):
    // 主要考虑两个因素：百分比是否很小，以及是否位于靠上的角度位置（靠下的角度位置 Echarts 的排布算法会工作的很好，不需要额外处理）。
    // 使用指数衰减函数，让线长随百分比平滑减少


    // 判断是否在"上方危险区" (大约 9点半 到 2点半)
    // 12点=90度。我们设定范围：30度(2点) ~ 150度(10点) 为拥挤区
    const isTop = angle > 0 && angle < 180;
    let len1, len2;

    if (isTop) {
        // 上方拥挤区：使用较长的线，且随百分比快速衰减（小扇区推远）
        // 第一段线 (length): 主要负责把标签"推"离饼图
        // 第二段线 (length2): 主要负责横向对齐，小扇区需要更长的横向空间来错开
        len1 = Math.max(15, 50 * Math.exp(-0.08 * percent));
        len2 = Math.max(15, 20 * Math.exp(-0.08 * percent));
    } else {
        // 下方宽敞区：使用较短的线，保持紧凑
        len1 = Math.max(15, 20 * Math.exp(-0.5 * percent));
        len2 = Math.max(15, 20 * Math.exp(-0.5 * percent));
    }

    return {
        length: len1,
        length2: len2
    };
}

mbtiConfig.forEach(config => {
    const item = typeDataMap[config.type];
    if (!item) return;

    pieData.push({
        ...item,
        itemStyle: { color: config.color },
        labelLine: computeDynamicLine(item.value, accumValue) 
    });
    accumValue += item.value;
});

// 2.3 (可选) 处理配置表中没有但原始数据里有的"模糊类型"
typeRawData.forEach(item => {
    const type = item.name;
    if (colorMap[type]) return;

    // "模糊类型"项为 0 时不显示
    if (item.value === 0) return;
    
    pieData.push({
        ...item,
        itemStyle: { color: defaultColor },
        labelLine: computeDynamicLine(item.value, accumValue)
    });
    accumValue += item.value;
});

// 2. 数据处理：柱状图也需要数据
// 柱状图通常按照数量排序，或者按照固定 MBTI 顺序排序
// 这里我们按照 mbtiConfig 的固定顺序（分析家->外交家...）来排，方便对比
const barData = pieData; // 直接复用已排序好的数据
const categories = barData.map(item => item.name);

// 2.1 去掉饼图数据中 value 为 0 的项
pieData = pieData.filter(item => item.value > 0);

// 饼图选项
const pieOption = {
    backgroundColor: '#ffffff',
    textStyle: {
        fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif'
    },
    title: {
        text: '类型分布',
        left: 'center'
    },
    tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}人 ({d}%)'
    },
    series: [
        {
            name: 'MBTI 分布',
            type: 'pie',
            radius: ['35%', '60%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: true,
            itemStyle: {
                borderRadius: 5,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: {
                show: true,
                position: 'outside',
                formatter: function (params) {
                    const type = params.name;
                    const percent =
                        params.percent >= 1 ? params.percent.toFixed(0)
                            : params.percent >= 0.1 ? params.percent.toFixed(1)
                                : params.percent.toFixed(2);

                    return `{title|${type}}\n{sub|${percent}%}`;
                },
                rich: {
                    title: {
                        color: '#333',
                        fontSize: 12,
                        fontWeight: 'bold',
                        align: 'center',
                        padding: [2, 0]
                    },
                    sub: {
                        color: '#666',
                        fontSize: 10,
                        align: 'center'
                    }

                },
                lineHeight: 12,
                overflow: 'break',
                width: 60
            },
            labelLine: {
                show: true,
                // 全局默认值保留一个适中的，具体值会被 data 里的 dynamicLine 覆盖
                length: 10,
                length2: 15,
                smooth: true
            },
            data: pieData
        }
    ]
};

// 柱状图选项
const barOption = {
    backgroundColor: '#ffffff',
    textStyle: {
        fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif'
    },
    title: {
        text: '类型统计',
        left: 'center'
    },
    tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}人'
    },
    grid: {
        left: '20%',
        right: '15%',
        top: '20%',
        bottom: '5%',
        containLabel: true
    },
    xAxis: {
        type: 'value',
        boundaryGap: [0, 0.01],
        splitLine: { show: false }
    },
    yAxis: {
        type: 'category',
        data: categories,
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
            fontSize: 12,
            fontWeight: 'bold',
            color: '#333'
        }
    },
    series: [
        {
            name: '人数统计',
            type: 'bar',
            data: barData,
            label: {
                show: true,
                position: 'right',
                formatter: '{c}人',
                color: '#666'
            },
            barWidth: '60%',
            itemStyle: {
                borderRadius: [5, 5, 5, 5]
            }
        }
    ]
};

// 设置图表选项
if (pieOption && typeof pieOption === "object") {
    pieChart.setOption(pieOption);
}

if (barOption && typeof barOption === "object") {
    barChart.setOption(barOption);
}

// 绘制历史趋势图（改为堆积柱状图）
if (typeHistoryData && typeHistoryData.length > 1) {
    // 准备趋势图数据
    const dates = typeHistoryData.map(record => {
        const d = new Date(record.timestamp);
        return `${d.getMonth()+1}-${d.getDate()}`;
    });
    
    // 定义四色分类
    const colorGroups = {
        "分析家": ["INTJ", "INTP", "ENTJ", "ENTP"],
        "外交家": ["INFJ", "INFP", "ENFJ", "ENFP"],
        "守护者": ["ISTJ", "ISFJ", "ESTJ", "ESFJ"],
        "探险家": ["ISTP", "ISFP", "ESTP", "ESFP"]
    };
    
    // 为每个四色组合创建数据系列
    const series = [];
    Object.entries(colorGroups).forEach(([groupName, types]) => {
        // 获取该组合在所有历史记录中的数值
        const groupData = typeHistoryData.map(record => {
            return types.reduce((sum, type) => {
                const item = record.data.find(d => d.name === type);
                return sum + (item ? item.value : 0);
            }, 0);
        });
        
        // 定义颜色
        let color;
        switch(groupName) {
            case "分析家": color = "#9b85c1"; break;
            case "外交家": color = "#70AD47"; break;
            case "守护者": color = "#2E75B6"; break;
            case "探险家": color = "#FFB703"; break;
            default: color = "#cccccc";
        }
        
        series.push({
            name: groupName,
            type: 'line',
            data: groupData,
            itemStyle: { color: color },
            lineStyle: {
                color: color,
                width: 2
            },
            symbol: 'circle',
            symbolSize: 6,
            smooth: true,
            emphasis: {
                focus: 'series',
                symbolSize: 8
            },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 0,
                    y2: 1,
                    colorStops: [{
                        offset: 0, color: color + '80' // 80是透明度，半透明
                    }, {
                        offset: 1, color: color + '10' // 10是透明度，几乎透明
                    }]
                }
            }
        });
    });
    
    const trendOption = {
        title: {
            text: '四色人格历史趋势',
            left: 'center',
            textStyle: {
                fontSize: 18,
                fontWeight: 'bold'
            }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                label: {
                    backgroundColor: '#6a7985'
                }
            },
            formatter: function (params) {
                let result = params[0].axisValueLabel + '<br/>';
                params.sort((a, b) => b.value - a.value);
                params.forEach(param => {
                    if (param.value > 0) {
                        result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${param.color};"></span>`;
                        result += `${param.seriesName}: ${param.value}人<br/>`;
                    }
                });
                return result;
            }
        },
        legend: {
            type: 'scroll',
            bottom: 0,
            data: Object.keys(colorGroups),
            textStyle: {
                fontSize: 12
            },
            itemWidth: 12,
            itemHeight: 12,
            orient: 'horizontal',
            pageIconSize: 12,
            pageTextStyle: {
                fontSize: 12
            },
            padding: [10, 10, 10, 10]
        },
        grid: {
            left: '5%',
            right: '5%',
            bottom: '5%',
            top: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
                fontSize: 12,
                rotate: 45,
                interval: 0
            },
            axisLine: {
                show: true
            },
            axisTick: {
                show: true
            },
            boundaryGap: false
        },
        yAxis: {
            type: 'value',
            name: '人数',
            nameTextStyle: {
                fontSize: 12,
                fontWeight: 'bold'
            },
            axisLabel: {
                fontSize: 12
            },
            axisLine: {
                show: true
            },
            axisTick: {
                show: true
            },
            splitLine: {
                show: true,
                lineStyle: {
                    type: 'dashed'
                }
            }
        },
        series: series
    };
    
    trendChart.setOption(trendOption);
    
    // 创建历史数据表格
    createTypeHistoryTable(typeHistoryData, colorGroups);
}

// 创建历史数据表格
function createTypeHistoryTable(historyData, colorGroups) {
    if (!historyData || historyData.length <= 1) return;
    
    let tableHTML = '<table>';
    
    // 表头
    tableHTML += '<thead><tr><th>日期</th>';
    
    // 添加所有类型列
    const allTypes = [...new Set(historyData.flatMap(record => 
        record.data.filter(item => item.value > 0).map(item => item.name)
    ))].sort();
    
    allTypes.forEach(type => {
        tableHTML += `<th>${type}</th>`;
    });
    
    tableHTML += '</tr></thead><tbody>';
    
    // 数据行
    historyData.forEach(record => {
        const d = new Date(record.timestamp);
        const dateStr = `${d.getMonth()+1}-${d.getDate()}`;
        tableHTML += `<tr><td>${dateStr}</td>`;
        
        // 为每种类型添加数据
        allTypes.forEach(type => {
            const item = record.data.find(d => d.name === type);
            const value = item ? item.value : 0;
            tableHTML += `<td>${value}</td>`;
        });
        
        tableHTML += '</tr>';
    });
    
    tableHTML += '</tbody></table>';
    tableContainer.innerHTML = tableHTML;
}

// ==================== 特质统计部分 ====================

// 4个维度的配置
// 颜色灵感来自 16Personalities 风格，但为了可见性进行了调整
const traitConfig = [
    {
        id: 'chart-ei',
        rawKey: 'EI',
        traits: ['I', 'E', 'X'], // 内向 (I) / 外向 (E)
        labels: ['I', 'E', '未知'],
    },
    {
        id: 'chart-ns',
        rawKey: 'SN',
        traits: ['N', 'S', 'X'], // 直觉 (N) / 实感 (S)
        labels: ['N', 'S', '未知'],
    },
    {
        id: 'chart-tf',
        rawKey: 'TF',
        traits: ['F', 'T', 'X'], // 情感 (F) / 思考 (T)
        labels: ['F', 'T', '未知'],
    },
    {
        id: 'chart-jp',
        rawKey: 'JP',
        traits: ['P', 'J', 'X'], // 展望 (P) / 计划 (J)
        labels: ['P', 'J', '未知'],
    }
];

// 基于连贯的方案重新分配颜色
traitConfig[0].colors = ['#EEAB7E', '#8EBBE6', '#ccc']; // I(橙色), E(蓝色)
traitConfig[1].colors = ['#89D18B', '#FFD863', '#ccc']; // N(绿色), S(黄色)
traitConfig[2].colors = ['#d4a5a5', '#9e9ac8', '#ccc']; // F(微红), T(微紫)
traitConfig[3].colors = ['#80b1d3', '#fdb462', '#ccc']; // P(蓝色), J(橙色)

// 初始化函数
traitConfig.forEach(cfg => {
    initTraitChart(cfg);
});

function initTraitChart(cfg) {
    let chart;
    switch(cfg.id) {
        case 'chart-ei': chart = eiChart; break;
        case 'chart-ns': chart = nsChart; break;
        case 'chart-tf': chart = tfChart; break;
        case 'chart-jp': chart = jpChart; break;
        default: return;
    }
    
    const trait1 = cfg.traits[0]; // e.g. 'I'
    const trait2 = cfg.traits[1]; // e.g. 'E'
    const traitX = cfg.traits[2]; // e.g. 'X'

    const name1 = cfg.labels[0];
    const name2 = cfg.labels[1];
    const nameX = cfg.labels[2];
    
    const data1 = {count: traitRawData[cfg.rawKey][trait1] || 0};
    const data2 = {count: traitRawData[cfg.rawKey][trait2] || 0};
    const dataX = {count: traitRawData[cfg.rawKey][traitX] || 0};

    // 饼图数据
    const pieData = [
        {
            value: data1.count, 
            name: name1, 
            itemStyle: { color: cfg.colors[0] },
            label: {
                formatter: `${name1}`,
                color: '#fff',
                fontSize: 16,
                fontWeight: 'bold',
                lineHeight: 20
            }
        },
        {
            value: data2.count, 
            name: name2, 
            itemStyle: { color: cfg.colors[1] },
            label: {
                formatter: `${name2}`,
                color: '#fff',
                fontSize: 16,
                fontWeight: 'bold',
                lineHeight: 20
            }
        },
        {
            value: dataX.count, 
            name: nameX, 
            itemStyle: { color: cfg.colors[2] },
            label: {
                formatter: `${nameX}`,
                color: '#fff',
                fontSize: 14,
                fontWeight: 'bold',
                lineHeight: 18
            }
        }
    ];

    // "未知"项为 0 时不显示
    if (dataX.count === 0) {
        pieData.pop();
    }

    const option = {
        title: {
            text: cfg.rawKey,
            left: 'center',
            textStyle: {
                fontSize: 14,
                fontWeight: 'bold'
            }
        },
        textStyle: {
            fontFamily: 'Noto Sans SC, Microsoft YaHei, sans-serif'
        },
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        series: [
            {
                name: 'Distribution',
                type: 'pie',
                radius: ['30%', '90%'],
                center: ['50%', '50%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 4,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    position: 'inside',
                    formatter: '{b}',
                    fontSize: 16,
                    fontWeight: 'bold',
                    color: '#fff',
                    lineHeight: 20,
                    align: 'center',
                    verticalAlign: 'middle'
                },
                labelLine: {
                    show: false
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 18,
                        fontWeight: 'bold'
                    }
                },
                data: pieData
            }
        ]
    };
    
    chart.setOption(option);
}

// 绘制16MBTI各种人格的数量变化堆积柱状图
if (typeHistoryData && typeHistoryData.length > 1) {
    // 准备趋势图数据
    const dates = typeHistoryData.map(record => {
        const d = new Date(record.timestamp);
        return `${d.getMonth()+1}-${d.getDate()}`;
    });
    
    // 获取所有16人格类型
    const allPersonalities = mbtiConfig.map(item => item.type);
    
    // 初始化各人格的数据数组
    const personalitySeriesData = {};
    allPersonalities.forEach(personality => {
        personalitySeriesData[personality] = Array(typeHistoryData.length).fill(0);
    });
    
    // 填充数据 - 按时间点和人格类型计算数量
    typeHistoryData.forEach((record, recordIndex) => {
        record.data.forEach(item => {
            if (personalitySeriesData[item.name] !== undefined) {
                personalitySeriesData[item.name][recordIndex] = item.value;
            }
        });
    });
    
    // 创建系列
    const series = [];
    
    allPersonalities.forEach(personality => {
        // 获取对应颜色
        const color = colorMap[personality] || defaultColor;
        
        series.push({
            name: personality,
            type: 'bar',
            stack: '总量',
            data: personalitySeriesData[personality],
            itemStyle: { color: color },
            barGap: 0, // 相邻柱状条间距为0
            label: {
                show: false,
                position: 'top',
                fontSize: 8,
                formatter: '{c}'
            }
        });
    });
    
    const trendOption = {
        title: {
            text: '16人格数量变化趋势',
            left: 'center',
            textStyle: {
                fontSize: 18,
                fontWeight: 'bold'
            }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            },
            formatter: function (params) {
                let result = params[0].axisValueLabel + '<br/>';
                // 按系列值从大到小排序
                params.sort((a, b) => b.value - a.value);
                params.forEach(param => {
                    if (param.value > 0) {
                        result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${param.color};"></span>`;
                        result += `${param.seriesName}: ${param.value}人<br/>`;
                    }
                });
                return result;
            }
        },
        legend: {
            type: 'scroll',
            bottom: 0,
            data: allPersonalities,
            textStyle: {
                fontSize: 10
            },
            itemWidth: 10,
            itemHeight: 10,
            orient: 'horizontal',
            pageIconSize: 10,
            pageTextStyle: {
                fontSize: 10
            },
            padding: [0, 0, 0, 0],
            pageButtonItemGap: 5,
            pageButtonGap: 10
        },
        grid: {
            left: '5%',
            right: '5%',
            bottom: '5%',
            top: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
                fontSize: 12,
                rotate: 45,
                interval: 0
            },
            axisLine: {
                show: true
            },
            axisTick: {
                show: true
            }
        },
        yAxis: {
            type: 'value',
            name: '人数',
            nameTextStyle: {
                fontSize: 12,
                fontWeight: 'bold'
            },
            axisLabel: {
                fontSize: 12
            },
            axisLine: {
                show: true
            },
            axisTick: {
                show: true
            },
            splitLine: {
                show: true,
                lineStyle: {
                    type: 'dashed'
                }
            }
        },
        series: series
    };
    
    // 使用traitTrendChart绘制16人格数量变化堆积柱状图
    traitTrendChart.setOption(trendOption);
    
    // 创建历史数据表格
    createTraitHistoryTable(traitHistoryData);
}

// 创建历史数据表格
function createTraitHistoryTable(historyData) {
    if (!historyData || historyData.length <= 1) return;
    
    let tableHTML = '<table>';
    
    // 表头
    tableHTML += '<thead><tr><th>日期</th>';
    
    // 添加所有维度列
    const allDimensions = ['EI', 'SN', 'TF', 'JP'];
    const allTraits = {
        'EI': ['E', 'I', 'X'],
        'SN': ['S', 'N', 'X'],
        'TF': ['T', 'F', 'X'],
        'JP': ['J', 'P', 'X']
    };
    
    allDimensions.forEach(dim => {
        allTraits[dim].forEach(trait => {
            tableHTML += `<th>${dim}-${trait}</th>`;
        });
    });
    
    tableHTML += '</tr></thead><tbody>';
    
    // 数据行
    historyData.forEach(record => {
        const d = new Date(record.timestamp);
        const dateStr = `${d.getMonth()+1}-${d.getDate()}`;
        tableHTML += `<tr><td>${dateStr}</td>`;
        
        // 为每个维度和特质添加数据
        allDimensions.forEach(dim => {
            const dimData = (record.trait_data || {})[dim] || {};
            allTraits[dim].forEach(trait => {
                const value = dimData[trait] || 0;
                tableHTML += `<td>${value}</td>`;
            });
        });
        
        tableHTML += '</tr>';
    });
    
    tableHTML += '</tbody></table>';
    traitTableContainer.innerHTML = tableHTML;
}
