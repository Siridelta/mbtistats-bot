from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Playwright, Browser, Page
from nonebot import get_driver, logger

class PlaywrightContext:
    """
    Playwright 全局上下文管理器。
    负责维护全局唯一的 Browser 实例，并提供页面创建接口。
    """
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None

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
                # 启动 Chromium
                # args 参数是为了兼容 Docker/Linux 环境 (no-sandbox)
                cls._browser = await cls._playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                logger.info("Playwright 浏览器内核启动成功")
            except Exception as e:
                logger.error(f"Playwright 启动失败: {e}")
                # 如果初始化失败，可能需要阻止 Bot 启动或做好降级处理，这里选择抛出异常
                raise e

    @classmethod
    async def close(cls):
        """
        关闭 Playwright 资源。
        挂载到 NoneBot 的 on_shutdown 钩子。
        """
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
    @asynccontextmanager
    async def new_page(cls, **kwargs) -> AsyncGenerator[Page, None]:
        """
        获取一个新的 Page 上下文管理器。
        自动处理 Context 的创建和关闭。

        Args:
            **kwargs: 传递给 browser.new_context() 的参数，例如 viewport, device_scale_factor 等。

        Usage:
            async with PlaywrightContext.new_page(viewport={...}) as page:
                await page.goto(...)
        """
        browser = await cls.get_browser()
        # 创建独立的 Context，确保任务间互不干扰（如 Cookie、Storage 等隔离）
        context = await browser.new_context(**kwargs)
        page = await context.new_page()
        try:
            yield page
        finally:
            # 任务结束后关闭 Context，回收资源
            await context.close()

# 注册 NoneBot 生命周期钩子，实现自动启动和关闭
driver = get_driver()
driver.on_startup(PlaywrightContext.init)
driver.on_shutdown(PlaywrightContext.close)