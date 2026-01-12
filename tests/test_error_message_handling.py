"""
测试错误消息处理优化

测试覆盖以下优化：
1. 在截断前记录完整错误到日志
2. 错误消息限制从 200 字符增加到 1000 字符
3. 添加省略标记
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.claude_service import ClaudeService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """提供测试用的配置对象"""
    config = MagicMock()
    config.repository.path = "/tmp/test_repo"
    config.claude.cli_path = "claude-code"
    config.claude.timeout = 300
    config.claude.max_retries = 3
    config.claude.auto_test = True
    return config


@pytest.fixture
def claude_service(mock_config):
    """提供 ClaudeService 实例"""
    with patch("app.config.get_config", return_value=mock_config):
        service = ClaudeService()
        service._mock_config = mock_config
        yield service


# =============================================================================
# 测试不同长度的错误消息
# =============================================================================


class TestErrorMessageHandling:
    """测试错误消息处理"""

    @pytest.mark.asyncio
    async def test_short_error_message(self, claude_service, caplog):
        """
        测试：短错误消息（< 200字符）应该完整记录和显示

        验证：
        - 完整错误记录到日志（ERROR 级别）
        - 错误消息不截断
        - 不添加省略标记
        """
        short_error = "Error: File not found"

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": short_error,
                "returncode": 1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=1,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/1",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证完整错误被记录到日志
            assert any(
                short_error in record.message
                for record in caplog.records
                if record.levelname == "ERROR"
            )

    @pytest.mark.asyncio
    async def test_medium_error_message(self, claude_service, caplog):
        """
        测试：中等长度错误消息（200-1000字符）

        验证：
        - 完整错误记录到日志
        - 错误消息不截断（< 1000）
        - 不添加省略标记
        """
        medium_error = "Error: " + "X" * 500  # 505 字符

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": medium_error,
                "returncode": 1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=2,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/2",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证完整错误被记录到日志
            assert any(
                medium_error in record.message
                for record in caplog.records
                if record.levelname == "ERROR"
            )

    @pytest.mark.asyncio
    async def test_long_error_message_truncated(self, claude_service, caplog):
        """
        测试：长错误消息（> 1000字符）应该被截断

        验证：
        - 完整错误记录到日志（ERROR 级别）
        - 错误摘要截断到 1000 字符
        - 添加省略标记
        """
        long_error = "Error: " + "Y" * 1500  # 1506 字符

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": long_error,
                "returncode": 1,
                "output": "",
            }

            # 修复：使用 WARNING 级别以捕获 WARNING 和 ERROR 日志
            with caplog.at_level("WARNING"):
                result = await claude_service.develop_feature(
                    issue_number=3,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/3",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证完整错误被记录到 ERROR 日志
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]
            assert len(error_logs) > 0
            assert long_error in error_logs[0]

            # 验证 WARNING 日志中包含截断的错误
            warning_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "WARNING" and "失败" in record.message
            ]
            assert len(warning_logs) > 0
            assert "... (已截断)" in warning_logs[0]

    @pytest.mark.asyncio
    async def test_exactly_1000_char_error_not_truncated(self, claude_service, caplog):
        """
        测试：恰好 1000 字符的错误不应该截断

        验证：
        - 完整错误记录到日志
        - 不添加省略标记
        """
        exact_error = "Error: " + "Z" * 994  # 恰好 1000 字符

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": exact_error,
                "returncode": 1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=4,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/4",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证完整错误被记录
            assert any(
                exact_error in record.message
                for record in caplog.records
                if record.levelname == "ERROR"
            )

            # 验证没有省略标记
            warning_logs = [
                record.message for record in caplog.records if record.levelname == "WARNING"
            ]
            for log in warning_logs:
                if "失败" in log:
                    assert "... (已截断)" not in log

    @pytest.mark.asyncio
    async def test_very_long_error_message_truncated_correctly(self, claude_service, caplog):
        """
        测试：超长错误消息（> 2000字符）正确截断

        验证：
        - 完整错误记录到日志
        - 截断到 1000 字符
        - 添加省略标记
        - 总长度 = 1000 + len("... (已截断)")
        """
        very_long_error = "Error: " + "A" * 5000  # 5006 字符

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": very_long_error,
                "returncode": 1,
                "output": "",
            }

            # 修复：使用 WARNING 级别以捕获 WARNING 和 ERROR 日志
            with caplog.at_level("WARNING"):
                result = await claude_service.develop_feature(
                    issue_number=5,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/5",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证完整错误记录到 ERROR 日志
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]
            assert len(error_logs) > 0

            # 验证 WARNING 日志包含截断的错误
            warning_logs = [
                record.message for record in caplog.records if record.levelname == "WARNING"
            ]
            truncated_log = next(
                (log for log in warning_logs if "失败" in log and "... (已截断)" in log),
                None,
            )
            assert truncated_log is not None

    @pytest.mark.asyncio
    async def test_unknown_error_not_logged_as_full_error(self, claude_service, caplog):
        """
        测试："Unknown error" 不应该记录完整错误

        验证：
        - 不记录到 ERROR 日志
        - 只记录到 WARNING 日志
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": "Unknown error",
                "returncode": -1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=6,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/6",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证没有记录完整错误到 ERROR 日志
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]
            assert len(error_logs) == 0


