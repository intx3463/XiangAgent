# AGENTS.md

## 项目概述 XiangAgent

XiangAgent基于 LangChain/LangGraph 的多智能体系统，支持单 Agent 和多 Agent 两种模式。具备浏览器自动化、网络搜索、天气查询、动漫名言获取等功能。

## 技术栈

| 框架 | 版本 | 用途 |
|------|------|------|
| LangChain | 1.3.7 | LLM 应用开发框架 |
| LangGraph | 1.2.4 | 多智能体工作流编排 |
| DeepAgents | 0.6.8 | 深度代理框架（agent 创建） |
| FastAPI | 0.136.3 | Web 服务器 |
| Uvicorn | 0.49.0 | ASGI 服务器 |
| Playwright | 1.60.0 | 浏览器自动化 |
| OpenAI | 2.41.1 | LLM API 客户端 |

## 安装

```bash
# 1. 克隆项目
git clone <repo_url>
cd agnet_1

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install langchain langchain-openai langgraph deepagents playwright fastapi uvicorn python-dotenv tavily-python

# 4. 安装 Playwright 浏览器
playwright install firefox

# 5. 配置环境变量
cp .env.example .env  # 或手动创建
```

## 运行方式

```bash
# 单 Agent 模式（交互式命令行）
python agent.py

# 多 Agent 模式（交互式命令行）
python agent.py --multi

# Web 服务器（SSE 流式输出）
python server.py
# 访问 http://localhost:8000
```

## 使用示例
```
使用浏览器打开哔哩哔哩然后打开每周必看观看第一个，然后了解一下南宁西乡塘的天气和动漫名言
```


## 功能特性

### 内置工具
| 工具 | 说明 | 依赖 |
|------|------|------|
| `weather` | 查询城市天气 | 无需 |
| `hitokoto` | 获取动漫名言/语录 | 无需 |
| `internet_search` | 网络搜索 | TAVILY_API_KEY |
| `calculator` | 数学计算 | 无需 |

### 浏览器工具
| 工具 | 说明 |
|------|------|
| `browser_navigate` | 打开网页 |
| `browser_click` | 点击元素 |
| `browser_click_new_tab` | 点击并在新标签页打开 |
| `browser_switch_tab` | 切换标签页 |
| `browser_list_tabs` | 列出所有标签页 |
| `browser_fill` | 填写表单 |
| `browser_select` | 下拉选择 |
| `browser_scroll` | 滚动页面 |
| `browser_get_content` | 获取页面内容 |
| `browser_screenshot` | 截图 |
| `browser_evaluate` | 执行 JavaScript |

### 动态工具
通过 `tools/builder.py` 运行时创建新工具并持久化到 `tools/custom/`。

## 架构

```
├── agent.py              # 单 Agent 入口
├── server.py             # Web 服务器
├── config.py             # 配置管理
├── orchestrator/
│   ├── graph.py          # LangGraph 工作流（路由→分解→执行→综合）
│   ├── router.py         # 问题类型路由
│   ├── decompose.py      # 任务分解
│   ├── subagent.py       # 子 Agent 并发执行
│   ├── synthesize.py     # 结果综合
│   └── queue.py          # SSE 事件队列
├── tools/
│   ├── registry.py       # 工具注册中心
│   ├── browser.py        # Playwright 浏览器管理
│   ├── browser_tools.py  # 浏览器工具定义
│   ├── builder.py        # 动态工具构建器
│   └── custom/           # 动态创建的工具
└── static/
    └── index.html        # Web 前端
```

## 工作流程

1. **路由**：分析用户问题，决定直接处理还是分解
2. **分解**：将复杂问题拆分为子任务
3. **执行**：并发执行子任务（浏览器/工具 agent）
4. **综合**：LLM 综合所有结果生成最终回答

## 注意事项

- 浏览器工具使用 `headless=False`，会弹出 Firefox 窗口
- `internet_search` 需要 `TAVILY_API_KEY`，否则不可用
- API 限流时自动重试（最多 3 次，指数退避 2s→4s→8s）
- 复合查询（如"打开B站+查天气"）会自动拆分为浏览器和工具任务并发执行
