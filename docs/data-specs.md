# 数据格式

> 当前约定 / 使用的数据格式。由于本项目为多语言，多技术开发，关键数据格式无法在代码里直观体现，故使用此文档来描述记录。

## 1. MBTI 统计数据 ( mbti stats data ) / 时间点数据 ( mbti stats data point )

这个数据是能构成时间序列/历史记录的结构化数据。mbti-stats 时间点数据里除去 timestamp 等字段外，其等价性是机器人判断时间点数据是否发生变化的依据，如果 mbti 统计数据没有变化则使用缓存图片而不渲染新图。

`data/v1/cache-charts/{{ group_id }}/mbti-stats.json` 里存储时间序列数据。

时间点数据示例：
```js
{
    "timestamp": 1766297997000,
    "group_name": "未知群名称",
    "total_count": 213,
    "type_data": [
        {"name": "ESTP", "value": 20},
        {"name": "INTP", "value": 16},
        {"name": "ENFJ", "value": 13},
        ...,
        {"name": "模糊类型", "value": 13}
    ],
    "trait_data": {
        "EI": {
            "E": 104,
            "I": 107,
            "X": 2
        },
        "SN": {
            "S": 109,
            "N": 103,
            "X": 1
        },
        "TF": {
            "T": 108,
            "F": 99,
            "X": 6
        },
        "JP": {
            "J": 103,
            "P": 106,
            "X": 4
        }
    }
}
```

时间序列数据（`mbti-stats.json` 里存储的数据）示例：
```js
[
    timestamp_data_1,
    timestamp_data_2,
    ...
]
```

## 2. 渲染数据 ( render data )

这是输入给前端的渲染数据。不同指令的渲染数据不同（虽然现阶段设计里只用一个指令），但都是由 mbti 统计数据转换而来，需要注意与 mbti 统计数据区分。

### 2.1. 新版合一指令 mbti-stats (/mbti)

新版合一指令 mbti-stats (/mbti) 的渲染数据示例：

```js
{
    "title": "MBTI 类型与特质分布统计", // 标题
    "group_name": "未知群名称",         // 群名
    "total_count": 213,               // 总人数

    // --- 当前统计数据 (直接取自最新的统计结果) ---
    "type_data": [                    // 类型分布数据 (List[Dict]), 格式依据 mbti stats 数据: mbtiStats[i].type_data
        {"name": "ESTP", "value": 20},
        {"name": "INTP", "value": 16},
        ...
    ],
    "trait_data": {                   // 特质分布数据 (Dict), 格式依据 mbti stats 数据: mbtiStats[i].trait_data
        "EI": {"E": 104, "I": 107, "X": 2},
        "SN": {"S": 109, "N": 103, "X": 1},
        ...
    },

    // --- 历史趋势数据 ---
    // 变换到渲染数据时，同一天的数据压缩，只取当天最后一条数据
    "type_history_data": [
        {
            "timestamp": 1766297997000,
            "data": [                        // 类型分布历史趋势数据 (List[Dict]), 格式依据 mbti stats 数据: mbtiStats[i].type_data
                {"name": "ESTP", "value": 20},
                {"name": "INTP", "value": 16},
                ...
            ],
            ...
        },
        ...
    ],
    "trait_history_data": [
        {
            "timestamp": 1766297997000,
            "data": {                       // 特质分布历史趋势数据 (Dict), 格式依据 mbti stats 数据: mbtiStats[i].trait_data
                "EI": {"E": 104, "I": 107, "X": 2},
                "SN": {"S": 109, "N": 103, "X": 1},
                ...
            },
            ...
        },
        ...
    ]
}
```

旧版指令暂时省略。
