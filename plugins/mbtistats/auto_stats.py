"""
自动统计功能

定时自动统计群成员 MBTI 分布并发送结果到群里。
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from nonebot import logger, require, get_driver
from nonebot.adapters import Bot

# 导入定时任务调度器
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

# 导入主动模式工具函数
from .proactive import (
    get_group_members_proactive,
    get_group_name_proactive,
    get_all_groups_proactive,
    send_image_to_group_proactive,
)

# 导入分析和渲染模块
from .analyze import analyze_type_stats, analyze_trait_stats
from .render import render_chart, use_cache, write_cache


# ========== 配置 ==========
# 配置项在 .env 文件中设置：
# auto_stats_debug=true           # 启用调试模式（不发送图片，只保存到文件）
# auto_stats_run_on_startup=true  # 启动时立即执行一次统计

driver = get_driver()

# 全局配置变量
DEBUG_MODE: bool = getattr(driver.config, "auto_stats_debug", False)
RUN_ON_STARTUP: bool = getattr(driver.config, "auto_stats_run_on_startup", False)

logger.info(f"[AutoStats] 模块加载完成 - DEBUG_MODE={DEBUG_MODE}, RUN_ON_STARTUP={RUN_ON_STARTUP}")


def get_disabled_groups() -> set[str]:
    """
    获取禁用了自动统计的群列表（黑名单模式）
    
    策略：
    1. 默认所有群都启用自动统计
    2. 检查 data/v1/auto_stats_disabled.txt 文件
    3. 文件中的群 ID 将被禁用自动统计
    
    Returns:
        禁用的群 ID 集合
    """
    config_path = Path("data/v1/auto_stats_disabled.txt")

    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()
        return set()
    
    try:
        content = config_path.read_text(encoding="utf-8")
        groups = {line.strip() for line in content.split("\n") if line.strip()}
        return groups
    except Exception as e:
        logger.error(f"[AutoStats] 读取禁用配置失败: {e}")
        return set()


async def perform_auto_stats(bot, group_id: str, debug_mode: bool = False):
    """
    执行自动统计
    
    Args:
        bot: Bot 实例
        group_id: 群 ID
        debug_mode: 调试模式，为 True 时不发送图片，只保存到文件
    """
    try:
        # 1. 获取群成员列表
        member_info_list = await get_group_members_proactive(bot, group_id)
        
        if not member_info_list:
            logger.warning(f"[AutoStats] 群 {group_id} 获取成员列表失败或为空")
            return
        
        member_names = [
            (
                member["card"] if "card" in member and not member["card"] == ''
                else member["nickname"] if "nickname" in member and not member["nickname"] == ''
                else ''
            ) for member in member_info_list
        ]
        
        # 2. 分析数据
        type_chart_data, type_total_count = analyze_type_stats(member_names)
        if type_total_count == 0:
            logger.info(f"[AutoStats] 群 {group_id} 未发现有效 MBTI 标识")
            return
        
        trait_chart_data, trait_total_count = analyze_trait_stats(member_names)
        
        # 3. 获取群名称
        group_name = await get_group_name_proactive(bot, group_id)
        
        # 4. 更新历史数据
        data_cache_path = f"data/v1/cache-charts/{group_id}/mbti-stats.json"
        img_cache_path = f"data/v1/cache-charts/{group_id}/mbti-stats.png"
        
        history_data = []
        if Path(data_cache_path).exists():
            try:
                with open(data_cache_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        history_data = content
            except Exception as e:
                logger.warning(f"[AutoStats] 读取历史数据失败: {e}")
        
        import time
        current_record = {
            "timestamp": int(time.time() * 1000),
            "group_name": group_name,
            "total_count": type_total_count,
            "type_data": type_chart_data,
            "trait_data": trait_chart_data
        }
        
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
            
            Path(data_cache_path).parent.mkdir(parents=True, exist_ok=True)
            with open(data_cache_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[AutoStats] 群 {group_id} 数据已更新，共 {type_total_count} 人参与统计")
        else:
            logger.debug(f"[AutoStats] 群 {group_id} 数据无变化，跳过记录")
        
        # 5. 准备渲染数据（使用与主动触发相同的逻辑）
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
            {"timestamp": record["timestamp"], "data": record["type_data"]}
            for record in compressed_history_data
        ]
        trait_history_data = [
            {"timestamp": record["timestamp"], "data": record["trait_data"]}
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
        
        # 6. 渲染图片
        image_bytes = None
        if data_updated:
            image_bytes = await render_chart(
                template_mode="mbti-stats",
                data=data,
                width=1050,
                height=2500,
            )
            await write_cache(img_cache_path, image_bytes)
        else:
            _image_bytes = await use_cache(img_cache_path)
            if _image_bytes is None:
                _image_bytes = await render_chart(
                    template_mode="mbti-stats",
                    data=data,
                    width=1050,
                    height=2500,
                )
                await write_cache(img_cache_path, _image_bytes)
            image_bytes = _image_bytes
        
        # 7. 发送图片到群里（调试模式下跳过）
        if debug_mode:
            logger.info(f"[AutoStats] [调试模式] 群 {group_id} 统计图已保存到 {img_cache_path}，跳过发送")
        else:
            await send_image_to_group_proactive(bot, group_id, image_bytes)
            logger.info(f"[AutoStats] 群 {group_id} 统计图已发送")
            
    except Exception as e:
        logger.exception(f"[AutoStats] 群 {group_id} 执行失败: {e}")


@scheduler.scheduled_job("cron", hour="0", minute="0", id="auto_mbti_stats")
async def auto_stats_job():
    """
    定时任务：每小时执行一次自动统计
    
    可以通过修改 hour 参数调整频率：
    - "*/1": 每小时
    - "*/2": 每 2 小时
    - "0,12": 每天 0 点和 12 点
    - "0": 每天 0 点
    """
    logger.info("[AutoStats] 定时任务开始执行")
    
    # 获取所有 Bot 实例
    bots = get_bots()
    
    if not bots:
        logger.warning("[AutoStats] 没有可用的 Bot 实例")
        return
    
    # 对于每个 Bot，执行统计任务
    for bot in bots.values():
        
        # 获取所有群和禁用列表
        all_groups = await get_all_groups_proactive(bot)
        disabled_groups = get_disabled_groups()
        
        # 过滤掉禁用的群
        enabled_groups = [g for g in all_groups if g not in disabled_groups]
        
        if not enabled_groups:
            logger.debug(f"[AutoStats] Bot {bot.self_id} 没有启用的群，跳过")
            continue
        
        logger.info(f"[AutoStats] Bot {bot.self_id} 发现 {len(enabled_groups)} 个启用的群（已排除 {len(disabled_groups)} 个禁用群）")
        
        for group_id in enabled_groups:
            await perform_auto_stats(bot, group_id, debug_mode=DEBUG_MODE)
        
        logger.info(f"[AutoStats] Bot {bot.self_id} 定时任务完成，处理了 {len(enabled_groups)} 个群")


# 记录上次执行时间，避免启动时重复执行
last_startup_execution_time = None

@driver.on_bot_connect
async def auto_stats_on_startup(bot: Bot):
    """Bot 连接成功后检查是否需要立即执行统计（调试用）"""
    if not RUN_ON_STARTUP:
        logger.debug("[AutoStats] 启动时执行已禁用（设置 auto_stats_run_on_startup=true 启用）")
        return
    
    logger.info(f"[AutoStats] 启动时立即执行统计... (DEBUG_MODE={DEBUG_MODE})")
    
    # 等待一小段时间确保连接稳定
    await asyncio.sleep(2)
    
    # 获取所有群和禁用列表
    all_groups = await get_all_groups_proactive(bot)
    disabled_groups = get_disabled_groups()
    
    # 过滤掉禁用的群
    enabled_groups = [g for g in all_groups if g not in disabled_groups]
    
    if not enabled_groups:
        logger.error("[AutoStats] 启动执行：没有启用的群")
        return
    
    logger.info(f"[AutoStats] 启动执行：发现 {len(enabled_groups)} 个启用的群: {enabled_groups}")

    global last_startup_execution_time
    if not last_startup_execution_time is None:
        if (datetime.now() - last_startup_execution_time).total_seconds() < 30:
            logger.info("[AutoStats] 启动时执行已在 30 秒内执行过，跳过")
            return
    else:
        last_startup_execution_time = datetime.now()
    
    for group_id in enabled_groups:
        await perform_auto_stats(bot, group_id, debug_mode=DEBUG_MODE)
    
    logger.info("[AutoStats] 启动执行完成")


# 延迟导入避免循环依赖
from nonebot import get_bots