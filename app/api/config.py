"""
配置管理 API
提供配置状态检查和 Webhook URL 生成
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ConfigStatusResponse(BaseModel):
    """配置状态响应"""

    configured: bool
    missing_keys: list[str] = []
    webhook_url: Optional[str] = None
    repo_info: Optional[dict] = None


@router.get("/api/config/status", response_model=ConfigStatusResponse, summary="获取配置状态")
async def get_config_status(request: Request) -> ConfigStatusResponse:
    """
    获取当前配置状态

    返回:
        - configured: 是否已配置
        - missing_keys: 缺失的配置项
        - webhook_url: Webhook URL（如果已配置）
        - repo_info: 仓库信息（如果已配置）
    """
    try:
        from app.config import get_config

        try:
            config = get_config()
            is_configured = True
            missing_keys = []

            # 生成 Webhook URL
            from app.utils.webhook import generate_webhook_url

            webhook_url = generate_webhook_url(request)

            repo_info = {
                "repo_full_name": config.github.repo_full_name,
                "repo_path": str(config.repository.path),
                "default_branch": config.repository.default_branch,
            }

        except Exception as e:
            is_configured = False
            missing_keys = ["请检查环境变量或配置文件"]
            webhook_url = None
            repo_info = None

        return ConfigStatusResponse(
            configured=is_configured,
            missing_keys=missing_keys,
            webhook_url=webhook_url,
            repo_info=repo_info,
        )

    except Exception as e:
        logger.error(f"获取配置状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/config/webhook-url", summary="获取 Webhook URL")
async def get_webhook_url(request: Request) -> dict:
    """
    获取 Webhook URL 和 Secret

    返回:
        - url: 完整的 Webhook URL
        - secret: Webhook 密钥
    """
    try:
        from app.config import get_config
        from app.utils.webhook import generate_webhook_url

        config = get_config()

        return {"url": generate_webhook_url(request), "secret": config.github.webhook_secret}

    except Exception as e:
        logger.error(f"获取 Webhook URL 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
