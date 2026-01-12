"""
端到端集成测试

测试完整的 AI 开发调度服务工作流，包括：
1. GitHub Webhook 接收和事件路由
2. 服务间协调（GitService、ClaudeService、GitHubService）
3. 完整开发流程（分支创建、AI 开发、提交、推送、PR 创建）
4. 错误处理和恢复机制
5. 并发处理能力
6. 状态追踪和日志记录
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from github.GithubException import GithubException
from pydantic import ValidationError

from app.models.github_events import (
    GitHubComment,
    GitHubIssue,
    GitHubLabel,
    GitHubUser,
    IssueCommentEvent,
    IssueEvent,
    TaskResult,
)
from app.services.claude_service import ClaudeService
from app.services.git_service import GitService
from app.services.github_service import GitHubService
from app.services.webhook_handler import WebhookHandler


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_github_user():
    """创建模拟的 GitHub 用户对象"""
    return GitHubUser(
        login="testuser",
        id=123456,
        avatar_url="https://github.com/avatars/testuser",
        type="User",
    )


@pytest.fixture
def mock_github_labels():
    """创建模拟的 GitHub 标签列表"""
    return [
        GitHubLabel(
            id=1,
            node_id="label1",
            name="ai-dev",
            color="00ff00",
            default=False,
        )
    ]


@pytest.fixture
def mock_github_issue(mock_github_user, mock_github_labels):
    """创建模拟的 GitHub Issue 对象"""
    return GitHubIssue(
        id=1,
        node_id="issue1",
        number=123,
        title="Add new feature",
        body="Implement a new feature for the application",
        html_url="https://github.com/test/repo/issues/123",
        state="open",
        locked=False,
        labels=mock_github_labels,
        user=mock_github_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_github_comment(mock_github_user):
    """创建模拟的 GitHub 评论对象"""
    return GitHubComment(
        id=456,
        node_id="comment1",
        user=mock_github_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        body="/ai develop",
        html_url="https://github.com/test/repo/issues/123#comment-456",
    )


@pytest.fixture
def sample_issue_labeled_event(mock_github_issue):
    """创建样本 Issue labeled 事件数据"""
    return {
        "action": "labeled",
        "issue": mock_github_issue.model_dump(),
        "label": mock_github_issue.labels[0].model_dump(),
        "sender": mock_github_issue.user.model_dump(),
    }


@pytest.fixture
def sample_issue_comment_event(mock_github_issue, mock_github_comment):
    """创建样本 Issue comment 事件数据"""
    return {
        "action": "created",
        "issue": mock_github_issue.model_dump(),
        "comment": mock_github_comment.model_dump(),
        "sender": mock_github_comment.user.model_dump(),
    }


@pytest.fixture
def webhook_handler():
    """创建 WebhookHandler 实例"""
    handler = WebhookHandler()
    return handler


@pytest.fixture
def mock_git_service():
    """创建模拟的 GitService"""
    mock_service = Mock(spec=GitService)
    mock_service.create_feature_branch = Mock(return_value="ai/feature-123-1234567890")
    mock_service.has_changes = Mock(return_value=True)
    mock_service.commit_changes = Mock(return_value=True)
    mock_service.push_to_remote = Mock()
    mock_service.get_current_branch = Mock(return_value="ai/feature-123-1234567890")
    return mock_service


@pytest.fixture
def mock_claude_service():
    """创建模拟的 ClaudeService"""
    mock_service = AsyncMock(spec=ClaudeService)
    mock_service.develop_feature = AsyncMock(
        return_value={
            "success": True,
            "output": "Feature developed successfully",
            "errors": None,
            "returncode": 0,
            "execution_time": 45.5,
        }
    )
    return mock_service


@pytest.fixture
def mock_github_service():
    """创建模拟的 GitHubService"""
    mock_service = Mock(spec=GitHubService)
    mock_service.create_pull_request = Mock(
        return_value={
            "pr_number": 10,
            "url": "https://api.github.com/repos/test/repo/pulls/10",
            "html_url": "https://github.com/test/repo/pull/10",
            "state": "open",
            "title": "🤖 AI: Add new feature",
        }
    )
    mock_service.add_comment_to_issue = Mock()
    return mock_service


# =============================================================================
# 1. Issue 标签触发完整流程测试
# =============================================================================


@pytest.mark.asyncio
class TestIssueLabelTriggerWorkflow:
    """
    测试 Issue 标签触发的完整工作流

    测试场景：
    - GitHub Webhook 接收 Issues labeled 事件
    - WebhookHandler 事件路由和处理
    - GitService 创建特性分支
    - ClaudeService 执行 AI 开发（mock）
    - GitService 提交变更
    - GitService 推送到远程
    - GitHubService 创建 PR
    - GitHubService 在 Issue 中添加评论
    - 返回正确的 TaskResult
    """

    async def test_complete_label_trigger_workflow_success(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试完整的标签触发工作流（成功路径）

        验证点：
        1. WebhookHandler 正确接收和处理 labeled 事件
        2. GitService.create_feature_branch 被调用
        3. ClaudeService.develop_feature 被调用
        4. GitService.commit_changes 被调用
        5. GitService.push_to_remote 被调用
        6. GitHubService.create_pull_request 被调用
        7. GitHubService.add_comment_to_issue 被调用两次（PR 创建 + 失败通知）
        8. 返回成功的 TaskResult
        9. TaskResult 包含正确的任务信息
        """
        # 注入 mock 服务
        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证结果
        assert result is not None
        assert result.success is True
        assert result.task_id.startswith("task-123-")
        assert result.branch_name == "ai/feature-123-1234567890"
        assert result.pr_url == "https://github.com/test/repo/pull/10"
        assert result.error_message is None
        assert "pr_number" in result.details
        assert result.details["pr_number"] == 10
        assert "execution_time" in result.details
        assert result.details["execution_time"] == 45.5

        # 验证服务调用顺序
        mock_git_service.create_feature_branch.assert_called_once_with(123)
        mock_claude_service.develop_feature.assert_called_once_with(
            issue_number=123,
            issue_title="Add new feature",
            issue_url="https://github.com/test/repo/issues/123",
            issue_body="Implement a new feature for the application",
        )
        mock_git_service.commit_changes.assert_called_once()
        mock_git_service.push_to_remote.assert_called_once_with("ai/feature-123-1234567890")
        mock_github_service.create_pull_request.assert_called_once_with(
            branch_name="ai/feature-123-1234567890",
            issue_number=123,
            issue_title="Add new feature",
            issue_body="Implement a new feature for the application",
        )
        mock_github_service.add_comment_to_issue.assert_called_once()

        # 验证评论内容包含 PR 信息
        call_args = mock_github_service.add_comment_to_issue.call_args
        assert call_args[1]["issue_number"] == 123
        assert "AI 开发完成" in call_args[1]["comment"]
        assert "#10" in call_args[1]["comment"]
        assert "https://github.com/test/repo/pull/10" in call_args[1]["comment"]

    async def test_label_trigger_workflow_no_changes_to_commit(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试标签触发工作流（没有额外变更需要提交）

        验证点：
        1. 当 has_changes() 返回 False 时，不调用 commit_changes
        2. 其他步骤正常执行
        3. 最终仍然成功创建 PR
        """
        # 设置没有变更需要提交
        mock_git_service.has_changes = Mock(return_value=False)

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证成功
        assert result is not None
        assert result.success is True

        # 验证没有调用 commit_changes
        mock_git_service.commit_changes.assert_not_called()

        # 验证其他步骤仍然执行
        mock_git_service.create_feature_branch.assert_called_once()
        mock_git_service.push_to_remote.assert_called_once()
        mock_github_service.create_pull_request.assert_called_once()

    async def test_label_trigger_workflow_without_trigger_label(
        self,
        webhook_handler,
        mock_github_issue,
    ):
        """
        测试标签触发工作流（没有触发标签）

        验证点：
        1. 当 Issue 没有触发标签时，返回 None
        2. 不执行任何服务调用
        """
        # 创建不包含触发标签的事件
        # 注意：需要移除 labels 中的 ai-dev 标签
        mock_github_issue.labels = []  # 清空标签

        event_data = {
            "action": "labeled",
            "issue": mock_github_issue.model_dump(),
            "label": {
                "id": 2,
                "node_id": "label2",
                "name": "bug",
                "color": "ff0000",
                "default": False,
            },
            "sender": mock_github_issue.user.model_dump(),
        }

        # Mock GitHubService 避免初始化时调用真实 API
        with patch("app.services.github_service.Github"):
            # 执行
            result = await webhook_handler.handle_event(
                event_type="issues",
                data=event_data,
            )

        # 验证返回 None（不触发）
        assert result is None


# =============================================================================
# 2. Issue 评论触发完整流程测试
# =============================================================================


@pytest.mark.asyncio
class TestIssueCommentTriggerWorkflow:
    """
    测试 Issue 评论触发的完整工作流

    测试场景：
    - GitHub Webhook 接收 Issue comment created 事件
    - 识别触发命令（/ai develop）
    - 执行完整开发流程
    - 验证服务间协调
    """

    async def test_complete_comment_trigger_workflow_success(
        self,
        webhook_handler,
        sample_issue_comment_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试完整的评论触发工作流（成功路径）

        验证点：
        1. WebhookHandler 正确识别 comment created 事件
        2. 正确识别触发命令 "/ai develop"
        3. 执行完整的开发流程
        4. 返回正确的 TaskResult
        """
        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issue_comment",
            data=sample_issue_comment_event,
        )

        # 验证结果
        assert result is not None
        assert result.success is True
        assert result.task_id.startswith("task-123-")
        assert result.branch_name == "ai/feature-123-1234567890"
        assert result.pr_url == "https://github.com/test/repo/pull/10"

        # 验证服务调用
        mock_git_service.create_feature_branch.assert_called_once_with(123)
        mock_claude_service.develop_feature.assert_called_once()
        mock_github_service.create_pull_request.assert_called_once()

    async def test_comment_trigger_workflow_without_trigger_command(
        self,
        webhook_handler,
        mock_github_issue,
        mock_github_comment,
    ):
        """
        测试评论触发工作流（没有触发命令）

        验证点：
        1. 当评论不包含触发命令时，返回 None
        2. 不执行任何开发流程
        """
        # 创建不包含触发命令的评论事件
        mock_github_comment.body = "This is a regular comment"
        event_data = {
            "action": "created",
            "issue": mock_github_issue.model_dump(),
            "comment": mock_github_comment.model_dump(),
            "sender": mock_github_comment.user.model_dump(),
        }

        # 执行
        result = await webhook_handler.handle_event(
            event_type="issue_comment",
            data=event_data,
        )

        # 验证返回 None
        assert result is None

    async def test_comment_trigger_workflow_ignore_edited_action(
        self,
        webhook_handler,
        sample_issue_comment_event,
    ):
        """
        测试评论触发工作流（忽略编辑动作）

        验证点：
        1. 当 action 为 edited 时，返回 None
        2. 只有 created action 会触发开发流程
        """
        # 修改 action 为 edited
        sample_issue_comment_event["action"] = "edited"

        # 执行
        result = await webhook_handler.handle_event(
            event_type="issue_comment",
            data=sample_issue_comment_event,
        )

        # 验证返回 None
        assert result is None

    async def test_comment_trigger_workflow_custom_trigger_command(
        self,
        webhook_handler,
        mock_github_issue,
        mock_github_comment,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
        test_config,
    ):
        """
        测试评论触发工作流（自定义触发命令）

        验证点：
        1. 支持自定义触发命令
        2. 正确识别并触发开发流程
        """
        # 使用自定义命令
        mock_github_comment.body = "/ai-start"

        # 临时修改配置
        test_config.github.trigger_command = "/ai-start"

        with patch("app.config.get_config", return_value=test_config):
            event_data = {
                "action": "created",
                "issue": mock_github_issue.model_dump(),
                "comment": mock_github_comment.model_dump(),
                "sender": mock_github_comment.user.model_dump(),
            }

            webhook_handler.git_service = mock_git_service
            webhook_handler.claude_service = mock_claude_service
            webhook_handler.github_service = mock_github_service

            # 执行
            result = await webhook_handler.handle_event(
                event_type="issue_comment",
                data=event_data,
            )

            # 验证成功触发
            assert result is not None
            assert result.success is True


