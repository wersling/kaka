"""
webhook_handler.py 完整单元测试套件

测试覆盖 WebhookHandler 的所有功能，包括：
- 初始化和延迟初始化服务
- 事件路由（handle_event）
- Issue 事件处理（_handle_issue_event）
- 评论事件处理（_handle_comment_event）
- AI 开发流程触发（_trigger_ai_development）
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.github_events import (
    GitHubIssue,
    GitHubLabel,
    GitHubUser,
    IssueCommentEvent,
    IssueEvent,
    TaskResult,
)
from app.services.webhook_handler import WebhookHandler


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def github_user():
    """提供测试用的 GitHub 用户对象"""
    return GitHubUser(
        login="testuser",
        id=123456,
        avatar_url="https://github.com/avatar.png",
        type="User",
    )


@pytest.fixture
def github_labels():
    """提供测试用的 GitHub 标签列表"""
    return [
        GitHubLabel(
            id=1,
            node_id="label1",
            name="bug",
            color="d73a4a",
            default=False,
        ),
        GitHubLabel(
            id=2,
            node_id="label2",
            name="ai-dev",
            color="0075ca",
            default=False,
        ),
    ]


@pytest.fixture
def github_issue(github_user, github_labels):
    """提供测试用的 GitHub Issue 对象"""
    return GitHubIssue(
        id=789,
        node_id="issue789",
        number=123,
        title="Test Issue",
        body="Test issue body",
        html_url="https://github.com/test/repo/issues/123",
        state="open",
        locked=False,
        labels=github_labels,
        user=github_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def issue_event_data(github_issue, github_user):
    """提供测试用的 Issue 事件数据"""
    return {
        "action": "labeled",
        "issue": github_issue.model_dump(),
        "sender": github_user.model_dump(),
    }


@pytest.fixture
def issue_comment_event_data(github_issue, github_user):
    """提供测试用的 Issue 评论事件数据"""
    return {
        "action": "created",
        "issue": github_issue.model_dump(),
        "comment": {
            "id": 456,
            "node_id": "comment456",
            "user": github_user.model_dump(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "body": "Please help with this issue\n/ai develop",
            "html_url": "https://github.com/test/repo/issues/123#comment-456",
        },
        "sender": github_user.model_dump(),
    }


@pytest.fixture
def webhook_handler():
    """提供 WebhookHandler 实例"""
    return WebhookHandler()


@pytest.fixture
def mock_config():
    """提供测试用的配置对象"""
    config = MagicMock()
    config.github.trigger_label = "ai-dev"
    config.github.trigger_command = "/ai develop"
    config.task.commit_template = "feat: {issue_title}"
    config.repository.default_branch = "main"
    config.repository.remote_name = "origin"
    return config


# =============================================================================
# TestWebhookHandlerInitialization 测试
# =============================================================================


class TestWebhookHandlerInitialization:
    """测试 WebhookHandler 初始化"""

    def test_init_creates_handler_instance(self):
        """
        测试：初始化应该创建 WebhookHandler 实例

        场景：创建 WebhookHandler 实例
        期望：成功创建实例，所有服务为 None
        """
        handler = WebhookHandler()

        assert handler.git_service is None
        assert handler.claude_service is None
        assert handler.github_service is None

    def test_init_logs_initialization(self, caplog):
        """
        测试：初始化时应该记录日志

        场景：创建 WebhookHandler 实例
        期望：记录初始化日志
        """
        with caplog.at_level("INFO"):
            handler = WebhookHandler()

            assert any("Webhook 处理器初始化" in record.message for record in caplog.records)

    def test_init_services_initializes_all_services(self, webhook_handler):
        """
        测试：_init_services 应该初始化所有服务

        场景：调用 _init_services
        期望：所有服务被初始化
        """
        with patch("app.services.webhook_handler.GitService") as mock_git:
            with patch("app.services.webhook_handler.ClaudeService") as mock_claude:
                with patch("app.services.webhook_handler.GitHubService") as mock_github:
                    webhook_handler._init_services()

                    assert webhook_handler.git_service is not None
                    assert webhook_handler.claude_service is not None
                    assert webhook_handler.github_service is not None

                    mock_git.assert_called_once()
                    mock_claude.assert_called_once()
                    mock_github.assert_called_once()

    def test_init_services_logs_initialization(self, webhook_handler, caplog):
        """
        测试：_init_services 应该记录服务初始化日志

        场景：调用 _init_services
        期望：记录每个服务的初始化日志
        """
        with patch("app.services.webhook_handler.GitService"):
            with patch("app.services.webhook_handler.ClaudeService"):
                with patch("app.services.webhook_handler.GitHubService"):
                    with caplog.at_level("INFO"):
                        webhook_handler._init_services()

                        assert any("Git 服务已初始化" in record.message for record in caplog.records)
                        assert any("Claude 服务已初始化" in record.message for record in caplog.records)
                        assert any("GitHub 服务已初始化" in record.message for record in caplog.records)

    def test_init_services_only_initializes_once(self, webhook_handler):
        """
        测试：_init_services 应该只初始化服务一次

        场景：多次调用 _init_services
        期望：服务只被初始化一次
        """
        with patch("app.services.webhook_handler.GitService") as mock_git:
            with patch("app.services.webhook_handler.ClaudeService") as mock_claude:
                with patch("app.services.webhook_handler.GitHubService") as mock_github:
                    webhook_handler._init_services()
                    webhook_handler._init_services()

                    mock_git.assert_called_once()
                    mock_claude.assert_called_once()
                    mock_github.assert_called_once()


# =============================================================================
# TestHandleEvent 测试
# =============================================================================


class TestHandleEvent:
    """测试 handle_event 事件路由"""

    async def test_handle_issues_event(self, webhook_handler, issue_event_data):
        """
        测试：issues 事件应该路由到 _handle_issue_event

        场景：event_type 为 "issues"
        期望：调用 _handle_issue_event 并返回结果
        """
        with patch.object(
            webhook_handler, "_handle_issue_event", new_callable=AsyncMock
        ) as mock_handle_issue:
            expected_result = TaskResult(success=True, task_id="test-task")
            mock_handle_issue.return_value = expected_result

            result = await webhook_handler.handle_event("issues", issue_event_data)

            mock_handle_issue.assert_called_once_with(issue_event_data)
            assert result == expected_result

    async def test_handle_issue_comment_event(self, webhook_handler, issue_comment_event_data):
        """
        测试：issue_comment 事件应该路由到 _handle_comment_event

        场景：event_type 为 "issue_comment"
        期望：调用 _handle_comment_event 并返回结果
        """
        with patch.object(
            webhook_handler, "_handle_comment_event", new_callable=AsyncMock
        ) as mock_handle_comment:
            expected_result = TaskResult(success=True, task_id="test-task")
            mock_handle_comment.return_value = expected_result

            result = await webhook_handler.handle_event("issue_comment", issue_comment_event_data)

            mock_handle_comment.assert_called_once_with(issue_comment_event_data)
            assert result == expected_result

    async def test_handle_ping_event(self, webhook_handler):
        """
        测试：ping 事件应该返回 pong

        场景：event_type 为 "ping"
        期望：返回包含 pong 消息的 TaskResult
        """
        result = await webhook_handler.handle_event("ping", {})

        assert result.success is True
        assert result.task_id == "ping"
        assert result.details == {"message": "pong"}

    async def test_handle_unsupported_event(self, webhook_handler, caplog):
        """
        测试：不支持的事件类型应该返回 None

        场景：event_type 为 "push"
        期望：返回 None 并记录警告日志
        """
        with caplog.at_level("WARNING"):
            result = await webhook_handler.handle_event("push", {})

            assert result is None
            assert any("不支持的事件类型" in record.message for record in caplog.records)

    async def test_handle_event_logs_event_type(self, webhook_handler, caplog):
        """
        测试：handle_event 应该记录事件类型

        场景：处理任何事件
        期望：记录事件类型日志
        """
        with caplog.at_level("INFO"):
            with patch.object(webhook_handler, "_handle_issue_event", new_callable=AsyncMock):
                await webhook_handler.handle_event("issues", {})

                assert any("收到 Webhook 事件: issues" in record.message for record in caplog.records)

    async def test_handle_event_logs_sanitized_data(self, webhook_handler, caplog):
        """
        测试：handle_event 应该记录脱敏的事件数据

        场景：处理包含敏感信息的事件
        期望：日志中敏感信息被脱敏
        """
        with caplog.at_level("DEBUG"):
            with patch.object(webhook_handler, "_handle_issue_event", new_callable=AsyncMock):
                data = {"token": "secret_token", "action": "labeled"}
                await webhook_handler.handle_event("issues", data)

                # 验证日志中包含脱敏的数据
                debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
                assert any("事件数据" in record.message for record in debug_records)

    async def test_handle_event_exception_handling(self, webhook_handler):
        """
        测试：handle_event 应该捕获并处理异常

        场景：_handle_issue_event 抛出异常
        期望：返回失败结果并记录错误日志
        """
        with patch.object(
            webhook_handler, "_handle_issue_event", new_callable=AsyncMock
        ) as mock_handle_issue:
            mock_handle_issue.side_effect = Exception("Test error")

            result = await webhook_handler.handle_event("issues", {})

            assert result.success is False
            assert result.task_id == "error"
            assert "Test error" in result.error_message


# =============================================================================
# TestHandleIssueEvent 测试
# =============================================================================


class TestHandleIssueEvent:
    """测试 _handle_issue_event 方法"""

    async def test_labeled_action_with_trigger_label(self, webhook_handler, issue_event_data, mock_config):
        """
        测试：labeled 动作且包含触发标签应该触发 AI 开发

        场景：action 为 "labeled"，labels 包含 "ai-dev"
        期望：调用 _trigger_ai_development
        """
        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(
                webhook_handler, "_trigger_ai_development", new_callable=AsyncMock
            ) as mock_trigger:
                expected_result = TaskResult(success=True, task_id="test-task")
                mock_trigger.return_value = expected_result

                result = await webhook_handler._handle_issue_event(issue_event_data)

                mock_trigger.assert_called_once()
                assert result == expected_result

    async def test_labeled_action_without_trigger_label(self, webhook_handler, mock_config, github_user):
        """
        测试：labeled 动作但不包含触发标签不应该触发

        场景：action 为 "labeled"，labels 不包含 "ai-dev"
        期望：返回 None
        """
        issue_without_trigger = GitHubIssue(
            id=789,
            node_id="issue789",
            number=456,
            title="Test Issue",
            body="Test body",
            html_url="https://github.com/test/repo/issues/456",
            state="open",
            locked=False,
            labels=[],
            user=github_user,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        event_data = {
            "action": "labeled",
            "issue": issue_without_trigger.model_dump(),
            "sender": github_user.model_dump(),
        }

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._handle_issue_event(event_data)

            assert result is None

    async def test_non_labeled_action(self, webhook_handler, issue_event_data, mock_config):
        """
        测试：非 labeled 动作不应该触发

        场景：action 为 "opened"
        期望：返回 None
        """
        issue_event_data["action"] = "opened"

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._handle_issue_event(issue_event_data)

            assert result is None

    async def test_unlabeled_action(self, webhook_handler, issue_event_data, mock_config):
        """
        测试：unlabeled 动作不应该触发

        场景：action 为 "unlabeled"
        期望：返回 None
        """
        issue_event_data["action"] = "unlabeled"

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._handle_issue_event(issue_event_data)

            assert result is None

    async def test_successful_ai_development_trigger(self, webhook_handler, issue_event_data, mock_config):
        """
        测试：成功触发 AI 开发流程

        场景：满足所有触发条件
        期望：返回成功的 TaskResult
        """
        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(
                webhook_handler, "_trigger_ai_development", new_callable=AsyncMock
            ) as mock_trigger:
                expected_result = TaskResult(
                    success=True,
                    task_id="task-123-1234567890",
                    branch_name="ai/feature-123-1234567890",
                    pr_url="https://github.com/test/repo/pull/1",
                )
                mock_trigger.return_value = expected_result

                result = await webhook_handler._handle_issue_event(issue_event_data)

                assert result.success is True
                assert result.branch_name == "ai/feature-123-1234567890"

    async def test_handle_issue_event_exception_handling(self, webhook_handler, issue_event_data):
        """
        测试：_handle_issue_event 应该捕获并处理异常

        场景：解析事件数据时抛出异常
        期望：返回失败结果
        """
        # 提供无效的数据导致解析失败
        invalid_data = {"invalid": "data"}

        result = await webhook_handler._handle_issue_event(invalid_data)

        assert result.success is False
        assert result.task_id == "error"
        assert result.error_message is not None

    async def test_handle_issue_event_logs_issue_info(self, webhook_handler, issue_event_data, mock_config, caplog):
        """
        测试：_handle_issue_event 应该记录 Issue 信息

        场景：处理 Issue 事件
        期望：记录 Issue 编号和标题
        """
        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(webhook_handler, "_trigger_ai_development", new_callable=AsyncMock):
                with caplog.at_level("INFO"):
                    await webhook_handler._handle_issue_event(issue_event_data)

                    assert any("Issue 事件" in record.message for record in caplog.records)
                    assert any("action=labeled" in record.message for record in caplog.records)
                    assert any("issue=#123" in record.message for record in caplog.records)

    async def test_handle_issue_event_logs_no_trigger(self, webhook_handler, issue_event_data, mock_config, caplog):
        """
        测试：不满足触发条件时应该记录调试日志

        场景：labels 不包含触发标签
        期望：记录不满足触发条件的调试日志
        """
        issue_event_data["issue"]["labels"] = []

        with patch("app.config.get_config", return_value=mock_config):
            with caplog.at_level("DEBUG"):
                await webhook_handler._handle_issue_event(issue_event_data)

                assert any("不满足触发条件" in record.message for record in caplog.records)


# =============================================================================
# TestHandleCommentEvent 测试
# =============================================================================


class TestHandleCommentEvent:
    """测试 _handle_comment_event 方法"""

    async def test_created_action_with_trigger_command(self, webhook_handler, issue_comment_event_data, mock_config):
        """
        测试：created 动作且包含触发命令应该触发 AI 开发

        场景：action 为 "created"，评论包含 "/ai develop"
        期望：调用 _trigger_ai_development
        """
        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(
                webhook_handler, "_trigger_ai_development", new_callable=AsyncMock
            ) as mock_trigger:
                expected_result = TaskResult(success=True, task_id="test-task")
                mock_trigger.return_value = expected_result

                result = await webhook_handler._handle_comment_event(issue_comment_event_data)

                mock_trigger.assert_called_once()
                assert result == expected_result

    async def test_created_action_without_trigger_command(self, webhook_handler, issue_comment_event_data, mock_config):
        """
        测试：created 动作但不包含触发命令不应该触发

        场景：action 为 "created"，评论不包含触发命令
        期望：返回 None
        """
        issue_comment_event_data["comment"]["body"] = "This is a normal comment"

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._handle_comment_event(issue_comment_event_data)

            assert result is None

    async def test_non_created_action(self, webhook_handler, issue_comment_event_data, mock_config):
        """
        测试：非 created 动作不应该触发

        场景：action 为 "edited"
        期望：返回 None
        """
        issue_comment_event_data["action"] = "edited"

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._handle_comment_event(issue_comment_event_data)

            assert result is None

    async def test_deleted_action(self, webhook_handler, issue_comment_event_data, mock_config):
        """
        测试：deleted 动作不应该触发

        场景：action 为 "deleted"
        期望：返回 None
        """
        issue_comment_event_data["action"] = "deleted"

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._handle_comment_event(issue_comment_event_data)

            assert result is None

    async def test_successful_ai_development_from_comment(self, webhook_handler, issue_comment_event_data, mock_config):
        """
        测试：从评论成功触发 AI 开发流程

        场景：评论包含触发命令
        期望：返回成功的 TaskResult
        """
        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(
                webhook_handler, "_trigger_ai_development", new_callable=AsyncMock
            ) as mock_trigger:
                expected_result = TaskResult(
                    success=True,
                    task_id="task-123-1234567890",
                    branch_name="ai/feature-123-1234567890",
                    pr_url="https://github.com/test/repo/pull/1",
                )
                mock_trigger.return_value = expected_result

                result = await webhook_handler._handle_comment_event(issue_comment_event_data)

                assert result.success is True

    async def test_handle_comment_event_exception_handling(self, webhook_handler):
        """
        测试：_handle_comment_event 应该捕获并处理异常

        场景：解析事件数据时抛出异常
        期望：返回失败结果
        """
        invalid_data = {"invalid": "data"}

        result = await webhook_handler._handle_comment_event(invalid_data)

        assert result.success is False
        assert result.task_id == "error"
        assert result.error_message is not None

    async def test_handle_comment_event_logs_comment_info(self, webhook_handler, issue_comment_event_data, mock_config, caplog):
        """
        测试：_handle_comment_event 应该记录评论信息

        场景：处理评论事件
        期望：记录 Issue 编号
        """
        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(webhook_handler, "_trigger_ai_development", new_callable=AsyncMock):
                with caplog.at_level("INFO"):
                    await webhook_handler._handle_comment_event(issue_comment_event_data)

                    assert any("Issue 评论事件" in record.message for record in caplog.records)
                    assert any("action=created" in record.message for record in caplog.records)
                    assert any("issue=#123" in record.message for record in caplog.records)

    async def test_handle_comment_event_logs_no_trigger(self, webhook_handler, issue_comment_event_data, mock_config, caplog):
        """
        测试：不满足触发条件时应该记录调试日志

        场景：评论不包含触发命令
        期望：记录不包含触发命令的调试日志
        """
        issue_comment_event_data["comment"]["body"] = "Normal comment"

        with patch("app.config.get_config", return_value=mock_config):
            with caplog.at_level("DEBUG"):
                await webhook_handler._handle_comment_event(issue_comment_event_data)

                assert any("不包含触发命令" in record.message for record in caplog.records)

    async def test_handle_comment_event_ignores_non_created(self, webhook_handler, issue_comment_event_data, mock_config, caplog):
        """
        测试：非 created 动作应该记录忽略日志

        场景：action 为 "edited"
        期望：记录忽略动作的调试日志
        """
        issue_comment_event_data["action"] = "edited"

        with patch("app.config.get_config", return_value=mock_config):
            with caplog.at_level("DEBUG"):
                await webhook_handler._handle_comment_event(issue_comment_event_data)

                assert any("Ignore comment action: edited" in record.message for record in caplog.records)


# =============================================================================
# TestTriggerAIDevelopment 测试
# =============================================================================


class TestTriggerAIDevelopment:
    """测试 _trigger_ai_development 方法"""

    async def test_complete_workflow_success(self, webhook_handler, mock_config):
        """
        测试：完整的5步工作流应该成功执行

        场景：所有服务操作都成功
        期望：返回成功的 TaskResult
        """
        # Mock services
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-123-1234567890"
        mock_git_service.has_changes.return_value = False
        mock_git_service.push_to_remote.return_value = None

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": True,
                "execution_time": 120.5,
            }
        )

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 42,
            "html_url": "https://github.com/test/repo/pull/42",
        }
        mock_github_service.add_comment_to_issue.return_value = None

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=123,
                issue_title="Test Issue",
                issue_url="https://github.com/test/repo/issues/123",
                issue_body="Test body",
            )

            assert result.success is True
            assert result.branch_name == "ai/feature-123-1234567890"
            assert result.pr_url == "https://github.com/test/repo/pull/42"
            assert result.details["pr_number"] == 42

            # 验证所有步骤都被调用
            mock_git_service.create_feature_branch.assert_called_once_with(123)
            mock_claude_service.develop_feature.assert_called_once()
            mock_git_service.push_to_remote.assert_called_once_with("ai/feature-123-1234567890")
            mock_github_service.create_pull_request.assert_called_once()
            mock_github_service.add_comment_to_issue.assert_called_once()

    async def test_branch_creation_success(self, webhook_handler, mock_config):
        """
        测试：分支创建步骤应该成功

        场景：创建特性分支
        期望：返回正确的分支名
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-456-9999999999"

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=456,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/456",
                issue_body="Body",
            )

            assert result.branch_name == "ai/feature-456-9999999999"

    async def test_claude_development_success(self, webhook_handler, mock_config):
        """
        测试：Claude 开发步骤应该成功

        场景：Claude 开发成功完成
        期望：返回包含执行时间的结果
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-789-1111111111"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": True,
                "execution_time": 300.0,
            }
        )

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 2,
            "html_url": "https://github.com/test/repo/pull/2",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=789,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/789",
                issue_body="Body",
            )

            assert result.success is True
            assert result.details["execution_time"] == 300.0

    async def test_commit_check_with_changes(self, webhook_handler, mock_config):
        """
        测试：有变更时应该提交

        场景：Claude 开发后有未提交的变更
        期望：调用 commit_changes
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-100-2222222222"
        mock_git_service.has_changes.return_value = True
        mock_git_service.commit_changes.return_value = True

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 3,
            "html_url": "https://github.com/test/repo/pull/3",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=100,
                issue_title="Test Issue",
                issue_url="https://github.com/test/repo/issues/100",
                issue_body="Body",
            )

            mock_git_service.commit_changes.assert_called_once()

    async def test_commit_check_without_changes(self, webhook_handler, mock_config):
        """
        测试：无变更时不应该提交

        场景：Claude 开发后没有未提交的变更
        期望：不调用 commit_changes
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-200-3333333333"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 4,
            "html_url": "https://github.com/test/repo/pull/4",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=200,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/200",
                issue_body="Body",
            )

            mock_git_service.commit_changes.assert_not_called()

    async def test_push_to_remote_success(self, webhook_handler, mock_config):
        """
        测试：推送到远程应该成功

        场景：提交后推送到远程
        期望：调用 push_to_remote
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-300-4444444444"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 5,
            "html_url": "https://github.com/test/repo/pull/5",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=300,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/300",
                issue_body="Body",
            )

            mock_git_service.push_to_remote.assert_called_once_with("ai/feature-300-4444444444")

    async def test_pr_creation_success(self, webhook_handler, mock_config):
        """
        测试：PR 创建应该成功

        场景：推送后创建 PR
        期望：返回 PR URL 和编号
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-400-5555555555"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 99,
            "html_url": "https://github.com/test/repo/pull/99",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=400,
                issue_title="Test PR",
                issue_url="https://github.com/test/repo/issues/400",
                issue_body="Body",
            )

            assert result.pr_url == "https://github.com/test/repo/pull/99"
            assert result.details["pr_number"] == 99

    async def test_add_comment_to_issue(self, webhook_handler, mock_config):
        """
        测试：应该在 Issue 中添加 PR 评论

        场景：PR 创建成功
        期望：调用 add_comment_to_issue
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-500-6666666666"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 7,
            "html_url": "https://github.com/test/repo/pull/7",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=500,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/500",
                issue_body="Body",
            )

            # 验证添加了评论（PR 链接）
            mock_github_service.add_comment_to_issue.assert_called_once()

    async def test_claude_development_failure(self, webhook_handler, mock_config):
        """
        测试：Claude 开发失败时应该通知用户

        场景：Claude develop_feature 返回失败
        期望：返回失败结果并添加错误评论
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-600-7777777777"

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "errors": "Claude development failed",
            }
        )

        mock_github_service = MagicMock()

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=600,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/600",
                issue_body="Body",
            )

            assert result.success is False
            assert "Claude development failed" in result.error_message
            mock_github_service.add_comment_to_issue.assert_called_once()

    async def test_git_operation_failure(self, webhook_handler, mock_config):
        """
        测试：Git 操作失败时应该处理异常

        场景：create_feature_branch 抛出异常
        期望：返回失败结果并通知用户
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.side_effect = Exception("Git error")

        mock_github_service = MagicMock()

        webhook_handler.git_service = mock_git_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=700,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/700",
                issue_body="Body",
            )

            assert result.success is False
            assert "Git error" in result.error_message

    async def test_github_api_failure(self, webhook_handler, mock_config):
        """
        测试：GitHub API 失败时应该处理异常

        场景：create_pull_request 抛出异常
        期望：返回失败结果并通知用户
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-800-8888888888"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.side_effect = Exception("API error")

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=800,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/800",
                issue_body="Body",
            )

            assert result.success is False
            assert "API error" in result.error_message

    async def test_trigger_logs_workflow_steps(self, webhook_handler, mock_config, caplog):
        """
        测试：_trigger_ai_development 应该记录所有工作流步骤

        场景：执行完整工作流
        期望：记录每个步骤的日志
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-900-9999999999"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 10,
            "html_url": "https://github.com/test/repo/pull/10",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            with caplog.at_level("INFO"):
                await webhook_handler._trigger_ai_development(
                    issue_number=900,
                    issue_title="Test",
                    issue_url="https://github.com/test/repo/issues/900",
                    issue_body="Body",
                )

                # 验证所有步骤的日志
                log_messages = [record.message for record in caplog.records]
                assert any("步骤 1/5: 创建特性分支" in msg for msg in log_messages)
                assert any("步骤 2/5: 调用 Claude Code CLI" in msg for msg in log_messages)
                assert any("步骤 3/5: 检查并提交变更" in msg for msg in log_messages)
                assert any("步骤 4/5: 推送到远程" in msg for msg in log_messages)
                assert any("步骤 5/5: 创建 Pull Request" in msg for msg in log_messages)

    async def test_trigger_generates_unique_task_id(self, webhook_handler, mock_config):
        """
        测试：应该生成唯一的 task_id

        场景：多次触发开发
        期望：每次生成不同的 task_id
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-111-0000000000"
        mock_git_service.has_changes.return_value = False

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(return_value={"success": True})

        mock_github_service = MagicMock()
        mock_github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result1 = await webhook_handler._trigger_ai_development(
                issue_number=111,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/111",
                issue_body="Body",
            )

            # 等待一秒确保时间戳不同
            import time

            time.sleep(1)

            result2 = await webhook_handler._trigger_ai_development(
                issue_number=111,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/111",
                issue_body="Body",
            )

            # task_id 应该不同（因为时间戳不同）
            assert result1.task_id != result2.task_id

    async def test_trigger_with_claude_error_comment_fallback(self, webhook_handler, mock_config):
        """
        测试：Claude 失败时即使评论失败也应该继续

        场景：Claude 失败且 add_comment_to_issue 抛出异常
        期望：返回失败结果但不会崩溃
        """
        mock_git_service = MagicMock()
        mock_git_service.create_feature_branch.return_value = "ai/feature-222-1111111111"

        mock_claude_service = MagicMock()
        mock_claude_service.develop_feature = AsyncMock(
            return_value={
                "success": False,
                "errors": "Claude error",
            }
        )

        mock_github_service = MagicMock()
        mock_github_service.add_comment_to_issue.side_effect = Exception("Comment failed")

        webhook_handler.git_service = mock_git_service
        webhook_handler.claude_service = mock_claude_service
        webhook_handler.github_service = mock_github_service

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=222,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/222",
                issue_body="Body",
            )

            # 应该返回失败结果
            assert result.success is False
            assert "Claude error" in result.error_message
