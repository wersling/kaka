"""
测试 ClaudeService 成功判断逻辑的优化

测试覆盖以下优化：
1. 限制返回码范围为 [0, 1, 2]
2. 检查 result 消息的 status 字段
3. 添加明确的错误关键词检测
4. 详细的失败原因记录
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.claude_service import ClaudeService


# =============================================================================
# 测试辅助函数
# =============================================================================


def create_stream_json_message(msg_type: str, **kwargs) -> bytes:
    """
    创建符合 stream-json 格式的消息

    Args:
        msg_type: 消息类型 ("assistant", "result", "error")
        **kwargs: 其他字段

    Returns:
        bytes: JSON消息字节
    """
    msg = {"type": msg_type, **kwargs}
    return (json.dumps(msg) + "\n").encode("utf-8")


def create_assistant_message(text: str) -> bytes:
    """创建 assistant 消息"""
    return create_stream_json_message(
        "assistant",
        message={
            "content": [{"type": "text", "text": text}],
            "role": "assistant"
        }
    )


def create_result_message(**kwargs) -> bytes:
    """创建 result 消息"""
    defaults = {
        "cost_usd": 0.001,
        "duration_ms": 1000,
        "num_turns": 1,
    }
    defaults.update(kwargs)
    return create_stream_json_message("result", **defaults)


def create_error_message(error_text: str) -> bytes:
    """创建 error 消息"""
    return create_stream_json_message("error", message=error_text)


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


@pytest.fixture
def mock_process():
    """提供 Mock 的子进程对象"""
    process = AsyncMock()
    process.returncode = 0
    process.communicate = AsyncMock(return_value=(b"", b""))  # 使用 communicate() 而不是 stdout.read()
    process.kill = MagicMock()
    process.wait = AsyncMock()
    return process


# =============================================================================
# 测试返回码范围限制
# =============================================================================


class TestReturnCodeValidation:
    """测试返回码验证逻辑"""

    @pytest.mark.asyncio
    async def test_returncode_0_with_output_success(self, claude_service, mock_process, caplog):
        """
        测试：返回码 0 且有输出应该成功

        验证：
        - is_success 为 True
        - 不记录警告
        """
        mock_process.returncode = 0

        # 模拟成功的 stream-json 输出
        stdout_data = (
            create_assistant_message("Success output") +
            create_result_message(status="success")
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True
            assert result["returncode"] == 0

            # 验证没有非零返回码警告
            with caplog.at_level("WARNING"):
                assert not any("非零返回码" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_returncode_1_with_output_success(self, claude_service, mock_process, caplog):
        """
        测试：返回码 1 且有完整成功信号应该成功

        验证：
        - is_success 为 True（允许的返回码）
        - 记录非零返回码警告
        """
        mock_process.returncode = 1

        # 使用正确的 stream-json 格式（纯JSON，不是SSE格式）
        stdout_data = (
            create_assistant_message("Some output") +
            create_result_message(status="success")
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True
            assert result["returncode"] == 1

    @pytest.mark.asyncio
    async def test_returncode_2_with_output_success(self, claude_service, mock_process):
        """
        测试：返回码 2 且有完整成功信号应该成功

        验证：
        - is_success 为 True（允许的返回码）
        """
        mock_process.returncode = 2

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output with misuse") +
            create_result_message(status="success")
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True
            assert result["returncode"] == 2

    @pytest.mark.asyncio
    async def test_returncode_3_failure(self, claude_service, mock_process, caplog):
        """
        测试：返回码 3 应该失败

        验证：
        - is_success 为 False
        - 记录失败原因："返回码=3不在允许范围"
        """
        mock_process.returncode = 3

        # 使用正确的 stream-json 格式
        stdout_data = create_assistant_message("Output")
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False
            assert result["returncode"] == 3

    @pytest.mark.asyncio
    async def test_returncode_negative_failure(self, claude_service, mock_process, caplog):
        """
        测试：负返回码应该失败

        验证：
        - is_success 为 False
        - 记录失败原因
        """
        mock_process.returncode = -1

        # 使用正确的 stream-json 格式
        stdout_data = create_assistant_message("Output")
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False
            assert result["returncode"] == -1


# =============================================================================
# 测试 result status 检查
# =============================================================================


class TestResultStatusValidation:
    """测试 result status 验证逻辑"""

    @pytest.mark.asyncio
    async def test_status_success_passes(self, claude_service, mock_process):
        """
        测试：status="success" 应该通过

        验证：
        - is_success 为 True
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_status_completed_passes(self, claude_service, mock_process):
        """
        测试：status="completed" 应该通过

        验证：
        - is_success 为 True
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="completed")
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_status_empty_passes(self, claude_service, mock_process):
        """
        测试：status 为空应该通过

        验证：
        - is_success 为 True（无状态字段默认通过）
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式（无 status 字段）
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message()  # 不传 status，会使用默认值
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_status_error_fails(self, claude_service, mock_process, caplog):
        """
        测试：status="error" 应该失败

        验证：
        - is_success 为 False
        - 记录失败原因："result状态=error"
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="error")
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("WARNING"):
                result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False
            # 验证记录了正确的失败原因
            assert any("result状态=error" in record.message for record in caplog.records)


# =============================================================================
# 测试错误关键词检测
# =============================================================================


class TestErrorKeywordDetection:
    """测试错误关键词检测逻辑"""

    @pytest.mark.asyncio
    async def test_stderr_with_warning_only_passes(self, claude_service, mock_process):
        """
        测试：stderr 只包含警告应该通过

        验证：
        - is_success 为 True（警告不是错误）
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        # 警告信息，不是错误（使用 Unicode 转义）
        stderr_data = "Pre-flight check is taking longer\nRun with ANTHROPIC_LOG=debug\n\u26a0️ Warning\n".encode('utf-8')
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True
            assert result["errors"] == ""  # 警告不应该作为 errors

    @pytest.mark.asyncio
    async def test_stderr_with_error_keyword_fails(self, claude_service, mock_process, caplog):
        """
        测试：stderr 包含 "error" 关键词应该失败

        验证：
        - is_success 为 False
        - 记录失败原因："检测到错误输出"
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        stderr_data = b"Error: Something went wrong\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("WARNING"):
                result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False
            assert "检测到错误输出" in caplog.text

    @pytest.mark.asyncio
    async def test_stderr_with_failed_keyword_fails(self, claude_service, mock_process):
        """
        测试：stderr 包含 "failed" 关键词应该失败

        验证：
        - is_success 为 False
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        stderr_data = b"Build failed\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_stderr_with_exception_keyword_fails(self, claude_service, mock_process):
        """
        测试：stderr 包含 "exception" 关键词应该失败

        验证：
        - is_success 为 False
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        stderr_data = b"Exception occurred\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_stderr_with_traceback_keyword_fails(self, claude_service, mock_process):
        """
        测试：stderr 包含 "traceback" 关键词应该失败

        验证：
        - is_success 为 False
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        stderr_data = b"Traceback (most recent call last):\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_stderr_with_critical_keyword_fails(self, claude_service, mock_process):
        """
        测试：stderr 包含 "critical" 关键词应该失败

        验证：
        - is_success 为 False
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        stderr_data = b"Critical error occurred\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_stderr_multi_line_mixed_content(self, claude_service, mock_process):
        """
        测试：stderr 多行混合内容（警告+错误）应该失败

        验证：
        - is_success 为 False（有错误行就失败）
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        # 混合警告和错误
        stderr_data = b"Warning message\nPre-flight check is taking longer\nError: failed\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_stderr_many_lines_without_error_keywords(self, claude_service, mock_process):
        """
        测试：stderr 多行但不包含错误关键词且 <= 3 行应该通过

        验证：
        - is_success 为 True
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        # 3 行，都不是错误
        stderr_data = b"Line 1\nLine 2\nLine 3\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_stderr_many_lines_without_error_keywords_exceeds_threshold(self, claude_service, mock_process):
        """
        测试：stderr 多行（>3行）不包含错误关键词应该失败

        验证：
        - is_success 为 False（行数过多）
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="success")
        )
        # 4 行，都不是明确的错误，但行数 > 3
        stderr_data = b"Line 1\nLine 2\nLine 3\nLine 4\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False


