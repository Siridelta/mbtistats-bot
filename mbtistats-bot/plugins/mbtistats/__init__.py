import json
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
from .render import render_chart
from .get_group_data import get_group_members, get_group_id, get_group_name
from .send_image import send_image

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

    # 2. 渲染图片
    image_bytes = None

    img_cache_path = f"data/cache-charts/{group_id}/mbti-stats.png"
    data_cache_path = f"data/cache-charts/{group_id}/mbti-stats.json"
    type_history_data_path = f"data/history-charts/{group_id}/type-stats-history.json"
    trait_history_data_path = f"data/history-charts/{group_id}/trait-stats-history.json"
    
    # 加载历史数据
    type_history_data = []
    if Path(type_history_data_path).exists():
        try:
            with open(type_history_data_path, "r", encoding="utf-8") as f:
                type_history_data = json.load(f)
        except Exception as e:
            logger.warning(f"读取类型历史数据失败: {e}")
    
    trait_history_data = []
    if Path(trait_history_data_path).exists():
        try:
            with open(trait_history_data_path, "r", encoding="utf-8") as f:
                trait_history_data = json.load(f)
        except Exception as e:
            logger.warning(f"读取特质历史数据失败: {e}")
    
    data = {
        "title": "MBTI 类型与特质分布统计",
        "group_name": group_name,
        "total_count": type_total_count,
        "type_data": type_chart_data,
        "trait_data": trait_chart_data,
        "type_history_data": type_history_data,
        "trait_history_data": trait_history_data
    }
    
    try:
        image_bytes = await render_chart(
            template_name="mbti-stats/index.html",
            data=data,
            width=1050,
            height=2500,  # 增加高度以容纳所有内容
            img_cache_path=img_cache_path,
            data_cache_path=data_cache_path,
            force_rerender=isDebug    # 如果调试模式，则强制重新缓存；否则优先复用缓存
        )
    except Exception as e:
        logger.exception("图表生成失败")
        await matcher.finish(f"❌ 图表生成失败: {e}")
        return
    
    # 3. 写入数据缓存和历史数据
    with open(data_cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # 保存类型历史数据
    try:
        # 确保目录存在
        Path(type_history_data_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 添加当前数据到历史记录
        current_record = {
            "timestamp": datetime.now().isoformat(),
            "data": type_chart_data,
            "total_count": type_total_count
        }
        
        # 保留最多50条历史记录
        type_history_data.append(current_record)
        if len(type_history_data) > 50:
            type_history_data = type_history_data[-50:]
        
        with open(type_history_data_path, "w", encoding="utf-8") as f:
            json.dump(type_history_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.warning(f"保存类型历史数据失败: {e}")
    
    # 保存特质历史数据
    try:
        # 确保目录存在
        Path(trait_history_data_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 添加当前数据到历史记录
        current_record = {
            "timestamp": datetime.now().isoformat(),
            "data": trait_chart_data,
            "total_count": trait_total_count
        }
        
        # 保留最多50条历史记录
        trait_history_data.append(current_record)
        if len(trait_history_data) > 50:
            trait_history_data = trait_history_data[-50:]
        
        with open(trait_history_data_path, "w", encoding="utf-8") as f:
            json.dump(trait_history_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.warning(f"保存特质历史数据失败: {e}")

    # 4. 发送图片
    await send_image(bot, matcher, image_bytes)
