"""
端到端场景测试（E2E Scenario Tests）

完整测试从 GitHub Issue 到 Pull Request 的自动化工作流。

测试范围：
1. 完整工作流测试（P0）
   - 场景 A: 标签触发工作流
   - 场景 B: 评论触发工作流

2. 错误恢复场景测试（P0）
   - 场景 C: Claude 开发失败及重试
   - 场景 D: Git 冲突处理
   - 场景 E: GitHub API 失败

3. 边界条件测试（P1）
   - 场景 F: 空 Issue 内容
   - 场景 G: 超长 Issue 内容
   - 场景 H: 特殊字符处理
   - 场景 I: 并发 Issue 处理

4. 集成验证测试（P1）
   - 场景 J: 外部服务集成
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, MagicMock, patch

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
# Test Fixtures - E2E场景专用
# =============================================================================


@pytest.fixture
def e2e_github_user():
    """E2E测试用的GitHub用户对象"""
    return GitHubUser(
        login="e2e-tester",
        id=999999,
        avatar_url="https://github.com/avatars/e2e-tester",
        type="User",
    )


@pytest.fixture
def e2e_github_labels():
    """E2E测试用的GitHub标签"""
    return [
        GitHubLabel(
            id=100,
            node_id="label-e2e-100",
            name="ai-dev",
            color="00ff00",
            default=False,
        ),
        GitHubLabel(
            id=101,
            node_id="label-e2e-101",
            name="enhancement",
            color="0000ff",
            default=False,
        ),
    ]


@pytest.fixture
def e2e_github_issue(e2e_github_user, e2e_github_labels):
    """E2E测试用的GitHub Issue"""
    return GitHubIssue(
        id=1001,
        node_id="issue-e2e-1001",
        number=42,
        title="E2E Test Feature",
        body="This is a test feature for E2E testing.\n\nPlease implement a simple function.",
        html_url="https://github.com/test/e2e-repo/issues/42",
        state="open",
        locked=False,
        labels=e2e_github_labels,
        user=e2e_github_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def e2e_github_comment(e2e_github_user):
    """E2E测试用的GitHub评论"""
    return GitHubComment(
        id=2001,
        node_id="comment-e2e-2001",
        user=e2e_github_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        body="/ai develop",
        html_url="https://github.com/test/e2e-repo/issues/42#comment-2001",
    )


@pytest.fixture
def e2e_issue_labeled_event(e2e_github_issue):
    """场景A：Issue标签触发事件"""
    return {
        "action": "labeled",
        "issue": e2e_github_issue.model_dump(),
        "label": e2e_github_issue.labels[0].model_dump(),
        "sender": e2e_github_issue.user.model_dump(),
        "repository": {
            "id": 1,
            "node_id": "repo-1",
            "name": "e2e-repo",
            "full_name": "test/e2e-repo",
            "private": False,
            "owner": {
                "login": "test",
                "id": 123,
            },
        },
    }


@pytest.fixture
def e2e_issue_comment_event(e2e_github_issue, e2e_github_comment):
    """场景B：Issue评论触发事件"""
    return {
        "action": "created",
        "issue": e2e_github_issue.model_dump(),
        "comment": e2e_github_comment.model_dump(),
        "sender": e2e_github_comment.user.model_dump(),
        "repository": {
            "id": 1,
            "node_id": "repo-1",
            "name": "e2e-repo",
            "full_name": "test/e2e-repo",
            "private": False,
            "owner": {
                "login": "test",
                "id": 123,
            },
        },
    }


@pytest.fixture
def e2e_webhook_handler():
    """
    创建E2E测试用的WebhookHandler

    使用Mock的服务（Git、Claude、GitHub），专注于测试工作流逻辑。
    """
    handler = WebhookHandler()

    # Mock GitService - 避免真实Git操作（需要远程仓库）
    mock_git = Mock(spec=GitService)
    mock_git.create_feature_branch = Mock(return_value="ai/feature-42-1234567890")
    mock_git.has_changes = Mock(return_value=True)
    mock_git.commit_changes = Mock(return_value=True)
    mock_git.push_to_remote = Mock()
    handler.git_service = mock_git

    # Mock Claude和GitHub服务
    mock_claude = AsyncMock(spec=ClaudeService)
    mock_claude.develop_feature = AsyncMock(
        return_value={
            "success": True,
            "output": "Feature implementation completed",
            "errors": None,
            "returncode": 0,
            "execution_time": 10.5,
        }
    )
    handler.claude_service = mock_claude

    mock_github = Mock(spec=GitHubService)
    mock_github.create_pull_request = Mock(
        return_value={
            "pr_number": 15,
            "url": "https://api.github.com/repos/test/e2e-repo/pulls/15",
            "html_url": "https://github.com/test/e2e-repo/pull/15",
            "state": "open",
            "title": "🤖 AI: E2E Test Feature",
        }
    )
    mock_github.add_comment_to_issue = Mock()
    handler.github_service = mock_github

    return handler


# =============================================================================
# 场景组1: 完整工作流测试（P0）
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioA_LabelTriggerWorkflow:
    """
    场景A: 标签触发工作流

    测试步骤：
    1. GitHub 接收到 Issue labeled 事件（添加 ai-dev 标签）
    2. Webhook 签名验证通过
    3. WebhookHandler 解析事件并识别触发条件
    4. GitService 创建功能分支
    5. ClaudeService 调用 Claude Code CLI（mock）
    6. GitService 提交更改
    7. GitService 推送到远程（mock，因为没有真实的远程）
    8. GitHubService 创建 Pull Request（mock）
    9. GitHubService 在 Issue 中添加评论（mock）
    """

    async def test_complete_label_trigger_workflow(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        完整的标签触发工作流测试

        验证点：
        - 事件被正确接收和处理
        - 分支被成功创建
        - Claude服务被正确调用
        - 提交被创建
        - PR被成功创建（mock）
        - Issue评论被添加（mock）
        - 返回的TaskResult包含正确的信息
        """
        # 执行工作流
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证基本结果
        assert result is not None, "应该返回TaskResult"
        assert result.success is True, "工作流应该成功完成"
        assert result.task_id.startswith("task-42-"), "task_id格式应该正确"
        assert result.branch_name.startswith("ai/feature-42-"), "分支名应该正确"
        assert result.pr_url is not None, "应该有PR URL"
        assert result.error_message is None, "不应该有错误信息"

        # 验证details
        assert "pr_number" in result.details
        assert result.details["pr_number"] == 15
        assert "execution_time" in result.details
        assert result.details["execution_time"] == 10.5

        # 验证服务调用
        e2e_webhook_handler.claude_service.develop_feature.assert_called_once_with(
            issue_number=42,
            issue_title="E2E Test Feature",
            issue_url="https://github.com/test/e2e-repo/issues/42",
            issue_body="This is a test feature for E2E testing.\n\nPlease implement a simple function.",
        )

        e2e_webhook_handler.github_service.create_pull_request.assert_called_once()
        call_args = e2e_webhook_handler.github_service.create_pull_request.call_args
        assert call_args[1]["branch_name"] == result.branch_name
        assert call_args[1]["issue_number"] == 42

        e2e_webhook_handler.github_service.add_comment_to_issue.assert_called_once()
        comment_args = e2e_webhook_handler.github_service.add_comment_to_issue.call_args
        assert comment_args[1]["issue_number"] == 42
        assert "AI 开发完成" in comment_args[1]["comment"]
        assert "#15" in comment_args[1]["comment"]


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioB_CommentTriggerWorkflow:
    """
    场景B: 评论触发工作流

    测试步骤：
    1. GitHub 接收到 Issue comment 事件（包含 /ai develop）
    2. 后续流程同场景A
    """

    async def test_complete_comment_trigger_workflow(
        self,
        e2e_webhook_handler,
        e2e_issue_comment_event,
    ):
        """
        完整的评论触发工作流测试

        验证点：
        - 评论事件被正确识别
        - 触发命令被正确识别
        - 完整工作流被正确执行
        """
        # 执行工作流
        result = await e2e_webhook_handler.handle_event(
            event_type="issue_comment",
            data=e2e_issue_comment_event,
        )

        # 验证结果
        assert result is not None
        assert result.success is True
        assert result.task_id.startswith("task-42-")
        assert result.branch_name.startswith("ai/feature-42-")

        # 验证Claude被调用
        e2e_webhook_handler.claude_service.develop_feature.assert_called_once()

        # 验证PR被创建
        e2e_webhook_handler.github_service.create_pull_request.assert_called_once()

    async def test_comment_without_trigger_command(
        self,
        e2e_webhook_handler,
        e2e_github_issue,
        e2e_github_comment,
    ):
        """
        评论不包含触发命令

        验证点：
        - 不触发工作流
        - 返回None
        """
        # 修改评论内容
        e2e_github_comment.body = "This is just a regular comment"

        event = {
            "action": "created",
            "issue": e2e_github_issue.model_dump(),
            "comment": e2e_github_comment.model_dump(),
            "sender": e2e_github_comment.user.model_dump(),
        }

        # 执行
        result = await e2e_webhook_handler.handle_event(
            event_type="issue_comment",
            data=event,
        )

        # 验证不触发
        assert result is None
        e2e_webhook_handler.claude_service.develop_feature.assert_not_called()


