"""Playwright 浏览器 LangChain 工具"""
from langchain_core.tools import tool
from .browser import browser_manager


@tool
async def browser_navigate(url: str) -> str:
    """在浏览器中打开指定网页

    Args:
        url: 要打开的网页 URL，如 https://example.com
    """
    try:
        await browser_manager.start()
        return await browser_manager.goto(url)
    except Exception as e:
        return f"导航失败: {e}"


@tool
async def browser_get_content(selector: str = "body") -> str:
    """获取当前网页的文本内容

    Args:
        selector: CSS 选择器，默认获取整个页面 body
    """
    try:
        return await browser_manager.get_content(selector)
    except Exception as e:
        return f"获取内容失败: {e}"


@tool
async def browser_screenshot(path: str = "screenshot.png") -> str:
    """对当前网页进行截图

    Args:
        path: 截图保存路径，默认 screenshot.png
    """
    try:
        return await browser_manager.screenshot(path)
    except Exception as e:
        return f"截图失败: {e}"


@tool
async def browser_click(selector: str) -> str:
    """点击网页上的元素

    Args:
        selector: CSS 选择器，如 #submit-btn, .click-me, a[href="..."]
    """
    try:
        return await browser_manager.click(selector)
    except Exception as e:
        return f"点击失败: {e}"


@tool
async def browser_click_new_tab(selector: str) -> str:
    """点击元素并在新标签页中打开，自动切换到新标签页

    Args:
        selector: CSS 选择器，如视频链接、外部链接等会在新标签页打开的元素
    """
    try:
        return await browser_manager.click(selector, new_tab=True)
    except Exception as e:
        return f"点击失败: {e}"


@tool
async def browser_switch_tab(index: int = -1) -> str:
    """切换到指定标签页

    Args:
        index: 标签页索引（从0开始），-1 表示切换到最新打开的标签页
    """
    try:
        if index == -1:
            return await browser_manager.switch_to_latest_tab()
        else:
            return await browser_manager.switch_to_tab(index)
    except Exception as e:
        return f"切换失败: {e}"


@tool
async def browser_list_tabs() -> str:
    """列出所有打开的标签页"""
    try:
        return await browser_manager.list_tabs()
    except Exception as e:
        return f"获取失败: {e}"


@tool
async def browser_fill(selector: str, value: str) -> str:
    """在输入框中填写内容

    Args:
        selector: 输入框的 CSS 选择器，如 #username, input[name="email"]
        value: 要填写的内容
    """
    try:
        return await browser_manager.fill(selector, value)
    except Exception as e:
        return f"填写失败: {e}"


@tool
async def browser_select(selector: str, value: str) -> str:
    """在下拉框中选择选项

    Args:
        selector: 下拉框的 CSS 选择器
        value: 要选择的选项值
    """
    try:
        return await browser_manager.select(selector, value)
    except Exception as e:
        return f"选择失败: {e}"


@tool
async def browser_scroll(direction: str = "down") -> str:
    """滚动页面

    Args:
        direction: 滚动方向，down 向下，up 向上
    """
    try:
        return await browser_manager.scroll(direction)
    except Exception as e:
        return f"滚动失败: {e}"


@tool
async def browser_back() -> str:
    """浏览器后退到上一页"""
    try:
        return await browser_manager.back()
    except Exception as e:
        return f"后退失败: {e}"


@tool
async def browser_forward() -> str:
    """浏览器前进到下一页"""
    try:
        return await browser_manager.forward()
    except Exception as e:
        return f"前进失败: {e}"


@tool
async def browser_reload() -> str:
    """刷新当前页面"""
    try:
        return await browser_manager.reload()
    except Exception as e:
        return f"刷新失败: {e}"


@tool
async def browser_evaluate(expression: str) -> str:
    """在当前页面执行 JavaScript 代码

    Args:
        expression: JavaScript 表达式或函数
    """
    try:
        return await browser_manager.evaluate(expression)
    except Exception as e:
        return f"执行失败: {e}"


@tool
async def browser_get_info() -> str:
    """获取当前页面信息（URL、标题）"""
    try:
        await browser_manager.start()
        url = await browser_manager.get_url()
        title = await browser_manager.get_title()
        return f"标题: {title}\nURL: {url}"
    except Exception as e:
        return f"获取信息失败: {e}"


BROWSER_TOOLS = [
    browser_navigate,
    browser_get_content,
    browser_screenshot,
    browser_click,
    browser_click_new_tab,
    browser_switch_tab,
    browser_list_tabs,
    browser_fill,
    browser_select,
    browser_scroll,
    browser_back,
    browser_forward,
    browser_reload,
    browser_evaluate,
    browser_get_info,
]
