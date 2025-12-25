# Consensus Document - MinIO Service

## 1. Requirement Confirmation
- **Core Goal**: Develop a MinIO object storage interface for MCP.
- **SDK**: Official `minio` Python SDK.
- **Async**: Implemented via `asyncio.to_thread` wrapping synchronous SDK calls.
- **Connection**: Custom `MinioClientManager` managing `urllib3` pool.
- **Quality**: 80% test coverage, strict typing, JSON logging.

## 2. Technical Decisions
- **Async Implementation**: Since `minio` is sync, we will offload I/O to thread pool.
- **Configuration**: Extended `app/core/config.py`.
- **Error Handling**: Map `S3Error` to application-specific exceptions.

## 3. Acceptance Criteria
- Unit tests pass with >80% coverage.
- File upload/download/delete works.
- Connection pool respects max size.
- Logs are in JSON format.
