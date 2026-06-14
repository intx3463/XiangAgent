# XiangAgent

基于 LangChain/LangGraph 的多智能体系统，支持浏览器自动化、网络搜索、天气查询、动漫名言获取等功能。

## 技术栈

| 框架 | 版本 | 用途 |
|------|------|------|
| LangChain | 1.3.7 | LLM 应用开发框架 |
| LangGraph | 1.2.4 | 多智能体工作流编排 |
| DeepAgents | 0.6.8 | 深度代理框架 |
| FastAPI | 0.136.3 | Web 服务器 |
| Playwright | 1.60.0 | 浏览器自动化 |

## 安装

```bash
# 1. 克隆项目
git clone <repo_url>
cd agnet_1

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install langchain langchain-openai langgraph deepagents playwright fastapi uvicorn python-dotenv tavily-python

# 4. 安装 Playwright 浏览器
playwright install firefox

# 5. 配置环境变量
cp .env.example .env
```

## 环境配置

创建 `.env` 文件：

```env
# 必需
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_ID=gpt-4o

# 可选
TAVILY_API_KEY=your_tavily_key    # 启用网络搜索
```

## 运行

```bash
# 单 Agent 模式
python agent.py

# 多 Agent 模式
python agent.py --multi

# Web 服务器
python server.py
# 访问 http://localhost:8000
```

## 使用示例

### 浏览器操作
```
使用浏览器打开哔哩哔哩
打开百度搜索 Python 教程
截图保存当前页面
```

### 工具查询
```
查询南宁天气
获取一条动漫名言
搜索最新的 AI 新闻
```

### 复合查询（自动拆分并发执行）
```
使用浏览器打开哔哩哔哩然后打开每周必看观看第一个，然后了解一下南宁西乡塘的天气和动漫名言
```

## 功能特性

### 内置工具
- `weather` - 查询城市天气
- `hitokoto` - 获取动漫名言/语录
- `internet_search` - 网络搜索（需要 TAVILY_API_KEY）
- `calculator` - 数学计算

### 浏览器工具
- 打开网页、点击元素、填写表单
- 新标签页管理（打开、切换、列出）
- 获取页面内容、截图、执行 JavaScript

### 动态工具
通过 `tools/builder.py` 运行时创建新工具并持久化。

## 架构

```
├── agent.py              # 单 Agent 入口
├── server.py             # Web 服务器
├── config.py             # 配置管理
├── orchestrator/
│   ├── graph.py          # LangGraph 工作流
│   ├── router.py         # 问题类型路由
│   ├── decompose.py      # 任务分解
│   ├── subagent.py       # 子 Agent 并发执行
│   └── synthesize.py     # 结果综合
├── tools/
│   ├── registry.py       # 工具注册中心
│   ├── browser.py        # Playwright 浏览器管理
│   └── browser_tools.py  # 浏览器工具定义
└── static/
    └── index.html        # Web 前端
```

## 工作流程

1. **路由** - 分析用户问题，决定直接处理还是分解
2. **分解** - 将复杂问题拆分为子任务
3. **执行** - 并发执行子任务（浏览器/工具 agent）
4. **综合** - LLM 综合所有结果生成最终回答

## 注意事项

- 浏览器工具使用 `headless=False`，会弹出 Firefox 窗口
- API 限流时自动重试（最多 3 次，指数退避）
- 复合查询会自动拆分为浏览器和工具任务并发执行
