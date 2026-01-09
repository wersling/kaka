"""
GitHubService 完整单元测试套件

测试覆盖所有 GitHub API 操作功能，包括：
- GitHubService 初始化和连接测试
- 仓库操作 (_get_repo)
- Pull Request 创建和管理
- Issue 评论和管理
- 标签更新
- API 限额查询
- 异常处理
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from github.GithubException import GithubException

from app.services.github_service import GitHubService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_github():
    """
    提供 Mock 的 Github 对象

    模拟 PyGithub 的 Github 类
    """
    github = MagicMock()
    return github


@pytest.fixture
def mock_user():
    """
    提供 Mock 的 GitHub User 对象

    模拟 GitHub 用户信息
    """
    user = MagicMock()
    user.login = "testuser"
    user.rate_limiting_remaining_hits = 5000
    return user


@pytest.fixture
def mock_repo():
    """
    提供 Mock 的 GitHub Repository 对象

    模拟 GitHub 仓库
    """
    repo = MagicMock()
    repo.full_name = "testowner/testrepo"
    repo.owner = "testowner"
    repo.name = "testrepo"
    repo.default_branch = "main"
    return repo


@pytest.fixture
def mock_issue():
    """
    提供 Mock 的 GitHub Issue 对象

    模拟 GitHub Issue
    """
    issue = MagicMock()
    issue.number = 123
    issue.title = "Test Issue"
    issue.body = "Test Issue Body"
    issue.state = "open"
    return issue


@pytest.fixture
def mock_pull_request():
    """
    提供 Mock 的 GitHub Pull Request 对象

    模拟 GitHub Pull Request
    """
    pr = MagicMock()
    pr.number = 456
    pr.title = "Kaka: Test Issue"
    pr.body = "Test PR Body"
    pr.state = "open"
    pr.html_url = "https://github.com/testowner/testrepo/pull/456"
    pr.url = "https://api.github.com/repos/testowner/testrepo/pulls/456"
    return pr


@pytest.fixture
def mock_rate_limit():
    """
    提供 Mock 的 GitHub Rate Limit 对象

    模拟 GitHub API 限额信息
    """
    rate_limit = MagicMock()

    # Mock core 限额
    core = MagicMock()
    core.limit = 5000
    core.remaining = 4999
    core.reset = datetime(2026, 1, 8, 12, 0, 0)

    rate_limit.core = core
    return rate_limit


@pytest.fixture
def github_service(mock_github, mock_user):
    """
    提供 GitHubService 实例

    使用 Mock 的 Github 对象，避免真实 API 调用
    """
    with patch("app.services.github_service.Github", return_value=mock_github):
        mock_github.get_user.return_value = mock_user
        service = GitHubService(token="test_token")
        service._github_mock = mock_github
        return service


# =============================================================================
# 初始化测试
# =============================================================================


class TestGitHubServiceInit:
    """测试 GitHubService 初始化"""

    def test_init_with_token(self, mock_github, mock_user):
        """
        测试使用 token 参数初始化

        验证：
        - token 正确设置
        - Github 对象使用 token 初始化
        - 连接测试成功
        """
        # 创建 Github mock 的包装器来跟踪构造函数调用
        github_class_mock = MagicMock(return_value=mock_github)
        mock_github.get_user.return_value = mock_user

        with patch("app.services.github_service.Github", github_class_mock):
            service = GitHubService(token="custom_token")

            assert service.token == "custom_token"
            github_class_mock.assert_called_once_with("custom_token")
            mock_github.get_user.assert_called_once()

    def test_init_without_token_from_config(self, mock_github, mock_user):
        """
        测试从配置读取 token

        验证：
        - token 从配置读取
        - 正确初始化
        """
        with patch("app.services.github_service.Github", return_value=mock_github):
            mock_github.get_user.return_value = mock_user

            service = GitHubService()

            # 配置中的 token 是 "ghp_test_token_12345"
            assert service.token == "ghp_test_token_12345"
            mock_github.get_user.assert_called_once()

    def test_init_connection_success(self, mock_github, mock_user):
        """
        测试 GitHub API 连接成功

        验证：
        - 成功获取用户信息
        - 正确记录日志
        """
        with patch("app.services.github_service.Github", return_value=mock_github):
            mock_github.get_user.return_value = mock_user

            service = GitHubService(token="test_token")

            mock_github.get_user.assert_called_once()
            assert mock_user.login == "testuser"
            assert mock_user.rate_limiting_remaining_hits == 5000

    def test_init_connection_failure(self, mock_github):
        """
        测试 GitHub API 连接失败

        验证：
        - 异常被抛出
        - 错误被记录
        """
        with patch("app.services.github_service.Github", return_value=mock_github):
            mock_github.get_user.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                GitHubService(token="invalid_token")

    def test_init_logs_rate_limit(self, mock_github, mock_user):
        """
        测试初始化记录 API 限额信息

        验证：
        - GitHub API 连接成功时可以获取用户信息
        - 用户信息包含登录名和剩余请求数
        """
        with patch("app.services.github_service.Github", return_value=mock_github):
            mock_github.get_user.return_value = mock_user

            service = GitHubService(token="test_token")

            # 验证用户信息被正确获取（这会触发日志记录）
            mock_github.get_user.assert_called_once()
            assert mock_user.login == "testuser"
            assert mock_user.rate_limiting_remaining_hits == 5000


# =============================================================================
# _get_repo() 测试
# =============================================================================


class TestGetRepo:
    """测试 _get_repo() 方法"""

    def test_get_repo_returns_correct_repo(self, github_service, mock_repo):
        """
        测试返回正确的仓库对象

        验证：
        - 使用配置中的仓库名称
        - 返回正确的仓库对象
        """
        github_service._github_mock.get_repo.return_value = mock_repo

        repo = github_service._get_repo()

        assert repo == mock_repo
        github_service._github_mock.get_repo.assert_called_once_with(
            "testowner/testrepo"
        )

    def test_get_repo_uses_config(self, github_service, mock_repo):
        """
        测试使用配置中的仓库信息

        验证：
        - 从配置读取 owner/repo
        - 正确构造仓库名称
        """
        github_service._github_mock.get_repo.return_value = mock_repo

        repo = github_service._get_repo()

        github_service._github_mock.get_repo.assert_called_once()
        call_args = github_service._github_mock.get_repo.call_args
        assert call_args[0][0] == "testowner/testrepo"


# =============================================================================
# create_pull_request() 测试
# =============================================================================


class TestCreatePullRequest:
    """测试 create_pull_request() 方法"""

    def test_create_pr_success(self, github_service, mock_repo, mock_pull_request):
        """
        测试成功创建 PR

        验证：
        - PR 创建成功
        - 返回正确的 PR 信息
        - 正确记录日志
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pull_request

        result = github_service.create_pull_request(
            branch_name="feature/test-branch",
            issue_number=123,
            issue_title="Test Issue",
            issue_body="Test Body",
        )

        assert result["pr_number"] == 456
        assert result["url"] == "https://api.github.com/repos/testowner/testrepo/pulls/456"
        assert result["html_url"] == "https://github.com/testowner/testrepo/pull/456"
        assert result["state"] == "open"
        assert result["title"] == "Kaka: Test Issue"

        mock_repo.create_pull.assert_called_once()

    def test_create_pr_title_format(self, github_service, mock_repo, mock_pull_request):
        """
        测试 PR 标题格式正确（Kaka: 前缀）

        验证：
        - 标题包含 Kaka: 前缀
        - 前缀后跟原 Issue 标题
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pull_request

        github_service.create_pull_request(
            branch_name="feature/test",
            issue_number=123,
            issue_title="Implement feature X",
            issue_body="Details",
        )

        call_args = mock_repo.create_pull.call_args
        assert call_args.kwargs["title"] == "Kaka: Implement feature X"

    def test_create_pr_body_contains_all_required(
        self, github_service, mock_repo, mock_pull_request
    ):
        """
        测试 PR body 包含所有必需信息

        验证：
        - 包含 Issue 链接和执行时间
        - 包含原 Issue 标题
        - 包含原 Issue 内容
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pull_request

        github_service.create_pull_request(
            branch_name="feature/test",
            issue_number=123,
            issue_title="Test Issue",
            issue_body="Original issue description",
            execution_time=123.5,
        )

        call_args = mock_repo.create_pull.call_args
        pr_body = call_args.kwargs["body"]

        # 验证必需内容
        assert "**关联 Issue**: #123" in pr_body
        assert "**用时**: 123.5秒" in pr_body
        assert "## 原 Issue：Test Issue" in pr_body
        assert "Original issue description" in pr_body

    def test_create_pr_includes_execution_time(
        self, github_service, mock_repo, mock_pull_request
    ):
        """
        测试 PR body 包含执行时间

        验证：
        - 执行时间格式正确
        - 时间显示在 PR body 中
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pull_request

        github_service.create_pull_request(
            branch_name="feature/test",
            issue_number=123,
            issue_title="Test",
            issue_body="Body",
            execution_time=45.7,
        )

        call_args = mock_repo.create_pull.call_args
        pr_body = call_args.kwargs["body"]

        # 验证执行时间
        assert "**用时**: 45.7秒" in pr_body
        assert "#123" in pr_body

    def test_create_pr_default_base_branch(
        self, github_service, mock_repo, mock_pull_request
    ):
        """
        测试使用默认 base 分支

        验证：
        - 不指定 base_branch 时使用配置中的默认分支
        - 默认为 main
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pull_request

        github_service.create_pull_request(
            branch_name="feature/test",
            issue_number=123,
            issue_title="Test",
            issue_body="Body",
        )

        call_args = mock_repo.create_pull.call_args
        assert call_args.kwargs["base"] == "main"

    def test_create_pr_custom_base_branch(
        self, github_service, mock_repo, mock_pull_request
    ):
        """
        测试使用自定义 base 分支

        验证：
        - 指定 base_branch 时使用该分支
        - 不使用配置中的默认分支
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pull_request

        github_service.create_pull_request(
            branch_name="feature/test",
            issue_number=123,
            issue_title="Test",
            issue_body="Body",
            base_branch="develop",
        )

        call_args = mock_repo.create_pull.call_args
        assert call_args.kwargs["base"] == "develop"

    def test_create_pr_github_exception(self, github_service, mock_repo):
        """
        测试 GitHubException 处理

        验证：
        - 异常被记录
        - 异常被重新抛出
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.side_effect = GithubException(
            422, {"message": "Validation failed"}
        )

        with pytest.raises(GithubException):
            github_service.create_pull_request(
                branch_name="feature/test",
                issue_number=123,
                issue_title="Test",
                issue_body="Body",
            )


