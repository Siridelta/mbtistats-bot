"""
主动触发模式工具函数

这些函数用于在非事件响应场景下（如定时任务）主动调用 Bot API，
与事件响应模式（通过 Event 对象获取信息）相区分。
"""

import base64
from nonebot import logger
from nonebot.adapters import Bot


async def get_group_members_proactive(bot: Bot, group_id: str):
    """
    主动模式：获取群成员列表
    
    Args:
        bot: Bot 实例
        group_id: 群 ID
        
    Returns:
        群成员列表，失败返回空列表
    """
    try:
        adapter_name = bot.adapter.get_name()
        
        if adapter_name == "OneBot V11":
            # OneBot V11 协议
            members = await bot.get_group_member_list(group_id=int(group_id))
            return members
        elif adapter_name == "QQ":
            # QQ 官方 API 暂不支持获取群成员列表
            logger.warning("[Proactive] QQ 官方适配器暂不支持获取群成员列表")
            return []
        else:
            logger.warning(f"[Proactive] 未知适配器: {adapter_name}")
            return []
    except Exception as e:
        logger.error(f"[Proactive] 获取群成员失败: {e}")
        return []


async def get_group_name_proactive(bot: Bot, group_id: str) -> str:
    """
    主动模式：获取群名称
    
    Args:
        bot: Bot 实例
        group_id: 群 ID
        
    Returns:
        群名称，失败返回默认格式"群{group_id}"
    """
    try:
        adapter_name = bot.adapter.get_name()
        
        if adapter_name == "OneBot V11":
            group_info = await bot.get_group_info(group_id=int(group_id))
            return group_info.get("group_name", f"群{group_id}")
        else:
            return f"群{group_id}"
    except Exception as e:
        logger.warning(f"[Proactive] 获取群名称失败: {e}")
        return f"群{group_id}"


async def get_all_groups_proactive(bot: Bot) -> list[str]:
    """
    主动模式：获取 Bot 所在的所有群列表
    
    Args:
        bot: Bot 实例
        
    Returns:
        群 ID 列表
    """
    try:
        adapter_name = bot.adapter.get_name()
        
        if adapter_name == "OneBot V11":
            groups = await bot.get_group_list()
            return [str(g["group_id"]) for g in groups]
        else:
            logger.warning(f"[Proactive] 适配器 {adapter_name} 暂不支持获取群列表")
            return []
    except Exception as e:
        logger.error(f"[Proactive] 获取群列表失败: {e}")
        return []


async def send_image_to_group_proactive(bot: Bot, group_id: str, image_bytes: bytes):
    """
    主动模式：发送图片到指定群
    
    Args:
        bot: Bot 实例
        group_id: 群 ID
        image_bytes: 图片二进制数据
    """
    try:
        adapter_name = bot.adapter.get_name()
        
        if adapter_name == "OneBot V11":
            # 使用 CQ 码发送图片 (base64)
            base64_str = base64.b64encode(image_bytes).decode()
            message = f"[CQ:image,file=base64://{base64_str}]"
            await bot.send_group_msg(group_id=int(group_id), message=message)
        else:
            logger.warning(f"[Proactive] 适配器 {adapter_name} 暂不支持主动发送群消息")
    except Exception as e:
        logger.error(f"[Proactive] 发送图片到群 {group_id} 失败: {e}")