# =============================================================================
# 测试无输出场景
# =============================================================================


class TestNoOutputScenarios:
    """测试无输出场景"""

    @pytest.mark.asyncio
    async def test_no_output_failure(self, claude_service, mock_process, caplog):
        """
        测试：无任何输出应该失败

        验证：
        - is_success 为 False
        - 记录失败原因："无有效输出"
        """
        mock_process.returncode = 0

        # 空输出
        stdout_data = b""
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("WARNING"):
                result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False
            assert "无有效输出" in caplog.text


# =============================================================================
# 测试失败原因记录
# =============================================================================


class TestFailureReasonLogging:
    """测试失败原因记录"""

    @pytest.mark.asyncio
    async def test_multiple_failure_reasons_logged(self, claude_service, mock_process, caplog):
        """
        测试：多个失败原因都应该被记录

        验证：
        - 记录所有失败的判断条件
        """
        mock_process.returncode = 5  # 不在允许范围

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="error")
        )
        stderr_data = b"Error occurred\n"
        mock_process.communicate.return_value = (stdout_data, stderr_data)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("WARNING"):
                result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False

            # 验证所有失败原因都被记录
            log_text = caplog.text
            assert "返回码=5不在允许范围" in log_text
            assert "result状态=error" in log_text
            assert "检测到错误输出" in log_text

    @pytest.mark.asyncio
    async def test_single_failure_reason_logged(self, claude_service, mock_process, caplog):
        """
        测试：单个失败原因应该被记录

        验证：
        - 记录特定的失败原因
        """
        mock_process.returncode = 0

        # 使用正确的 stream-json 格式
        stdout_data = (
            create_assistant_message("Output") +
            create_result_message(status="error")
        )
        mock_process.communicate.return_value = (stdout_data, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("WARNING"):
                result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False
            assert "result状态=error" in caplog.text