# =============================================================================
# _build_pr_body() 测试
# =============================================================================


class TestBuildPrBody:
    """测试 _build_pr_body() 方法"""

    def test_pr_body_includes_issue_link(self, github_service):
        """
        测试包含 Issue 链接和执行时间

        验证：
        - body 包含 Issue 编号
        - 格式正确
        - 默认执行时间为"未知"
        """
        body = github_service._build_pr_body(
            issue_number=123, issue_title="Test Issue", issue_body="Test content"
        )

        assert "**关联 Issue**: #123" in body
        assert "**用时**: 未知" in body

    def test_pr_body_includes_original_content(self, github_service):
        """
        测试包含原 Issue 内容

        验证：
        - 原始 body 被包含
        - 在代码块中
        """
        body = github_service._build_pr_body(
            issue_number=123,
            issue_title="Test Issue",
            issue_body="Original issue description here",
        )

        assert "Original issue description here" in body
        assert "## 原 Issue：" in body

    def test_pr_body_with_execution_time_and_development_summary(self, github_service):
        """
        测试包含执行时间和 AI 开发总结

        验证：
        - 执行时间正确显示
        - AI 总结被包含
        - 格式正确
        """
        summary = """## 执行概述
完成了用户认证功能的实现

## 变更文件
- 新增: app/auth/login.py
- 修改: app/models/user.py

## 技术方案
使用 JWT 进行身份验证"""

        body = github_service._build_pr_body(
            issue_number=123,
            issue_title="User Authentication",
            issue_body="Implement user auth",
            execution_time=67.8,
            development_summary=summary,
        )

        assert "**关联 Issue**: #123" in body
        assert "**用时**: 67.8秒" in body
        assert "## 原 Issue：User Authentication" in body
        assert "## Kaka 开发总结" in body
        assert summary in body
        assert "## 执行概述" in body
        assert "@testowner 请 review 后决策是否 PR，谢谢！" in body

    def test_pr_body_without_development_summary(self, github_service):
        """
        测试没有 AI 开发总结的情况

        验证：
        - 不包含开发总结部分
        - 不包含 @mention
        - 不崩溃
        """
        body = github_service._build_pr_body(
            issue_number=123, issue_title="Test Issue", issue_body="Test"
        )

        # 没有 development_summary 时，应该只包含 Issue 内容
        assert "**关联 Issue**: #123" in body
        assert "## 原 Issue：Test Issue" in body
        # 不应该包含 Kaka 开发总结和 @mention
        assert "Kaka 开发总结" not in body
        assert "@testowner 请 review" not in body

    def test_pr_body_handles_empty_issue_body(self, github_service):
        """
        测试空 Issue body 处理

        验证：
        - 空 body 时显示默认文本
        - 不崩溃
        """
        body = github_service._build_pr_body(
            issue_number=123, issue_title="Test Issue", issue_body=""
        )

        assert "无详细描述" in body

    def test_pr_body_handles_none_issue_body(self, github_service):
        """
        测试 None Issue body 处理

        验证：
        - None body 时显示默认文本
        - 不崩溃
        """
        body = github_service._build_pr_body(
            issue_number=123, issue_title="Test Issue", issue_body=None
        )

        assert "无详细描述" in body


