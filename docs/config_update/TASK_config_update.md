# TASK_config_update

## 任务清单

### 1. Update Config Definition
*   **文件**: `app/core/config.py`
*   **内容**: 在 `Settings` 类中添加 `HOST` 和 `PORT`。
*   **验收**: 单元测试或 import 检查可以看到新字段。

### 2. Update .env.example
*   **文件**: `.env.example`
*   **内容**: 添加 `HOST=0.0.0.0` 和 `PORT=8000` 注释说明。
*   **验收**: 文件包含新字段。

### 3. Refactor run_server.py
*   **文件**: `run_server.py`
*   **内容**: 导入 settings，使用动态配置替代硬编码。
*   **验收**: 运行脚本能正常启动服务。

### 4. Refactor MCP Server
*   **文件**: `app/mcp/server.py`
*   **内容**: 确保 `FastMCP` 初始化使用 settings 中的配置。
*   **验收**: 代码审查确认使用了 settings。

### 5. Verification
*   **内容**: 创建一个临时的 `.env` 修改端口，验证服务是否在端口启动。
*   **验收**: 服务在指定端口可访问。
