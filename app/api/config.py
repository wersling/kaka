"""
配置管理 API
提供配置验证、状态检查和 Webhook URL 生成
"""

import secrets
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ConfigStatusResponse(BaseModel):
    """配置状态响应"""
    configured: bool
    missing_keys: list[str] = []
    webhook_url: Optional[str] = None
    repo_info: Optional[dict] = None


class ValidateConfigRequest(BaseModel):
    """配置验证请求"""
    github_token: str = Field(..., min_length=1)
    repo_owner: str = Field(..., min_length=1)
    repo_name: str = Field(..., min_length=1)
    repo_path: str = Field(..., min_length=1)
    anthropic_api_key: str = Field(..., min_length=1)

    @validator('github_token')
    def validate_github_token(cls, v):
        if not v.startswith('ghp_') and not v.startswith('github_pat_'):
            raise ValueError('GitHub Token 格式无效，应以 ghp_ 或 github_pat_ 开头')
        return v

    @validator('anthropic_api_key')
    def validate_anthropic_key(cls, v):
        if not v.startswith('sk-ant-'):
            raise ValueError('Anthropic API Key 格式无效，应以 sk-ant- 开头')
        return v


class SaveConfigRequest(BaseModel):
    """保存配置请求"""
    github_token: str
    repo_owner: str
    repo_name: str
    repo_path: str
    anthropic_api_key: str
    webhook_secret: Optional[str] = None


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
            repo_info=repo_info
        )

    except Exception as e:
        logger.error(f"获取配置状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/validate", summary="验证配置")
async def validate_config(req: ValidateConfigRequest) -> dict:
    """
    验证配置有效性

    验证项:
        - GitHub Token 是否有效
        - 仓库路径是否有效
        - Anthropic API Key 是否有效

    返回:
        - 验证结果字典，包含各项验证状态
    """
    results = {}

    # 1. 验证 GitHub Token
    try:
        from app.services.github_service import GitHubService

        github = GitHubService(req.github_token)
        is_valid = await github.authenticate()

        results["github_token"] = {
            "valid": is_valid,
            "message": "Token 有效" if is_valid else "Token 无效或权限不足"
        }

        if is_valid:
            # 验证仓库是否存在
            try:
                repo_exists = await github.check_repository_exists(req.repo_owner, req.repo_name)
                results["github_repository"] = {
                    "valid": repo_exists,
                    "message": f"仓库 {req.repo_owner}/{req.repo_name} 存在" if repo_exists else "仓库不存在或无访问权限"
                }
            except Exception as e:
                results["github_repository"] = {
                    "valid": False,
                    "message": f"仓库验证失败: {str(e)}"
                }

    except Exception as e:
        results["github_token"] = {"valid": False, "message": f"验证失败: {str(e)}"}

    # 2. 验证仓库路径
    try:
        from pathlib import Path

        repo_path = Path(req.repo_path).expanduser().resolve()

        if not repo_path.exists():
            results["repo_path"] = {
                "valid": False,
                "message": "路径不存在"
            }
        elif not (repo_path / ".git").exists():
            results["repo_path"] = {
                "valid": False,
                "message": "不是有效的 Git 仓库"
            }
        else:
            results["repo_path"] = {
                "valid": True,
                "message": f"有效: {repo_path}"
            }

    except Exception as e:
        results["repo_path"] = {"valid": False, "message": f"验证失败: {str(e)}"}

    # 3. 验证 Anthropic API Key
    try:
        from app.services.claude_service import ClaudeService

        claude = ClaudeService(req.anthropic_api_key)
        # 这里做简单的格式验证，实际调用会在使用时验证
        results["anthropic_api_key"] = {
            "valid": bool(req.anthropic_api_key.startswith('sk-ant-')),
            "message": "API Key 格式有效"
        }

    except Exception as e:
        results["anthropic_api_key"] = {"valid": False, "message": f"验证失败: {str(e)}"}

    return results


@router.post("/api/config/save", summary="保存配置")
async def save_config(req: SaveConfigRequest) -> dict:
    """
    保存配置到环境变量文件

    保存配置到 .env 文件，并返回成功状态
    """
    try:
        from pathlib import Path

        # 生成 Webhook Secret（如果未提供）
        if not req.webhook_secret:
            req.webhook_secret = secrets.token_urlsafe(32)

        # 读取现有的 .env 文件
        env_path = Path(".env")
        existing_lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()

        # 构建新的环境变量字典
        env_vars = {}
        for line in existing_lines:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value

        # 更新配置
        env_vars["GITHUB_TOKEN"] = req.github_token
        env_vars["GITHUB_REPO_OWNER"] = req.repo_owner
        env_vars["GITHUB_REPO_NAME"] = req.repo_name
        env_vars["REPO_PATH"] = req.repo_path
        env_vars["ANTHROPIC_API_KEY"] = req.anthropic_api_key
        env_vars["GITHUB_WEBHOOK_SECRET"] = req.webhook_secret

        # 写回文件
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# AI 开发调度服务配置\n")
            f.write("# 由配置向导自动生成\n\n")
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        logger.info("配置已保存到 .env 文件")

        return {
            "success": True,
            "message": "配置已保存",
            "webhook_secret": req.webhook_secret
        }

    except Exception as e:
        logger.error(f"保存配置失败: {e}", exc_info=True)
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

        return {
            "url": generate_webhook_url(request),
            "secret": config.github.webhook_secret
        }

    except Exception as e:
        logger.error(f"获取 Webhook URL 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/generate-secret", summary="生成 Webhook Secret")
async def generate_webhook_secret() -> dict:
    """
    生成新的 Webhook Secret

    返回一个安全的随机密钥用于 Webhook 验证
    """
    secret = secrets.token_urlsafe(32)

    return {
        "secret": secret,
        "message": "请将此密钥保存到 .env 文件的 GITHUB_WEBHOOK_SECRET 变量中"
    }