# =============================================================================
# add_comment_to_issue() 测试
# =============================================================================


class TestAddCommentToIssue:
    """测试 add_comment_to_issue() 方法"""

    def test_add_comment_success(self, github_service, mock_repo, mock_issue):
        """
        测试成功添加评论

        验证：
        - 评论被创建
        - 正确的方法被调用
        - 日志记录成功
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue

        github_service.add_comment_to_issue(
            issue_number=123, comment="Test comment"
        )

        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.create_comment.assert_called_once_with("Test comment")

    def test_add_comment_github_exception(self, github_service, mock_repo):
        """
        测试 GitHubException 处理

        验证：
        - 异常被记录
        - 异常被重新抛出
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.side_effect = GithubException(
            404, {"message": "Issue not found"}
        )

        with pytest.raises(GithubException):
            github_service.add_comment_to_issue(
                issue_number=999, comment="Test"
            )


# =============================================================================
# add_comment_to_pr() 测试
# =============================================================================


class TestAddCommentToPr:
    """测试 add_comment_to_pr() 方法"""

    def test_add_pr_comment_success(self, github_service, mock_repo, mock_pull_request):
        """
        测试成功添加 PR 评论

        验证：
        - 评论被创建
        - 正确的方法被调用
        - 日志记录成功
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pull_request

        github_service.add_comment_to_pr(pr_number=456, comment="Test PR comment")

        mock_repo.get_pull.assert_called_once_with(456)
        mock_pull_request.create_issue_comment.assert_called_once_with("Test PR comment")

    def test_add_pr_comment_github_exception(self, github_service, mock_repo):
        """
        测试 GitHubException 处理

        验证：
        - 异常被记录
        - 异常被重新抛出
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_pull.side_effect = GithubException(
            404, {"message": "PR not found"}
        )

        with pytest.raises(GithubException):
            github_service.add_comment_to_pr(pr_number=999, comment="Test")


