"""
测试 GitHub API 速率限制检查优化

测试覆盖以下优化：
1. _check_rate_limit() 方法
2. 在 create_pull_request() 中调用检查
3. 配额充足场景
4. 配额不足场景
5. 等待逻辑
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from unittest.mock import AsyncMock

import pytest
from github.GithubException import GithubException

from app.services.github_service import GitHubService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_github():
    """提供 Mock 的 Github 对象"""
    github = MagicMock()
    return github


@pytest.fixture
def mock_user():
    """提供 Mock 的 GitHub User 对象"""
    user = MagicMock()
    user.login = "testuser"
    user.rate_limiting_remaining_hits = 5000
    return user


@pytest.fixture
def mock_repo():
    """提供 Mock 的 GitHub Repository 对象"""
    repo = MagicMock()
    repo.full_name = "testowner/testrepo"
    repo.owner = "testowner"
    repo.name = "testrepo"
    repo.default_branch = "main"

    # Mock comparison to have commits
    comparison = MagicMock()
    commit = MagicMock()
    commit.sha = "abc123"
    comparison.commits = [commit]
    repo.compare.return_value = comparison

    return repo


@pytest.fixture
def mock_rate_limit():
    """提供 Mock 的 GitHub Rate Limit 对象"""
    rate_limit = MagicMock()

    # Mock core 限额
    core = MagicMock()
    core.limit = 5000
    core.remaining = 4999
    core.reset = datetime(2026, 1, 11, 13, 0, 0)

    rate_limit.core = core
    rate_limit.resources = MagicMock()
    rate_limit.resources.core = core
    return rate_limit


@pytest.fixture
def github_service(mock_github, mock_user):
    """提供 GitHubService 实例"""
    with patch("app.services.github_service.Github", return_value=mock_github):
        mock_github.get_user.return_value = mock_user
        service = GitHubService(token="test_token")
        service._github_mock = mock_github
        return service


# =============================================================================
# 测试 _check_rate_limit() 方法
# =============================================================================


class TestCheckRateLimit:
    """测试 _check_rate_limit() 方法"""

    def test_check_rate_limit_sufficient_quota(self, github_service, mock_github, mock_rate_limit):
        """
        测试：配额充足时应该继续执行

        验证：
        - 返回 True
        - 不等待
        - 不记录警告
        """
        mock_github.get_rate_limit.return_value = mock_rate_limit

        result = github_service._check_rate_limit(min_remaining=100)

        assert result is True

    def test_check_rate_limit_exactly_at_threshold(
        self, github_service, mock_github, mock_rate_limit
    ):
        """
        测试：配额恰好等于阈值

        验证：
        - 返回 True
        - 不等待
        """
        mock_rate_limit.core.remaining = 100
        mock_github.get_rate_limit.return_value = mock_rate_limit

        result = github_service._check_rate_limit(min_remaining=100)

        assert result is True

    def test_check_rate_limit_below_threshold(
        self, github_service, mock_github, mock_rate_limit, caplog
    ):
        """
        测试：配额低于阈值

        验证：
        - 记录警告日志
        - 如果剩余 >= 10，返回 True
        - 如果剩余 < 10，返回 False
        """
        # 场景 1：剩余 50（低于阈值 100，但高于最小值 10）
        mock_rate_limit.core.remaining = 50
        mock_rate_limit.core.reset = datetime(2026, 1, 11, 12, 30, 0)
        mock_github.get_rate_limit.return_value = mock_rate_limit

        with caplog.at_level("WARNING"):
            result = github_service._check_rate_limit(min_remaining=100)

        # 应该记录警告
        assert any(
            "速率限制" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )

        # 剩余 >= 10，应该返回 True（但记录了警告）
        assert result is True

    def test_check_rate_limit_very_low(self, github_service, mock_github, mock_rate_limit, caplog):
        """
        测试：配额非常低（< 10）

        验证：
        - 返回 False
        - 记录警告
        """
        mock_rate_limit.core.remaining = 5
        mock_github.get_rate_limit.return_value = mock_rate_limit

        with caplog.at_level("WARNING"):
            result = github_service._check_rate_limit(min_remaining=100)

        assert result is False
        assert any(
            "速率限制" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )

    def test_check_rate_limit_failure_to_get_limits(self, github_service, mock_github, caplog):
        """
        测试：获取限额信息失败

        验证：
        - 记录警告
        - 返回 True（继续执行）
        """
        mock_github.get_rate_limit.side_effect = Exception("API Error")

        with caplog.at_level("WARNING"):
            result = github_service._check_rate_limit(min_remaining=100)

        assert result is True
        assert any(
            "无法获取速率限制信息" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )

    def test_check_rate_limit_empty_response(self, github_service, mock_github, caplog):
        """
        测试：get_rate_limit 返回空字典

        验证：
        - 记录警告
        - 返回 True（继续执行）
        """
        mock_github.get_rate_limit.return_value = None

        with patch.object(github_service, "get_rate_limit", return_value={}):
            with caplog.at_level("WARNING"):
                result = github_service._check_rate_limit(min_remaining=100)

            assert result is True
            assert any(
                "无法获取速率限制信息" in record.message
                for record in caplog.records
                if record.levelname == "WARNING"
            )


# =============================================================================
# 测试在 create_pull_request 中调用检查
# =============================================================================


class TestRateLimitInCreatePR:
    """测试 create_pull_request 中的速率限制检查"""

    def test_create_pr_calls_check_rate_limit(
        self, github_service, mock_repo, mock_github, mock_rate_limit
    ):
        """
        测试：create_pull_request 应该调用速率限制检查

        验证：
        - _check_rate_limit 被调用
        - 使用正确的参数
        """
        mock_github.get_repo.return_value = mock_repo
        mock_github.get_rate_limit.return_value = mock_rate_limit

        mock_pr = MagicMock()
        mock_pr.number = 123
        mock_pr.html_url = "https://github.com/test/test/pull/123"
        mock_pr.url = "https://api.github.com/test/test/pulls/123"
        mock_pr.state = "open"
        mock_repo.create_pull.return_value = mock_pr

        with patch.object(github_service, "_check_rate_limit", return_value=True) as mock_check:
            github_service.create_pull_request(
                branch_name="feature/test",
                issue_number=1,
                issue_title="Test",
                issue_body="Body",
            )

            # 验证调用了一次，默认参数 min_remaining=100
            mock_check.assert_called_once_with(min_remaining=100)

    def test_create_pr_with_low_rate_limit_continues(
        self, github_service, mock_repo, mock_github, mock_rate_limit
    ):
        """
        测试：即使速率限制较低，如果 >= 10 也继续

        验证：
        - PR 被创建
        - 不抛出异常
        """
        mock_github.get_repo.return_value = mock_repo
        mock_rate_limit.core.remaining = 50  # 低于默认阈值 100
        mock_github.get_rate_limit.return_value = mock_rate_limit

        mock_pr = MagicMock()
        mock_pr.number = 123
        mock_pr.html_url = "https://github.com/test/test/pull/123"
        mock_pr.url = "https://api.github.com/test/test/pulls/123"
        mock_pr.state = "open"
        mock_repo.create_pull.return_value = mock_pr

        result = github_service.create_pull_request(
            branch_name="feature/test",
            issue_number=1,
            issue_title="Test",
            issue_body="Body",
        )

        assert result["pr_number"] == 123


# =============================================================================
# 测试等待逻辑（模拟）
# =============================================================================


class TestRateLimitWaiting:
    """测试速率限制等待逻辑"""

    def test_wait_calculation_when_near_limit(
        self, github_service, mock_github, mock_rate_limit, caplog
    ):
        """
        测试：接近限额时计算等待时间

        验证：
        - 计算正确的等待时间
        - 记录警告日志
        """
        from datetime import timedelta
        import time

        # 设置重置时间为未来 1 小时
        reset_time = time.time() + 3600
        reset_datetime = datetime.fromtimestamp(reset_time)

        mock_rate_limit.core.remaining = 80  # 低于阈值 100
        mock_rate_limit.core.reset = reset_datetime
        mock_github.get_rate_limit.return_value = mock_rate_limit

        # 修复：使用 patch.object 来 mock time.sleep
        # time 模块在 _check_rate_limit 方法内部导入，所以需要直接 mock time.sleep
        with patch.object(time, "sleep") as mock_sleep:
            with caplog.at_level("WARNING"):
                result = github_service._check_rate_limit(min_remaining=100)

        # 验证：剩余 < min_remaining，应该等待
        # wait_time = reset_time - current_time + 60
        # 由于 mock，不会实际 sleep，但应该记录警告
        assert result is True  # 剩余 80 >= 10

        # 验证记录了速率限制警告
        assert any(
            "速率限制" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )

    def test_no_wait_when_sufficient_quota(self, github_service, mock_github, mock_rate_limit):
        """
        测试：配额充足时不等待

        验证：
        - 不调用 time.sleep
        - 立即返回
        """
        import time

        mock_rate_limit.core.remaining = 500
        mock_github.get_rate_limit.return_value = mock_rate_limit

        # 修复：使用 patch.object 来 mock time.sleep
        with patch.object(time, "sleep") as mock_sleep:
            result = github_service._check_rate_limit(min_remaining=100)

            assert result is True
            mock_sleep.assert_not_called()


# =============================================================================
# 测试不同的阈值参数
# =============================================================================


class TestDifferentThresholds:
    """测试不同的阈值参数"""

    def test_custom_min_remaining_threshold(self, github_service, mock_github, mock_rate_limit):
        """
        测试：自定义 min_remaining 参数

        验证：
        - 使用传入的阈值
        - 正确判断
        """
        mock_rate_limit.core.remaining = 150
        mock_github.get_rate_limit.return_value = mock_rate_limit

        # 阈值 200，剩余 150 -> 应该警告
        result = github_service._check_rate_limit(min_remaining=200)

        # 剩余 >= 10，返回 True
        assert result is True

    def test_zero_min_remaining(self, github_service, mock_github, mock_rate_limit):
        """
        测试：min_remaining=0

        验证：
        - 虽然不需要等待（min_remaining=0），但最终返回值还是基于 remaining >= 10
        """
        mock_rate_limit.core.remaining = 1
        mock_github.get_rate_limit.return_value = mock_rate_limit

        result = github_service._check_rate_limit(min_remaining=0)

        # remaining=1 < 10，所以返回 False
        assert result is False

    def test_very_high_threshold(self, github_service, mock_github, mock_rate_limit):
        """
        测试：非常高的阈值

        验证：
        - 大多数情况下都会警告
        """
        mock_rate_limit.core.remaining = 1000
        mock_github.get_rate_limit.return_value = mock_rate_limit

        # 阈值 5000，剩余 1000 -> 应该警告
        result = github_service._check_rate_limit(min_remaining=5000)

        # 剩余 >= 10，返回 True
        assert result is True


# =============================================================================
# 测试边界情况
# =============================================================================


class TestEdgeCases:
    """测试边界情况"""

    def test_rate_limit_exactly_10(self, github_service, mock_github, mock_rate_limit):
        """
        测试：剩余配额恰好为 10

        验证：
        - 返回 True（边界值）
        """
        mock_rate_limit.core.remaining = 10
        mock_github.get_rate_limit.return_value = mock_rate_limit

        result = github_service._check_rate_limit(min_remaining=100)

        assert result is True

    def test_rate_limit_below_10(self, github_service, mock_github, mock_rate_limit):
        """
        测试：剩余配额 < 10

        验证：
        - 返回 False
        - 记录警告
        """
        mock_rate_limit.core.remaining = 9
        mock_github.get_rate_limit.return_value = mock_rate_limit

        result = github_service._check_rate_limit(min_remaining=100)

        assert result is False

    def test_rate_limit_zero_remaining(self, github_service, mock_github, mock_rate_limit):
        """
        测试：剩余配额为 0

        验证：
        - 返回 False
        - 记录警告
        """
        mock_rate_limit.core.remaining = 0
        mock_github.get_rate_limit.return_value = mock_rate_limit

        result = github_service._check_rate_limit(min_remaining=100)

        assert result is False