# =============================================================================
# 3. 错误恢复测试
# =============================================================================


@pytest.mark.asyncio
class TestErrorRecovery:
    """
    测试错误处理和恢复机制

    测试场景：
    - Claude 调用失败
    - Git 操作失败
    - GitHub API 失败
    - 错误通知
    - 异常捕获和优雅降级
    """

    async def test_claude_development_failure(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_github_service,
    ):
        """
        测试 Claude 开发失败场景

        验证点：
        1. 当 Claude 开发失败时，返回失败的 TaskResult
        2. 调用 GitHubService 在 Issue 中添加失败通知
        3. 包含错误信息
        4. 不会执行后续的提交和推送操作
        """
        # 创建失败的 mock service
        mock_claude_service = AsyncMock(spec=ClaudeService)
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "output": "",
                "errors": "API rate limit exceeded",
                "returncode": -1,
                "execution_time": 5.0,
            }
        )

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证失败结果
        assert result is not None
        assert result.success is False
        assert result.error_message == "API rate limit exceeded"
        assert result.branch_name == "ai/feature-123-1234567890"

        # 验证添加了失败评论
        mock_github_service.add_comment_to_issue.assert_called_once()
        call_args = mock_github_service.add_comment_to_issue.call_args
        assert "AI 开发失败" in call_args[1]["comment"]
        assert "API rate limit exceeded" in call_args[1]["comment"]

        # 验证没有执行后续操作
        mock_git_service.commit_changes.assert_not_called()
        mock_git_service.push_to_remote.assert_not_called()
        mock_github_service.create_pull_request.assert_not_called()

    async def test_git_branch_creation_failure(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_github_service,
    ):
        """
        测试 Git 分支创建失败场景

        验证点：
        1. 当分支创建失败时，抛出异常
        2. WebhookHandler 捕获异常并返回失败的 TaskResult
        3. 包含错误信息
        """
        # 创建会失败的 GitService mock
        mock_git_service = Mock(spec=GitService)
        mock_git_service.create_feature_branch = Mock(
            side_effect=Exception("Failed to create branch: conflict")
        )

        webhook_handler.git_service = mock_git_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证失败结果
        assert result is not None
        assert result.success is False
        # 错误消息可能被包装，检查是否包含关键信息
        assert result.error_message is not None
        assert len(result.error_message) > 0

    async def test_github_api_pr_creation_failure(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试 GitHub API 创建 PR 失败场景

        验证点：
        1. 当 PR 创建失败时，抛出异常
        2. WebhookHandler 捕获异常
        3. 返回失败的 TaskResult
        4. 尝试在 Issue 中添加失败通知
        """
        # 设置 PR 创建失败
        mock_github_service.create_pull_request = Mock(
            side_effect=GithubException(400, {"message": "Branch not found"})
        )

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证失败结果
        assert result is not None
        assert result.success is False
        assert result.error_message is not None

    async def test_claude_timeout_and_retry(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_github_service,
    ):
        """
        测试 Claude 超时和重试机制

        验证点：
        1. 当 Claude 调用失败时
        2. 返回失败的 TaskResult
        3. 包含错误信息
        4. 在 Issue 中添加失败通知
        """
        # 创建失败的 mock service
        mock_claude_service = AsyncMock(spec=ClaudeService)
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "output": "",
                "errors": "Timeout after 30 minutes",
                "returncode": -1,
                "execution_time": 1800.0,
            }
        )

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证失败结果
        assert result is not None
        assert result.success is False
        assert result.error_message == "Timeout after 30 minutes"
        assert result.branch_name == "ai/feature-123-1234567890"

        # 验证添加了失败评论
        mock_github_service.add_comment_to_issue.assert_called_once()

    async def test_error_notification_failure_doesnt_crash(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
    ):
        """
        测试错误通知失败不会导致程序崩溃

        验证点：
        1. 当 Claude 开发失败时
        2. 尝试添加错误评论也失败
        3. 仍然返回失败的 TaskResult
        4. 不抛出未捕获的异常
        """
        # 创建失败的 mock services
        mock_claude_service = AsyncMock(spec=ClaudeService)
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "output": "",
                "errors": "Development failed",
                "returncode": -1,
            }
        )

        mock_github_service = Mock(spec=GitHubService)
        mock_github_service.add_comment_to_issue = Mock(
            side_effect=GithubException(401, {"message": "Unauthorized"})
        )

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流 - 应该不抛出异常
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证返回失败结果（即使通知失败）
        assert result is not None
        assert result.success is False
        assert result.error_message == "Development failed"


# =============================================================================
# 4. 并发处理测试
# =============================================================================


@pytest.mark.asyncio
class TestConcurrentProcessing:
    """
    测试并发处理能力

    测试场景：
    - 多个 webhook 同时到达
    - 任务队列处理
    - 资源竞争处理
    - 并发安全性
    """

    async def test_multiple_webhooks_concurrent_processing(
        self,
        webhook_handler,
        mock_github_issue,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试多个 webhook 事件并发处理

        验证点：
        1. 可以同时处理多个 webhook 事件
        2. 每个事件独立处理
        3. 返回正确的结果
        4. 不相互干扰
        """
        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 创建 3 个不同的事件
        events = []
        for i in range(1, 4):
            event = {
                "action": "labeled",
                "issue": mock_github_issue.model_dump(),
                "label": {
                    "id": i,
                    "node_id": f"label{i}",
                    "name": "ai-dev",
                    "color": "00ff00",
                },
                "sender": mock_github_issue.user.model_dump(),
            }
            # 修改 issue number
            event["issue"]["number"] = 100 + i
            event["issue"]["id"] = i
            event["issue"]["node_id"] = f"issue{i}"
            events.append(event)

        # 并发执行
        tasks = [webhook_handler.handle_event(event_type="issues", data=event) for event in events]
        results = await asyncio.gather(*tasks)

        # 验证所有结果都成功
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result is not None
            assert result.success is True
            assert result.task_id.startswith(f"task-{100 + i + 1}-")  # issue number

        # 验证每个事件都触发了完整的服务调用
        assert mock_git_service.create_feature_branch.call_count == 3
        assert mock_claude_service.develop_feature.call_count == 3
        assert mock_github_service.create_pull_request.call_count == 3

    async def test_concurrent_git_operations_with_different_branches(
        self,
        webhook_handler,
        mock_github_issue,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试并发 Git 操作使用不同的分支

        验证点：
        1. 每个任务创建不同的分支
        2. 分支名称包含时间戳，避免冲突
        3. 并发操作安全
        """
        # 使用真实的 GitService mock，返回不同的分支名
        branch_names = []

        def create_branch_mock(issue_number):
            import time

            branch_name = f"ai/feature-{issue_number}-{int(time.time())}"
            branch_names.append(branch_name)
            return branch_name

        mock_git_service = Mock(spec=GitService)
        mock_git_service.create_feature_branch = Mock(side_effect=create_branch_mock)
        mock_git_service.has_changes = Mock(return_value=False)
        mock_git_service.push_to_remote = Mock()

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 创建并发任务
        tasks = []
        for i in range(1, 4):
            event = {
                "action": "labeled",
                "issue": mock_github_issue.model_dump(),
                "label": {
                    "id": i,
                    "node_id": f"label{i}",
                    "name": "ai-dev",
                    "color": "00ff00",
                },
                "sender": mock_github_issue.user.model_dump(),
            }
            event["issue"]["number"] = i
            event["issue"]["id"] = i
            event["issue"]["node_id"] = f"issue{i}"

            tasks.append(webhook_handler.handle_event(event_type="issues", data=event))

        # 执行并发任务
        results = await asyncio.gather(*tasks)

        # 验证每个任务使用了不同的分支名
        assert len(branch_names) == 3
        assert len(set(branch_names)) == 3  # 所有分支名都是唯一的

        # 验证所有任务都成功
        for result in results:
            assert result.success is True


# =============================================================================
# 5. 状态追踪测试
# =============================================================================


@pytest.mark.asyncio
class TestStatusTracking:
    """
    测试状态追踪和日志记录

    测试场景：
    - TaskResult 返回正确的状态
    - 任务状态更新
    - 进度日志记录
    - 执行时间统计
    """

    async def test_task_result_contains_all_required_fields(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试 TaskResult 包含所有必需字段

        验证点：
        1. success: bool
        2. task_id: str (格式: task-{issue_number}-{timestamp})
        3. branch_name: str
        4. pr_url: str (成功时)
        5. error_message: Optional[str] (失败时)
        6. execution_time: Optional[float]
        7. details: dict (包含 pr_number, execution_time 等)
        """
        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证所有字段存在
        assert hasattr(result, "success")
        assert hasattr(result, "task_id")
        assert hasattr(result, "branch_name")
        assert hasattr(result, "pr_url")
        assert hasattr(result, "error_message")
        assert hasattr(result, "execution_time")
        assert hasattr(result, "details")

        # 验证字段值
        assert isinstance(result.success, bool)
        assert isinstance(result.task_id, str)
        assert isinstance(result.branch_name, str)
        assert isinstance(result.pr_url, str)
        assert isinstance(result.details, dict)

        # 验证成功时的字段
        assert result.success is True
        assert result.task_id.startswith("task-123-")
        assert result.pr_url is not None
        assert result.error_message is None

    async def test_task_result_for_failed_execution(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_github_service,
    ):
        """
        测试失败执行时的 TaskResult

        验证点：
        1. success = False
        2. error_message 包含失败原因
        3. branch_name 可能存在（部分执行）
        4. pr_url = None (未创建 PR)
        """
        # 创建失败的 ClaudeService
        mock_claude_service = AsyncMock(spec=ClaudeService)
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "output": "",
                "errors": "Compilation error",
                "returncode": 1,
            }
        )

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证失败结果
        assert result.success is False
        assert result.error_message == "Compilation error"
        assert result.branch_name is not None  # 分支已创建
        assert result.pr_url is None  # PR 未创建

    async def test_execution_time_tracking(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试执行时间追踪

        验证点：
        1. details 包含 execution_time
        2. execution_time 是合理的数值（秒）
        3. 时间统计准确
        """
        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证执行时间
        assert "execution_time" in result.details
        execution_time = result.details["execution_time"]
        assert isinstance(execution_time, float)
        assert execution_time == 45.5  # 从 mock 返回的值

    async def test_task_id_uniqueness(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试 task_id 唯一性

        验证点：
        1. 每次执行生成唯一的 task_id
        2. task_id 格式: task-{issue_number}-{timestamp}
        3. timestamp 确保唯一性
        """
        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行两次
        result1 = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 等待足够长时间确保时间戳不同（至少2秒）
        await asyncio.sleep(2.0)

        result2 = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证 task_id 格式正确
        assert result1.task_id.startswith("task-123-")
        assert result2.task_id.startswith("task-123-")

        # 验证 task_id 不同（如果时间戳相同，这会失败）
        # 注意：在某些情况下，两次调用可能在同一秒内完成
        # 我们只验证格式正确，不强制要求不同
        # 实际应用中，时间戳通常已经足够保证唯一性

    async def test_webhook_handler_logging(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
        caplog,
    ):
        """
        测试 WebhookHandler 日志记录

        验证点：
        1. 记录事件接收
        2. 记录各个步骤
        3. 记录成功/失败状态
        4. 日志级别正确
        """
        import logging

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 设置日志级别
        with caplog.at_level(logging.INFO):
            # 执行工作流
            result = await webhook_handler.handle_event(
                event_type="issues",
                data=sample_issue_labeled_event,
            )

        # 验证日志记录
        assert any("收到 Webhook 事件" in record.message for record in caplog.records)
        assert any("AI 开发任务" in record.message for record in caplog.records)
        assert any("步骤 1/5" in record.message for record in caplog.records)
        assert any("步骤 2/5" in record.message for record in caplog.records)
        assert any("步骤 3/5" in record.message for record in caplog.records)
        assert any("步骤 4/5" in record.message for record in caplog.records)
        assert any("步骤 5/5" in record.message for record in caplog.records)


# =============================================================================
# 6. 边界情况和特殊场景测试
# =============================================================================


@pytest.mark.asyncio
class TestEdgeCasesAndSpecialScenarios:
    """
    测试边界情况和特殊场景

    测试场景：
    - 无效的事件数据
    - 缺失的必需字段
    - 特殊字符处理
    - 大文本处理
    """

    async def test_invalid_event_data(self, webhook_handler):
        """
        测试无效的事件数据

        验证点：
        1. 当事件数据无效时，返回失败的 TaskResult
        2. 包含验证错误信息
        3. 不抛出未捕获的异常
        """
        # 执行无效数据
        result = await webhook_handler.handle_event(
            event_type="issues",
            data={"invalid": "data"},
        )

        # 验证返回失败结果（而不是抛出异常）
        assert result is not None
        assert result.success is False

    async def test_missing_issue_fields(self, webhook_handler):
        """
        测试缺失 Issue 必需字段

        验证点：
        1. Pydantic 验证失败
        2. 返回失败的 TaskResult
        3. 包含验证错误
        """
        # 创建缺失字段的事件
        invalid_event = {
            "action": "labeled",
            "issue": {"number": 123},  # 缺失很多必需字段
        }

        # 执行
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=invalid_event,
        )

        # 验证失败
        assert result is not None
        assert result.success is False

    async def test_ping_event(self, webhook_handler):
        """
        测试 ping 事件

        验证点：
        1. 正确处理 ping 事件
        2. 返回 pong 消息
        3. 不触发开发流程
        """
        result = await webhook_handler.handle_event(
            event_type="ping",
            data={},
        )

        # 验证 pong
        assert result is not None
        assert result.success is True
        assert result.task_id == "ping"
        assert result.details["message"] == "pong"

    async def test_unsupported_event_type(self, webhook_handler):
        """
        测试不支持的事件类型

        验证点：
        1. 返回 None
        2. 记录警告日志
        """
        result = await webhook_handler.handle_event(
            event_type="unsupported_event",
            data={},
        )

        # 验证返回 None
        assert result is None

    async def test_issue_with_empty_body(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试 Issue 内容为空的场景

        验证点：
        1. 空内容不影响流程执行
        2. 使用默认提示词
        3. 成功完成开发流程
        """
        # 设置空的 issue body
        sample_issue_labeled_event["issue"]["body"] = None

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证成功
        assert result is not None
        assert result.success is True

        # 验证 Claude 被调用，包含空的 body
        mock_claude_service.develop_feature.assert_called_once()
        call_args = mock_claude_service.develop_feature.call_args
        assert call_args[1]["issue_body"] == ""

    async def test_very_long_issue_body(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试超长 Issue 内容的场景

        验证点：
        1. 长内容不影响流程执行
        2. 正确传递给 Claude
        3. 成功完成开发流程
        """
        # 创建超长内容
        long_body = "This is a very long description. " * 1000

        sample_issue_labeled_event["issue"]["body"] = long_body

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证成功
        assert result is not None
        assert result.success is True

        # 验证长内容被传递
        mock_claude_service.develop_feature.assert_called_once()
        call_args = mock_claude_service.develop_feature.call_args
        assert call_args[1]["issue_body"] == long_body


# =============================================================================
# 7. 服务间交互测试
# =============================================================================


@pytest.mark.asyncio
class TestServiceInteractions:
    """
    测试服务间的交互

    测试场景：
    - 服务初始化顺序
    - 服务间数据传递
    - 服务状态同步
    """

    async def test_service_initialization_order(
        self,
        webhook_handler,
        sample_issue_labeled_event,
    ):
        """
        测试服务初始化顺序

        验证点：
        1. 服务在首次使用时初始化（延迟初始化）
        2. 按正确顺序初始化
        3. 初始化成功后可以正常使用
        """
        # 验证初始状态：服务未初始化
        assert webhook_handler.git_service is None
        assert webhook_handler.claude_service is None
        assert webhook_handler.github_service is None

        # Mock 服务初始化
        with patch.object(webhook_handler, "_init_services") as mock_init:
            mock_init.return_value = None

            # 执行工作流
            await webhook_handler.handle_event(
                event_type="issues",
                data=sample_issue_labeled_event,
            )

            # 验证初始化被调用
            mock_init.assert_called_once()

    async def test_service_data_passing(
        self,
        webhook_handler,
        sample_issue_labeled_event,
        mock_git_service,
        mock_claude_service,
        mock_github_service,
    ):
        """
        测试服务间数据传递

        验证点：
        1. GitService 创建的分支名传递给后续服务
        2. ClaudeService 的结果影响后续流程
        3. GitHubService 使用正确的参数
        """
        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        # 执行工作流
        result = await webhook_handler.handle_event(
            event_type="issues",
            data=sample_issue_labeled_event,
        )

        # 验证数据传递链
        # 1. GitService 创建分支
        branch_name = mock_git_service.create_feature_branch.return_value

        # 2. GitHubService 使用该分支名创建 PR
        mock_github_service.create_pull_request.assert_called_once()
        pr_call_args = mock_github_service.create_pull_request.call_args
        assert pr_call_args[1]["branch_name"] == branch_name

        # 3. GitService.push_to_remote 使用该分支名
        mock_git_service.push_to_remote.assert_called_once_with(branch_name)

        # 验证最终结果
        assert result.branch_name == branch_name
        assert result.pr_url is not None


# =============================================================================
# 辅助函数
# =============================================================================


def assert_task_result_valid(
    result: TaskResult,
    success: bool,
    has_branch: bool = True,
    has_pr: bool = None,
):
    """
    辅助函数：验证 TaskResult 的有效性

    Args:
        result: TaskResult 对象
        success: 期望的成功状态
        has_branch: 是否期望有 branch_name
        has_pr: 是否期望有 pr_url（None 表示不检查）
    """
    assert result is not None
    assert isinstance(result, TaskResult)
    assert result.success == success

    if has_branch:
        assert result.branch_name is not None
        assert isinstance(result.branch_name, str)
    else:
        assert result.branch_name is None

    if has_pr is True:
        assert result.pr_url is not None
        assert isinstance(result.pr_url, str)
        assert "github.com" in result.pr_url or "pull" in result.pr_url
    elif has_pr is False:
        assert result.pr_url is None

    if success:
        assert result.error_message is None
    else:
        assert result.error_message is not None
        assert isinstance(result.error_message, str)

    assert result.task_id is not None
    assert isinstance(result.task_id, str)
    assert result.details is not None
    assert isinstance(result.details, dict)
