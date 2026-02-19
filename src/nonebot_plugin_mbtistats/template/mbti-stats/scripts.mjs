import * as echarts from 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.esm.min.js';

export function setupCharts(data) {
    const { typeRawData, traitRawData, typeHistoryData: typeHistoryDataRaw, traitHistoryData: traitHistoryDataRaw } = data;

    const date = new Date();
    document.getElementById("timestamp").textContent =
        `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${date.toLocaleTimeString()}`;

    // 数据预处理：
    // 1) 保留全量历史点（不按天去重）；
    // 2) 过滤无效记录并按时间升序。
    function normalizeHistoryData(data) {
        if (!Array.isArray(data)) return [];
        return data
            .filter(item => item && Number.isFinite(item.timestamp))
            .slice()
            .sort((a, b) => a.timestamp - b.timestamp);
    }

    // 使用“全量 + 时间排序”后的数据用于图表绘制
    const typeHistoryData = normalizeHistoryData(typeHistoryDataRaw);
    const traitHistoryData = normalizeHistoryData(traitHistoryDataRaw);

    // 类型统计图表
    const pieDom = document.getElementById("pie-chart-container");
    const pieChart = echarts.init(pieDom);
    const barDom = document.getElementById("bar-chart-container");
    const barChart = echarts.init(barDom);
    const trendWindowsDom = document.getElementById("trend-windows-container"); // 多尺度趋势图统一容器
    const trendWindowRefs = {
        week: {
            card: document.getElementById("trend-window-week"),
            type16Dom: document.getElementById("trend-week-type16"),
            type4Dom: document.getElementById("trend-week-type4"),
        },
        month: {
            card: document.getElementById("trend-window-month"),
            type16Dom: document.getElementById("trend-month-type16"),
            type4Dom: document.getElementById("trend-month-type4"),
        },
        year: {
            card: document.getElementById("trend-window-year"),
            type16Dom: document.getElementById("trend-year-type16"),
            type4Dom: document.getElementById("trend-year-type4"),
        },
        all: {
            card: document.getElementById("trend-window-all"),
            type16Dom: document.getElementById("trend-all-type16"),
            type4Dom: document.getElementById("trend-all-type4"),
        },
    };
    const tableContainer = document.getElementById("history-table-container"); // 类型统计历史数据表格

    // 特质统计图表
    const eiDom = document.getElementById("chart-ei");
    const eiChart = echarts.init(eiDom);
    const nsDom = document.getElementById("chart-ns");
    const nsChart = echarts.init(nsDom);
    const tfDom = document.getElementById("chart-tf");
    const tfChart = echarts.init(tfDom);
    const jpDom = document.getElementById("chart-jp");
    const jpChart = echarts.init(jpDom);
    const traitTableContainer = document.getElementById("trait-history-table-container"); // 特质统计历史数据表格

    // 1. 定义 MBTI 颜色映射配置表 (保证顺序: NT分析家 -> NF外交家 -> SJ守护者 -> SP探险家)
    // 使用数组形式以保留严格顺序
    const mbtiConfig = [
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

    // 生成颜色映射表以便快速查找
    // 形如：{"INTJ": "#b59bc4", "INTP": "#9b85c1", "ENTJ": "#715c9d", ...}
    const colorMap = mbtiConfig.reduce((acc, item) => {
        acc[item.type] = item.color;
        return acc;
    }, {});

    // 默认颜色，面向模糊类型
    const defaultColor = "#cccccc";



    // --- 动态获取人数最多的人格类型并显示图片和文字说明 ---

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
        img.onload = function () {
            imageContainer.innerHTML = '';
            imageContainer.appendChild(img);
        };

        // 图片加载失败处理，显示紫色占位图
        img.onerror = function () {
            imageContainer.innerHTML = '<div class="purple-placeholder"></div>';
        };
    }

    displayTopPersonality();


    // ==================== 类型统计部分 ====================

    // --- 实时类型统计图表 ---

    function initTypeChart(typeRawData) {

        // --- 类型统计饼图 ---

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
                    center: ['50%', '52%'],
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
                    // 去掉饼图数据中 value 为 0 的项；由于 pieData 也共享到后面，后面 barData 不能过滤，因此不能修改 pieData，只能在这里过滤。
                    data: pieData.filter(item => item.value > 0)
                }
            ]
        };

        // 设置图表选项
        if (pieOption && typeof pieOption === "object") {
            pieChart.setOption(pieOption);
        }


        // --- 类型统计柱状图 ---

        // 2. 数据处理：柱状图也需要数据
        // 柱状图通常按照数量排序，或者按照固定 MBTI 顺序排序
        // 这里我们按照 mbtiConfig 的固定顺序（分析家->外交家...）来排，方便对比
        const barData = pieData; // 直接复用已排序好的数据
        const categories = barData.map(item => item.name);

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
                left: '8%',
                right: '15%',
                top: '10%',
                bottom: '0%',
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

        if (barOption && typeof barOption === "object") {
            barChart.setOption(barOption);
        }
    }

    initTypeChart(typeRawData);


    // --- 多尺度历史趋势图（连续段识别 + 多维 LTTB） ---
    const DAY_MS = 24 * 3600 * 1000;
    // 双列布局下单图实际宽度约 450px，作为分辨率估算的默认值。
    // 后续会优先读取 DOM 实际宽度，避免布局变化后手工改参数。
    const TREND_CHART_WIDTH_PX = 450;
    const TREND_POINT_SIZE_PX = 6;
    const TREND_CONTINUITY_GAP_PX = TREND_POINT_SIZE_PX * 2; // 视觉上两个端点近似相邻时视为连续
    const TREND_SAMPLE_GAP_PX = 3; // 约半个点直径

    function nextPowerOfTwo(value) {
        let n = 1;
        while (n < value) n <<= 1;
        return n;
    }

    function startOfDay(timestamp) {
        const d = new Date(timestamp);
        d.setHours(0, 0, 0, 0);
        return d.getTime();
    }

    function startOfNextDay(timestamp) {
        return startOfDay(timestamp + DAY_MS);
    }

    function addDays(timestamp, days) {
        return timestamp + days * DAY_MS;
    }

    function addMonths(timestamp, months) {
        const d = new Date(timestamp);
        d.setMonth(d.getMonth() + months);
        return d.getTime();
    }

    function addYears(timestamp, years) {
        const d = new Date(timestamp);
        d.setFullYear(d.getFullYear() + years);
        return d.getTime();
    }

    // 判据：总跨度 < 2 个月 / 2 年 使用“日期意义上的前推后比较”
    function isSpanLessThanCalendarMonths(start, end, months) {
        return addMonths(start, months) > end;
    }

    function isSpanLessThanCalendarYears(start, end, years) {
        return addYears(start, years) > end;
    }

    function computeRenderResolutions(start, end, chartWidthPx = TREND_CHART_WIDTH_PX) {
        const span = Math.max(1, end - start);
        const safeChartWidthPx = Math.max(200, chartWidthPx);
        const msPerPixel = span / safeChartWidthPx;
        const continuityResolution = Math.max(1, Math.round(msPerPixel * TREND_CONTINUITY_GAP_PX));
        const rawSampleResolution = Math.max(1, Math.ceil(msPerPixel * TREND_SAMPLE_GAP_PX));
        const sampleResolution = nextPowerOfTwo(rawSampleResolution);
        return { continuityResolution, sampleResolution };
    }

    function buildTrendWindows(history) {
        if (!history || history.length < 2) return [];

        const minTs = history[0].timestamp;
        const maxTs = history[history.length - 1].timestamp;
        const totalSpan = maxTs - minTs;
        const now = Date.now();
        const end = startOfNextDay(now); // 终点：当前时刻明日 0 点

        const windows = [];
        const addWindow = (key, label, start, endTs) => {
            if (start < endTs) {
                windows.push({ key, label, start, end: endTs });
            }
        };

        // 规则 1：只有 1 个点时不展示（在调用方已提前处理）
        // 规则 2：总跨度 < 7 天 => 只展示全历史
        if (totalSpan < 7 * DAY_MS) {
            addWindow('all', '全历史记录图', minTs, maxTs);
            return windows;
        }

        // 规则 3/4/5：优先展示短窗口，再展示全历史
        const weekStart = startOfDay(addDays(end, -6)); // 一周前又一日后的日期 0 点
        addWindow('week', '一周趋势图', weekStart, end);

        if (!isSpanLessThanCalendarMonths(minTs, maxTs, 2)) {
            const monthStart = startOfDay(addDays(addMonths(end, -1), 1));
            addWindow('month', '一月趋势图', monthStart, end);
        }

        if (!isSpanLessThanCalendarYears(minTs, maxTs, 2)) {
            const yearStart = startOfDay(addDays(addYears(end, -1), 1));
            addWindow('year', '一年趋势图', yearStart, end);
        }

        addWindow('all', '全历史记录图', minTs, maxTs);
        return windows;
    }

    function triangleAreaScore(aTime, aVec, bTime, bVec, cTime, cVec) {
        const dim = Math.min(aVec.length, bVec.length, cVec.length);
        let score = 0;
        for (let i = 0; i < dim; i += 1) {
            const area = Math.abs(
                aTime * (bVec[i] - cVec[i]) +
                bTime * (cVec[i] - aVec[i]) +
                cTime * (aVec[i] - bVec[i])
            ) / 2;
            score += area;
        }
        return score;
    }

    function getBucketCenter(points, lttbReference) {
        if (!points || points.length === 0) return null;
        if (points.length === 1) {
            return { timestamp: points[0].timestamp, vector: lttbReference(points[0].data) };
        }

        let timestampSum = 0;
        const firstVector = lttbReference(points[0].data);
        const vectorSum = new Array(firstVector.length).fill(0);
        points.forEach(point => {
            timestampSum += point.timestamp;
            const vector = lttbReference(point.data);
            for (let i = 0; i < vectorSum.length; i += 1) {
                vectorSum[i] += (vector[i] ?? 0);
            }
        });

        return {
            timestamp: timestampSum / points.length,
            vector: vectorSum.map(value => value / points.length),
        };
    }

    function lttbSampleContinuousPoints(points, sampleResolution, lttbReference) {
        if (!points || points.length <= 2) return points ? points.slice() : [];

        const first = points[0];
        const last = points[points.length - 1];
        const middle = points.slice(1, -1);

        if (middle.length <= 1) return points.slice();

        // 按时间分桶（桶宽 sampleResolution），多余时间自然并入最后一桶
        const bucketCount = Math.max(1, Math.ceil((last.timestamp - first.timestamp) / sampleResolution));
        if (bucketCount >= middle.length) return points.slice();

        const buckets = Array.from({ length: bucketCount }, () => []);
        middle.forEach(point => {
            const offset = Math.max(0, point.timestamp - first.timestamp);
            const rawIndex = Math.floor(offset / sampleResolution);
            const bucketIndex = Math.max(0, Math.min(bucketCount - 1, rawIndex));
            buckets[bucketIndex].push(point);
        });

        const sampled = [first];
        let prevSelected = first;

        for (let i = 0; i < buckets.length; i += 1) {
            const currentBucket = buckets[i];
            if (currentBucket.length === 0) continue;

            let nextBucket = null;
            for (let j = i + 1; j < buckets.length; j += 1) {
                if (buckets[j].length > 0) {
                    nextBucket = buckets[j];
                    break;
                }
            }
            const nextCenter = nextBucket
                ? getBucketCenter(nextBucket, lttbReference)
                : { timestamp: last.timestamp, vector: lttbReference(last.data) };

            const prevVector = lttbReference(prevSelected.data);
            let bestPoint = currentBucket[0];
            let bestScore = -1;

            currentBucket.forEach(candidate => {
                const score = triangleAreaScore(
                    prevSelected.timestamp,
                    prevVector,
                    candidate.timestamp,
                    lttbReference(candidate.data),
                    nextCenter.timestamp,
                    nextCenter.vector,
                );
                if (score > bestScore) {
                    bestScore = score;
                    bestPoint = candidate;
                }
            });

            sampled.push(bestPoint);
            prevSelected = bestPoint;
        }

        sampled.push(last);
        return sampled.sort((a, b) => a.timestamp - b.timestamp);
    }

    // 关键函数：返回由离散点与连续段构成的混合渲染数据
    function getIntervalRenderData(
        dataPoints,
        start,
        end,
        sampleResolution,
        continuityResolution,
        lttbReference,
    ) {
        if (!Array.isArray(dataPoints) || dataPoints.length === 0) return [];

        const inRange = dataPoints.filter(point => point.timestamp >= start && point.timestamp <= end);
        if (inRange.length === 0) return [];

        let leftAnchor = null;
        let rightAnchor = null;
        for (let i = dataPoints.length - 1; i >= 0; i -= 1) {
            if (dataPoints[i].timestamp < start) {
                leftAnchor = dataPoints[i];
                break;
            }
        }
        for (let i = 0; i < dataPoints.length; i += 1) {
            if (dataPoints[i].timestamp > end) {
                rightAnchor = dataPoints[i];
                break;
            }
        }

        const workingData = [];
        if (leftAnchor) workingData.push(leftAnchor);
        workingData.push(...inRange);
        if (rightAnchor) workingData.push(rightAnchor);

        if (workingData.length <= 1) return workingData;

        // 先按 continuityResolution 切分段，再分别判断是“连续段”还是“离散点”
        const rawSegments = [];
        let current = [workingData[0]];
        for (let i = 1; i < workingData.length; i += 1) {
            const prev = workingData[i - 1];
            const now = workingData[i];
            if ((now.timestamp - prev.timestamp) <= continuityResolution) {
                current.push(now);
            } else {
                rawSegments.push(current);
                current = [now];
            }
        }
        rawSegments.push(current);

        const renderData = [];
        rawSegments.forEach(segment => {
            if (segment.length === 1) {
                renderData.push(segment[0]);
                return;
            }

            const sampled = lttbSampleContinuousPoints(segment, sampleResolution, lttbReference);
            renderData.push({
                type: 'continuous',
                start: sampled[0],
                end: sampled[sampled.length - 1],
                series: sampled.slice(1, -1),
            });
        });

        return renderData;
    }

    function dedupePoints(points) {
        const seen = new Set();
        const result = [];
        points.forEach(([timestamp, value]) => {
            const key = `${timestamp}|${value}`;
            if (seen.has(key)) return;
            seen.add(key);
            result.push([timestamp, value]);
        });
        return result;
    }

    // 把混合渲染数据拆成三层：连续段、非连续区、符号点
    // 非连续区策略（关键）：
    // - 非连续线要与连续段“首尾相接”，保证视觉上整条线不断裂；
    // - 但在连续段内部，非连续线必须断开（用 null），避免与深色连续段重复覆盖。
    //
    // 具体做法：
    // 1) 遇到离散点：直接加入 nonContinuousData；
    // 2) 遇到连续段：把 start/end 作为“连接锚点”加入 nonContinuousData，
    //    并在它们之间插入 null，表示“连续段内部交给 continuousData 绘制”。
    function buildLayeredSeriesData(renderData, valueGetter) {
        const continuousData = [];
        const nonContinuousData = [];
        const symbolPoints = [];

        renderData.forEach(item => {
            if (item && item.type === 'continuous') {
                const segmentPoints = [item.start, ...item.series, item.end];
                segmentPoints.forEach(point => {
                    const value = valueGetter(point.data);
                    continuousData.push([point.timestamp, value]);
                });
                continuousData.push([null, null]); // 用 null 断开连续段

                // 连续段只在端点画点
                symbolPoints.push([item.start.timestamp, valueGetter(item.start.data)]);
                symbolPoints.push([item.end.timestamp, valueGetter(item.end.data)]);

                // 把连续段端点并入“非连续线”的锚点：
                // previousNonContinuous -> start (浅线可见)
                // start -> end 之间断开（null）
                // end -> nextNonContinuous (浅线可见)
                nonContinuousData.push([item.start.timestamp, valueGetter(item.start.data)]);
                nonContinuousData.push([null, null]);
                nonContinuousData.push([item.end.timestamp, valueGetter(item.end.data)]);

                return;
            }

            if (item && Number.isFinite(item.timestamp)) {
                const value = valueGetter(item.data);
                nonContinuousData.push([item.timestamp, value]);
                symbolPoints.push([item.timestamp, value]);
            }
        });

        return {
            continuousData,
            nonContinuousData,
            symbolData: dedupePoints(symbolPoints),
        };
    }

    function initChartOnDom(dom) {
        const existing = echarts.getInstanceByDom(dom);
        if (existing) {
            existing.dispose();
        }
        return echarts.init(dom);
    }

    function buildTooltipFormatter() {
        return function formatter(params) {
            const validParams = params.filter(p => Array.isArray(p.value) && Number.isFinite(p.value[1]));
            if (validParams.length === 0) return '';

            const date = new Date(validParams[0].value[0]);
            let result = `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}<br/>`;

            // 多层 series 会重复同名，这里合并同名并取最大值（用于显示该时间点真实值）
            const valueMap = new Map();
            validParams.forEach(param => {
                const old = valueMap.get(param.seriesName);
                const now = param.value[1];
                if (!old || now > old.value) {
                    valueMap.set(param.seriesName, { color: param.color, value: now });
                }
            });

            const merged = Array.from(valueMap.entries())
                .map(([name, payload]) => ({ name, ...payload }))
                .sort((a, b) => b.value - a.value);

            merged.forEach(item => {
                if (item.value > 0) {
                    result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${item.color};"></span>`;
                    result += `${item.name}: ${item.value}人<br/>`;
                }
            });
            return result;
        };
    }

    // --- 多尺度趋势图：每个时间窗口下同时渲染 type16 与 type4 ---
    function initCombinedTrendCharts(typeHistoryData) {
        if (!typeHistoryData || typeHistoryData.length <= 1) {
            trendWindowsDom.style.display = 'none';
            return;
        }

        trendWindowsDom.style.display = 'block';
        Object.values(trendWindowRefs).forEach(ref => {
            if (!ref || !ref.card) return;
            ref.card.style.display = 'none';
            const type16Instance = echarts.getInstanceByDom(ref.type16Dom);
            if (type16Instance) type16Instance.clear();
            const type4Instance = echarts.getInstanceByDom(ref.type4Dom);
            if (type4Instance) type4Instance.clear();
        });

        const allPersonalities = mbtiConfig.map(item => item.type);
        const colorGroups = {
            "分析家": ["INTJ", "INTP", "ENTJ", "ENTP"],
            "外交家": ["INFJ", "INFP", "ENFJ", "ENFP"],
            "守护者": ["ISTJ", "ISFJ", "ESTJ", "ESFJ"],
            "探险家": ["ISTP", "ISFP", "ESTP", "ESFP"]
        };
        const groupColorMap = {
            "分析家": "#9b85c1",
            "外交家": "#70AD47",
            "守护者": "#5293D0",
            "探险家": "#FFB703",
        };
        const groupNames = Object.keys(colorGroups);
        const tooltipFormatter = buildTooltipFormatter();
        const windows = buildTrendWindows(typeHistoryData);

        let renderedWindowCount = 0;
        windows.forEach(windowDef => {
            const windowRef = trendWindowRefs[windowDef.key];
            if (!windowRef || !windowRef.card || !windowRef.type16Dom || !windowRef.type4Dom) {
                return;
            }

            // 使用当前窗口左图的实际宽度来估算两个分辨率，提升在不同布局下的稳定性
            const chartWidthPx = windowRef.type16Dom.clientWidth || TREND_CHART_WIDTH_PX;
            const { continuityResolution, sampleResolution } = computeRenderResolutions(
                windowDef.start,
                windowDef.end,
                chartWidthPx,
            );

            // renderData 的 point.data 是原始 payload（即 typeHistoryData[i].data 数组）
            const renderData = getIntervalRenderData(
                typeHistoryData,
                windowDef.start,
                windowDef.end,
                sampleResolution,
                continuityResolution,
                payload => allPersonalities.map(type => {
                    const found = payload.find(item => item.name === type);
                    return found ? found.value : 0;
                }),
            );

            // 当前窗口数据不足，不渲染该子卡片
            if (renderData.length <= 1) return;

            windowRef.card.style.display = 'block';
            renderedWindowCount += 1;

            const type16Chart = initChartOnDom(windowRef.type16Dom);
            const type4Chart = initChartOnDom(windowRef.type4Dom);

            // ---- type16 series ----
            const type16Series = [];
            allPersonalities.forEach((personality, index) => {
                const color = colorMap[personality] || defaultColor;
                // 原始值：用于真正的堆叠面积计算（每个人格只计一次）
                const getRawValue = (payload) => {
                    const found = payload.find(item => item.name === personality);
                    return found ? found.value : 0;
                };
                // 累计值：用于非堆叠的线/点层，定位到当前人格在堆叠后的“顶边”
                const getCumulativeValue = (payload) => {
                    let total = 0;
                    for (let i = 0; i <= index; i += 1) {
                        const type = allPersonalities[i];
                        const found = payload.find(item => item.name === type);
                        total += found ? found.value : 0;
                    }
                    return total;
                };

                const layeredArea = buildLayeredSeriesData(renderData, getRawValue);
                const layeredTopLine = buildLayeredSeriesData(renderData, getCumulativeValue);
                const baseZ = 1000 - index * 10;

                type16Series.push({
                    name: personality, type: 'line', stack: '总量-非连续', data: layeredArea.nonContinuousData,
                    showSymbol: false, smooth: false, clip: true, z: baseZ,
                    lineStyle: { width: 0, opacity: 0 }, areaStyle: { color, opacity: 0.5 },
                });
                type16Series.push({
                    name: personality, type: 'line', stack: '总量-连续', data: layeredArea.continuousData,
                    showSymbol: false, smooth: false, clip: true, z: baseZ + 1,
                    lineStyle: { width: 0, opacity: 0 }, areaStyle: { color, opacity: 0.8 },
                });
                type16Series.push({
                    name: personality, type: 'line', data: layeredTopLine.nonContinuousData,
                    showSymbol: false, smooth: false, clip: true, z: baseZ + 2,
                    lineStyle: { color: `${color}80`, width: 2 },
                });
                type16Series.push({
                    name: personality, type: 'line', data: layeredTopLine.continuousData,
                    showSymbol: false, smooth: false, clip: true, z: baseZ + 3,
                    lineStyle: { color, width: 3 },
                });
                type16Series.push({
                    name: personality, type: 'line', data: layeredTopLine.symbolData,
                    showSymbol: true, symbol: 'emptyCircle', symbolSize: TREND_POINT_SIZE_PX,
                    smooth: false, clip: true, z: baseZ + 4,
                    lineStyle: { width: 0, opacity: 0 }, itemStyle: { color },
                });
            });

            type16Chart.setOption({
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: tooltipFormatter },
                legend: {
                    type: 'scroll', bottom: 0, data: allPersonalities,
                    textStyle: { fontSize: 9 }, itemWidth: 10, itemHeight: 10,
                },
                grid: { left: '6%', right: '6%', bottom: '12%', top: '7%', containLabel: true },
                xAxis: {
                    type: 'time', min: windowDef.start, max: windowDef.end, boundaryGap: false,
                    axisLabel: { fontSize: 11, formatter: '{yy}.{MM}.{dd}', hideOverlap: true, showMaxLabel: true, showMinLabel: true },
                },
                yAxis: { type: 'value', name: '人数', axisLabel: { fontSize: 11 }, splitLine: { show: true, lineStyle: { type: 'dashed' } } },
                series: type16Series,
            });

            // ---- type4 series ----
            const type4Series = [];
            groupNames.forEach((groupName, index) => {
                const color = groupColorMap[groupName] || defaultColor;
                const types = colorGroups[groupName];
                const getGroupValue = (payload) => {
                    return types.reduce((sum, type) => {
                        const item = payload.find(d => d.name === type);
                        return sum + (item ? item.value : 0);
                    }, 0);
                };
                const layered = buildLayeredSeriesData(renderData, getGroupValue);
                const z = 200 - index * 10;

                type4Series.push({
                    name: groupName, type: 'line', data: layered.nonContinuousData,
                    showSymbol: false, smooth: false, clip: true, z, lineStyle: { color: `${color}80`, width: 2 },
                });
                type4Series.push({
                    name: groupName, type: 'line', data: layered.continuousData,
                    showSymbol: false, smooth: false, clip: true, z: z + 1, lineStyle: { color, width: 3 },
                });
                type4Series.push({
                    name: groupName, type: 'line', data: layered.symbolData,
                    showSymbol: true, symbol: 'emptyCircle', symbolSize: TREND_POINT_SIZE_PX,
                    smooth: false, clip: true, z: z + 2,
                    lineStyle: { width: 0, opacity: 0 }, itemStyle: { color },
                });
            });

            type4Chart.setOption({
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: tooltipFormatter },
                legend: {
                    type: 'scroll', bottom: 0, data: groupNames,
                    textStyle: { fontSize: 11 }, itemWidth: 12, itemHeight: 12,
                },
                grid: { left: '6%', right: '6%', bottom: '12%', top: '7%', containLabel: true },
                xAxis: {
                    type: 'time', min: windowDef.start, max: windowDef.end, boundaryGap: false,
                    axisLabel: { fontSize: 11, formatter: '{yy}.{MM}.{dd}', hideOverlap: true, showMaxLabel: true, showMinLabel: true },
                },
                yAxis: { type: 'value', name: '人数', axisLabel: { fontSize: 11 }, splitLine: { show: true, lineStyle: { type: 'dashed' } } },
                series: type4Series,
            });
        });

        if (renderedWindowCount === 0) {
            trendWindowsDom.style.display = 'none';
        }
    }

    initCombinedTrendCharts(typeHistoryData);


    // --- 类型统计历史数据表格 ---

    function createTypeHistoryTable(historyData) {
        if (!historyData || historyData.length === 0) return;

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
        historyData.toReversed().forEach(record => {
            const d = new Date(record.timestamp);
            const dateStr = `${d.getMonth() + 1}-${d.getDate()}`;
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

    createTypeHistoryTable(typeHistoryData);

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

    function initTraitChart(cfg, traitRawData) {
        let chart;
        switch (cfg.id) {
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

        const data1 = { count: traitRawData[cfg.rawKey][trait1] || 0 };
        const data2 = { count: traitRawData[cfg.rawKey][trait2] || 0 };
        const dataX = { count: traitRawData[cfg.rawKey][traitX] || 0 };

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

    traitConfig.forEach(cfg => {
        initTraitChart(cfg, traitRawData);
    });

    // 创建历史数据表格
    function createTraitHistoryTable(traitHistoryData) {
        if (!traitHistoryData || traitHistoryData.length === 0) return;

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
        traitHistoryData.toReversed().forEach(record => {
            const d = new Date(record.timestamp);
            const dateStr = `${d.getMonth() + 1}-${d.getDate()}`;
            tableHTML += `<tr><td>${dateStr}</td>`;

            // 为每个维度和特质添加数据
            allDimensions.forEach(dim => {
                const dimData = record.data[dim] || {};
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

    createTraitHistoryTable(traitHistoryData);

}