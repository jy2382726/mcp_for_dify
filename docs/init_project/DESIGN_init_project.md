# DESIGN_init_project

## 1. 系统架构概览

本项目采用典型的分层架构，并集成了 MCP (Model Context Protocol) 服务层。

### 1.1 架构图
```mermaid
graph TD
    User[User / Dify] -->|SSE / HTTP| FastAPI[FastAPI / Uvicorn]
    FastAPI -->|Mount| MCPServer[MCP Server (FastMCP)]
    MCPServer -->|Registry| Plugins[Plugin / Tools]
    Plugins -->|Call| Services[Business Services]
    Services -->|Data| Repositories[Data Access]
    Services -->|Log| Logger[Loguru Logger]
```

### 1.2 目录结构
```
/root/code/mcp_for_dify/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口，挂载 MCP 服务
│   ├── core/                # 核心组件
│   │   ├── __init__.py
│   │   ├── config.py        # 配置管理 (Pydantic)
│   │   └── logger.py        # 日志配置 (Loguru)
│   ├── mcp/                 # MCP 相关
│   │   ├── __init__.py
│   │   └── server.py        # FastMCP 实例与初始化
│   ├── plugins/             # MCP 工具插件
│   │   ├── __init__.py
│   │   └── echo.py          # 示例插件
│   └── services/            # 业务逻辑层
│       ├── __init__.py
│       └── echo_service.py  # 示例业务逻辑
├── tests/                   # 测试
│   ├── __init__.py
│   └── test_echo.py
├── docs/                    # 文档
├── scripts/                 # 脚本
├── .env.example             # 环境变量示例
├── environment.yml          # Conda 环境
├── requirements.txt         # Pip 依赖
└── README.md                # 项目主文档
```

## 2. 核心模块设计

### 2.1 MCP 服务模块
- 使用 `mcp.server.fastmcp.FastMCP` 创建服务实例。
- 通过 `@mcp.tool()` 装饰器注册工具。
- 提供 `sse_app()` 供 FastAPI 挂载。

### 2.2 日志系统
- 使用 `loguru` 替代标准 logging。
- 配置 Console 输出 (彩色) 和 File 输出 (轮转)。
- 注入 `trace_id` (虽然 MCP 自身有上下文，但在 HTTP 层添加 request ID 有助于调试)。

### 2.3 配置管理
- 使用 `pydantic-settings` 读取环境变量。
- 支持 `.env` 文件。

## 3. 接口契约

### 3.1 MCP SSE 端点
- Path: `/sse` (用于建立连接)
- Path: `/messages` (用于客户端发送消息)
- 协议: 标准 MCP SSE 协议。

### 3.2 示例工具 Echo
- Name: `echo`
- Description: "Echoes back the input string."
- Input: `message` (str)
- Output: `str`

## 4. 依赖项
- python >= 3.11
- mcp (python-sdk)
- fastapi
- uvicorn
- pydantic-settings
- loguru
- pytest
- pytest-asyncio
