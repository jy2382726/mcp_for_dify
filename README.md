# MCP Service for Dify

这是一个基于 Python 的企业级项目，旨在提供符合 MCP (Model Context Protocol) 标准的服务，并专门优化以适配 Dify 1.8.1。

## 功能特性
- **MCP 服务**: 提供标准 SSE 接口，兼容 Dify。
- **FastAPI 集成**: 高性能异步 Web 框架。
- **模块化设计**: 清晰的分层架构 (Controller/Service/Repository)。
- **企业级特性**: 结构化日志、环境配置管理、Docker 支持。

## 快速开始

### 1. 环境准备
确保已安装 Conda。
```bash
conda env create -f environment.yml
conda activate mcp_for_dify
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 运行服务
#### 方式一：使用启动脚本（推荐）
```bash
python run_server.py
```

#### 方式二：作为模块运行
```bash
python -m app.main
```

服务将在 `http://localhost:8000` 启动。
API 文档位于 `http://localhost:8000/docs`。

## Dify 集成
1. 在 Dify 中，进入 **工具** -> **添加工具**。
2. 选择 **MCP 工具**。
3. 输入 SSE URL: `http://<your-server-ip>:8000/mcp/sse`。
4. Dify 将自动发现 `echo` 工具。

## 开发指南
- **添加新工具**: 在 `app/plugins/` 下创建新文件，使用 `@mcp.tool()` 注册函数，并在 `app/mcp/server.py` 中导入。
- **日志**: 使用 `app.core.logger.logger`。
- **配置**: 修改 `.env` 文件。

## 测试
```bash
pytest tests/
```
