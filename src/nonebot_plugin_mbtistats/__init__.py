import json
import time
from pathlib import Path
from nonebot import on_command, logger, require
from nonebot.rule import to_me
from nonebot.adapters import Bot, Event
from nonebot.internal.matcher import Matcher
from datetime import datetime

# 确保依赖的 scheduler 插件已加载
require("nonebot_plugin_apscheduler")

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
from .config import (
    get_group_data_path,
    get_chart_cache_path,
    get_latest_chart_cache,
    plugin_config
)
from .transform_render_data import transform_to_render_data
from nonebot.plugin import PluginMetadata

# 导入自动统计模块（会自动注册定时任务）
from . import auto_stats

__plugin_meta__ = PluginMetadata(
    name="mbtistats",
    description="MBTI 群聊统计插件 - 自动识别群名片中的 MBTI 类型并生成统计图表",
    usage="""本插件可自动统计当前群的 MBTI 类型分布，并生成精美统计图。

需要群友在群名片或 QQ 昵称中主动标注自己的 MBTI 类型才能被统计到。

支持的类型格式：
  • 标准型：INTP、enfp（全大写/全小写）
  • 模糊型：INXP、exxp（用 X/x 代替不确定字母）
  • 扩展型：INTP-T、INTP(5w4)（识别其中的 MBTI 代码）
  • OPS 型：Te/Se、Ni/Fe（识别优势功能代码）

生成图表：
  • MBTI 类型分布饼图
  • 特质维度（E/I, S/N, T/F, J/P）柱状图
  • 历史趋势折线图（需有历史数据）

指令：
  /mbti 或 /MBTI - 生成统计图表
  
注意：
  • 仅支持 OneBot V11 协议（QQ 群聊）
  • 自动统计功能需机器人运行者配置定时任务""",
    type="application",
)

# --- 命令定义 ---
mbti_stats_cmd = on_command("mbti", aliases={"MBTI"}, priority=10, block=True)

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

    # 获取数据文件路径（JSON 存档）
    data_cache_path = get_group_data_path(group_id)
    
    # 加载历史数据 (现在是 List 结构)
    history_data = []
    if data_cache_path.exists():
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
    # 如果数据不一致则追加；如果数据一致，冷却时间为 60 秒
    data_updated = False
    if history_data:
        last_record = history_data[-1]
        last_compare = {k: v for k, v in last_record.items() if k != "timestamp"}
        current_compare = {k: v for k, v in current_record.items() if k != "timestamp"}
        if last_compare != current_compare:
            if current_record["timestamp"] - last_record["timestamp"] < 60 * 1000:
                logger.info("数据与上次完全一致且冷却时间未到，不追加记录")
                data_updated = False
            else:
                data_updated = True
    else:
        data_updated = True
    
    if data_updated:
        history_data.append(current_record)
        try:
            with open(data_cache_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"写入数据缓存失败: {e}")
            await matcher.finish(f"❌ 写入数据缓存失败: {e}")
            return

    # 3. 准备渲染数据
    # 注意：history_data 包含了所有历史，包括刚刚可能追加的当前数据
    data = transform_to_render_data(
        history_data=history_data,
        title="MBTI 类型与特质分布统计",
        group_name=group_name,
        total_count=type_total_count,
    )
    
    # 4. 渲染图片
    # 生成图表缓存路径（带当前时间戳）
    current_timestamp = int(time.time() * 1000)
    img_cache_path = get_chart_cache_path(group_id, current_timestamp)
    
    try:
        if data_updated:
            # 数据有更新，渲染新图片
            image_bytes = await render_chart(
                template_mode="mbti-stats",
                data=data,
                width=plugin_config.mbtistats_viewport_width,
                height=plugin_config.mbtistats_viewport_height,
            )
            await write_cache(img_cache_path, image_bytes)
        else:
            # 数据无更新，尝试使用最新缓存
            latest_cache = get_latest_chart_cache(group_id)
            if latest_cache:
                _image_bytes = await use_cache(latest_cache)
            else:
                _image_bytes = None
                
            if _image_bytes is None:
                # 没有缓存，重新渲染
                _image_bytes = await render_chart(
                    template_mode="mbti-stats",
                    data=data,
                    width=plugin_config.mbtistats_viewport_width,
                    height=plugin_config.mbtistats_viewport_height,
                )
                await write_cache(img_cache_path, _image_bytes)
            image_bytes = _image_bytes
    except Exception as e:
        logger.exception("图表生成失败")
        await matcher.finish(f"❌ 图表生成失败: {e}")
        return


    # 5. 发送图片
    await send_image(bot, matcher, image_bytes)
