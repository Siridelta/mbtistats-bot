import asyncio
import socket
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from jinja2 import Environment, FileSystemLoader
from .playwright_context import PlaywrightContext
from nonebot import logger

# 模板根目录: template/
TEMPLATE_ROOT = \
    Path(__file__).parent.parent.parent \
    / "template"


def find_free_port() -> int:
    """找一个可用的随机端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class QuietHTTPHandler(SimpleHTTPRequestHandler):
    """静默的 HTTP Handler，不切换工作目录，支持 .mjs MIME 类型"""
    
    # 扩展 MIME 类型映射
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        '.mjs': 'application/javascript',
        '.js': 'application/javascript',
    }
    
    def __init__(self, *args, root_dir: Path = None, **kwargs):
        self.root_dir = root_dir
        super().__init__(*args, **kwargs)
    
    def translate_path(self, path):
        """重写路径转换，使用指定的根目录而不是当前工作目录"""
        # 移除开头的 /
        path = path.lstrip('/')
        # 拼接完整路径
        return str(self.root_dir / path)
    
    def log_message(self, format, *args):
        pass  # 静默，不输出访问日志


class TempHTTPServer:
    """临时 HTTP 服务器，用于服务模板文件"""
    
    def __init__(self, root_dir: Path, port: int = 0):
        self.root_dir = root_dir
        self.port = port if port else find_free_port()
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None
        
    def start(self):
        """在后台线程启动服务器"""
        def run_server():
            # 使用 lambda 传递 root_dir 给 Handler
            handler = lambda *args, **kwargs: QuietHTTPHandler(*args, root_dir=self.root_dir, **kwargs)
            self.server = HTTPServer(("localhost", self.port), handler)
            self.server.serve_forever()
        
        self.thread = Thread(target=run_server, daemon=True)
        self.thread.start()
        logger.debug(f"[TempHTTPServer] 启动于 http://localhost:{self.port}, 根目录: {self.root_dir}")
        
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.debug(f"[TempHTTPServer] 已停止")


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

    # 3. 写入临时文件
    temp_filename = f"render_{uuid.uuid4().hex}.html"
    output_dir = TEMPLATE_ROOT / template_mode
    output_path = output_dir / temp_filename
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        logger.error(f"写入临时 HTML 文件失败: {e}")
        raise e

    # 4. 启动临时 HTTP 服务器
    http_server = TempHTTPServer(TEMPLATE_ROOT)
    http_server.start()
    await asyncio.sleep(0.5)  # 等待服务器启动
    
    # 构建 HTTP URL（相对于模板根目录）
    http_url = f"http://localhost:{http_server.port}/{template_mode}/{temp_filename}"
    
    try:
        # 5. 使用 Playwright 截图
        async with PlaywrightContext.new_page(
            viewport={"width": width, "height": height}
        ) as page:
            
            page.on("console", lambda msg: logger.info(f"[Browser Console] {msg.text}"))
            page.on("pageerror", lambda exc: logger.error(f"[Browser Error] {exc}"))
            
            # 通过 HTTP 加载页面
            await page.goto(http_url)
            
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
    finally:
        # 6. 清理
        http_server.stop()
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception as e:
                logger.debug(f"删除临时文件失败: {e}")