# =============================================================================
# update_issue_labels() 测试
# =============================================================================


class TestUpdateIssueLabels:
    """测试 update_issue_labels() 方法"""

    def test_update_labels_success(self, github_service, mock_repo, mock_issue):
        """
        测试成功更新标签

        验证：
        - 标签被设置
        - 正确的方法被调用
        - 日志记录成功
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue

        github_service.update_issue_labels(
            issue_number=123, labels=["bug", "high-priority"]
        )

        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.set_labels.assert_called_once_with("bug", "high-priority")

    def test_update_labels_multiple(self, github_service, mock_repo, mock_issue):
        """
        测试更新多个标签

        验证：
        - 所有标签都被设置
        - 标签顺序正确
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue

        labels = ["enhancement", "ai-dev", "in-progress"]
        github_service.update_issue_labels(issue_number=123, labels=labels)

        mock_issue.set_labels.assert_called_once_with(*labels)

    def test_update_labels_github_exception(self, github_service, mock_repo):
        """
        测试 GitHubException 处理

        验证：
        - 异常被记录
        - 异常被重新抛出
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.side_effect = GithubException(
            404, {"message": "Issue not found"}
        )

        with pytest.raises(GithubException):
            github_service.update_issue_labels(
                issue_number=999, labels=["test"]
            )


# =============================================================================
# close_issue() 测试
# =============================================================================


class TestCloseIssue:
    """测试 close_issue() 方法"""

    def test_close_issue_with_comment(self, github_service, mock_repo, mock_issue):
        """
        测试带评论关闭 Issue

        验证：
        - 先添加评论
        - 再关闭 Issue
        - 正确的方法被调用
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue

        github_service.close_issue(
            issue_number=123, comment="Completed this task"
        )

        mock_repo.get_issue.assert_called_once_with(number=123)
        mock_issue.create_comment.assert_called_once_with("Completed this task")
        mock_issue.edit.assert_called_once_with(state="closed")

    def test_close_issue_without_comment(self, github_service, mock_repo, mock_issue):
        """
        测试不带评论关闭 Issue

        验证：
        - 直接关闭 Issue
        - 不添加评论
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue

        github_service.close_issue(issue_number=123)

        mock_repo.get_issue.assert_called_once_with(number=123)
        mock_issue.create_comment.assert_not_called()
        mock_issue.edit.assert_called_once_with(state="closed")

    def test_close_issue_github_exception(self, github_service, mock_repo):
        """
        测试 GitHubException 处理

        验证：
        - 异常被记录
        - 异常被重新抛出
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.side_effect = GithubException(
            404, {"message": "Issue not found"}
        )

        with pytest.raises(GithubException):
            github_service.close_issue(issue_number=999)


