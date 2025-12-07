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
from .get_group_data import get_group_members, get_group_id
from .send_image import send_image

# --- 命令定义 ---
type_stats_cmd = on_command("类型统计", priority=10, block=True)
trait_stats_cmd = on_command("特质统计", priority=10, block=True)

@type_stats_cmd.handle()
async def handle_type_stats(bot: Bot, event: Event, matcher: Matcher):
    """
    处理 /类型统计 命令
    """
    await matcher.send("正在统计 MBTI 类型分布，请稍候... (首次运行可能需要启动浏览器内核)")

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
    group_name = "未知群名称"

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
    await send_image(matcher, image_bytes)


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
    group_name = "未知群名称"

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
        logger.exception("渲染图表失败")
        await matcher.finish(f"❌ 图表渲染失败: {e}")
        return

    # 3. 写入数据缓存
    with open(data_cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 4. 发送图片
    await send_image(matcher, image_bytes)
