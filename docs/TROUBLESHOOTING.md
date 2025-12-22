# 故障排除指南

## 1. Dify 连接报错 "Request validation failed" / "Invalid Host header"

### 现象
Dify 添加 MCP 工具时报错，服务端日志显示：
```
Invalid Host header: 172.xx.xx.xx:8000
ValueError: Request validation failed
```

### 原因
`mcp` Python SDK 的 `FastMCP` 类默认启用了 DNS 重绑定保护 (Transport Security)。当它检测到服务运行在 `localhost` 或 `127.0.0.1` 时，会强制校验请求的 `Host` 头是否为 localhost。
由于 Dify 通常运行在 Docker 容器中，它访问宿主机服务时使用的 Host 是宿主机 IP (如 `172.16.0.148:8000`)，导致校验失败。

### 解决方案
在初始化 `FastMCP` 时，显式将 `host` 设置为 `0.0.0.0`。这不仅允许外部访问，还会禁用默认的 localhost 安全策略。

**修改文件**: `app/mcp/server.py`
```python
mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    dependencies=[],
    host="0.0.0.0",  # 关键配置
    port=8000
)
```

## 2. 启动报错 "ModuleNotFoundError: No module named 'app'"

### 现象
直接运行 `python app/main.py` 时报错。

### 原因
Python 的模块导入路径问题。直接运行子目录脚本时，项目根目录不在 `sys.path` 中。

### 解决方案
使用项目根目录下的启动脚本 `run_server.py`，或者使用 `python -m app.main` 运行。
