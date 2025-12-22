# ALIGNMENT_config_update

## 1. 原始需求
修改 `config`，使整个项目通过 `.env` 文件配置动态加载，并让端口 (PORT) 和主机地址 (HOST) 可以动态配置。

## 2. 需求理解与分析
当前项目使用 `pydantic-settings` 管理配置 (`app/core/config.py`)，但 `HOST` 和 `PORT` 目前在 `run_server.py` 和 `app/mcp/server.py` 中是硬编码的。

需要做的改变：
1.  在 `app/core/config.py` 的 `Settings` 类中添加 `HOST` and `PORT` 字段。
2.  设置合理的默认值 (HOST: 0.0.0.0, PORT: 8000)。
3.  修改 `run_server.py` 使用配置中的 `HOST` 和 `PORT`。
4.  修改 `app/mcp/server.py` 使用配置中的 `HOST` 和 `PORT`。
5.  确保 `.env` 文件（如果存在）能覆盖这些默认值。

## 3. 疑问与澄清
*   **Q:** 是否需要更新 `.env.example`？
    *   **A:** 是的，应该在 `.env.example` 中添加新的配置项以供参考。
*   **Q:** `run_server.py` 中的 `reload` 参数是否也需要配置？
    *   **A:** 虽然用户只明确提到了 host 和 port，但通常 `reload` 与 `APP_ENV` (dev/prod) 有关。为了保持简单且符合用户明确要求，暂时只处理 HOST 和 PORT。但可以考虑让 `reload` 依赖于 `APP_ENV == 'development'`。
    *   **决策**: 为了完全响应用户需求，主要关注 HOST 和 PORT。同时我会把 `reload` 的逻辑稍微优化一下（如果 `APP_ENV` 是 dev 则 reload True），但这属于附带优化。

## 4. 任务边界
*   修改 `app/core/config.py`
*   修改 `run_server.py`
*   修改 `app/mcp/server.py`
*   更新 `.env.example`
*   验证服务能否使用新配置启动

## 5. 验收标准
1.  `app/core/config.py` 包含 `HOST` 和 `PORT`。
2.  在 `.env` 中修改 `PORT` 后，重启服务，服务应监听新端口。
3.  `run_server.py` 和 `app/mcp/server.py` 不再包含硬编码的 IP 和端口（除了默认值作为 fallback，但应优先使用 config）。
