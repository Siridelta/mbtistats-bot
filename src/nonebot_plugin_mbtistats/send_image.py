from nonebot.internal.matcher import Matcher
from nonebot.exception import FinishedException
from nonebot import logger
from nonebot.adapters import Bot
from nonebot.adapters.qq import MessageSegment as QQMessageSegment
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment

async def send_image(bot: Bot, matcher: Matcher, image_bytes: bytes):
    """
    通用图片发送逻辑，处理不同 Adapter 的兼容性
    """
    try:
        if bot.adapter.get_name() == "QQ":
            await matcher.finish(QQMessageSegment.file_image(image_bytes))
        elif bot.adapter.get_name() == "OneBot V11":
            await matcher.finish(OneBotV11MessageSegment.image(image_bytes))
        else:
            raise Exception(f"不支持的 Adapter: {bot.adapter.get_name()}")
    except FinishedException:
        pass
    except Exception as e:
        # 兜底
        logger.warning(f"发送图片失败，尝试降级发送: {e}")
        await matcher.finish("统计完成，但发送图片失败。")