from app.core.logger import logger

class EchoService:
    """
    回显服务业务逻辑层
    """
    
    async def process_echo(self, message: str) -> str:
        """
        处理回显请求
        
        Args:
            message (str): 输入消息
            
        Returns:
            str: 处理后的消息
        """
        logger.debug(f"Processing echo for message: {message}")
        return f"Echo: {message}"

# 单例实例
echo_service = EchoService()
