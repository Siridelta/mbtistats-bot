import asyncio
import socket
import uuid
import time
from pathlib import Path
from typing import Dict, Any, Optional
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from jinja2 import Environment, FileSystemLoader
from .playwright_context import PlaywrightContext
from .config import plugin_config, CACHE_DIR
from nonebot import logger

# 模板根目录: 现在位于插件包内部 template/
TEMPLATE_ROOT = Path(__file__).parent / "template"


def find_free_port() -> int:
    """找一个可用的随机端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class QuietHTTPHandler(SimpleHTTPRequestHandler):
    """静默的 HTTP Handler，不切换工作目录，支持 .mjs MIME 类型"""
    # 关键：禁用 HTTP Keep-Alive，避免浏览器长连接导致 shutdown 阶段阻塞。
    # 在 Windows 场景下，SimpleHTTPRequestHandler + 持久连接更容易出现清理卡住。
    protocol_version = "HTTP/1.0"
    
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
            def handler(*args, **kwargs):
                return QuietHTTPHandler(*args, root_dir=self.root_dir, **kwargs)
            # 使用 ThreadingHTTPServer 避免单请求阻塞 shutdown。
            self.server = ThreadingHTTPServer(("localhost", self.port), handler)
            self.server.serve_forever()
        
        self.thread = Thread(target=run_server, daemon=True)
        self.thread.start()
        logger.debug(f"[TempHTTPServer] 启动于 http://localhost:{self.port}, 根目录: {self.root_dir}")
        
    def stop(self, join_timeout: float = 2.0):
        """
        停止服务器（带超时兜底，避免阻塞主流程）。
        """
        if not self.server:
            return

        server = self.server
        thread = self.thread

        # 关键：shutdown 放到独立线程执行，避免主线程被永久阻塞。
        shutdown_thread = Thread(target=server.shutdown, daemon=True)
        shutdown_thread.start()
        shutdown_thread.join(timeout=join_timeout)
        if shutdown_thread.is_alive():
            logger.warning("[TempHTTPServer] shutdown 超时，继续执行清理流程")

        try:
            server.server_close()
        except Exception as e:
            logger.warning(f"[TempHTTPServer] server_close 异常: {e}")

        # 线程兜底：避免 server 线程残留导致“看起来卡死”。
        if thread and thread.is_alive():
            thread.join(timeout=join_timeout)
            if thread.is_alive():
                logger.warning("[TempHTTPServer] 服务器线程未在超时内退出，继续后续流程")
            else:
                logger.debug("[TempHTTPServer] 服务器线程已退出")

        self.server = None
        self.thread = None
        logger.debug("[TempHTTPServer] 已停止")


def _create_render_debug_log_path(template_mode: str) -> Path:
    """
    生成一次渲染对应的调试日志路径。
    日志落盘到 cache 目录，避免仅依赖 NoneBot Console TUI。
    """
    debug_dir = CACHE_DIR / "_render_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    return debug_dir / f"render-debug-{template_mode}-{ts}.log"


def _write_render_debug_log(log_path: Path, lines: list[str]) -> None:
    """将渲染阶段日志写入文件。"""
    try:
        log_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        logger.warning(f"写入渲染调试日志失败: {e}")


def _append_render_debug_log(log_path: Path, line: str) -> None:
    """追加单行日志，确保卡住时也能看到过程。"""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        logger.warning(f"追加渲染调试日志失败: {e}")


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
    
    debug_log_path = _create_render_debug_log_path(template_mode)
    debug_lines: list[str] = []
    render_started_at = time.perf_counter()

    def debug_log(message: str, level: str = "debug") -> None:
        """统一记录渲染阶段日志：文件 + NoneBot logger。"""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        debug_lines.append(line)
        _append_render_debug_log(debug_log_path, line)
        if level == "error":
            logger.error(line)
        elif level == "warning":
            logger.warning(line)
        elif level == "info":
            logger.info(line)
        else:
            logger.debug(line)

    async def _render_once() -> bytes:
        # 5. 使用 Playwright 截图
        async with PlaywrightContext.new_page(
            viewport={"width": width, "height": height}
        ) as page:
            page.on("console", lambda msg: debug_log(f"[Browser Console.{msg.type}] {msg.text}", level="info"))
            page.on("pageerror", lambda exc: debug_log(f"[Browser Error] {exc}", level="error"))
            page.on(
                "response",
                lambda resp: debug_log(
                    f"[Browser Response] {resp.status} {resp.url}",
                    level="warning" if resp.status >= 400 else "debug",
                ),
            )
            page.on(
                "requestfailed",
                lambda req: debug_log(f"[Browser RequestFailed] {req.url} :: {req.failure}", level="warning"),
            )

            goto_started_at = time.perf_counter()
            # 通过 HTTP 加载页面。使用 domcontentloaded 降低“等待外部资源”导致的卡死概率。
            await page.goto(
                http_url,
                timeout=plugin_config.mbtistats_render_timeout * 1000,
                wait_until="domcontentloaded",
            )
            debug_log(f"阶段完成: goto(domcontentloaded), 耗时 {(time.perf_counter() - goto_started_at):.3f}s")

            # 等待渲染
            canvas_wait_started_at = time.perf_counter()
            try:
                await page.wait_for_selector("canvas", timeout=10000)
                await page.wait_for_timeout(1000)
                debug_log(f"阶段完成: wait_for_canvas, 耗时 {(time.perf_counter() - canvas_wait_started_at):.3f}s")
            except Exception as e:
                debug_log(f"等待 Canvas 超时，尝试直接截图: {e}", level="warning")

            # 截图
            screenshot_started_at = time.perf_counter()
            try:
                element = await page.query_selector(".container")
                if element:
                    screenshot = await element.screenshot(type="png")
                    debug_log("截图路径: .container")
                else:
                    debug_log("未找到 .container 元素，回退到全屏截图", level="warning")
                    screenshot = await page.screenshot(full_page=True, type="png")
            except Exception as e:
                debug_log(f"截取 .container 失败，回退到全屏截图: {e}", level="warning")
                screenshot = await page.screenshot(full_page=True, type="png")
            debug_log(f"阶段完成: screenshot, 耗时 {(time.perf_counter() - screenshot_started_at):.3f}s")
            return screenshot

    try:
        debug_log(f"渲染开始: template={template_mode}, viewport={width}x{height}")
        debug_log(f"临时页面 URL: {http_url}")

        # 总超时保护：在 page.goto 超时外再加一层兜底，防止渲染链路“看起来卡死”。
        total_timeout = plugin_config.mbtistats_render_timeout + 20
        screenshot = await asyncio.wait_for(_render_once(), timeout=total_timeout)
        debug_log(f"渲染成功，总耗时 {(time.perf_counter() - render_started_at):.3f}s")
        return screenshot
    except asyncio.TimeoutError as e:
        debug_log("渲染触发总超时保护，可能存在等待链路阻塞", level="error")
        logger.error(f"Playwright 渲染超时(总超时保护): {e}")
        raise e
    except Exception as e:
        debug_log(f"渲染异常: {e}", level="error")
        logger.error(f"Playwright 渲染出错: {e}")
        raise e
    finally:
        # 6. 清理
        debug_log("进入清理阶段")
        debug_log("开始停止临时 HTTP 服务器")
        http_server.stop()
        debug_log("临时 HTTP 服务器停止完成")
        if output_path.exists():
            try:
                output_path.unlink()
                debug_log("临时 HTML 文件删除完成")
            except Exception as e:
                debug_log(f"删除临时文件失败: {e}", level="warning")
        debug_log(f"渲染日志路径: {debug_log_path}")
        _write_render_debug_log(debug_log_path, debug_lines)
