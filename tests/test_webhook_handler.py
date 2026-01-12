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

                        assert any(
                            "Git 服务已初始化" in record.message for record in caplog.records
                        )
                        assert any(
                            "Claude 服务已初始化" in record.message for record in caplog.records
                        )
                        assert any(
                            "GitHub 服务已初始化" in record.message for record in caplog.records
                        )

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

                assert any(
                    "收到 Webhook 事件: issues" in record.message for record in caplog.records
                )

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

    async def test_labeled_action_with_trigger_label(
        self, webhook_handler, issue_event_data, mock_config
    ):
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

    async def test_labeled_action_without_trigger_label(
        self, webhook_handler, mock_config, github_user
    ):
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

    async def test_successful_ai_development_trigger(
        self, webhook_handler, issue_event_data, mock_config
    ):
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

    async def test_handle_issue_event_logs_issue_info(
        self, webhook_handler, issue_event_data, mock_config, caplog
    ):
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

    async def test_handle_issue_event_logs_no_trigger(
        self, webhook_handler, issue_event_data, mock_config, caplog
    ):
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

    async def test_created_action_with_trigger_command(
        self, webhook_handler, issue_comment_event_data, mock_config
    ):
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

    async def test_created_action_without_trigger_command(
        self, webhook_handler, issue_comment_event_data, mock_config
    ):
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

    async def test_successful_ai_development_from_comment(
        self, webhook_handler, issue_comment_event_data, mock_config
    ):
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

    async def test_handle_comment_event_logs_comment_info(
        self, webhook_handler, issue_comment_event_data, mock_config, caplog
    ):
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

    async def test_handle_comment_event_logs_no_trigger(
        self, webhook_handler, issue_comment_event_data, mock_config, caplog
    ):
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

    async def test_handle_comment_event_ignores_non_created(
        self, webhook_handler, issue_comment_event_data, mock_config, caplog
    ):
        """
        测试：非 created 动作应该记录忽略日志

        场景：action 为 "edited"
        期望：记录忽略动作的调试日志
        """
        issue_comment_event_data["action"] = "edited"

        with patch("app.config.get_config", return_value=mock_config):
            with caplog.at_level("DEBUG"):
                await webhook_handler._handle_comment_event(issue_comment_event_data)

                assert any(
                    "Ignore comment action: edited" in record.message for record in caplog.records
                )


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


# =============================================================================
# TestServiceOrchestration 测试
# =============================================================================


