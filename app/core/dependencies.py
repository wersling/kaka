"""
依赖注入模块

提供 FastAPI 依赖注入函数，用于在端点中注入配置和服务
"""

from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Config, get_config
from app.db.database import get_db
from app.services.claude_service import ClaudeService
from app.services.github_service import GitHubService
from app.services.git_service import GitService
from app.services.webhook_handler import WebhookHandler


@lru_cache
def get_cached_config() -> Config:
    """
    获取缓存的配置实例（单例模式）

    使用 lru_cache 确保配置只加载一次

    Returns:
        Config: 配置实例
    """
    return get_config()


async def get_config_dependency() -> Config:
    """
    FastAPI 依赖注入：获取配置

    可以在端点中使用：
        @app.get("/")
        async def endpoint(config: Config = Depends(get_config_dependency)):
            ...

    Returns:
        Config: 配置实例
    """
    return get_cached_config()


async def get_git_service(
    config: Config = Depends(get_config_dependency),
) -> AsyncGenerator[GitService, None]:
    """
    FastAPI 依赖注入：获取 Git 服务

    Args:
        config: 配置实例

    Yields:
        GitService: Git 服务实例
    """
    from pathlib import Path

    service = GitService(repo_path=Path(config.git.repo_path))
    try:
        yield service
    finally:
        # GitService 不需要显式清理
        pass


async def get_github_service(
    config: Config = Depends(get_config_dependency),
) -> AsyncGenerator[GitHubService, None]:
    """
    FastAPI 依赖注入：获取 GitHub 服务

    Args:
        config: 配置实例

    Yields:
        GitHubService: GitHub 服务实例
    """
    service = GitHubService(
        token=config.github.token,
        repo_owner=config.github.repo_owner,
        repo_name=config.github.repo_name,
    )
    try:
        yield service
    finally:
        # GitHubService 不需要显式清理
        pass


async def get_claude_service(
    config: Config = Depends(get_config_dependency),
) -> AsyncGenerator[ClaudeService, None]:
    """
    FastAPI 依赖注入：获取 Claude 服务

    Args:
        config: 配置实例

    Yields:
        ClaudeService: Claude 服务实例
    """
    service = ClaudeService(
        claude_path=config.claude.claude_path,
        timeout=config.claude.timeout,
    )
    try:
        yield service
    finally:
        # ClaudeService 不需要显式清理
        pass


async def get_webhook_handler(
    git_service: GitService = Depends(get_git_service),
    github_service: GitHubService = Depends(get_github_service),
    claude_service: ClaudeService = Depends(get_claude_service),
    config: Config = Depends(get_config_dependency),
) -> AsyncGenerator[WebhookHandler, None]:
    """
    FastAPI 依赖注入：获取 Webhook 处理器

    Args:
        git_service: Git 服务实例
        github_service: GitHub 服务实例
        claude_service: Claude 服务实例
        config: 配置实例

    Yields:
        WebhookHandler: Webhook 处理器实例
    """
    handler = WebhookHandler(
        git_service=git_service,
        github_service=github_service,
        claude_service=claude_service,
    )
    try:
        yield handler
    finally:
        # WebhookHandler 不需要显式清理
        pass


# 导出所有依赖函数
__all__ = [
    "get_config_dependency",
    "get_git_service",
    "get_github_service",
    "get_claude_service",
    "get_webhook_handler",
    "get_db",  # 重新导出数据库依赖
]
