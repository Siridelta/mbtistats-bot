import json
import time
from pathlib import Path
from nonebot import on_command, logger
from nonebot.rule import to_me
from nonebot.adapters import Bot, Event
from nonebot.internal.matcher import Matcher
from datetime import datetime

# 导入拆分后的模块
from .analyze import (
    analyze_type_stats, 
    analyze_trait_stats, 
    get_mock_data, 
    get_mock_trait_data
)
from .render import render_chart, use_cache, write_cache
from .get_group_data import get_group_members, get_group_id, get_group_name
from .send_image import send_image

# 导入自动统计模块（会自动注册定时任务）
from . import auto_stats

# --- 命令定义 ---
mbti_stats_cmd = on_command("mbti", aliases={"MBTI"}, priority=10, block=True)
help_cmd = on_command("帮助", aliases={"help"}, rule=to_me(), priority=10, block=True)

@help_cmd.handle()
async def handle_help(bot: Bot, event: Event, matcher: Matcher):
    """
    处理 /帮助 命令
    """
    await matcher.send("""
欢迎使用 MBTI 计数菌！
本 bot 可自动统计当前群的 MBTI 类型分布，并生成统计图。
需要群友在群名片或 QQ 昵称中主动声明/标注自己的 MBTI 类型哦~
支持各种标注类型：MBTI（全大写/全小写），模糊类型（用X/x代替其中的若干字母，如"INXP"，"exxp"），各种扩展型（识别其中的普通 MBTI 代码），OPS 类型（识别其中的优势功能部分代码，如"Te/Se"）。
支持生成 MBTI 类型分布图、以及 MBTI 特质维度分布图。

使用帮助：
/mbti：统计当前群的 MBTI 类型分布和特质维度分布，并生成统计图。
/帮助 (或 /help)：显示这条帮助信息。
    """.strip())

@mbti_stats_cmd.handle()
async def handle_mbti_stats(bot: Bot, event: Event, matcher: Matcher):
    """
    处理 /mbti 命令，合并类型统计和特质统计
    """
    await matcher.send("正在统计 MBTI 类型分布和特质维度分布，请稍候...")

    # 1. 获取数据
    group_id = get_group_id(bot, event)
    member_list = await get_group_members(bot, event)

    isDebug = bot.adapter.get_name() == "Console"
    
    if not member_list:
        await matcher.send("❌ 未能获取到群成员列表。")
        return
    
    if isDebug:
        logger.info(f"mock data: member_list = {member_list}")
    
    # 类型统计数据
    type_chart_data, type_total_count = analyze_type_stats(member_list)
    if type_total_count == 0:
        await matcher.finish("❌ 在群成员昵称中未发现任何有效的 MBTI 标识。")
        return
    
    # 特质统计数据
    trait_chart_data, trait_total_count = analyze_trait_stats(member_list)
    
    group_name = await get_group_name(group_id, bot)

    # 2. 判断与更新历史数据
    image_bytes = None

    img_cache_path = f"data/v1/cache-charts/{group_id}/mbti-stats.png"
    # 统一使用 mbti-stats.json 作为历史记录和数据源
    data_cache_path = f"data/v1/cache-charts/{group_id}/mbti-stats.json"
    
    # 加载历史数据 (现在是 List 结构)
    history_data = []
    if Path(data_cache_path).exists():
        try:
            with open(data_cache_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list):
                    history_data = content
                else:
                    # 兼容旧格式或空文件，初始化为空列表
                    history_data = []
        except Exception as e:
            logger.warning(f"读取历史数据失败: {e}")
            history_data = []
    
    # 构造当前数据记录
    current_record = {
        "timestamp": int(time.time() * 1000),
        "group_name": group_name,
        "total_count": type_total_count,
        "type_data": type_chart_data,
        "trait_data": trait_chart_data
    }
    
    # 对比最后一条历史数据，决定是否追加
    # 为了避免重复记录（比如短时间内重复触发），判断数据是否完全一致，timestamp 字段除外
    # 对比最后一条数据，避免重复记录
    data_updated = False
    if history_data:
        last_record = history_data[-1]
        if datetime.fromtimestamp(last_record["timestamp"] / 1000).date() != datetime.fromtimestamp(current_record["timestamp"] / 1000).date():
            data_updated = True
        else:
            last_compare = {k: v for k, v in last_record.items() if k != "timestamp"}
            current_compare = {k: v for k, v in current_record.items() if k != "timestamp"}
            if last_compare != current_compare:
                data_updated = True
    else:
        data_updated = True
    
    if data_updated:
        history_data.append(current_record)
        try:
            # 确保目录存在
            Path(data_cache_path).parent.mkdir(parents=True, exist_ok=True)
            with open(data_cache_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"写入数据缓存失败: {e}")
            await matcher.finish(f"❌ 写入数据缓存失败: {e}")
            return

    # 3. 准备渲染数据
    # 注意：history_data 包含了所有历史，包括刚刚可能追加的当前数据
    # 每天的最后一个时间戳
    last_t_per_day = {}
    def get_day_key(t): return datetime.fromtimestamp(t / 1000).strftime("%Y-%m-%d")
    for record in history_data:
        day_key = get_day_key(record["timestamp"])
        if day_key not in last_t_per_day or last_t_per_day[day_key] < record["timestamp"]:
            last_t_per_day[day_key] = record["timestamp"]
    
    compressed_history_data = [ 
        record for record in history_data 
        if record["timestamp"] == last_t_per_day[get_day_key(record["timestamp"])]
    ]

    type_history_data = [
        {
            "timestamp": record["timestamp"],
            "data": record["type_data"]
        }
        for record in compressed_history_data
    ]
    trait_history_data = [
        {
            "timestamp": record["timestamp"],
            "data": record["trait_data"]
        }
        for record in compressed_history_data
    ]
    data = {
        "title": "MBTI 类型与特质分布统计",
        "group_name": group_name,
        "total_count": type_total_count,
        "type_data": type_chart_data,
        "trait_data": trait_chart_data,
        "type_history_data": type_history_data,
        "trait_history_data": trait_history_data
    }
    
    # 4. 渲染图片
    try:
        if data_updated:
            image_bytes = await render_chart(
                template_mode="mbti-stats",
                data=data,
                width=1050,
                height=2500,  # 增加高度以容纳所有内容
            )
            await write_cache(img_cache_path, image_bytes)
        else:
            _image_bytes = await use_cache(img_cache_path)
            if _image_bytes is None:
                _image_bytes = await render_chart(
                    template_mode="mbti-stats",
                    data=data,
                    width=1050,
                    height=2500,  # 增加高度以容纳所有内容
                )
                await write_cache(img_cache_path, _image_bytes)
            image_bytes = _image_bytes
    except Exception as e:
        logger.exception("图表生成失败")
        await matcher.finish(f"❌ 图表生成失败: {e}")
        return


    # 5. 发送图片
    await send_image(bot, matcher, image_bytes)
