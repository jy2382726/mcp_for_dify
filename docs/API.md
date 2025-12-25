# API 接口文档

## 1. 基础接口

### 健康检查
- **URL**: `/health`
- **Method**: `GET`
- **Description**: 检查服务运行状态
- **Response**:
  ```json
  {
    "status": "ok",
    "app_name": "MCP Service for Dify"
  }
  ```

## 2. REST API 接口

### 2.1 文件上传接口
- **URL**: `/api/v1/minio/upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Description**: 上传文件到 MinIO 对象存储
- **Parameters**:
  - `file` (file, required): 要上传的文件
  - `object_name` (string, optional): 对象名称，未提供则自动生成
  - `original_url` (string, optional): 文件原始 URL 地址
- **Response**:
  ```json
  {
    "object_name": "2025/12/25/uuid-filename.txt",
    "original_filename": "test.txt",
    "file_size": 1024,
    "preview_url": "http://localhost:9001/api/v1/buckets/bucket-name/objects/download?preview=true&prefix=...",
    "upload_time": "2025-12-25T10:00:00",
    "etag": "abc123",
    "original_url": "http://example.com/file.txt"
  }
  ```
- **Error Response** (400):
  ```json
  {
    "detail": "错误信息"
  }
  ```

### 2.2 文件删除接口
- **URL**: `/api/v1/minio/delete`
- **Method**: `DELETE`
- **Description**: 从 MinIO 对象存储中删除文件
- **Parameters**:
  - `object_name` (string, required, query): 要删除的对象名称
- **Response**:
  ```json
  {
    "object_name": "2025/12/25/uuid-filename.txt",
    "deleted": true,
    "delete_time": "2025-12-25T10:00:00"
  }
  ```
- **Error Response** (400):
  ```json
  {
    "detail": "文件不存在"
  }
  ```

## 3. MCP 协议接口

本服务实现了 MCP (Model Context Protocol) 标准，供 Dify 等客户端调用。

### 3.1 SSE 连接端点
- **URL**: `/mcp/sse`
- **Method**: `GET`
- **Description**: 建立 Server-Sent Events 连接。Dify 通过此接口连接服务。

### 3.2 消息处理端点
- **URL**: `/mcp/messages`
- **Method**: `POST`
- **Description**: 处理 MCP 协议消息 (JSON-RPC 2.0)。客户端通过 SSE 接收到 endpoint URL 后，会向此地址发送 POST 请求。

## 4. MCP 工具列表

通过 MCP 协议可调用的工具列表：

### 4.1 Echo 工具
- **Name**: `echo_tool`
- **Description**: 接收一个字符串并将其原样返回（带有 Echo 前缀）
- **Parameters**:
  - `message` (string, required): 需要回显的字符串消息
- **Returns**:
  ```json
  "Echo: 消息内容"
  ```

### 4.2 文本分块工具
- **Name**: `text_splitter`
- **Description**: 支持 PDF、Markdown 表格、纯文本（带预览链接）的分块处理
- **Parameters**:
  - `mode` (string, required): 分块模式，取值: `pdf` (PDF文本), `table` (Markdown表格), `image` (纯文本带图片预览)
  - `content` (string, required): 待处理的文本内容
  - `parent_block_size` (integer, optional): 父块大小上限，默认 1280
  - `sub_block_size` (integer, optional): 子块大小上限，默认 512
  - `parent_separator` (string, optional): 父块之间的分隔符，默认 `"\n\n\n\n"`
  - `sub_separator` (string, optional): 子块之间的分隔符，默认 `"\n\n\n"`
  - `preview_url` (string, optional): 当 mode=`image` 时必填的图片预览地址
- **Returns**:
  ```json
  {
    "result": "分块后的文本内容"
  }
  ```

### 4.3 MinIO 文件信息查询工具
- **Name**: `get_file_info`
- **Description**: 根据对象名称查询文件的元数据信息
- **Parameters**:
  - `object_name` (string, required): 对象存储中的对象名称（路径）
- **Returns**:
  ```json
  {
    "object_name": "2025/12/25/uuid-filename.txt",
    "size": 1024,
    "last_modified": "2025-12-25T10:00:00",
    "etag": "abc123",
    "content_type": "text/plain"
  }
  ```
- **Error Response**:
  ```json
  {
    "error": "文件不存在"
  }
  ```

### 4.4 MinIO 文件删除工具
- **Name**: `delete_file`
- **Description**: 从 MinIO 对象存储中删除指定的文件
- **Parameters**:
  - `object_name` (string, required): 要删除的对象名称（路径）
- **Returns**:
  ```json
  {
    "object_name": "2025/12/25/uuid-filename.txt",
    "deleted": true,
    "delete_time": "2025-12-25T10:00:00"
  }
  ```
- **Error Response**:
  ```json
  {
    "error": "文件不存在"
  }
  ```
