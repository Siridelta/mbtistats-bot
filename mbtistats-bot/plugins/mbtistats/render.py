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

async def render_chart(
    template_name: str, 
    data: Dict[str, Any], 
    width: int = 1080, 
    height: int = 1080,
    img_cache_path: Optional[str] = None,
    data_cache_path: Optional[str] = None,
    force_rerender: bool = False,
) -> bytes:
    """
    使用 Playwright 渲染 HTML 模板并截图。
    
    Args:
        template_name: 模板相对路径，例如 "type-stats/index.html"
        data: 传递给 Jinja2 模板的上下文数据
        width: 视口宽度
        height: 视口高度
        img_cache_path: 缓存路径，例如 "data/cache-charts/123456789/type-stats.png"，如果为 None，则不缓存
        data_cache_path: 数据缓存路径，例如 "data/cache-charts/123456789/type-stats.json"，如果为 None，则不缓存
        force_rerender: 是否强制重新缓存，如果为 True，则不使用缓存，并在 img_cache_path 参数存在时重新写入缓存；否则优先复用缓存
    Returns:
        bytes: 图片的二进制数据
    """
    
    # 0. 缓存检查与复用
    # 读取统计数据缓存，和 data 比对，如果相同则直接返回图像缓存。
    if not force_rerender:
        # 读取数据缓存
        data_cache = None
        if data_cache_path and Path(data_cache_path).exists():
            try:
                with open(data_cache_path, "r", encoding="utf-8") as f:
                    data_cache = json.load(f)
            except Exception as e:
                logger.error(f"读取数据缓存失败: {e}")
        # 读取图像缓存
        img_cache = None
        if img_cache_path and Path(img_cache_path).exists():
            try:
                with open(img_cache_path, "rb") as f:
                    img_cache = f.read()
            except Exception as e:
                logger.error(f"读取图像缓存失败: {e}")
        # 如果数据缓存和图像缓存都存在，并且数据相同，则直接返回图像缓存
        if data_cache and img_cache and data_cache == data:
            logger.info(f"使用缓存: {img_cache_path}")
            return img_cache

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
                screenshot = await page.locator(".container").screenshot(type="png", path=img_cache_path)
            else:
                screenshot = await page.screenshot(type="png", full_page=True, path=img_cache_path)
                
            await browser.close()
            return screenshot
            
        except Exception as e:
            logger.error(f"Playwright 渲染出错: {e}")
            raise e

