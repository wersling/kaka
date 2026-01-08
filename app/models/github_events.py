"""
GitHub Webhook 事件数据模型

定义 GitHub Webhook 事件的数据结构
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub 用户信息"""

    login: str
    id: int
    avatar_url: str
    type: str = "User"


class GitHubLabel(BaseModel):
    """GitHub 标签信息"""

    id: int
    node_id: str
    name: str
    color: str
    default: bool = False


class GitHubIssue(BaseModel):
    """GitHub Issue 信息"""

    id: int
    node_id: str
    number: int
    title: str
    body: Optional[str] = None
    html_url: str
    state: str
    locked: bool = False
    labels: list[GitHubLabel] = Field(default_factory=list)
    user: GitHubUser
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None


class GitHubComment(BaseModel):
    """GitHub 评论信息"""

    id: int
    node_id: str
    user: GitHubUser
    created_at: datetime
    updated_at: datetime
    body: str
    html_url: str


class IssueEvent(BaseModel):
    """Issue 事件（labeled, unlabeled, opened, edited 等）"""

    action: str  # labeled, unlabeled, opened, edited, closed, reopened 等
    issue: GitHubIssue
    label: Optional[GitHubLabel] = None  # 仅当 action 为 labeled/unlabeled 时存在
    changes: Optional[dict[str, Any]] = None  # 仅当 action 为 edited 时存在
    repository: Optional[dict[str, Any]] = None
    sender: GitHubUser


class IssueCommentEvent(BaseModel):
    """Issue 评论事件"""

    action: str  # created, edited, deleted
    issue: GitHubIssue
    comment: GitHubComment
    repository: Optional[dict[str, Any]] = None
    sender: GitHubUser


class WebhookPayload(BaseModel):
    """Webhook 载荷基础模型"""

    # GitHub 通用字段
    event_type: str = Field(..., alias="X-GitHub-Event")
    delivery_id: str = Field(..., alias="X-GitHub-Delivery")
    signature_256: Optional[str] = Field(None, alias="X-Hub-Signature-256")

    # 事件数据（根据事件类型，将是 IssueEvent 或 IssueCommentEvent）
    data: dict[str, Any]


class TriggerCondition(BaseModel):
    """触发条件检查结果"""

    should_trigger: bool
    trigger_type: Optional[str] = None  # "label" 或 "command"
    trigger_value: Optional[str] = None  # 标签名或命令文本
    issue: Optional[GitHubIssue] = None


class DevelopmentTask(BaseModel):
    """开发任务信息"""

    task_id: str
    issue_number: int
    issue_title: str
    issue_url: str
    issue_body: str
    branch_name: str
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # PR 信息
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None


class TaskResult(BaseModel):
    """任务执行结果"""

    success: bool
    task_id: str
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None  # 秒
    details: dict[str, Any] = Field(default_factory=dict)


class RepositoryInfo(BaseModel):
    """仓库信息"""

    id: int
    node_id: str
    name: str
    full_name: str
    private: bool
    owner: GitHubUser
    html_url: str
    description: Optional[str] = None
    default_branch: str = "main"
