from nonebot.internal.matcher import Matcher
from nonebot import logger

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