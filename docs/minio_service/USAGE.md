# Usage Guide - MinIO Service

## Overview
The `MinioService` provides asynchronous methods to interact with MinIO object storage. It handles connection pooling, validation, and error handling.

## Initialization
The service is designed as a singleton and uses configuration from `app/core/config.py`.

```python
from app.services.minio_service import get_minio_service

service = get_minio_service()
```

## API Reference

### `upload_file`
Uploads a file to MinIO.

```python
async def upload_file(
    self, 
    file_obj: BinaryIO, 
    filename: str, 
    object_name: str = None, 
    original_url: str = None
) -> Dict[str, Any]
```

**Parameters:**
- `file_obj`: File-like object (bytes).
- `filename`: Original filename (for validation and type detection).
- `object_name`: (Optional) Custom object name in bucket.
- `original_url`: (Optional) Metadata.

**Returns:**
```json
{
    "object_name": "2023/10/27/uuid.jpg",
    "original_filename": "image.jpg",
    "file_size": 1024,
    "preview_url": "http://...",
    "etag": "..."
}
```

### `delete_file`
Deletes a file.

```python
async def delete_file(self, object_name: str) -> Dict[str, Any]
```

### `get_file_info`
Gets file metadata.

```python
async def get_file_info(self, object_name: str) -> Dict[str, Any]
```

## Configuration
Configure via `.env` or environment variables:
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET_NAME`
