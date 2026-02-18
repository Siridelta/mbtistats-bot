from typing import Optional, AsyncGenerator, Dict
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Playwright, Browser, Page, BrowserContext
from nonebot import get_driver, logger

class PlaywrightContext:
    """
    Playwright 全局上下文管理器。
    负责维护全局唯一的 Browser 和 Context 实例。
    """
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None

    @classmethod
    async def init(cls):
        """
        初始化 Playwright 和全局 Browser 实例。
        挂载到 NoneBot 的 on_startup 钩子。
        """
        if cls._playwright is None:
            logger.info("正在启动 Playwright 浏览器内核...")
            try:
                cls._playwright = await async_playwright().start()
            except Exception as e:
                logger.error(f"Playwright 启动失败: {e}")
                # 如果初始化失败，可能需要阻止 Bot 启动或做好降级处理，这里选择抛出异常
                raise e
        if cls._playwright is None:
            raise RuntimeError("Playwright initialization failed")
        if cls._browser is None:
            cls._browser = await cls._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
        if cls._browser is None:
            raise RuntimeError("Playwright Browser initialization failed")
        if cls._context is None:
            cls._context = await cls._browser.new_context(
                device_scale_factor=2,
                viewport=None,
                bypass_csp=True  # 绕过 CSP 限制，允许 ES6 module 加载本地文件
            )
        if cls._context is None:
            raise RuntimeError("Playwright Context initialization failed")
        logger.info("Playwright 浏览器内核及上下文启动成功")

    @classmethod
    async def close(cls):
        """
        关闭 Playwright 资源。
        挂载到 NoneBot 的 on_shutdown 钩子。
        """
        if cls._context:
            await cls._context.close()
            cls._context = None

        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
        logger.info("Playwright 资源已释放")

    @classmethod
    async def get_browser(cls) -> Browser:
        """
        获取全局 Browser 实例。
        如果意外未初始化（如热重载场景），会尝试重新初始化。
        """
        if cls._browser is None:
            await cls.init()
        if cls._browser is None:
             raise RuntimeError("Playwright Browser initialization failed")
        return cls._browser

    @classmethod
    async def get_context(cls) -> BrowserContext:
        """
        获取全局 Context 实例。
        """
        if cls._context is None:
            await cls.init()
        if cls._context is None:
             raise RuntimeError("Playwright Context initialization failed")
        return cls._context

    @classmethod
    @asynccontextmanager
    async def new_page(cls, viewport: Optional[Dict[str, int]] = None, **kwargs) -> AsyncGenerator[Page, None]:
        """
        获取一个新的 Page 上下文管理器。
        自动处理 Context 的创建和关闭。

        Args:
            viewport: {"width": 100, "height": 100}
            **kwargs: 兼容旧接口，会被忽略或记录日志

        Usage:
            async with PlaywrightContext.new_page(viewport={...}) as page:
                await page.goto(...)
        """
        context = await cls.get_context()
        page = await context.new_page()
        
        try:
            # 如果指定了视口大小，单独为这个页面设置
            if viewport:
                await page.set_viewport_size(viewport)
            
            yield page
        finally:
            # 必须关闭 Page，否则内存会泄漏
            await page.close()

# 注册 NoneBot 生命周期钩子，实现自动启动和关闭
driver = get_driver()
driver.on_startup(PlaywrightContext.init)
driver.on_shutdown(PlaywrightContext.close)
