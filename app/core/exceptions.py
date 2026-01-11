"""
统一异常处理模块

定义自定义异常类和错误响应格式
"""

from typing import Any, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""

    # 通用错误 (1xxx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # GitHub 相关错误 (2xxx)
    GITHUB_API_ERROR = "GITHUB_API_ERROR"
    GITHUB_RATE_LIMIT = "GITHUB_RATE_LIMIT"
    GITHUB_WEBHOOK_INVALID = "GITHUB_WEBHOOK_INVALID"

    # Git 相关错误 (3xxx)
    GIT_OPERATION_FAILED = "GIT_OPERATION_FAILED"
    GIT_REPO_NOT_FOUND = "GIT_REPO_NOT_FOUND"
    GIT_BRANCH_EXISTS = "GIT_BRANCH_EXISTS"

    # Claude 相关错误 (4xxx)
    CLAUDE_EXECUTION_FAILED = "CLAUDE_EXECUTION_FAILED"
    CLAUDE_TIMEOUT = "CLAUDE_TIMEOUT"
    CLAUDE_NOT_FOUND = "CLAUDE_NOT_FOUND"

    # 任务相关错误 (5xxx)
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_RUNNING = "TASK_ALREADY_RUNNING"
    TASK_CONCURRENT_LIMIT = "TASK_CONCURRENT_LIMIT"

    # 数据库错误 (6xxx)
    DATABASE_ERROR = "DATABASE_ERROR"


class AppException(Exception):
    """
    应用基础异常类

    所有自定义异常的基类
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        初始化异常

        Args:
            message: 错误消息
            code: 错误码
            status_code: HTTP 状态码
            details: 额外的错误详情
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式

        Returns:
            dict: 包含错误信息的字典
        """
        return {
            "error": True,
            "code": self.code.value,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


# ============================================================================
# GitHub 相关异常
# ============================================================================


class GitHubAPIError(AppException):
    """GitHub API 调用失败"""

    def __init__(
        self,
        message: str = "GitHub API 调用失败",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.GITHUB_API_ERROR,
            status_code=502,
            details=details,
        )


class GitHubRateLimitError(AppException):
    """GitHub API 速率限制"""

    def __init__(
        self,
        message: str = "GitHub API 速率限制",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.GITHUB_RATE_LIMIT,
            status_code=429,
            details=details,
        )


class GitHubWebhookInvalidError(AppException):
    """GitHub Webhook 签名验证失败"""

    def __init__(
        self,
        message: str = "Webhook 签名验证失败",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.GITHUB_WEBHOOK_INVALID,
            status_code=401,
            details=details,
        )


# ============================================================================
# Git 相关异常
# ============================================================================


class GitOperationError(AppException):
    """Git 操作失败"""

    def __init__(
        self,
        message: str = "Git 操作失败",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.GIT_OPERATION_FAILED,
            status_code=500,
            details=details,
        )


class GitRepoNotFoundError(AppException):
    """Git 仓库未找到"""

    def __init__(
        self,
        message: str = "Git 仓库未找到",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.GIT_REPO_NOT_FOUND,
            status_code=404,
            details=details,
        )


class GitBranchExistsError(AppException):
    """Git 分支已存在"""

    def __init__(
        self,
        message: str = "Git 分支已存在",
        branch_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if branch_name:
            details["branch_name"] = branch_name
        super().__init__(
            message=message,
            code=ErrorCode.GIT_BRANCH_EXISTS,
            status_code=409,
            details=details,
        )


# ============================================================================
# Claude 相关异常
# ============================================================================


class ClaudeExecutionError(AppException):
    """Claude CLI 执行失败"""

    def __init__(
        self,
        message: str = "Claude CLI 执行失败",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.CLAUDE_EXECUTION_FAILED,
            status_code=500,
            details=details,
        )


class ClaudeTimeoutError(AppException):
    """Claude CLI 执行超时"""

    def __init__(
        self,
        message: str = "Claude CLI 执行超时",
        timeout: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if timeout:
            details["timeout_seconds"] = timeout
        super().__init__(
            message=message,
            code=ErrorCode.CLAUDE_TIMEOUT,
            status_code=504,
            details=details,
        )


class ClaudeNotFoundError(AppException):
    """Claude CLI 未找到"""

    def __init__(
        self,
        message: str = "Claude CLI 未找到",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.CLAUDE_NOT_FOUND,
            status_code=500,
            details=details,
        )


# ============================================================================
# 任务相关异常
# ============================================================================


class TaskNotFoundError(AppException):
    """任务未找到"""

    def __init__(
        self,
        message: str = "任务未找到",
        task_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if task_id:
            details["task_id"] = task_id
        super().__init__(
            message=message,
            code=ErrorCode.TASK_NOT_FOUND,
            status_code=404,
            details=details,
        )


class TaskAlreadyRunningError(AppException):
    """任务已在运行中"""

    def __init__(
        self,
        message: str = "任务已在运行中",
        task_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if task_id:
            details["task_id"] = task_id
        super().__init__(
            message=message,
            code=ErrorCode.TASK_ALREADY_RUNNING,
            status_code=409,
            details=details,
        )


class TaskConcurrentLimitError(AppException):
    """达到并发任务限制"""

    def __init__(
        self,
        message: str = "达到并发任务限制",
        current: Optional[int] = None,
        max_concurrent: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if current is not None:
            details["current_running"] = current
        if max_concurrent is not None:
            details["max_concurrent"] = max_concurrent
        super().__init__(
            message=message,
            code=ErrorCode.TASK_CONCURRENT_LIMIT,
            status_code=429,
            details=details,
        )


# ============================================================================
# 数据库相关异常
# ============================================================================


class DatabaseError(AppException):
    """数据库错误"""

    def __init__(
        self,
        message: str = "数据库错误",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details=details,
        )


# ============================================================================
# 导出所有异常类
# ============================================================================

__all__ = [
    "ErrorCode",
    "AppException",
    "GitHubAPIError",
    "GitHubRateLimitError",
    "GitHubWebhookInvalidError",
    "GitOperationError",
    "GitRepoNotFoundError",
    "GitBranchExistsError",
    "ClaudeExecutionError",
    "ClaudeTimeoutError",
    "ClaudeNotFoundError",
    "TaskNotFoundError",
    "TaskAlreadyRunningError",
    "TaskConcurrentLimitError",
    "DatabaseError",
]