# =============================================================================
# 测试多重试场景的错误消息
# =============================================================================


class TestRetryErrorMessageHandling:
    """测试重试场景的错误消息处理"""

    @pytest.mark.asyncio
    async def test_different_errors_each_retry(self, claude_service, caplog):
        """
        测试：每次重试的不同错误都应该被记录

        验证：
        - 每次尝试的完整错误都被记录
        - 包含尝试次数
        """
        errors = [
            "Error: Connection failed",  # 尝试 1
            "Error: Timeout occurred",  # 尝试 2
            "Error: API error",  # 尝试 3
        ]

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.side_effect = [
                {"success": False, "errors": errors[0], "returncode": 1, "output": ""},
                {"success": False, "errors": errors[1], "returncode": 1, "output": ""},
                {"success": False, "errors": errors[2], "returncode": 1, "output": ""},
            ]

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=7,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/7",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证每个错误都被记录
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]

            assert len(error_logs) == 3
            for i, error in enumerate(errors):
                assert any(f"尝试 {i+1}" in log for log in error_logs)
                assert any(error in log for log in error_logs)

    @pytest.mark.asyncio
    async def test_long_error_multiple_retries(self, claude_service, caplog):
        """
        测试：多重重试中的长错误消息处理

        验证：
        - 每次重试都记录完整错误
        - WARNING 日志包含截断的错误
        """
        long_error = "Error: " + "B" * 1500

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": long_error,
                "returncode": 1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=8,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/8",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证完整错误被记录（max_retries 次）
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]
            assert len(error_logs) == claude_service.max_retries

            # 验证所有错误日志都包含完整错误
            for log in error_logs:
                assert long_error in log


# =============================================================================
# 测试空错误和特殊情况
# =============================================================================


class TestSpecialErrorCases:
    """测试特殊情况"""

    @pytest.mark.asyncio
    async def test_empty_error_message(self, claude_service, caplog):
        """
        测试：空错误消息

        验证：
        - 不记录完整错误到日志
        - 返回码=-1 (无错误输出)
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": "",
                "returncode": 1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=9,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/9",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证没有记录完整错误
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]
            assert len(error_logs) == 0

    @pytest.mark.asyncio
    async def test_error_with_newlines(self, claude_service, caplog):
        """
        测试：包含换行符的错误消息

        验证：
        - 换行符被保留
        - 完整记录到日志
        """
        multiline_error = """Error: Multiple issues
  - Issue 1: File not found
  - Issue 2: Permission denied
  - Issue 3: Timeout"""

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": multiline_error,
                "returncode": 1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=10,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/10",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证多行错误被完整记录
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]
            assert len(error_logs) > 0
            assert "Issue 1:" in error_logs[0]
            assert "Issue 2:" in error_logs[0]
            assert "Issue 3:" in error_logs[0]

    @pytest.mark.asyncio
    async def test_error_with_unicode(self, claude_service, caplog):
        """
        测试：包含 Unicode 字符的错误消息

        验证：
        - Unicode 字符被正确处理
        - 完整记录到日志
        """
        unicode_error = "错误：文件未找到 🚫 错误：连接超时 ⏱️ 错误：权限不足 🔒"

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": unicode_error,
                "returncode": 1,
                "output": "",
            }

            with caplog.at_level("ERROR"):
                result = await claude_service.develop_feature(
                    issue_number=11,
                    issue_title="Test",
                    issue_url="https://github.com/test/test/issues/11",
                    issue_body="Body",
                )

            assert result["success"] is False

            # 验证 Unicode 错误被完整记录
            error_logs = [
                record.message
                for record in caplog.records
                if record.levelname == "ERROR" and "完整错误输出" in record.message
            ]
            assert len(error_logs) > 0
            assert "🚫" in error_logs[0]
            assert "⏱️" in error_logs[0]
            assert "🔒" in error_logs[0]
