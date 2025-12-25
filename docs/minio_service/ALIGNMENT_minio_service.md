# Alignment Document - MinIO Object Storage Service

## 1. Project Context Analysis
- **Project Structure**:
    - `app/core/config.py`: Pydantic settings.
    - `app/core/logger.py`: Loguru logging.
    - `demo/file_service.py`: Reference implementation (sync).
    - `requirements.txt`: Dependencies.
- **Dependencies**: `minio` (Official Python SDK) is required. Latest version: `7.2.20`.
- **Architecture**: MCP (Model Context Protocol) pattern. Service layer + MCP server.

## 2. Requirements Understanding
- **Dependency**: Install `minio` (official).
- **Interface**:
    - Replicate `demo/file_service.py` logic.
    - **Async Non-blocking**: Official SDK is synchronous. **Decision**: Use `asyncio.to_thread` to wrap blocking calls.
- **Connection Management**:
    - "Connection Pool": MinIO client uses `urllib3` internally.
    - **Decision**: Create a `MinioClientManager` class.
        - **Lazy Load**: Initialize client on first access or explicit `connect()`.
        - **Preheat**: Optional `warmup()` method.
        - **Pool Config**: Pass custom `urllib3.PoolManager` with `maxsize` (max connections). Min connections is implicit (pool starts empty).
        - **Health Check**: `bucket_exists` or `list_buckets` check.
- **Code Quality**:
    - Annotations, Unit Tests (>80%), Static Check.
- **Logging**:
    - JSON format (Loguru supports `serialize=True` or custom format). Use `app/core/logger.py`.
- **Other**:
    - Swagger/OAS3 (FastAPI default).
    - Metrics (Prometheus? or just logs?). I will add simple timing logs/metrics.
    - Configurable endpoints.

## 3. Ambiguities & Strategies
- **Async Support**: Official SDK is sync.
    - **Strategy**: Wrap in `run_in_executor` / `to_thread`.
- **Connection Pool**: MinIO client *is* the pool owner.
    - **Strategy**: Configure the underlying `urllib3` pool.

## 4. Proposal
- **File Structure**:
    - `app/services/minio_service.py`: The service logic (async wrapper).
    - `app/core/minio_client.py`: The connection manager (Singleton).
    - `app/core/config.py`: Add MinIO config.
    - `tests/test_minio_service.py`: Tests.

## 5. Decision Check
- **User**: "Determine MinIO client SDK... recommend official".
    - **Decision**: Use `minio` package.
- **User**: "Async non-blocking".
    - **Decision**: `asyncio.to_thread(client.func, ...)`

## 6. Next Steps
- Create Consensus document (I will merge Alignment and Consensus steps here as I am confident).
- Create Design document.