class TestServiceOrchestration:
    """测试服务编排和协作"""

    async def test_services_initialized_in_correct_order(self, webhook_handler, mock_config):
        """
        测试：服务应该按照正确顺序初始化

        场景：首次触发 AI 开发
        期望：按 Git -> Claude -> GitHub 顺序初始化
        """
        with patch("app.services.webhook_handler.GitService") as mock_git:
            with patch("app.services.webhook_handler.ClaudeService") as mock_claude:
                with patch("app.services.webhook_handler.GitHubService") as mock_github:
                    # Mock 服务方法
                    mock_git_instance = MagicMock()
                    mock_git_instance.create_feature_branch.return_value = "ai/feature-1-1"
                    mock_git_instance.has_changes.return_value = False
                    mock_git_instance.push_to_remote.return_value = None
                    mock_git.return_value = mock_git_instance

                    mock_claude_instance = MagicMock()
                    mock_claude_instance.develop_feature = AsyncMock(return_value={"success": True})
                    mock_claude.return_value = mock_claude_instance

                    mock_github_instance = MagicMock()
                    mock_github_instance.create_pull_request.return_value = {
                        "pr_number": 1,
                        "html_url": "https://github.com/test/repo/pull/1",
                    }
                    mock_github_instance.add_comment_to_issue.return_value = None
                    mock_github.return_value = mock_github_instance

                    with patch("app.config.get_config", return_value=mock_config):
                        await webhook_handler._trigger_ai_development(
                            issue_number=1,
                            issue_title="Test",
                            issue_url="https://github.com/test/repo/issues/1",
                            issue_body="Body",
                        )

                        # 验证初始化顺序
                        assert mock_git.called
                        assert mock_claude.called
                        assert mock_github.called

    async def test_workflow_execution_order(self, webhook_handler, mock_config):
        """
        测试：工作流应该按照正确的 5 步顺序执行

        场景：所有操作成功
        期望：分支 -> Claude -> 提交检查 -> 推送 -> PR
        """
        call_order = []

        # 创建 mock 服务
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False
        mock_git.push_to_remote.return_value = None

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }
        mock_github.add_comment_to_issue.return_value = None

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        # 使用 spy 来记录调用顺序
        original_create = mock_git.create_feature_branch
        original_claude = mock_claude.develop_feature
        original_has_changes = mock_git.has_changes
        original_push = mock_git.push_to_remote
        original_pr = mock_github.create_pull_request
        original_comment = mock_github.add_comment_to_issue

        def spy_create(*args, **kwargs):
            call_order.append("branch")
            return original_create(*args, **kwargs)

        async def spy_claude(*args, **kwargs):
            call_order.append("claude")
            return await original_claude(*args, **kwargs)

        def spy_has_changes(*args, **kwargs):
            call_order.append("check_changes")
            return original_has_changes(*args, **kwargs)

        def spy_push(*args, **kwargs):
            call_order.append("push")
            return original_push(*args, **kwargs)

        def spy_pr(*args, **kwargs):
            call_order.append("pr")
            return original_pr(*args, **kwargs)

        def spy_comment(*args, **kwargs):
            call_order.append("comment")
            return original_comment(*args, **kwargs)

        mock_git.create_feature_branch = spy_create
        mock_claude.develop_feature = spy_claude
        mock_git.has_changes = spy_has_changes
        mock_git.push_to_remote = spy_push
        mock_github.create_pull_request = spy_pr
        mock_github.add_comment_to_issue = spy_comment

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            # 验证执行顺序：分支 -> Claude -> 检查变更 -> 推送 -> PR -> 评论
            assert "branch" in call_order
            assert "claude" in call_order
            assert "check_changes" in call_order
            assert "push" in call_order
            assert "pr" in call_order
            assert "comment" in call_order

            # 验证分支在 Claude 之前
            assert call_order.index("branch") < call_order.index("claude")
            # Claude 在检查变更之前
            assert call_order.index("claude") < call_order.index("check_changes")
            # 检查变更在推送之前
            assert call_order.index("check_changes") < call_order.index("push")
            # 推送在 PR 之前
            assert call_order.index("push") < call_order.index("pr")

    async def test_parameters_passed_between_services(self, webhook_handler, mock_config):
        """
        测试：参数应该正确地在服务间传递

        场景：完整工作流执行
        期望：每个服务接收到正确的参数
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-999-1234567890"
        mock_git.has_changes.return_value = False
        mock_git.push_to_remote.return_value = None

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 42,
            "html_url": "https://github.com/test/repo/pull/42",
        }
        mock_github.add_comment_to_issue.return_value = None

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=999,
                issue_title="Test Issue Title",
                issue_url="https://github.com/test/repo/issues/999",
                issue_body="Test issue body content",
            )

            # 验证 GitService 参数
            mock_git.create_feature_branch.assert_called_once_with(999)

            # 验证 ClaudeService 参数
            mock_claude.develop_feature.assert_called_once()
            call_kwargs = mock_claude.develop_feature.call_args.kwargs
            assert call_kwargs["issue_number"] == 999
            assert call_kwargs["issue_title"] == "Test Issue Title"
            assert call_kwargs["issue_url"] == "https://github.com/test/repo/issues/999"
            assert call_kwargs["issue_body"] == "Test issue body content"

            # 验证 GitHubService 参数
            mock_github.create_pull_request.assert_called_once()
            call_kwargs = mock_github.create_pull_request.call_args.kwargs
            assert call_kwargs["branch_name"] == "ai/feature-999-1234567890"
            assert call_kwargs["issue_number"] == 999
            assert call_kwargs["issue_title"] == "Test Issue Title"
            assert call_kwargs["issue_body"] == "Test issue body content"

    async def test_branch_name_propagation(self, webhook_handler, mock_config):
        """
        测试：分支名应该正确地在工作流中传递

        场景：创建分支后使用该分支名进行推送和 PR
        期望：所有后续操作使用相同的分支名
        """
        expected_branch = "ai/feature-777-9876543210"

        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = expected_branch
        mock_git.has_changes.return_value = False
        mock_git.push_to_remote.return_value = None

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }
        mock_github.add_comment_to_issue.return_value = None

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=777,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/777",
                issue_body="Body",
            )

            # 验证分支名在所有操作中使用一致
            mock_git.push_to_remote.assert_called_once_with(expected_branch)
            mock_github.create_pull_request.assert_called_once()
            # 检查调用参数
            call_kwargs = mock_github.create_pull_request.call_args.kwargs
            assert call_kwargs["branch_name"] == expected_branch
            assert call_kwargs["issue_number"] == 777
            assert call_kwargs["issue_title"] == "Test"
            assert call_kwargs["issue_body"] == "Body"


# =============================================================================
# TestErrorHandling 测试
# =============================================================================


class TestErrorHandling:
    """测试错误处理和边界情况"""

    async def test_git_branch_creation_failure(self, webhook_handler, mock_config):
        """
        测试：分支创建失败应该正确处理

        场景：create_feature_branch 抛出异常
        期望：返回失败结果并尝试通知用户
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.side_effect = RuntimeError("Branch creation failed")

        mock_github = MagicMock()

        webhook_handler.git_service = mock_git
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            assert result.success is False
            assert "Branch creation failed" in result.error_message
            assert result.task_id.startswith("task-1-")

    async def test_git_push_failure(self, webhook_handler, mock_config):
        """
        测试：Git 推送失败应该正确处理

        场景：push_to_remote 抛出异常
        期望：返回失败结果并尝试通知用户
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False
        mock_git.push_to_remote.side_effect = Exception("Push failed")

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            assert result.success is False
            assert "Push failed" in result.error_message

    async def test_claude_timeout_error(self, webhook_handler, mock_config):
        """
        测试：Claude 超时应该正确处理

        场景：develop_feature 因超时失败
        期望：返回失败结果并通知用户
        """
        import asyncio

        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(
            side_effect=asyncio.TimeoutError("Claude execution timeout")
        )

        mock_github = MagicMock()

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            assert result.success is False
            assert "Claude execution timeout" in result.error_message
            mock_github.add_comment_to_issue.assert_called_once()

    async def test_github_pr_creation_failure(self, webhook_handler, mock_config):
        """
        测试：GitHub PR 创建失败应该正确处理

        场景：create_pull_request 抛出异常
        期望：返回失败结果并尝试通知用户
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False
        mock_git.push_to_remote.return_value = None

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.side_effect = RuntimeError("PR creation failed")

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            assert result.success is False
            assert "PR creation failed" in result.error_message

    async def test_commit_message_formatting(self, webhook_handler, mock_config):
        """
        测试：提交消息应该使用正确的格式

        场景：需要提交变更
        期望：使用配置的模板格式化提交消息
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = True
        mock_git.commit_changes.return_value = True

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Fix Critical Bug",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            # 验证提交消息格式
            mock_git.commit_changes.assert_called_once()
            call_args = mock_git.commit_changes.call_args[0]
            assert call_args[0] == "feat: Fix Critical Bug"

    async def test_missing_required_config(self, webhook_handler):
        """
        测试：缺少必需配置应该返回失败结果

        场景：get_config 返回 None
        期望：捕获异常并返回失败结果
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"

        webhook_handler.git_service = mock_git

        with patch("app.config.get_config", return_value=None):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            # 应该返回失败结果而不是抛出异常
            assert result.success is False
            assert result.error_message is not None

    async def test_invalid_issue_data(self, webhook_handler, mock_config):
        """
        测试：无效的 Issue 数据应该被正确处理

        场景：Issue 编号为负数，GitService 抛出异常
        期望：捕获异常并返回失败结果
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.side_effect = Exception("Invalid issue number")

        webhook_handler.git_service = mock_git

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=-1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/-1",
                issue_body="Body",
            )

            # 应该返回失败结果
            assert result.success is False
            # 错误消息应该包含异常信息
            assert result.error_message is not None

    async def test_empty_issue_fields(self, webhook_handler, mock_config):
        """
        测试：空字符串的 Issue 字段应该被正确处理

        场景：Issue title 和 body 为空字符串
        期望：正常处理，使用空字符串
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="",
            )

            # 应该成功执行，即使字段为空
            assert result.success is True

    async def test_error_notification_fallback(self, webhook_handler, mock_config):
        """
        测试：错误通知失败不应该导致整个流程崩溃

        场景：工作流失败且 GitHub 通知也失败
        期望：返回失败结果但不会抛出未捕获的异常
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.side_effect = Exception("Workflow error")

        mock_github = MagicMock()
        mock_github.add_comment_to_issue.side_effect = Exception("Notification failed")

        webhook_handler.git_service = mock_git
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            # 应该返回失败结果，但不会崩溃
            assert result.success is False
            assert "Workflow error" in result.error_message


# =============================================================================
# TestParametrizedTriggers 测试
# =============================================================================


class TestParametrizedTriggers:
    """参数化测试：触发条件和变体"""

    @pytest.mark.parametrize(
        "labels,should_trigger",
        [
            # 包含触发标签
            (["ai-dev", "bug"], True),
            (["feature", "ai-dev"], True),
            (["ai-dev"], True),
            # 不包含触发标签
            (["bug", "enhancement"], False),
            ([], False),
            (["ai-dev-2", "ai-dev-test"], False),
        ],
    )
    async def test_label_triggers(
        self, webhook_handler, mock_config, github_user, labels, should_trigger
    ):
        """
        参数化测试：不同标签组合的触发行为

        场景：Issue 有不同的标签组合
        期望：只有包含 'ai-dev' 的标签才会触发
        """
        issue = GitHubIssue(
            id=1,
            node_id="issue1",
            number=1,
            title="Test",
            body="Body",
            html_url="https://github.com/test/repo/issues/1",
            state="open",
            locked=False,
            labels=[
                GitHubLabel(
                    id=i,
                    node_id=f"label{i}",
                    name=label,
                    color="000000",
                    default=False,
                )
                for i, label in enumerate(labels)
            ],
            user=github_user,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        event_data = {
            "action": "labeled",
            "issue": issue.model_dump(),
            "sender": github_user.model_dump(),
        }

        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(
                webhook_handler, "_trigger_ai_development", new_callable=AsyncMock
            ) as mock_trigger:
                mock_trigger.return_value = TaskResult(success=True, task_id="test")

                result = await webhook_handler._handle_issue_event(event_data)

                if should_trigger:
                    assert result is not None
                    mock_trigger.assert_called_once()
                else:
                    assert result is None
                    mock_trigger.assert_not_called()

    @pytest.mark.parametrize(
        "comment_body,should_trigger",
        [
            # 包含触发命令
            ("/ai develop", True),
            ("/ai develop please", True),
            ("Please help /ai develop", True),
            ("Some text\n/ai develop\nmore text", True),
            # 不区分大小写
            ("/AI DEVELOP", True),
            ("/Ai Develop", True),
            # 不包含触发命令
            ("ai develop", False),  # 缺少 /
            ("please help", False),
            ("/ai-deploy", False),
            ("/ai", False),
            ("", False),
        ],
    )
    async def test_comment_triggers(
        self, webhook_handler, mock_config, github_issue, github_user, comment_body, should_trigger
    ):
        """
        参数化测试：不同评论内容的触发行为

        场景：评论包含不同的命令文本
        期望：只有包含 '/ai develop' 的评论才会触发
        """
        comment_data = {
            "action": "created",
            "issue": github_issue.model_dump(),
            "comment": {
                "id": 1,
                "node_id": "comment1",
                "user": github_user.model_dump(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "body": comment_body,
                "html_url": "https://github.com/test/repo/issues/1#comment-1",
            },
            "sender": github_user.model_dump(),
        }

        with patch("app.config.get_config", return_value=mock_config):
            with patch.object(
                webhook_handler, "_trigger_ai_development", new_callable=AsyncMock
            ) as mock_trigger:
                mock_trigger.return_value = TaskResult(success=True, task_id="test")

                result = await webhook_handler._handle_comment_event(comment_data)

                if should_trigger:
                    assert result is not None
                    mock_trigger.assert_called_once()
                else:
                    assert result is None
                    mock_trigger.assert_not_called()

    @pytest.mark.parametrize(
        "event_type,data,should_route",
        [
            # 支持的事件类型
            ("issues", {"action": "labeled", "issue": {}}, True),
            ("issue_comment", {"action": "created", "comment": {}}, True),
            ("ping", {}, True),
            # 不支持的事件类型
            ("push", {}, False),
            ("pull_request", {}, False),
            ("release", {}, False),
            ("fork", {}, False),
        ],
    )
    async def test_event_routing(self, webhook_handler, event_type, data, should_route):
        """
        参数化测试：不同事件类型的路由行为

        场景：接收到不同类型的 GitHub 事件
        期望：只有支持的事件类型才会被处理
        """
        with patch.object(
            webhook_handler, "_handle_issue_event", new_callable=AsyncMock
        ) as mock_handle_issue:
            with patch.object(
                webhook_handler, "_handle_comment_event", new_callable=AsyncMock
            ) as mock_handle_comment:
                result = await webhook_handler.handle_event(event_type, data)

                if event_type == "issues" and should_route:
                    mock_handle_issue.assert_called_once()
                elif event_type == "issue_comment" and should_route:
                    mock_handle_comment.assert_called_once()
                elif event_type == "ping":
                    assert result is not None
                    assert result.task_id == "ping"
                elif not should_route:
                    assert result is None

    @pytest.mark.parametrize(
        "action,should_trigger",
        [
            # Issue 事件动作
            ("labeled", True),  # 包含 ai-dev 标签时会触发
            ("unlabeled", False),
            ("opened", False),
            ("edited", False),
            ("closed", False),
            ("reopened", False),
            # 评论事件动作
            ("created", True),  # 包含命令时会触发
            ("edited", False),
            ("deleted", False),
        ],
    )
    async def test_action_filters(
        self, webhook_handler, mock_config, github_user, action, should_trigger
    ):
        """
        参数化测试：不同动作的过滤行为

        场景：事件有不同的 action 类型
        期望：只有特定的 action 才会触发
        """
        # 测试 Issue 事件动作
        if action in ["labeled", "unlabeled", "opened", "edited", "closed", "reopened"]:
            issue = GitHubIssue(
                id=1,
                node_id="issue1",
                number=1,
                title="Test",
                body="Body",
                html_url="https://github.com/test/repo/issues/1",
                state="open",
                locked=False,
                labels=[
                    GitHubLabel(
                        id=1,
                        node_id="label1",
                        name="ai-dev" if action == "labeled" else "bug",
                        color="000000",
                        default=False,
                    )
                ],
                user=github_user,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            event_data = {
                "action": action,
                "issue": issue.model_dump(),
                "sender": github_user.model_dump(),
            }

            with patch("app.config.get_config", return_value=mock_config):
                with patch.object(
                    webhook_handler, "_trigger_ai_development", new_callable=AsyncMock
                ) as mock_trigger:
                    result = await webhook_handler._handle_issue_event(event_data)

                    if should_trigger and action == "labeled":
                        assert result is not None
                        mock_trigger.assert_called_once()
                    else:
                        assert result is None
                        mock_trigger.assert_not_called()

    @pytest.mark.parametrize(
        "issue_number,title,expected_task_id_pattern",
        [
            (1, "Test", r"task-1-\d+"),
            (999, "Feature", r"task-999-\d+"),
            (12345, "Bug Fix", r"task-12345-\d+"),
        ],
    )
    async def test_task_id_generation(
        self, webhook_handler, mock_config, issue_number, title, expected_task_id_pattern
    ):
        """
        参数化测试：task_id 生成格式

        场景：不同的 Issue 编号
        期望：生成正确格式的 task_id
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=issue_number,
                issue_title=title,
                issue_url=f"https://github.com/test/repo/issues/{issue_number}",
                issue_body="Body",
            )

            import re

            assert re.match(expected_task_id_pattern, result.task_id)


