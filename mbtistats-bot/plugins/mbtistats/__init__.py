import re
import json
from collections import Counter
from pathlib import Path
from typing import List, Dict, Optional

from nonebot import on_command, logger
from nonebot.adapters import Bot, Event
from nonebot.internal.matcher import Matcher
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

# --- 配置 ---
# 定义模板目录
TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "template"
# 定义 MBTI 正则 (忽略大小写)
MBTI_REGEX = re.compile(r"([eiEI][snSN][tfTF][jpJP])")

# --- 命令定义 ---
stats_cmd = on_command("类型统计", aliases={"mbti统计", "MBTI统计"}, priority=10, block=True)

@stats_cmd.handle()
async def handle_stats(bot: Bot, event: Event, matcher: Matcher):
    await matcher.send("正在统计中，请稍候... (首次运行可能需要启动浏览器内核)")

    # 1. 获取数据 (这里为了演示原型，如果无法获取真实数据则使用模拟数据)
    # 在实际生产中，这里需要调用 bot.get_group_member_list 等 API
    member_list = await get_group_members(bot, event)
    
    if not member_list:
        await matcher.send("⚠️ 未能获取到群成员列表或处于测试环境，将使用【演示数据】生成图表。")
        # 模拟一些数据
        mbti_counts = Counter({
            "INTP": 15, "INTJ": 8, "ENTP": 12, "ENTJ": 5,
            "INFP": 20, "INFJ": 10, "ENFP": 18, "ENFJ": 7,
            "ISTP": 6,  "ISTJ": 9, "ESTP": 4,  "ESTJ": 11,
            "ISFP": 5,  "ISFJ": 14, "ESFP": 8,  "ESFJ": 12
        })
        group_name = "演示测试群"
        total_count = 164
    else:
        # 2. 解析数据
        mbti_data = []
        for name in member_list:
            match = MBTI_REGEX.search(name)
            if match:
                mbti_data.append(match.group(1).upper())
        
        if not mbti_data:
            await matcher.finish("❌ 在群成员昵称中未发现任何有效的 MBTI 标识。")
            return

        mbti_counts = Counter(mbti_data)
        group_name = "当前群聊"
        total_count = len(mbti_data) # 样本数仅包含识别出 MBTI 的人

    # 3. 准备绘图数据
    # ECharts 需要的数据格式: [{'name': 'INTP', 'value': 10}, ...]
    chart_data = [{"name": k, "value": v} for k, v in mbti_counts.items()]
    # 按数量排序
    chart_data.sort(key=lambda x: x['value'], reverse=True)
    
    # 4. 渲染图片
    try:
        image_bytes = await render_chart(
            title="MBTI 类型分布统计",
            group_name=group_name,
            total_count=total_count,
            data=chart_data
        )
    except Exception as e:
        logger.exception("渲染图表失败")
        await matcher.finish(f"❌ 图表渲染失败: {e}")
        return

    # 5. 发送图片
    # 尝试使用 QQ Adapter 的消息段构造
    try:
        from nonebot.adapters.qq import MessageSegment
        await matcher.finish(MessageSegment.file_image(image_bytes))
    except ImportError:
        # 如果没有安装 QQ Adapter 或者在 Console 环境下
        await matcher.send("图片已生成 (当前环境无法直接发送图片消息)")
    except Exception as e:
         # 兜底
        logger.warning(f"发送图片失败，尝试降级发送: {e}")
        await matcher.finish("统计完成，但发送图片失败。")


async def get_group_members(bot: Bot, event: Event) -> List[str]:
    """
    尝试获取群成员列表。
    返回成员昵称/群名片列表。
    """
    # 这里留空，默认返回空列表以触发演示模式
    # 未来接入真实 API 时在此处实现
    return []


async def render_chart(title: str, group_name: str, total_count: int, data: List[Dict]) -> bytes:
    """
    使用 Playwright 渲染 HTML 模板并截图
    """
    # 1. 渲染 HTML
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("chart.html")
    html_content = template.render(
        title=title,
        group_name=group_name,
        total_count=total_count,
        data=data
    )

    # 2. 启动浏览器截图
    async with async_playwright() as p:
        # 启动 Chromium，注意：在 Docker 或服务器上可能需要 args=['--no-sandbox']
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(viewport={"width": 800, "height": 600}, device_scale_factor=2)
        page = await context.new_page()
        
        # 设置 HTML 内容
        await page.set_content(html_content)
        
        # 等待 ECharts 动画或渲染完成
        try:
            await page.wait_for_selector("canvas", timeout=5000)
            # 稍微多等一下确保动画结束
            await page.wait_for_timeout(1000) 
            
            # 截图 .container 元素
            screenshot = await page.locator(".container").screenshot(type="png")
        except Exception as e:
             logger.error(f"Playwright 等待超时或出错: {e}")
             raise e
        finally:            
            await page.screenshot(path="data/debug_chart.png")
            await browser.close()

        return screenshot

