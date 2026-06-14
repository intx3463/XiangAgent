"""Playwright Firefox 浏览器管理器（单例，持久运行）"""
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """管理 Firefox 浏览器的生命周期"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._pages: dict[str, Page] = {}
        self._current_page: Page | None = None

    async def start(self):
        """启动 Firefox 浏览器"""
        if self._browser:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.firefox.launch(headless=False)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        page = await self._context.new_page()
        self._pages["default"] = page
        self._current_page = page

    async def stop(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._context = None
        self._pages.clear()
        self._current_page = None

    @property
    def page(self) -> Page:
        """获取当前页面"""
        if not self._current_page:
            raise RuntimeError("浏览器未启动，请先调用 start()")
        return self._current_page

    async def goto(self, url: str) -> str:
        """导航到指定 URL"""
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await self.page.title()
        return f"已打开: {title} ({url})"

    async def get_content(self, selector: str = "body") -> str:
        """获取页面文本内容"""
        element = self.page.locator(selector)
        text = await element.inner_text()
        return text[:5000] if text else "页面为空"

    async def get_html(self, selector: str = "body") -> str:
        """获取页面 HTML"""
        element = self.page.locator(selector)
        html = await element.inner_html()
        return html[:10000] if html else "页面为空"

    async def screenshot(self, path: str = "screenshot.png", full_page: bool = False) -> str:
        """截图"""
        await self.page.screenshot(path=path, full_page=full_page)
        return f"截图已保存: {path}"

    async def click(self, selector: str, new_tab: bool = False) -> str:
        """点击元素，可选处理新标签页"""
        if new_tab:
            async with self.page.expect_popup() as popup_info:
                await self.page.click(selector, timeout=5000)
            new_page = await popup_info.value
            await new_page.wait_for_load_state("domcontentloaded")
            self._current_page = new_page
            title = await new_page.title()
            url = new_page.url
            return f"已点击并切换到新标签页: {title} ({url})"
        else:
            await self.page.click(selector, timeout=5000)
            return f"已点击: {selector}"

    async def switch_to_latest_tab(self) -> str:
        """切换到最新打开的标签页"""
        pages = self._context.pages
        if len(pages) > 1:
            self._current_page = pages[-1]
            title = await self._current_page.title()
            url = self._current_page.url
            return f"已切换到最新标签页: {title} ({url})"
        return "只有一个标签页"

    async def switch_to_tab(self, index: int) -> str:
        """切换到指定索引的标签页"""
        pages = self._context.pages
        if 0 <= index < len(pages):
            self._current_page = pages[index]
            title = await pages[index].title()
            url = pages[index].url
            return f"已切换到标签页 {index + 1}: {title} ({url})"
        return f"标签页 {index + 1} 不存在，共 {len(pages)} 个标签页"

    async def list_tabs(self) -> str:
        """列出所有打开的标签页"""
        pages = self._context.pages
        result = [f"共 {len(pages)} 个标签页:"]
        for i, page in enumerate(pages):
            title = await page.title()
            url = page.url
            result.append(f"  {i + 1}. {title} - {url}")
        return "\n".join(result)

    async def fill(self, selector: str, value: str) -> str:
        """填写表单"""
        await self.page.fill(selector, value, timeout=10000)
        return f"已填写 {selector}: {value}"

    async def select(self, selector: str, value: str) -> str:
        """下拉选择"""
        await self.page.select_option(selector, value, timeout=10000)
        return f"已选择 {selector}: {value}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        """滚动页面"""
        if direction == "down":
            await self.page.mouse.wheel(0, amount)
        elif direction == "up":
            await self.page.mouse.wheel(0, -amount)
        return f"已滚动 {direction} {amount}px"

    async def back(self) -> str:
        """后退"""
        await self.page.go_back()
        return "已后退"

    async def forward(self) -> str:
        """前进"""
        await self.page.go_forward()
        return "已前进"

    async def reload(self) -> str:
        """刷新"""
        await self.page.reload()
        return "已刷新"

    async def evaluate(self, expression: str) -> str:
        """执行 JavaScript"""
        try:
            result = await self.page.evaluate(expression)
            return str(result) if result else "执行完成"
        except Exception as e:
            return f"执行失败: {e}"

    async def wait_for(self, selector: str, timeout: int = 5000) -> str:
        """等待元素出现"""
        await self.page.wait_for_selector(selector, timeout=timeout)
        return f"元素已出现: {selector}"

    async def get_url(self) -> str:
        """获取当前 URL"""
        return self.page.url

    async def get_title(self) -> str:
        """获取页面标题"""
        return await self.page.title()


browser_manager = BrowserManager()
