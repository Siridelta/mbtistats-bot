import uuid
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, unquote
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import Route
from .playwright_context import PlaywrightContext
from .config import plugin_config
from nonebot import logger

# 模板根目录: 现在位于插件包内部 template/
TEMPLATE_ROOT = Path(__file__).parent / "template"
VIRTUAL_ORIGIN = "http://mbti.local"


def _guess_content_type(file_path: Path) -> str:
    """根据文件后缀推断响应 Content-Type。"""
    if file_path.suffix == ".mjs":
        return "application/javascript"
    if file_path.suffix == ".js":
        return "application/javascript"
    guessed, _ = mimetypes.guess_type(str(file_path))
    return guessed or "application/octet-stream"


async def use_cache(
    img_cache_path: Path,
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
    img_cache_path: Path,
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
    if not TEMPLATE_ROOT.exists():
        logger.error(f"模板目录不存在: {TEMPLATE_ROOT}")
        raise FileNotFoundError(f"Template directory not found: {TEMPLATE_ROOT}")

    env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT))
    
    template_path = f"{template_mode}/index.html"
    
    try:
        template = env.get_template(template_path)
    except Exception as e:
        logger.error(f"加载模板失败 {template_path}: {e}")
        raise e

    # 2. 渲染 HTML 内容
    html_content = template.render(**data)

    # 3. 使用虚拟站点 URL（由 page.route 拦截并返回内存 HTML + 本地模板静态资源）
    entry_filename = f"render_{uuid.uuid4().hex}.html"
    entry_path = f"/{template_mode}/{entry_filename}"
    http_url = f"{VIRTUAL_ORIGIN}{entry_path}"

    try:
        # 5. 使用 Playwright 截图
        async with PlaywrightContext.new_page(
            viewport={"width": width, "height": height}
        ) as page:

            page.on("console", lambda msg: logger.info(f"[Browser Console] {msg.text}"))
            page.on("pageerror", lambda exc: logger.error(f"[Browser Error] {exc}"))

            async def _route_virtual_files(route: Route):
                request_url = route.request.url
                parsed = urlparse(request_url)
                request_path = unquote(parsed.path)

                # 主入口 HTML 直接从内存返回，不再落盘临时文件。
                if request_path == entry_path:
                    await route.fulfill(
                        status=200,
                        body=html_content.encode("utf-8"),
                        headers={
                            "Content-Type": "text/html; charset=utf-8",
                            "Cache-Control": "no-cache",
                            "Access-Control-Allow-Origin": "*",
                        },
                    )
                    return

                relative_path = request_path.lstrip("/")
                local_path = (TEMPLATE_ROOT / relative_path).resolve()

                # 仅允许访问模板根目录内文件，防止路径穿越。
                try:
                    local_path.relative_to(TEMPLATE_ROOT.resolve())
                except ValueError:
                    await route.fulfill(status=403, body="Forbidden")
                    return

                if not local_path.exists() or not local_path.is_file():
                    await route.fulfill(status=404, body="File not found")
                    return

                try:
                    body = local_path.read_bytes()
                    await route.fulfill(
                        status=200,
                        body=body,
                        headers={
                            "Content-Type": _guess_content_type(local_path),
                            "Cache-Control": "no-cache",
                            "Access-Control-Allow-Origin": "*",
                        },
                    )
                except Exception as e:
                    logger.error(f"读取模板资源失败 {local_path}: {e}")
                    await route.fulfill(status=500, body="Internal server error")

            await page.route(f"{VIRTUAL_ORIGIN}/**", _route_virtual_files)

            # 通过虚拟 HTTP URL 加载页面。使用 domcontentloaded 可以减少等待外部资源导致的阻塞风险。
            await page.goto(
                http_url,
                timeout=plugin_config.mbtistats_render_timeout * 1000,
                wait_until="domcontentloaded",
            )
            
            # 等待渲染
            try:
                await page.wait_for_selector("canvas", timeout=10000)
                await page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"等待 Canvas 超时，尝试直接截图: {e}")

            # 截图
            try:
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
