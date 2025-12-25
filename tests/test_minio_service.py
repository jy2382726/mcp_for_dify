import pytest
import asyncio
from unittest.mock import MagicMock, patch
from io import BytesIO
from datetime import datetime
from minio.error import S3Error
from app.services.minio_service import MinioService
from app.exceptions import FileValidationError, FileUploadError, FileDownloadError

# Mock settings
@pytest.fixture
def mock_settings():
    with patch("app.services.minio_service.settings") as mock:
        mock.MINIO_BUCKET_NAME = "test-bucket"
        mock.ALLOWED_EXTENSIONS = ["txt", "jpg"]
        mock.MAX_FILE_SIZE = 1024 * 1024
        mock.MINIO_CONSOLE_ENDPOINT = "localhost:9001"
        mock.MINIO_SECURE = False
        yield mock

# Mock Minio Client
@pytest.fixture
def mock_minio_client():
    with patch("app.services.minio_service.get_minio_client") as mock_get:
        mock_manager = MagicMock()
        mock_client = MagicMock()
        mock_manager.get_client.return_value = mock_client
        mock_get.return_value = mock_manager
        yield mock_client

@pytest.fixture
def service(mock_settings, mock_minio_client):
    return MinioService()

@pytest.mark.asyncio
async def test_upload_file_success(service, mock_minio_client):
    # Setup
    file_content = b"hello world"
    file_obj = BytesIO(file_content)
    filename = "test.txt"
    
    mock_result = MagicMock()
    mock_result.etag = "123456"
    mock_minio_client.put_object.return_value = mock_result
    
    # Execute
    result = await service.upload_file(file_obj, filename)
    
    # Verify
    assert result['original_filename'] == filename
    assert result['etag'] == "123456"
    assert 'object_name' in result
    
    # Verify minio call
    mock_minio_client.put_object.assert_called_once()
    args, kwargs = mock_minio_client.put_object.call_args
    assert kwargs['bucket_name'] == "test-bucket"
    assert kwargs['length'] == len(file_content)

@pytest.mark.asyncio
async def test_upload_file_validation_error(service):
    # Setup
    file_obj = BytesIO(b"")
    filename = "test.exe" # Invalid extension
    
    # Execute & Verify
    with pytest.raises(FileValidationError):
        await service.upload_file(file_obj, filename)

@pytest.mark.asyncio
async def test_get_file_info_success(service, mock_minio_client):
    # Setup
    mock_stat = MagicMock()
    mock_stat.size = 100
    mock_stat.last_modified = datetime.now()
    mock_stat.etag = "abc"
    mock_stat.content_type = "text/plain"
    mock_minio_client.stat_object.return_value = mock_stat
    
    # Execute
    info = await service.get_file_info("test.txt")
    
    # Verify
    assert info['size'] == 100
    assert info['content_type'] == "text/plain"

@pytest.mark.asyncio
async def test_delete_file_success(service, mock_minio_client):
    # Setup
    mock_minio_client.stat_object.return_value = MagicMock() # Exists
    
    # Execute
    result = await service.delete_file("test.txt")
    
    # Verify
    assert result['deleted'] is True
    mock_minio_client.remove_object.assert_called_once()

@pytest.mark.asyncio
async def test_delete_file_not_found(service, mock_minio_client):
    # Setup
    error = S3Error(code="NoSuchKey", message="Not Found", resource="/test", request_id="1", host_id="1", response="response")
    mock_minio_client.stat_object.side_effect = error
    
    # Execute & Verify
    with pytest.raises(FileDownloadError) as exc:
        await service.delete_file("test.txt")
    assert exc.value.code == "FILE_NOT_FOUND"
