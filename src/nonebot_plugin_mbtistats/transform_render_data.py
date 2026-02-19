"""
数据转换模块：将 MBTI 统计数据转换为前端渲染数据。

本模块负责将后端存储的时间序列数据（stats-data.json 格式）
转换为前端渲染所需的格式（mock.json 格式）。
"""

from typing import Dict, Any, List, Optional


def transform_to_render_data(
    history_data: List[Dict[str, Any]],
    title: str = "MBTI 类型与特质分布统计",
    group_name: Optional[str] = None,
    total_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    将 MBTI 统计数据转换为前端渲染数据。

    转换逻辑：
    - 接收后端存储格式的全量历史数据（无清洗）
    - 提取最新的统计数据作为当前数据
    - 将历史数据转换为前端所需的时间序列格式

    Args:
        history_data: 后端存储格式的历史数据列表（stats-data.json 格式）
        title: 统计标题
        group_name: 群名称（可选，默认使用最新记录的群名）
        total_count: 总人数（可选，默认使用最新记录的人数）

    Returns:
        前端渲染数据（mock.json 格式）

    Raises:
        ValueError: 当 history_data 为空列表时
    """
    if not history_data:
        raise ValueError("历史数据不能为空")

    # 获取最新记录作为当前统计数据
    latest_record = history_data[-1]

    # 使用传入参数或从最新记录提取
    group_name = group_name or latest_record.get("group_name", "未知群名称")
    total_count = total_count or latest_record.get("total_count", 0)

    # 转换历史数据为前端格式
    type_history_data = [
        {"timestamp": record["timestamp"], "data": record["type_data"]}
        for record in history_data
    ]

    trait_history_data = [
        {"timestamp": record["timestamp"], "data": record["trait_data"]}
        for record in history_data
    ]

    render_data = {
        "title": title,
        "group_name": group_name,
        "total_count": total_count,
        "type_data": latest_record["type_data"],
        "trait_data": latest_record["trait_data"],
        "type_history_data": type_history_data,
        "trait_history_data": trait_history_data,
    }

    return render_data


def load_and_transform(
    stats_data_path: str,
    title: str = "MBTI 类型与特质分布统计",
) -> Optional[Dict[str, Any]]:
    """
    从文件加载 MBTI 统计数据并转换为渲染数据。

    Args:
        stats_data_path: stats-data.json 文件路径
        title: 统计标题

    Returns:
        前端渲染数据，加载失败时返回 None
    """
    import json
    from pathlib import Path

    path = Path(stats_data_path)
    if not path.exists():
        print(f"[TransformRenderData] 数据文件不存在: {stats_data_path}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            history_data = json.load(f)

        if not isinstance(history_data, list):
            print(f"[TransformRenderData] 数据格式错误: 期望列表，实际为 {type(history_data)}")
            return None

        return transform_to_render_data(history_data, title=title)

    except json.JSONDecodeError as e:
        print(f"[TransformRenderData] JSON 解析失败: {e}")
        return None
    except Exception as e:
        print(f"[TransformRenderData] 数据转换失败: {e}")
        return None