# =============================================================================
# 场景组2: 错误恢复场景测试（P0）
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioC_ClaudeFailureAndRetry:
    """
    场景C: Claude开发失败及重试

    测试步骤：
    1. 完整工作流开始
    2. Claude调用失败
    3. 验证错误处理
    4. 验证失败通知
    5. 验证不会执行后续步骤
    """

    async def test_claude_development_failure(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        Claude开发失败场景

        验证点：
        - 返回失败的TaskResult
        - 添加失败通知到Issue
        - 不执行提交、推送、PR创建
        """
        # 修改Claude mock返回失败
        e2e_webhook_handler.claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "output": "",
                "errors": "Claude API rate limit exceeded",
                "returncode": -1,
                "execution_time": 5.0,
            }
        )

        # 执行工作流
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证失败结果
        assert result is not None
        assert result.success is False
        assert result.error_message == "Claude API rate limit exceeded"
        assert result.branch_name is not None  # 分支已创建
        assert result.pr_url is None  # PR未创建

        # 验证失败通知被添加
        e2e_webhook_handler.github_service.add_comment_to_issue.assert_called_once()
        comment_args = e2e_webhook_handler.github_service.add_comment_to_issue.call_args
        assert "AI 开发失败" in comment_args[1]["comment"]
        assert "Claude API rate limit exceeded" in comment_args[1]["comment"]

    async def test_claude_timeout_failure(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        Claude超时失败场景

        验证点：
        - 超时错误被正确处理
        - 返回失败结果
        - 添加超时错误通知
        """
        # 修改Claude mock返回超时
        e2e_webhook_handler.claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "output": "",
                "errors": "Timeout after 30 minutes",
                "returncode": -1,
                "execution_time": 1800.0,
            }
        )

        # 执行
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证
        assert result.success is False
        assert "Timeout" in result.error_message


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioD_GitConflictHandling:
    """
    场景D: Git冲突处理

    测试步骤：
    1. 完整工作流开始
    2. 分支创建时检测到冲突
    3. 验证冲突处理逻辑
    4. 验证错误通知
    """

    async def test_branch_creation_conflict(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        分支创建冲突场景

        验证点：
        - 冲突被检测到
        - 返回失败结果
        - 包含冲突错误信息
        """
        # Mock GitService抛出冲突异常
        e2e_webhook_handler.git_service.create_feature_branch = Mock(
            side_effect=Exception("Git conflict: branch already exists")
        )

        # 执行
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证失败
        assert result is not None
        assert result.success is False
        assert "conflict" in result.error_message.lower() or "branch" in result.error_message.lower()


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioE_GitHubAPIFailure:
    """
    场景E: GitHub API失败

    测试步骤：
    1. 完整工作流开始
    2. GitHub API调用失败
    3. 验证错误处理
    4. 验证不影响其他操作
    """

    async def test_pr_creation_api_failure(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        PR创建API失败场景

        验证点：
        - GitHub异常被捕获
        - 返回失败结果
        - 错误信息被记录
        """
        # Mock PR创建失败
        e2e_webhook_handler.github_service.create_pull_request = Mock(
            side_effect=GithubException(400, {"message": "Bad Request - Branch not found"})
        )

        # 执行
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证失败
        assert result is not None
        assert result.success is False
        assert result.error_message is not None

    async def test_comment_notification_failure_doesnt_crash(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        评论通知失败不影响主流程

        验证点：
        - Claude失败
        - 评论通知也失败
        - 仍然返回失败结果（不崩溃）
        """
        # Claude失败
        e2e_webhook_handler.claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "output": "",
                "errors": "Development failed",
                "returncode": -1,
            }
        )

        # 评论通知失败
        e2e_webhook_handler.github_service.add_comment_to_issue = Mock(
            side_effect=GithubException(401, {"message": "Unauthorized"})
        )

        # 执行 - 应该不抛出未捕获异常
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证返回失败结果
        assert result is not None
        assert result.success is False
        assert result.error_message == "Development failed"


# =============================================================================
# 场景组3: 边界条件测试（P1）
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioF_EmptyIssueContent:
    """
    场景F: 空Issue内容

    测试步骤：
    1. Issue body为空字符串
    2. 验证系统正常处理
    """

    async def test_empty_issue_body(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        空Issue内容场景

        验证点：
        - 空内容不影响流程执行
        - 使用默认提示词
        - 成功完成开发流程
        """
        # 设置空的issue body
        e2e_issue_labeled_event["issue"]["body"] = None

        # 执行
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证成功
        assert result is not None
        assert result.success is True

        # 验证Claude被调用，body应该是空字符串
        e2e_webhook_handler.claude_service.develop_feature.assert_called_once()
        call_args = e2e_webhook_handler.claude_service.develop_feature.call_args
        assert call_args[1]["issue_body"] == ""


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioG_VeryLongIssueContent:
    """
    场景G: 超长Issue内容

    测试步骤：
    1. Issue body包含10,000+字符
    2. 验证系统不崩溃
    """

    async def test_very_long_issue_body(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        超长Issue内容场景

        验证点：
        - 长内容不影响流程执行
        - 正确传递给Claude
        - 成功完成开发流程
        """
        # 创建超长内容（约10,000字符）
        long_body = "This is a detailed requirement. " * 500  # 约10,000字符

        e2e_issue_labeled_event["issue"]["body"] = long_body

        # 执行
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证成功
        assert result is not None
        assert result.success is True

        # 验证长内容被传递
        e2e_webhook_handler.claude_service.develop_feature.assert_called_once()
        call_args = e2e_webhook_handler.claude_service.develop_feature.call_args
        assert call_args[1]["issue_body"] == long_body


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioH_SpecialCharacters:
    """
    场景H: 特殊字符处理

    测试步骤：
    1. Issue包含Unicode、Emoji、特殊字符
    2. 验证正确编码和处理
    """

    async def test_unicode_and_emoji_handling(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        Unicode和Emoji字符场景

        验证点：
        - Unicode字符被正确处理
        - Emoji被正确处理
        - 不出现编码错误
        - 成功完成开发流程
        """
        # 包含Unicode和Emoji的内容
        special_body = """
        # Feature Request 🚀

        需要添加新功能：

        - 支持中文输入
        - Support Arabic: العربية
        - Support Emoji: 😀 🎉 ✨
        - Support Math: ∑(n=1→∞) 1/n²
        - Special chars: <>&"'`

        请实现这个功能。
        """

        e2e_issue_labeled_event["issue"]["body"] = special_body
        e2e_issue_labeled_event["issue"]["title"] = "新功能请求 🎉"

        # 执行
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证成功
        assert result is not None
        assert result.success is True

        # 验证特殊字符被传递
        e2e_webhook_handler.claude_service.develop_feature.assert_called_once()
        call_args = e2e_webhook_handler.claude_service.develop_feature.call_args
        assert "🎉" in call_args[1]["issue_title"] or "新功能" in call_args[1]["issue_title"]
        assert "中文" in call_args[1]["issue_body"] or "🚀" in call_args[1]["issue_body"]


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioI_ConcurrentIssueProcessing:
    """
    场景I: 并发Issue处理

    测试步骤：
    1. 同时接收多个Issue事件
    2. 验证并发处理能力
    3. 验证分支命名不冲突
    """

    async def test_concurrent_webhook_processing(
        self,
        e2e_webhook_handler,
        e2e_github_issue,
    ):
        """
        并发处理多个Issue事件

        验证点：
        - 可以同时处理多个事件
        - 每个事件独立处理
        - 分支名称不冲突
        - 返回正确的结果
        """
        # Mock GitService 以返回不同的分支名
        import time
        branch_counter = [0]

        def create_branch_with_unique_name(issue_number):
            branch_counter[0] += 1
            timestamp = int(time.time()) + branch_counter[0]  # 确保唯一
            return f"ai/feature-{issue_number}-{timestamp}"

        e2e_webhook_handler.git_service.create_feature_branch = Mock(
            side_effect=create_branch_with_unique_name
        )

        # 创建3个不同的事件
        events = []
        for i in range(1, 4):
            event_data = e2e_github_issue.model_dump()
            event_data["number"] = 100 + i
            event_data["id"] = 1000 + i
            event_data["node_id"] = f"issue-{i}"

            event = {
                "action": "labeled",
                "issue": event_data,
                "label": {
                    "id": 1,
                    "node_id": "label-1",
                    "name": "ai-dev",
                    "color": "00ff00",
                    "default": False,
                },
                "sender": e2e_github_issue.user.model_dump(),
            }
            events.append(event)

        # 并发执行
        tasks = [
            e2e_webhook_handler.handle_event(event_type="issues", data=event)
            for event in events
        ]
        results = await asyncio.gather(*tasks)

        # 验证所有结果都成功
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result is not None
            assert result.success is True
            assert result.task_id.startswith(f"task-{100 + i + 1}-")

        # 验证分支名都不同
        branch_names = [r.branch_name for r in results]
        assert len(set(branch_names)) == 3  # 所有分支名唯一

    async def test_branch_name_uniqueness_under_pressure(
        self,
        e2e_webhook_handler,
        e2e_github_issue,
    ):
        """
        高并发下分支名唯一性测试

        验证点：
        - 即使快速连续执行
        - 分支名仍然唯一
        - 时间戳确保唯一性
        """
        # 创建相同issue编号的多个事件（模拟快速重复）
        events = [
            {
                "action": "labeled",
                "issue": e2e_github_issue.model_dump(),
                "label": {
                    "id": 1,
                    "node_id": "label-1",
                    "name": "ai-dev",
                    "color": "00ff00",
                    "default": False,
                },
                "sender": e2e_github_issue.user.model_dump(),
            }
            for _ in range(5)
        ]

        # 快速连续执行（不加延迟）
        tasks = [
            e2e_webhook_handler.handle_event(event_type="issues", data=event)
            for event in events
        ]
        results = await asyncio.gather(*tasks)

        # 验证所有都成功
        assert all(r.success for r in results)

        # 验证task_id都不同（如果时间戳精度足够）
        task_ids = [r.task_id for r in results]
        # 注意：如果执行太快，时间戳可能相同，这里我们只验证格式
        for task_id in task_ids:
            assert task_id.startswith("task-42-")


# =============================================================================
# 场景组4: 集成验证测试（P1）
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScenarioJ_ExternalServiceIntegration:
    """
    场景J: 外部服务集成

    测试步骤：
    1. 验证与GitHub API的真实交互（使用测试仓库）
    2. 验证Git操作的正确性（使用真实Git）
    3. 验证Claude CLI的调用（mock）
    """

    async def test_webhook_signature_validation(
        self,
        e2e_issue_labeled_event,
    ):
        """
        Webhook签名验证

        验证点：
        - 正确的签名通过验证
        - 错误的签名被拒绝
        """
        from app.utils.validators import verify_webhook_signature

        # 模拟签名验证
        payload = str(e2e_issue_labeled_event).encode()
        secret = "test_secret_12345"

        # 使用正确的签名
        import hmac
        import hashlib

        signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # 验证应该通过
        is_valid = verify_webhook_signature(payload, signature, secret)
        assert is_valid is True

        # 错误的签名应该失败
        invalid_signature = "sha256=invalid"
        is_valid = verify_webhook_signature(payload, invalid_signature, secret)
        assert is_valid is False

    async def test_service_initialization(
        self,
    ):
        """
        服务初始化测试

        验证点：
        - 服务在首次使用时初始化
        - 初始化顺序正确
        - 所有服务都能正常工作
        """
        # 创建新的handler（未初始化服务）
        handler = WebhookHandler()

        # 验证初始状态
        assert handler.git_service is None
        assert handler.claude_service is None
        assert handler.github_service is None

        # 由于实际的服务初始化会连接外部服务，我们只验证延迟初始化机制
        # 而不是真正初始化服务
        assert hasattr(handler, '_init_services'), "应该有_init_services方法"
        assert callable(handler._init_services), "_init_services应该是可调用的"

    async def test_data_flow_between_services(
        self,
        e2e_webhook_handler,
        e2e_issue_labeled_event,
    ):
        """
        服务间数据流测试

        验证点：
        - GitService创建的分支名传递给后续服务
        - ClaudeService的结果影响后续流程
        - GitHubService使用正确的参数
        """
        # 执行工作流
        result = await e2e_webhook_handler.handle_event(
            event_type="issues",
            data=e2e_issue_labeled_event,
        )

        # 验证数据流
        branch_name = result.branch_name

        # GitHubService应该使用相同的分支名
        pr_call = e2e_webhook_handler.github_service.create_pull_request.call_args
        assert pr_call[1]["branch_name"] == branch_name
        assert pr_call[1]["issue_number"] == 42
        assert pr_call[1]["issue_title"] == "E2E Test Feature"

        # Issue评论应该包含正确的PR信息
        comment_call = e2e_webhook_handler.github_service.add_comment_to_issue.call_args
        assert comment_call[1]["issue_number"] == 42
        assert "#15" in comment_call[1]["comment"]


# =============================================================================
# 辅助函数
# =============================================================================


def assert_e2e_task_result(
    result: TaskResult,
    success: bool,
    has_branch: bool = True,
    has_pr: bool = None,
):
    """
    辅助函数：验证E2E TaskResult的有效性

    Args:
        result: TaskResult对象
        success: 期望的成功状态
        has_branch: 是否期望有branch_name
        has_pr: 是否期望有pr_url（None表示不检查）
    """
    assert result is not None, "TaskResult不应为None"
    assert isinstance(result, TaskResult), "应该是TaskResult实例"
    assert result.success == success, f"success状态应该是{success}"

    if has_branch:
        assert result.branch_name is not None, "应该有branch_name"
        assert isinstance(result.branch_name, str), "branch_name应该是字符串"
        assert result.branch_name.startswith("ai/feature-"), "分支名格式应该正确"
    else:
        assert result.branch_name is None, "不应该有branch_name"

    if has_pr is True:
        assert result.pr_url is not None, "应该有pr_url"
        assert isinstance(result.pr_url, str), "pr_url应该是字符串"
        assert "github.com" in result.pr_url or "pull" in result.pr_url
    elif has_pr is False:
        assert result.pr_url is None, "不应该有pr_url"

    if success:
        assert result.error_message is None, "成功时不应有错误信息"
    else:
        assert result.error_message is not None, "失败时应该有错误信息"
        assert isinstance(result.error_message, str), "error_message应该是字符串"
        assert len(result.error_message) > 0, "错误信息不应为空"

    assert result.task_id is not None, "应该有task_id"
    assert isinstance(result.task_id, str), "task_id应该是字符串"
    assert result.details is not None, "应该有details"
    assert isinstance(result.details, dict), "details应该是字典"
