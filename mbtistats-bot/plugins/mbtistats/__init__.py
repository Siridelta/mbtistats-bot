import json
from nonebot import on_command, logger
from nonebot.adapters import Bot, Event
from nonebot.internal.matcher import Matcher

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
type_stats_cmd = on_command("类型统计", aliases={"mbti"}, priority=10, block=True)
trait_stats_cmd = on_command("特质统计", aliases={"mbti-traits"}, priority=10, block=True)
help_cmd = on_command("帮助", aliases={"help"}, priority=10, block=True)

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
/类型统计 (或 /mbti)：统计当前群的 MBTI 类型分布，并生成统计图。
/特质统计 (或 /mbti-traits)：统计当前群的 MBTI 特质维度分布（E/I, S/N, T/F, J/P），并生成统计图。
/帮助 (或 /help)：显示这条帮助信息。
    """.strip())

@type_stats_cmd.handle()
async def handle_type_stats(bot: Bot, event: Event, matcher: Matcher):
    """
    处理 /类型统计 命令
    """
    await matcher.send("正在统计 MBTI 类型分布，请稍候...")

    # 1. 获取数据
    group_id = get_group_id(bot, event)
    member_list = await get_group_members(bot, event)

    isDebug = bot.adapter.get_name() == "Console"
    
    if not member_list:
        await matcher.send("❌ 未能获取到群成员列表。")
        return
    
    if isDebug:
        logger.info(f"mock data: member_list = {member_list}")
    
    chart_data, total_count = analyze_type_stats(member_list)
    if total_count == 0:
        await matcher.finish("❌ 在群成员昵称中未发现任何有效的 MBTI 标识。")
        return
    group_name = await get_group_name(group_id, bot)

    # 2. 渲染图片
    image_bytes = None

    img_cache_path = f"data/cache-charts/{group_id}/type-stats.png"
    data_cache_path = f"data/cache-charts/{group_id}/type-stats.json"
    
    data = {
        "title": "MBTI 类型分布统计",
        "group_name": group_name,
        "total_count": total_count,
        "data": chart_data
    }
    
    try:
        image_bytes = await render_chart(
            template_name="type-stats/index.html",
            data=data,
            width=1050,
            height=650,
            img_cache_path=img_cache_path,
            data_cache_path=data_cache_path,
            force_rerender=isDebug    # 如果调试模式，则强制重新缓存；否则优先复用缓存
        )
    except Exception as e:
        logger.exception("图表生成失败")
        await matcher.finish(f"❌ 图表生成失败: {e}")
        return
    
    # 3. 写入数据缓存
    with open(data_cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 4. 发送图片
    await send_image(bot, matcher, image_bytes)


@trait_stats_cmd.handle()
async def handle_trait_stats(bot: Bot, event: Event, matcher: Matcher):
    """
    处理 /特质统计 命令
    """
    await matcher.send("正在统计 MBTI 特质维度分布，请稍候...")

    # 1. 获取数据
    group_id = get_group_id(bot, event)
    member_list = await get_group_members(bot, event)

    isDebug = bot.adapter.get_name() == "Console"
    
    if not member_list:
        await matcher.send("❌ 未能获取到群成员列表。")
        return
    
    if isDebug:
        logger.info(f"mock data: member_list = {member_list}")
    
    chart_data, total_count = analyze_trait_stats(member_list)
    if total_count == 0:
        await matcher.finish("❌ 在群成员昵称中未发现任何有效的 MBTI 标识。")
        return
    group_name = await get_group_name(group_id, bot)

    # 2. 渲染图片
    image_bytes = None

    img_cache_path = f"data/cache-charts/{group_id}/trait-stats.png"
    data_cache_path = f"data/cache-charts/{group_id}/trait-stats.json"

    data = {
        "title": "MBTI 特质维度统计",
        "group_name": group_name,
        "total_count": total_count,
        "data": chart_data
    }
    
    try: 
        image_bytes = await render_chart(
            template_name="trait-stats/index.html",
            data=data,
            width=650,
            height=750,
            img_cache_path=img_cache_path,
            data_cache_path=data_cache_path,
            force_rerender=isDebug    # 如果调试模式，则强制重新缓存；否则优先复用缓存
        )
    except Exception as e:
        logger.exception("图表生成失败")
        await matcher.finish(f"❌ 图表生成失败: {e}")
        return

    # 3. 写入数据缓存
    with open(data_cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 4. 发送图片
    await send_image(bot, matcher, image_bytes)
