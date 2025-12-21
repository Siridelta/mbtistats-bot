import json
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from nonebot import logger

# 模板根目录: mbtistats-bot/template
TEMPLATE_ROOT = \
    Path(__file__).parent.parent.parent.parent \
    / "template"

async def use_cache(
    img_cache_path: str,
) -> Optional[bytes]:
    """
    使用缓存图片。
    如果缓存不存在则返回 None。
    """
    if not Path(img_cache_path).exists():
        return None
    with open(img_cache_path, "rb") as f:
        img_cache = f.read()
    return img_cache

async def write_cache(
    img_cache_path: str,
    img_cache: bytes,
) -> None:
    """
    写入缓存图片。
    """
    try:
        Path(img_cache_path).parent.mkdir(parents=True, exist_ok=True)
        with open(img_cache_path, "wb") as f:
            f.write(img_cache)
    except Exception as e:
        logger.error(f"写入缓存图片失败: {e}")

async def render_chart(
    template_name: str, 
    data: Dict[str, Any], 
    width: int = 1080, 
    height: int = 1080,
) -> bytes:
    """
    使用 Playwright 渲染 HTML 模板并截图。
    
    Args:
        template_name: 模板相对路径，例如 "type-stats/index.html"
        data: 传递给 Jinja2 模板的上下文数据
        width: 视口宽度
        height: 视口高度
    Returns:
        bytes: 图片的二进制数据
    """

    # 1. 准备模板环境
    # 我们将 TEMPLATE_ROOT 设为 searchpath，这样 template_name 可以是相对路径
    if not TEMPLATE_ROOT.exists():
        logger.error(f"模板目录不存在: {TEMPLATE_ROOT}")
        raise FileNotFoundError(f"Template directory not found: {TEMPLATE_ROOT}")

    env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT))
    try:
        template = env.get_template(template_name)
    except Exception as e:
        logger.error(f"加载模板失败 {template_name}: {e}")
        raise e

    # 2. 渲染 HTML 内容
    html_content = template.render(**data)

    # 3. 启动浏览器截图
    async with async_playwright() as p:
        try:
            # 启动 Chromium
            # 注意：在 Docker 或服务器上可能需要 args=['--no-sandbox']
            # 这里默认加上，以防万一
            browser = await p.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # 创建上下文，设置视口和设备缩放比（提高清晰度）
            context = await browser.new_context(
                viewport={"width": width, "height": height}, 
                device_scale_factor=2
            )
            page = await context.new_page()

            # --- 监听控制台日志和页面错误 ---
            page.on("console", lambda msg: logger.info(f"[Browser Console] {msg.text}"))
            page.on("pageerror", lambda exc: logger.error(f"[Browser Error] {exc}"))
            # -------------------------------
            
            # 设置 HTML 内容
            await page.set_content(html_content)
            
            # 等待渲染
            # 等待 ECharts 的 canvas 出现
            try:
                await page.wait_for_selector("canvas", timeout=10000)
                # 额外等待一点时间确保动画完成
                await page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"等待 Canvas 超时，尝试直接截图: {e}")

            # 截图
            # 优先截取 .container，如果没找到则截全屏
            if await page.locator(".container").count() > 0:
                screenshot = await page.locator(".container").screenshot(type="png")
            else:
                screenshot = await page.screenshot(type="png", full_page=True)
                
            await browser.close()
            return screenshot
            
        except Exception as e:
            logger.error(f"Playwright 渲染出错: {e}")
            raise e

