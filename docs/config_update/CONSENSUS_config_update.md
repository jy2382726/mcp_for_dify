# CONSENSUS_config_update

## 1. 需求描述
将项目的 `HOST` 和 `PORT` 配置移至 `app/core/config.py` 管理，支持通过 `.env` 文件动态加载，并替换代码中硬编码的值。

## 2. 技术方案
### 2.1 配置中心 (`app/core/config.py`)
更新 `Settings` 类：
```python
class Settings(BaseSettings):
    # ... existing ...
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # ...
```

### 2.2 服务启动入口 (`run_server.py`)
使用 `settings.HOST` 和 `settings.PORT`：
```python
uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.APP_ENV == "development")
```

### 2.3 MCP 服务定义 (`app/mcp/server.py`)
使用 `settings.HOST` 和 `settings.PORT` 初始化 `FastMCP`。

### 2.4 环境文件 (`.env.example`)
添加示例配置。

## 3. 验收标准
1.  代码中无硬编码的 `0.0.0.0` 或 `8000`（除了在 config 定义默认值）。
2.  可以通过环境变量或 `.env` 文件改变服务端口。
