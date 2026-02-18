import random
from typing import List, cast, Literal
from nonebot.adapters import Bot, Event
from nonebot import logger
from nonebot.adapters.qq.bot import (
    Bot as QQBot, 
)
from nonebot.adapters.qq.event import (
    Event as QQEvent,
    EventType as QQEventType,
    GroupMsgReceiveEvent as QQGroupMsgReceiveEvent,
)
from nonebot.adapters.onebot.v11.bot import (
    Bot as OneBotV11Bot,
)
from nonebot.adapters.onebot.v11.event import (
    Event as OneBotV11Event,
    MessageEvent as OneBotV11MessageEvent,
    GroupMessageEvent as OneBotV11GroupMessageEvent,
)

def get_group_id(bot: Bot, event: Event) -> str:
    """
    获取群 ID。
    """
    adapter_name = bot.adapter.get_name()

    # --- 1. QQ 官方机器人环境 ---
    if adapter_name == "QQ":
        event = cast(QQEvent, event)
        if event.__type__ == QQEventType.GROUP_MSG_RECEIVE:
            event = cast(QQGroupMsgReceiveEvent, event)
            return event.group_openid
        else:
            return None
    
    # --- 2. OneBot V11 环境 ---
    if adapter_name == "OneBot V11":
        event = cast(OneBotV11Event, event)

        if event.get_type() != "message":
            return None
        event = cast(OneBotV11MessageEvent, event)
        
        if event.message_type != "group":
            return None
        event = cast(OneBotV11GroupMessageEvent, event)

        return str(event.group_id)
        
    # --- 3. Console 环境模拟 (开发调试用) ---
    if adapter_name == "Console":
        return "Console_Group"

    return None

async def get_group_name(id: str, bot: Bot) -> str:
    """
    获取群名称。
    """
    adapter_name = bot.adapter.get_name()

    # --- 1. QQ 官方机器人环境 ---
    if adapter_name == "QQ":
        return "未知群名称"

    # --- 2. OneBot V11 环境 ---
    if adapter_name == "OneBot V11":
        bot = cast(OneBotV11Bot, bot)
        info = await bot.get_group_info(group_id=int(id), no_cache=True)
        return info['group_name']

    return "未知群名称"

async def get_group_members(bot: Bot, event: Event) -> List[str]:
    """
    获取群成员列表（昵称列表）。
    """
    adapter_name = bot.adapter.get_name()
    
    # --- 1. Console 环境模拟 (开发调试用) ---
    if adapter_name == "Console":
        logger.info("🔧 [Dev] 检测到 Console 环境，正在生成模拟群成员数据...")
        # 模拟 300 个群友，让统计结果看起来丰富一点
        return generate_mock_members(count=300)

    # --- 2. QQ 官方机器人环境 ---
    if adapter_name == "QQ":
        bot = cast(QQBot, bot)
        # TODO: ⚠️ 严重警告 ⚠️
        # QQ 官方 Bot API 的 post_group_members 接口目前仅返回 member_openid，
        # 通常不包含 nick/card (群名片) 字段。
        # 如果官方不更新 API，无法通过此方法获取群成员昵称进行统计。
        try:
            # 这里的实现仅为占位，实际上 result.members 里可能没有 nick
            logger.warning("⚠️ QQ 官方 Bot API 目前可能不支持直接拉取群成员昵称，无法进行统计。")

            group_id = get_group_id(bot, event)
            result = await bot.post_group_members(group_id=group_id, limit=400)
            return [m.nick for m in result.members if hasattr(m, 'nick')]
        except Exception as e:
            logger.error(f"获取QQ群成员失败: {e}")
            return []

    # --- 3. OneBot V11 环境 ---
    if adapter_name == "OneBot V11":
        bot = cast(OneBotV11Bot, bot)
        event = cast(OneBotV11Event, event)
        group_id = get_group_id(bot, event)
        try:
            # OneBot V11 获取群成员列表的标准 API
            # no_cache=True 强制拉取最新数据
            member_list = await bot.get_group_member_list(group_id=int(group_id), no_cache=True)
            
            # 优先使用群名片(card)，如果没有则使用昵称(nickname)
            return [m['card'] or m['nickname'] for m in member_list]
        except Exception as e:
            logger.error(f"OneBot 获取群成员失败: {e}")
            raise e

    return []

