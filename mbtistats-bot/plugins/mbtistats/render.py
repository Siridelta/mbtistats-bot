import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
# 移除旧的 async_playwright 导入，导入新的管理器
from .playwright_context import PlaywrightContext
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
    template_mode: str, 
    data: Dict[str, Any], 
    width: int = 1080, 
    height: int = 1080,
) -> bytes:
    """
    使用 Playwright 渲染 HTML 模板并截图。
    
    Args:
        template_mode: 模板目录名（位于 template/ 下），例如 "mbti-stats"
                       必须包含 index.html
        data: 传递给 Jinja2 模板的上下文数据
        width: 视口宽度
        height: 视口高度
    Returns:
        bytes: 图片的二进制数据
    """

    # 1. 准备模板环境
    # 我们将 TEMPLATE_ROOT 设为 searchpath
    if not TEMPLATE_ROOT.exists():
        logger.error(f"模板目录不存在: {TEMPLATE_ROOT}")
        raise FileNotFoundError(f"Template directory not found: {TEMPLATE_ROOT}")

    env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT))
    
    # 约定：index.html 位于 template_mode 目录下
    template_path = f"{template_mode}/index.html"
    
    try:
        template = env.get_template(template_path)
    except Exception as e:
        logger.error(f"加载模板失败 {template_path}: {e}")
        raise e

    # 2. 渲染 HTML 内容
    html_content = template.render(**data)

    # --- 修改：写入临时文件 ---
    # 为了解决 Playwright 不允许读取本地资源的问题，我们将渲染后的 HTML 写入到模板目录下的临时文件
    # 然后使用 page.goto 加载本地文件
    
    # 生成临时文件名，避免并发冲突
    temp_filename = f"render_{uuid.uuid4().hex}.html"
    
    # 输出目录即为模板所在目录，确保相对路径正确
    output_dir = TEMPLATE_ROOT / template_mode
    output_path = output_dir / temp_filename
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        file_url = output_path.absolute().as_uri()
        
    except Exception as e:
        logger.error(f"写入临时 HTML 文件失败: {e}")
        raise e
    # -------------------------

    # 3. 启动浏览器截图
    # 使用 PlaywrightContext.new_page 替代原本的 async with async_playwright() ...
    try:
        async with PlaywrightContext.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=2
        ) as page:
            
            # --- 监听控制台日志和页面错误 ---
            page.on("console", lambda msg: logger.info(f"[Browser Console] {msg.text}"))
            page.on("pageerror", lambda exc: logger.error(f"[Browser Error] {exc}"))
            # -------------------------------
            
            # 加载页面
            await page.goto(file_url)
            
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
            try:
                # 尝试截取特定容器，去掉可能存在的空白边缘
                element = await page.query_selector(".container")
                if element:
                    screenshot = await element.screenshot(type="png")
                else:
                    logger.warning("未找到 .container 元素，回退到全屏截图")
                    screenshot = await page.screenshot(full_page=True, type="png")
            except Exception as e:
                logger.warning(f"截取 .container 失败，回退到全屏截图: {e}")
                screenshot = await page.screenshot(full_page=True, type="png")
                
            return screenshot
            
    except Exception as e:
        logger.error(f"Playwright 渲染出错: {e}")
        raise e
    finally:
        # 清理临时文件
        if output_path.exists():
           output_path.unlink()
        pass

