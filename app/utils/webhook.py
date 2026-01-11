"""
Webhook 工具函数
"""

from fastapi import Request


def generate_webhook_url(request: Request) -> str:
    """
    生成 Webhook URL

    根据请求自动生成完整的 Webhook URL

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 完整的 Webhook URL
    """
    # 获取协议（http 或 https）
    scheme = request.url.scheme

    # 获取主机名
    host = request.headers.get("host", "localhost:8000")

    # 构建 Webhook URL
    webhook_url = f"{scheme}://{host}/webhook/github"

    return webhook_url