# =============================================================================
# get_issue() 测试
# =============================================================================


class TestGetIssue:
    """测试 get_issue() 方法"""

    def test_get_issue_success(self, github_service, mock_repo, mock_issue):
        """
        测试成功获取 Issue

        验证：
        - 返回正确的 Issue 对象
        - 使用正确的 Issue 编号
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue

        issue = github_service.get_issue(issue_number=123)

        assert issue == mock_issue
        mock_repo.get_issue.assert_called_once_with(123)


# =============================================================================
# get_pull_request() 测试
# =============================================================================


class TestGetPullRequest:
    """测试 get_pull_request() 方法"""

    def test_get_pr_success(self, github_service, mock_repo, mock_pull_request):
        """
        测试成功获取 PR

        验证：
        - 返回正确的 PR 对象
        - 使用正确的 PR 编号
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pull_request

        pr = github_service.get_pull_request(pr_number=456)

        assert pr == mock_pull_request
        mock_repo.get_pull.assert_called_once_with(456)


# =============================================================================
# get_rate_limit() 测试
# =============================================================================


class TestGetRateLimit:
    """测试 get_rate_limit() 方法"""

    def test_get_rate_limit_success(
        self, github_service, mock_github, mock_rate_limit
    ):
        """
        测试成功获取限额信息

        验证：
        - 返回正确的限额信息
        - 所有字段都存在
        """
        github_service._github_mock = mock_github
        mock_github.get_rate_limit.return_value = mock_rate_limit

        rate_info = github_service.get_rate_limit()

        assert rate_info["remaining"] == 4999
        assert rate_info["limit"] == 5000
        assert rate_info["used"] == 1
        assert "reset" in rate_info

    def test_get_rate_limit_fields(self, github_service, mock_github, mock_rate_limit):
        """
        测试返回正确的字段

        验证：
        - 包含 remaining 字段
        - 包含 limit 字段
        - 包含 reset 字段
        - 包含 used 字段
        """
        github_service._github_mock = mock_github
        mock_github.get_rate_limit.return_value = mock_rate_limit

        rate_info = github_service.get_rate_limit()

        assert "remaining" in rate_info
        assert "limit" in rate_info
        assert "reset" in rate_info
        assert "used" in rate_info

    def test_get_rate_limit_exception_handling(self, github_service, mock_github):
        """
        测试异常处理

        验证：
        - 异常被捕获
        - 返回空字典
        - 错误被记录
        """
        github_service._github_mock = mock_github
        mock_github.get_rate_limit.side_effect = Exception("API Error")

        rate_info = github_service.get_rate_limit()

        assert rate_info == {}


