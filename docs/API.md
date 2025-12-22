# API 接口文档

## 1. 基础接口

### 健康检查
- **URL**: `/health`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "status": "ok",
    "app_name": "MCP Service for Dify"
  }
  ```

## 2. MCP 协议接口

本服务实现了 MCP (Model Context Protocol) 标准。

### SSE 连接端点
- **URL**: `/mcp/sse`
- **Method**: `GET`
- **Description**: 建立 Server-Sent Events 连接。Dify 通过此接口连接服务。

### 消息处理端点
- **URL**: `/mcp/messages`
- **Method**: `POST`
- **Description**: 处理 MCP 协议消息 (JSON-RPC 2.0)。客户端通过 SSE 接收到 endpoint URL 后，会向此地址发送 POST 请求。

## 3. 已注册工具

### Echo
- **Name**: `echo_tool`
- **Description**: Echoes back the input string.
- **Parameters**:
  - `message` (string): 需要回显的消息。
