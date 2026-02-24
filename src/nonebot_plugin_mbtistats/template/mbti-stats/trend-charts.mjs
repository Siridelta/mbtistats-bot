import { MbtistatsDashboard } from './dashboard-class.mjs';

const DAY_MS = 24 * 3600 * 1000;
// estimated reference dimensions
const TREND_CHART_WIDTH_PX = 450;
const TREND_POINT_SIZE_PX = 6;
// resolutions depend on them
const TREND_CONTINUITY_GAP_PX = TREND_POINT_SIZE_PX * 2;
const TREND_SAMPLE_GAP_PX = 3;

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
    const end = startOfNextDay(Date.now());

    const windows = [];
    const addWindow = (key, label, start, endTs) => {
        if (start < endTs) windows.push({ key, label, start, end: endTs });
    };

    if (totalSpan < 7 * DAY_MS) {
        addWindow('all', '全历史记录图', minTs, maxTs);
        return windows;
    }

    const weekStart = startOfDay(addDays(end, -6));
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

function getIntervalRenderData(dataPoints, start, end, sampleResolution, continuityResolution, lttbReference) {
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
            continuousData.push([null, null]);

            symbolPoints.push([item.start.timestamp, valueGetter(item.start.data)]);
            symbolPoints.push([item.end.timestamp, valueGetter(item.end.data)]);

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

function initChartOnDom(echarts, dom) {
    const existing = echarts.getInstanceByDom(dom);
    if (existing) existing.dispose();
    return echarts.init(dom);
}

function buildTooltipFormatter() {
    return function formatter(params) {
        const validParams = params.filter(p => Array.isArray(p.value) && Number.isFinite(p.value[1]));
        if (validParams.length === 0) return '';

        const date = new Date(validParams[0].value[0]);
        let result = `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}<br/>`;

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

MbtistatsDashboard.prototype.renderTrendCharts = function() {
    if (!this.typeHistoryData || this.typeHistoryData.length <= 1) {
        this.trendWindowsDom.style.display = 'none';
        return;
    }

    this.trendWindowsDom.style.display = 'block';
    Object.values(this.trendWindowRefs).forEach(ref => {
        if (!ref || !ref.card) return;
        ref.card.style.display = 'none';
        const type16Instance = this.echarts.getInstanceByDom(ref.type16Dom);
        if (type16Instance) type16Instance.clear();
        const type4Instance = this.echarts.getInstanceByDom(ref.type4Dom);
        if (type4Instance) type4Instance.clear();
    });

    const allPersonalities = this.mbtiConfig.map(item => item.type);
    const colorGroups = {
        "分析家": ["INTJ", "INTP", "ENTJ", "ENTP"],
        "外交家": ["INFJ", "INFP", "ENFJ", "ENFP"],
        "守护者": ["ISTJ", "ISFJ", "ESTJ", "ESFJ"],
        "探险家": ["ISTP", "ISFP", "ESTP", "ESFP"],
    };
    const groupColorMap = {
        "分析家": "#9b85c1",
        "外交家": "#70AD47",
        "守护者": "#5293D0",
        "探险家": "#FFB703",
    };
    const groupNames = Object.keys(colorGroups);
    const tooltipFormatter = buildTooltipFormatter();
    const windows = buildTrendWindows(this.typeHistoryData);

    let renderedWindowCount = 0;
    windows.forEach(windowDef => {
        const windowRef = this.trendWindowRefs[windowDef.key];
        if (!windowRef || !windowRef.card || !windowRef.type16Dom || !windowRef.type4Dom) return;

        const chartWidthPx = windowRef.type16Dom.clientWidth || TREND_CHART_WIDTH_PX;
        const { continuityResolution, sampleResolution } = computeRenderResolutions(
            windowDef.start,
            windowDef.end,
            chartWidthPx,
        );

        const renderData = getIntervalRenderData(
            this.typeHistoryData,
            windowDef.start,
            windowDef.end,
            sampleResolution,
            continuityResolution,
            payload => allPersonalities.map(type => {
                const found = payload.find(item => item.name === type);
                return found ? found.value : 0;
            }),
        );
        if (renderData.length <= 1) return;

        windowRef.card.style.display = 'block';
        renderedWindowCount += 1;

        const type16Chart = initChartOnDom(this.echarts, windowRef.type16Dom);
        const type4Chart = initChartOnDom(this.echarts, windowRef.type4Dom);

        const type16Series = [];
        allPersonalities.forEach((personality, index) => {
            const color = this.colorMap[personality] || this.defaultColor;
            const getRawValue = (payload) => {
                const found = payload.find(item => item.name === personality);
                return found ? found.value : 0;
            };
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
                color,
                showSymbol: false, smooth: false, clip: true, z: baseZ,
                lineStyle: { color, width: 0, opacity: 0 }, areaStyle: { color, opacity: 0.5 },
            });
            type16Series.push({
                name: personality, type: 'line', stack: '总量-连续', data: layeredArea.continuousData,
                color,
                showSymbol: false, smooth: false, clip: true, z: baseZ + 1,
                lineStyle: { color, width: 0, opacity: 0 }, areaStyle: { color, opacity: 0.8 },
            });
            type16Series.push({
                name: personality, type: 'line', data: layeredTopLine.nonContinuousData,
                color,
                showSymbol: false, smooth: false, clip: true, z: baseZ + 2,
                lineStyle: { color: `${color}80`, width: 2 },
            });
            type16Series.push({
                name: personality, type: 'line', data: layeredTopLine.continuousData,
                color,
                showSymbol: false, smooth: false, clip: true, z: baseZ + 3,
                lineStyle: { color, width: 3 },
            });
            type16Series.push({
                name: personality, type: 'line', data: layeredTopLine.symbolData,
                color,
                showSymbol: true, symbol: 'emptyCircle', symbolSize: TREND_POINT_SIZE_PX,
                smooth: false, clip: true, z: baseZ + 4,
                lineStyle: { width: 0, opacity: 0 }, itemStyle: { color },
            });
        });

        // 双列布局下单图宽度较窄，16 个图例横向一行放不下。
        // 将图例拆成 2 行（每行 8 个，按大类分组），避免出现 1/2 分页。
        const type16LegendRows = [
            [
                "INTP", "ENTP", "INTJ", "ENTJ",  // 分析家
                "INFP", "ENFP", "INFJ", "ENFJ", // 外交家
            ],
            [
                "ISTJ", "ESTJ", "ISFJ", "ESFJ", // 守护者
                "ISTP", "ESTP", "ISFP", "ESFP", // 探险家
            ],
        ];
        const type16Legend = type16LegendRows.map((row, rowIndex) => ({
            type: 'plain',
            orient: 'horizontal',
            // 两行使用相同左边界，避免“各行单独居中”导致列错位
            left: '11%',
            // 逐行向上偏移，形成稳定 2 行布局
            bottom: rowIndex * 20,
            selectedMode: true,
            itemWidth: 10,
            itemHeight: 10,
            itemGap: 4,
            // 通过固定宽度的 rich 文本单元格，让每个图例项在“格子”内左对齐
            formatter: (name) => `{legendCell|${name}}`,
            textStyle: {
                rich: {
                    legendCell: {
                        width: 32,
                        align: 'left',
                        lineHeight: 10,
                        padding: [0, 0, 0, 0],
                        fontSize: 10,
                    },
                },
            },
            data: row,
        }));

        type16Chart.setOption({
            // 显式指定 legend 的调色盘，避免同名多层 series 时回落到默认彩虹色
            color: allPersonalities.map(type => this.colorMap[type] || this.defaultColor),
            tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: tooltipFormatter },
            legend: type16Legend,
            grid: { left: '6%', right: '6%', bottom: '12%', top: '7%', containLabel: true },
            xAxis: {
                type: 'time', min: windowDef.start, max: windowDef.end, boundaryGap: false,
                axisLabel: { fontSize: 11, formatter: '{yy}.{MM}.{dd}', hideOverlap: true, showMaxLabel: true, showMinLabel: true },
            },
            yAxis: { type: 'value', name: '人数', axisLabel: { fontSize: 11 }, splitLine: { show: true, lineStyle: { type: 'dashed' } } },
            series: type16Series,
        });

        const type4Series = [];
        groupNames.forEach((groupName, index) => {
            const color = groupColorMap[groupName] || this.defaultColor;
            const types = colorGroups[groupName];
            const getGroupValue = (payload) => types.reduce((sum, type) => {
                const item = payload.find(d => d.name === type);
                return sum + (item ? item.value : 0);
            }, 0);
            const layered = buildLayeredSeriesData(renderData, getGroupValue);
            const z = 200 - index * 10;

            type4Series.push({
                name: groupName, type: 'line', data: layered.nonContinuousData,
                color,
                showSymbol: false, smooth: false, clip: true, z, lineStyle: { color: `${color}80`, width: 2 },
            });
            type4Series.push({
                name: groupName, type: 'line', data: layered.continuousData,
                color,
                showSymbol: false, smooth: false, clip: true, z: z + 1, lineStyle: { color, width: 3 },
            });
            type4Series.push({
                name: groupName, type: 'line', data: layered.symbolData,
                color,
                showSymbol: true, symbol: 'emptyCircle', symbolSize: TREND_POINT_SIZE_PX,
                smooth: false, clip: true, z: z + 2,
                lineStyle: { width: 0, opacity: 0 }, itemStyle: { color },
            });
        });

        type4Chart.setOption({
            // 显式指定图例色，保证与四色曲线颜色一致
            color: groupNames.map(groupName => groupColorMap[groupName] || this.defaultColor),
            tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: tooltipFormatter },
            legend: { type: 'scroll', bottom: 0, data: groupNames, textStyle: { fontSize: 11 }, itemWidth: 12, itemHeight: 12 },
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
        this.trendWindowsDom.style.display = 'none';
    }
};