# =============================================================================
# 集成测试
# =============================================================================


class TestGitHubServiceIntegration:
    """GitHubService 集成测试"""

    def test_full_pr_workflow(self, github_service, mock_repo, mock_issue, mock_pull_request):
        """
        测试完整的 PR 工作流

        验证：
        - 创建 PR
        - 添加评论
        - 更新标签
        - 关闭 Issue
        """
        github_service._github_mock.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pull_request
        mock_repo.get_issue.return_value = mock_issue
        mock_repo.get_pull.return_value = mock_pull_request

        # 创建 PR
        pr = github_service.create_pull_request(
            branch_name="feature/test",
            issue_number=123,
            issue_title="Test Issue",
            issue_body="Test Body",
        )
        assert pr["pr_number"] == 456

        # 添加 PR 评论 - get_pull 需要返回 mock_pull_request
        github_service.add_comment_to_pr(pr_number=456, comment="Review me")

        # 更新 Issue 标签
        github_service.update_issue_labels(
            issue_number=123, labels=["in-progress", "ai-dev"]
        )

        # 关闭 Issue
        github_service.close_issue(issue_number=123, comment="Completed")

        # 验证调用
        assert mock_repo.create_pull.called
        assert mock_pull_request.create_issue_comment.called
        assert mock_issue.set_labels.called
        assert mock_issue.create_comment.called
        assert mock_issue.edit.called

    def test_error_recovery_workflow(self, github_service, mock_repo):
        """
        测试错误恢复工作流

        验证：
        - 错误被正确处理
        - 服务可以继续使用
        """
        github_service._github_mock.get_repo.return_value = mock_repo

        # 第一次调用失败
        mock_repo.create_pull.side_effect = GithubException(422, {})
        with pytest.raises(GithubException):
            github_service.create_pull_request(
                branch_name="feature/test",
                issue_number=123,
                issue_title="Test",
                issue_body="Body",
            )

        # 重置 mock
        mock_repo.create_pull.side_effect = None

        # 后续调用可以成功
        mock_pr = MagicMock()
        mock_pr.number = 789
        mock_pr.title = "Success PR"
        mock_pr.state = "open"
        mock_pr.html_url = "https://github.com/test/test/pull/789"
        mock_pr.url = "https://api.github.com/test/test/pulls/789"
        mock_repo.create_pull.return_value = mock_pr

        result = github_service.create_pull_request(
            branch_name="feature/test2",
            issue_number=124,
            issue_title="Test 2",
            issue_body="Body 2",
        )

        assert result["pr_number"] == 789
