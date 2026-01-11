"""
健康检查 API

提供服务健康状态检查端点
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    service: str = "kaka"
    version: str = "0.1.0"
    timestamp: str  # 改为字符串类型，使用ISO格式
    uptime_seconds: float
    checks: dict[str, Any]


class ServiceCheck(BaseModel):
    """服务检查结果"""

    healthy: bool
    message: str
    details: dict[str, Any] | None = None


# 服务启动时间
_start_time = datetime.now()


def get_uptime() -> float:
    """获取服务运行时间（秒）"""
    return (datetime.now() - _start_time).total_seconds()


async def check_config() -> ServiceCheck:
    """检查配置状态（不返回敏感信息）"""
    try:
        from app.config import get_config

        config = get_config()

        # 只返回状态，不返回敏感配置
        return ServiceCheck(
            healthy=True,
            message="配置加载成功",
            details={
                "repo_configured": True,
                "github_configured": True,
                "claude_configured": True,
            },
        )
    except Exception as e:
        logger.error(f"配置检查失败: {e}")
        return ServiceCheck(
            healthy=False,
            message=f"配置检查失败: {e}",
            details=None,
        )


async def check_git_repository() -> ServiceCheck:
    """检查 Git 仓库状态（不返回敏感路径）"""
    try:
        from app.config import get_config

        config = get_config()
        repo_path = config.repository.path

        if not repo_path.exists():
            return ServiceCheck(
                healthy=False,
                message="仓库路径不存在",
                details=None,
            )

        # 检查是否是 Git 仓库
        if not (repo_path / ".git").exists():
            return ServiceCheck(
                healthy=False,
                message="不是有效的 Git 仓库",
                details=None,
            )

        # 只返回状态，不返回实际路径
        return ServiceCheck(
            healthy=True,
            message="Git 仓库正常",
            details={"configured": True},
        )
    except Exception as e:
        logger.error(f"Git 仓库检查失败: {e}")
        return ServiceCheck(
            healthy=False,
            message=f"检查失败: {e}",
            details=None,
        )


async def check_claude_cli() -> ServiceCheck:
    """检查 Claude Code CLI"""
    try:
        import shutil

        # 查找 claude 命令
        claude_path = shutil.which("claude")

        if not claude_path:
            return ServiceCheck(
                healthy=False,
                message="Claude Code CLI 未安装",
                details={
                    "提示": "请确保 Claude Code CLI 已正确安装并添加到 PATH"
                },
            )

        # 尝试获取版本信息
        try:
            import subprocess
            result = subprocess.run(
                [claude_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip() if result.returncode == 0 else "unknown"
        except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
            version = "unknown"

        return ServiceCheck(
            healthy=True,
            message="Claude Code CLI 已安装",
            details={"path": claude_path, "version": version},
        )
    except Exception as e:
        logger.error(f"Claude CLI 检查失败: {e}")
        return ServiceCheck(
            healthy=False,
            message=f"检查失败: {e}",
            details=None,
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查服务及其依赖项的健康状态",
)
async def health_check() -> HealthResponse:
    """
    健康检查端点

    检查以下内容：
    - 配置文件是否正确加载
    - Git 仓库是否可访问
    - Claude Code CLI 是否安装
    """
    logger.debug("执行健康检查")

    # 并发执行所有检查
    import asyncio

    config_check, git_check, claude_check = await asyncio.gather(
        check_config(),
        check_git_repository(),
        check_claude_cli(),
    )

    # 汇总检查结果
    all_healthy = all(
        [
            config_check.healthy,
            git_check.healthy,
            claude_check.healthy,
        ]
    )

    checks = {
        "config": config_check.model_dump(),
        "git_repository": git_check.model_dump(),
        "claude_cli": claude_check.model_dump(),
    }

    response = HealthResponse(
        status="healthy" if all_healthy else "unhealthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=get_uptime(),
        checks=checks,
    )

    # 如果有检查失败，返回 503 状态码
    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.model_dump(),
        )

    return response


@router.get(
    "/ping",
    summary="简单检查",
    description="快速检查服务是否在线",
)
async def ping() -> dict[str, str]:
    """
    简单的 ping 端点，用于快速检查服务是否在线
    """
    return {"status": "pong", "service": "kaka"}
