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
from .get_group_data import get_group_members
# --- 命令定义 ---
type_stats_cmd = on_command("类型统计", priority=10, block=True)
trait_stats_cmd = on_command("特质统计", priority=10, block=True)

@type_stats_cmd.handle()
async def handle_type_stats(bot: Bot, event: Event, matcher: Matcher):
    """
    处理 /类型统计 命令
    """
    await matcher.send("正在统计 MBTI 类型分布，请稍候... (首次运行可能需要启动浏览器内核)")

    isDebug = None

    # 1. 获取数据
    member_list = await get_group_members(bot, event)
    
    if not member_list:
        await matcher.send("⚠️ 未能获取到群成员列表或处于测试环境，将使用【演示数据】生成图表。")
        chart_data, total_count = get_mock_data()
        group_name = "演示测试群"
        isDebug = True
    else:
        chart_data, total_count = analyze_type_stats(member_list)
        if total_count == 0:
            await matcher.finish("❌ 在群成员昵称中未发现任何有效的 MBTI 标识。")
            return
        group_name = "当前群聊"
        isDebug = False

    # 2. 渲染图片
    image_bytes = None
    img_cache_path = ""
    data_cache_path = ""

    if isDebug:
        img_cache_path = "data/debug-charts/type-stats.png"
        data_cache_path = "data/debug-charts/type-stats.json"
    else:
        img_cache_path = f"data/cache-charts/{event.group_id}/type-stats.png"
        data_cache_path = f"data/cache-charts/{event.group_id}/type-stats.json"
    
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

    isDebug = None

    # 1. 获取数据
    member_list = await get_group_members(bot, event)
    
    if not member_list:
        await matcher.send("⚠️ 未能获取到群成员列表或处于测试环境，将使用【演示数据】生成图表。")
        trait_data, total_count = get_mock_trait_data()
        group_name = "演示测试群"
        isDebug = True
    else:
        trait_data, total_count = analyze_trait_stats(member_list)
        if total_count == 0:
            await matcher.finish("❌ 在群成员昵称中未发现任何有效的 MBTI 标识。")
            return
        group_name = "当前群聊"
        isDebug = False

    # 2. 渲染图片
    try:
        cache_path = ""
        if isDebug:
            cache_path = "data/debug-charts/trait-stats.png"
        else:
            cache_path = f"data/cache-charts/{event.group_id}/trait-stats.png"
        
        image_bytes = await render_chart(
            template_name="trait-stats/index.html",
            data={
                "title": "MBTI 特质维度统计",
                "group_name": group_name,
                "total_count": total_count,
                "data": trait_data
            },
            width=650,
            height=750,
            img_cache_path=cache_path,
            force_rerender=isDebug    # 如果调试模式，则强制重新缓存；否则优先复用缓存
        )
    except Exception as e:
        logger.exception("渲染图表失败")
        await matcher.finish(f"❌ 图表渲染失败: {e}")
        return

    # 3. 发送图片
    await send_image(matcher, image_bytes)


async def send_image(matcher: Matcher, image_bytes: bytes):
    """
    通用图片发送逻辑，处理不同 Adapter 的兼容性
    """
    try:
        # 尝试使用 QQ Adapter 的 MessageSegment
        from nonebot.adapters.qq import MessageSegment
        await matcher.finish(MessageSegment.file_image(image_bytes))
    except ImportError:
        # 尝试使用 OneBot V11 Adapter 的 MessageSegment (如果有)
        try:
            from nonebot.adapters.onebot.v11 import MessageSegment
            await matcher.finish(MessageSegment.image(image_bytes))
        except ImportError:
             pass
             
    except Exception as e:
        # 兜底
        logger.warning(f"发送图片失败，尝试降级发送: {e}")
        await matcher.finish("统计完成，但发送图片失败。")
    
    # 如果以上都失败（例如 Console Adapter）
    await matcher.send("图片已生成 (当前环境无法直接发送图片消息)")