# ------
# mocks
# ------

def generate_mock_members(count: int = 200) -> List[str]:
    """
    生成模拟的群成员昵称列表，包含各种 MBTI 标注格式
    """
    
    def generate_mbti_type() -> str:
        mbti_type = ""
        
        x_p = 0.02
        non_x_p = (1 - x_p) / 2
        mbti_type += random.choices(["I", "E", "X"], k=1, weights=[non_x_p, non_x_p, x_p])[0]
        mbti_type += random.choices(["S", "N", "X"], k=1, weights=[non_x_p, non_x_p, x_p])[0]
        mbti_type += random.choices(["T", "F", "X"], k=1, weights=[non_x_p, non_x_p, x_p])[0]
        mbti_type += random.choices(["J", "P", "X"], k=1, weights=[non_x_p, non_x_p, x_p])[0]

        mbti_type = random.choice([mbti_type, mbti_type.lower()])
        return mbti_type
    
    def generate_ops_label() -> str:
        # Function Pair
        decider_functions = ["Ti", "Te", "Fi", "Fe"]
        observer_functions = ["Ni", "Ne", "Si", "Se"]
        decider = random.choice(decider_functions)
        observer = random.choice(observer_functions)
        function_pair = ""
        if random.random() < 0.5:
            function_pair = decider + "/" + observer
        else:
            function_pair = observer + "/" + decider
        
        # Sexual Variations
        sexual_vars = ["MM", "FF", "MF", "FM"]
        sexual_var = random.choice(sexual_vars)
        
        # Animal Stack
        animals = ["C", "B", "S", "P"]
        animal_dual = {
            "C": "B",
            "B": "C",
            "S": "P",
            "P": "S",
        }
        a1 = random.choice(animals)
        a2 = random.choice([a for a in animals if a != a1 and a != animal_dual[a1]])
        a_rests = [a for a in animals if a != a1 and a != a2]
        a3 = random.choice(a_rests)
        a4 = [a for a in animals if a != a1 and a != a2 and a != a3][0]
        is_simp = random.random() < 0.5
        animal_stack = ""
        if is_simp:
            animal_stack = a1 + a2 + a3 + a4
        else:
            animal_stack = a1 + a2 + '/' + a3 + '(' + a4 + ')'
        
        # OPS Label
        add_sexual_var = random.random() < 0.5
        add_animal_stack = random.random() < 0.5
        ops_label = ""
        if add_sexual_var:
            ops_label += sexual_var + '-'
        ops_label += function_pair
        if add_animal_stack:
            ops_label += '-' + animal_stack
        return ops_label
    
    # 模拟各种昵称格式
    templates = [
        "{name} | {mbti}",       # 标准格式
        "{mbti} - {name}",       # 前缀格式
        "[{mbti}] {name}",       # 括号前缀
        "{name}（{mbti}）",      # 中文括号后缀
        "{name}",                # 无标注
        "User_{i}",              # 无标注纯英文
        "{name} (测试{mbti})",   # 干扰项
        "{name} {mbti} 5w4",     # 混合九型
        "{name} {ops_label}",     # OPS 类型
        "{name}",                # 大量路人
    ]
    
    names = ["小明", "张三", "李四", "Alice", "Bob", "Kanna", "Momo", "Official", "管理员", "请输入文本"]
    
    mock_data = []
    for i in range(count):
        name = random.choice(names) + str(i)
        template = random.choice(templates)

        args = {
            "name": name,
            "i": i,
            "mbti": generate_mbti_type(),
            "ops_label": generate_ops_label(),
        }
        nick = template.format(**args)
        mock_data.append(nick)
        
    logger.debug(f"已生成 {len(mock_data)} 条模拟数据")
    return mock_data