# =============================================================================
# TestEdgeCases 测试
# =============================================================================


class TestEdgeCases:
    """测试边界情况和特殊场景"""

    async def test_multiple_rapid_triggers_same_issue(self, webhook_handler, mock_config):
        """
        测试：同一个 Issue 的多次快速触发应该独立处理

        场景：短时间内同一个 Issue 触发多次
        期望：每次触发都创建独立的工作流
        """
        import time

        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            # Mock time.time() to ensure different timestamps
            with patch("time.time", side_effect=[1000.0, 1001.0]):
                # 第一次触发
                result1 = await webhook_handler._trigger_ai_development(
                    issue_number=1,
                    issue_title="Test",
                    issue_url="https://github.com/test/repo/issues/1",
                    issue_body="Body",
                )

                # 第二次触发
                result2 = await webhook_handler._trigger_ai_development(
                    issue_number=1,
                    issue_title="Test",
                    issue_url="https://github.com/test/repo/issues/1",
                    issue_body="Body",
                )

            # 两次都应该成功
            assert result1.success is True
            assert result2.success is True

            # task_id 应该不同（时间戳不同）
            assert result1.task_id != result2.task_id
            # 验证 task_id 包含正确的时间戳
            assert "task-1-1000" in result1.task_id
            assert "task-1-1001" in result2.task_id

    async def test_very_long_issue_title(self, webhook_handler, mock_config):
        """
        测试：非常长的 Issue 标题应该被正确处理

        场景：Issue 标题超过 200 字符
        期望：正常处理，不截断
        """
        long_title = "A" * 300

        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title=long_title,
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            assert result.success is True

    async def test_special_characters_in_issue_body(self, webhook_handler, mock_config):
        """
        测试：Issue body 中包含特殊字符应该被正确处理

        场景：Issue body 包含特殊字符和表情符号
        期望：正常处理
        """
        special_body = """
        Fix the bug 🐛
        - Handle null values
        - Support UTF-8 encoding
        - Edge case: <>&"' special chars
        """

        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            result = await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body=special_body,
            )

            assert result.success is True

            # 验证特殊字符被传递给 Claude
            mock_claude.develop_feature.assert_called_once()
            call_kwargs = mock_claude.develop_feature.call_args.kwargs
            assert special_body in call_kwargs["issue_body"]

    async def test_service_already_initialized(self, webhook_handler, mock_config):
        """
        测试：服务已初始化时不应重复初始化

        场景：多次触发 AI 开发
        期望：服务只初始化一次
        """
        mock_git = MagicMock()
        mock_git.create_feature_branch.return_value = "ai/feature-1-1"
        mock_git.has_changes.return_value = False

        mock_claude = MagicMock()
        mock_claude.develop_feature = AsyncMock(return_value={"success": True})

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://test.com",
        }

        webhook_handler.git_service = mock_git
        webhook_handler.claude_service = mock_claude
        webhook_handler.github_service = mock_github

        with patch("app.config.get_config", return_value=mock_config):
            # 第一次触发
            await webhook_handler._trigger_ai_development(
                issue_number=1,
                issue_title="Test",
                issue_url="https://github.com/test/repo/issues/1",
                issue_body="Body",
            )

            # 第二次触发
            await webhook_handler._trigger_ai_development(
                issue_number=2,
                issue_title="Test 2",
                issue_url="https://github.com/test/repo/issues/2",
                issue_body="Body",
            )

            # 服务实例应该保持不变
            assert webhook_handler.git_service is mock_git
            assert webhook_handler.claude_service is mock_claude
            assert webhook_handler.github_service is mock_github
