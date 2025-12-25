# TODO - MinIO Service

1.  **Integration Testing**: Verify with a real MinIO instance (requires running MinIO container).
2.  **MCP Tool Registration**: Create an MCP Tool (in `app/plugins/`) that exposes `upload_file` if external access is needed via MCP protocol.
3.  **Metrics**: Integrate with Prometheus/OpenTelemetry for detailed metrics beyond logs.
4.  **Environment Setup**: Ensure `.env` file is populated with actual MinIO credentials in deployment.
