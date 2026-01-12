"""
ClaudeService 完整单元测试套件

测试覆盖所有 Claude Code CLI 服务功能，包括：
- ClaudeService 初始化
- Prompt 构建（_build_prompt）
- AI 开发（develop_feature）
- Claude CLI 执行（_execute_claude）
- 连接测试（test_connection）
- 重试机制和超时处理
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from unittest.mock import call

import pytest

from app.services.claude_service import ClaudeService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """
    提供测试用的配置对象

    Mock 配置对象，包含 Claude 和仓库配置
    """
    config = MagicMock()
    config.repository.path = Path("/tmp/test_repo")
    config.claude.cli_path = "claude-code"
    config.claude.timeout = 300
    config.claude.max_retries = 3
    config.claude.auto_test = True
    return config


@pytest.fixture
def claude_service(mock_config):
    """
    提供 ClaudeService 实例

    使用 Mock 配置创建服务实例
    """
    with patch("app.config.get_config", return_value=mock_config):
        service = ClaudeService()
        service._mock_config = mock_config
        yield service


@pytest.fixture
def mock_process():
    """
    提供 Mock 的子进程对象

    模拟 asyncio.subprocess.Process
    """
    process = AsyncMock()
    process.returncode = 0
    process.stdout = AsyncMock()
    process.stderr = AsyncMock()
    process.communicate = AsyncMock()
    process.kill = MagicMock()
    process.wait = AsyncMock()
    return process


# =============================================================================
# TestClaudeServiceInitialization 测试
# =============================================================================


class TestClaudeServiceInitialization:
    """测试 ClaudeService 初始化"""

    def test_init_with_default_parameters(self, mock_config):
        """
        测试：使用默认参数初始化应该成功

        场景：不提供任何参数
        期望：从配置读取所有参数
        """
        with patch("app.config.get_config", return_value=mock_config):
            service = ClaudeService()

            assert service.repo_path == mock_config.repository.path
            assert service.claude_cli_path == mock_config.claude.cli_path
            assert service.timeout == mock_config.claude.timeout
            assert service.max_retries == mock_config.claude.max_retries

    def test_init_with_custom_repo_path(self, mock_config):
        """
        测试：自定义仓库路径应该覆盖配置

        场景：提供自定义的 repo_path
        期望：使用提供的路径而不是配置中的路径
        """
        custom_path = Path("/custom/repo/path")

        with patch("app.config.get_config", return_value=mock_config):
            service = ClaudeService(repo_path=custom_path)

            assert service.repo_path == custom_path

    def test_init_with_custom_claude_cli_path(self, mock_config):
        """
        测试：自定义 CLI 路径应该覆盖配置

        场景：提供自定义的 claude_cli_path
        期望：使用提供的路径而不是配置中的路径
        """
        custom_cli = "/usr/local/bin/custom-claude"

        with patch("app.config.get_config", return_value=mock_config):
            service = ClaudeService(claude_cli_path=custom_cli)

            assert service.claude_cli_path == custom_cli

    def test_init_with_both_custom_parameters(self, mock_config):
        """
        测试：同时自定义多个参数

        场景：提供自定义的 repo_path 和 claude_cli_path
        期望：所有自定义参数都生效
        """
        custom_path = Path("/custom/repo")
        custom_cli = "custom-claude"

        with patch("app.config.get_config", return_value=mock_config):
            service = ClaudeService(
                repo_path=custom_path,
                claude_cli_path=custom_cli,
            )

            assert service.repo_path == custom_path
            assert service.claude_cli_path == custom_cli
            assert service.timeout == mock_config.claude.timeout
            assert service.max_retries == mock_config.claude.max_retries

    def test_init_logs_initialization(self, claude_service, caplog):
        """
        测试：初始化时应该记录日志

        场景：创建 ClaudeService 实例
        期望：记录包含 CLI 路径、超时和重试次数的日志
        """
        with patch("app.config.get_config", return_value=claude_service._mock_config):
            with caplog.at_level("INFO"):
                service = ClaudeService()

                assert any("Claude 服务初始化" in record.message for record in caplog.records)
                assert any("CLI=" in record.message for record in caplog.records)
                assert any("超时=" in record.message for record in caplog.records)


# =============================================================================
# TestBuildPrompt 测试
# =============================================================================


class TestBuildPrompt:
    """测试 _build_prompt() 方法"""

    def test_build_prompt_contains_all_required_elements(self, claude_service):
        """
        测试：生成的 prompt 应该包含所有必需元素

        场景：提供完整的 Issue 信息
        期望：prompt 包含 Issue 编号、标题、URL 和内容
        """
        issue_url = "https://github.com/test/test/issues/123"
        issue_title = "Test Feature"
        issue_body = "Implement a test feature"
        issue_number = 123

        prompt = claude_service._build_prompt(issue_url, issue_title, issue_body, issue_number)

        assert f"Issue #{issue_number}" in prompt
        assert issue_title in prompt
        assert issue_url in prompt
        assert issue_body in prompt

    def test_build_prompt_with_empty_body(self, claude_service):
        """
        测试：空 body 应该显示默认文本

        场景：issue_body 为空字符串
        期望：显示 "（无详细描述）"
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/456",
            issue_title="Test",
            issue_body="",
            issue_number=456,
        )

        assert "（无详细描述）" in prompt

    def test_build_prompt_includes_development_summary_note(self, claude_service):
        """
        测试：prompt 应该包含开发总结说明

        场景：构建 prompt
        期望：包含任务完成后输出作为开发总结的重要说明
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/789",
            issue_title="Test",
            issue_body="Body",
            issue_number=789,
        )

        assert "**重要：任务完成后的输出将作为 PR 描述的开发总结**" in prompt
        assert "请在开发完成后，使用 git commit 提交变更" in prompt

    def test_build_prompt_includes_commit_instruction(self, claude_service):
        """
        测试：prompt 应该包含 git commit 说明

        场景：构建 prompt
        期望：包含提交代码的说明
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/101",
            issue_title="Test",
            issue_body="Body",
            issue_number=101,
        )

        assert "git commit 提交变更" in prompt

    def test_build_prompt_simplified_format(self, claude_service):
        """
        测试：prompt 应该使用简化格式

        场景：构建 prompt
        期望：包含简洁的说明，不包含详细的步骤和注意事项
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/202",
            issue_title="Test",
            issue_body="Body",
            issue_number=202,
        )

        # 应该包含基本元素
        assert "请分析以下 GitHub Issue 并完成开发任务：" in prompt
        assert "Issue 内容:" in prompt

        # 不应该包含旧的详细步骤和注意事项
        assert "任务要求：" not in prompt
        assert "请按照以下步骤执行：" not in prompt
        assert "注意事项：" not in prompt
        assert "- 遵循项目现有的代码风格" not in prompt
        assert "- 添加必要的文档和注释" not in prompt

    def test_build_prompt_correct_format(self, claude_service):
        """
        测试：prompt 格式应该正确

        场景：构建完整的 prompt
        期望：包含正确的标题、Issue 信息和简化说明
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/404",
            issue_title="Error Handling",
            issue_body="Add error handling",
            issue_number=404,
        )

        # 验证主要标题和内容
        assert "请分析以下 GitHub Issue 并完成开发任务：" in prompt
        assert "Issue #404: Error Handling" in prompt
        assert "Issue URL: https://github.com/test/test/issues/404" in prompt
        assert "Issue 内容:" in prompt
        assert "Add error handling" in prompt
        assert "**重要：任务完成后的输出将作为 PR 描述的开发总结**" in prompt
        assert "开始执行任务。" in prompt


# =============================================================================
# TestDevelopFeature 测试
# =============================================================================


class TestDevelopFeature:
    """测试 develop_feature() 方法"""

    @pytest.mark.asyncio
    async def test_develop_feature_successfully(self, claude_service, mock_process):
        """
        测试：成功执行开发任务

        场景：CLI 返回成功
        期望：返回成功结果，包含所有字段和 development_summary
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success output\nDevelopment completed", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=123,
                issue_title="Test Feature",
                issue_url="https://github.com/test/test/issues/123",
                issue_body="Implement feature",
            )

            assert result["success"] is True
            assert "Success output" in result["output"]
            assert result["returncode"] == 0
            assert "execution_time" in result
            assert result["execution_time"] > 0
            # 验证 development_summary 字段存在且来自 output
            assert "development_summary" in result
            assert "Development completed" in result["development_summary"]

    @pytest.mark.asyncio
    async def test_develop_feature_returns_all_required_fields(self, claude_service, mock_process):
        """
        测试：返回结果应该包含所有必需字段

        场景：执行开发任务
        期望：返回包含 success, output, errors, returncode, execution_time, development_summary
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Output with summary", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=456,
                issue_title="Feature",
                issue_url="https://github.com/test/test/issues/456",
                issue_body="Body",
            )

            assert "success" in result
            assert "output" in result
            assert "errors" in result
            assert "returncode" in result
            assert "execution_time" in result
            assert "development_summary" in result

    @pytest.mark.asyncio
    async def test_develop_feature_includes_development_summary(self, claude_service, mock_process):
        """
        测试：成功执行后应该包含 development_summary

        场景：CLI 返回成功
        期望：development_summary 字段等于 output
        """
        test_output = """## 执行概述
成功实现了用户认证功能

## 变更文件
- app/auth/login.py
- app/models/user.py

## 技术方案
使用 JWT 进行身份验证"""

        mock_process.returncode = 0
        mock_process.communicate.return_value = (test_output.encode(), b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=789,
                issue_title="User Auth",
                issue_url="https://github.com/test/test/issues/789",
                issue_body="Implement user auth",
            )

            assert result["success"] is True
            assert "development_summary" in result
            # development_summary 应该等于 output（去除首尾空白）
            assert result["development_summary"] == test_output.strip()
            assert result["output"] == test_output

    @pytest.mark.asyncio
    async def test_develop_feature_records_execution_time(self, claude_service, mock_process):
        """
        测试：应该记录执行时间

        场景：执行开发任务
        期望：execution_time 是正数
        """
        import time

        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")

        start = time.time()
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=789,
                issue_title="Feature",
                issue_url="https://github.com/test/test/issues/789",
                issue_body="Body",
            )
        end = time.time()

        assert "execution_time" in result
        assert result["execution_time"] > 0
        assert result["execution_time"] <= (end - start + 0.1)  # 允许小的误差

    @pytest.mark.asyncio
    async def test_develop_feature_retry_on_first_failure(self, claude_service, mock_process):
        """
        测试：第一次失败应该重试

        场景：第1次失败，第2次成功
        期望：重试后返回成功结果
        """
        # 第一次失败，第二次成功
        mock_process.returncode = 0
        mock_process.communicate.side_effect = [
            (b"", b"Error 1"),  # 第1次失败
            (b"Success", b""),  # 第2次成功
        ]

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch.object(claude_service, "_execute_claude") as mock_execute:
                # 第1次失败（returncode=1），第2次成功（returncode=0）
                mock_execute.side_effect = [
                    {"success": False, "errors": "Error 1", "returncode": 1, "output": ""},
                    {"success": True, "output": "Success", "errors": "", "returncode": 0},
                ]

                result = await claude_service.develop_feature(
                    issue_number=111,
                    issue_title="Retry Test",
                    issue_url="https://github.com/test/test/issues/111",
                    issue_body="Body",
                )

                assert result["success"] is True
                assert mock_execute.call_count == 2

    @pytest.mark.asyncio
    async def test_develop_feature_all_retries_fail(self, claude_service):
        """
        测试：所有重试都失败应该返回失败结果

        场景：所有尝试都失败
        期望：返回 success=False，包含错误信息
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": "Persistent error",
                "returncode": 1,
                "output": "",
            }

            result = await claude_service.develop_feature(
                issue_number=222,
                issue_title="Fail Test",
                issue_url="https://github.com/test/test/issues/222",
                issue_body="Body",
            )

            assert result["success"] is False
            assert "Persistent error" in result["errors"]
            assert result["returncode"] == -1
            assert mock_execute.call_count == claude_service.max_retries

    @pytest.mark.asyncio
    async def test_develop_feature_timeout_handling(self, claude_service):
        """
        测试：超时应该被正确处理

        场景：执行超时
        期望：捕获超时异常并重试
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.side_effect = asyncio.TimeoutError()

            result = await claude_service.develop_feature(
                issue_number=333,
                issue_title="Timeout Test",
                issue_url="https://github.com/test/test/issues/333",
                issue_body="Body",
            )

            assert result["success"] is False
            assert "超时" in result["errors"]

    @pytest.mark.asyncio
    async def test_develop_feature_exception_handling(self, claude_service):
        """
        测试：异常应该被正确处理

        场景：执行抛出异常
        期望：捕获异常并重试
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.side_effect = Exception("Unexpected error")

            result = await claude_service.develop_feature(
                issue_number=444,
                issue_title="Exception Test",
                issue_url="https://github.com/test/test/issues/444",
                issue_body="Body",
            )

            assert result["success"] is False
            assert "Unexpected error" in result["errors"]

    @pytest.mark.asyncio
    async def test_develop_feature_logs_correctly(self, claude_service, mock_process, caplog):
        """
        测试：应该记录正确的日志

        场景：执行开发任务
        期望：记录开始、完成等信息
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("INFO"):
                await claude_service.develop_feature(
                    issue_number=555,
                    issue_title="Log Test",
                    issue_url="https://github.com/test/test/issues/555",
                    issue_body="Body",
                )

                assert any("开始 AI 开发任务" in record.message for record in caplog.records)
                assert any("AI 开发任务完成" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_develop_feature_exponential_backoff(self, claude_service):
        """
        测试：重试应该使用指数退避

        场景：第1次失败，等待后重试
        期望：等待时间按指数增长（最多10秒）
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": "Error",
                "returncode": 1,
                "output": "",
            }

            with patch("asyncio.sleep") as mock_sleep:
                await claude_service.develop_feature(
                    issue_number=666,
                    issue_title="Backoff Test",
                    issue_url="https://github.com/test/test/issues/666",
                    issue_body="Body",
                )

                # 验证 sleep 被调用（重试次数 - 1）
                assert mock_sleep.call_count == claude_service.max_retries - 1

                # 验证等待时间递增
                wait_times = [call.args[0] for call in mock_sleep.call_args_list]
                for i, wait_time in enumerate(wait_times):
                    expected = min(2 ** (i + 1), 10)
                    assert wait_time == expected


# =============================================================================
# TestExecuteClaude 测试
# =============================================================================


class TestExecuteClaude:
    """测试 _execute_claude() 方法"""

    @pytest.mark.asyncio
    async def test_execute_claude_success(self, claude_service, mock_process):
        """
        测试：成功执行 CLI

        场景：CLI 返回码为 0
        期望：返回 success=True
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"Claude output",
            b"",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True
            assert result["output"] == "Claude output"
            assert result["errors"] == ""
            assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_execute_claude_non_zero_returncode(self, claude_service, mock_process):
        """
        测试：非零返回码应该标记为失败

        场景：CLI 返回码非 0
        期望：返回 success=False
        """
        mock_process.returncode = 1
        mock_process.communicate.return_value = (
            b"Some output",
            b"Error message",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is False
            assert result["output"] == "Some output"
            assert result["errors"] == "Error message"
            assert result["returncode"] == 1

    @pytest.mark.asyncio
    async def test_execute_claude_captures_stdout(self, claude_service, mock_process):
        """
        测试：应该捕获 stdout

        场景：CLI 输出到标准输出
        期望：output 字段包含 stdout 内容
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"Standard output content",
            b"",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["output"] == "Standard output content"

    @pytest.mark.asyncio
    async def test_execute_claude_captures_stderr(self, claude_service, mock_process):
        """
        测试：应该捕获 stderr

        场景：CLI 输出到标准错误
        期望：errors 字段包含 stderr 内容
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"",
            b"Standard error content",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["errors"] == "Standard error content"

    @pytest.mark.asyncio
    async def test_execute_claude_timeout_raises_timeout_error(self, claude_service, mock_process):
        """
        测试：超时应该抛出 asyncio.TimeoutError

        场景：communicate 超时
        期望：抛出 asyncio.TimeoutError
        """
        mock_process.communicate.side_effect = asyncio.TimeoutError()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(asyncio.TimeoutError):
                await claude_service._execute_claude("Test prompt")

            # 验证进程被终止
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_claude_file_not_found_raises_exception(self, claude_service):
        """
        测试：CLI 未找到应该抛出异常

        场景：CLI 路径不存在
        期望：抛出包含安装提示的异常
        """
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            with pytest.raises(Exception) as exc_info:
                await claude_service._execute_claude("Test prompt")

            assert "Claude CLI 未找到" in str(exc_info.value)
            assert "npm install" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_claude_other_exceptions_propagate(self, claude_service):
        """
        测试：其他异常应该传播

        场景：发生其他异常
        期望：异常被重新抛出
        """
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("System error")):
            with pytest.raises(OSError) as exc_info:
                await claude_service._execute_claude("Test prompt")

            assert "System error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_claude_handles_unicode_errors(self, claude_service, mock_process):
        """
        测试：应该处理 Unicode 解码错误

        场景：输出包含无效的 UTF-8 序列
        期望：使用错误替换模式解码
        """
        mock_process.returncode = 0
        # 包含无效 UTF-8 的字节序列
        mock_process.communicate.return_value = (
            b"Valid text \xff\xfe Invalid bytes",
            b"Error \x80\x81 text",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            # 应该使用替换标记而不是抛出异常
            assert result["success"] is True
            assert "Valid text" in result["output"]
            assert result["errors"] is not None

    @pytest.mark.asyncio
    async def test_execute_claude_writes_prompt_to_stdin(self, claude_service, mock_process):
        """
        测试：应该将 prompt 写入 stdin

        场景：执行 CLI
        期望：prompt 被编码并传递给 stdin
        """
        test_prompt = "Test prompt content"
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await claude_service._execute_claude(test_prompt)

            # 验证 communicate 被调用，且传入了编码的 prompt
            mock_process.communicate.assert_called_once()
            stdin_input = mock_process.communicate.call_args[1]["input"]
            assert stdin_input == test_prompt.encode()

    @pytest.mark.asyncio
    async def test_execute_claude_logs_output(self, claude_service, mock_process, caplog):
        """
        测试：应该记录输出日志

        场景：CLI 有输出
        期望：记录 DEBUG 级别的输出日志
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Debug output", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("DEBUG"):
                await claude_service._execute_claude("Test prompt")

                assert any(
                    "Claude 输出:" in record.message
                    for record in caplog.records
                    if record.levelname == "DEBUG"
                )

    @pytest.mark.asyncio
    async def test_execute_claude_logs_errors(self, claude_service, mock_process, caplog):
        """
        测试：应该记录错误日志

        场景：CLI 有错误输出
        期望：记录 WARNING 级别的错误日志
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"Error output")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("WARNING"):
                await claude_service._execute_claude("Test prompt")

                assert any(
                    "Claude 错误:" in record.message
                    for record in caplog.records
                    if record.levelname == "WARNING"
                )


# =============================================================================
# TestConnection 测试
# =============================================================================


class TestConnection:
    """测试 test_connection() 方法"""

    @pytest.mark.asyncio
    async def test_connection_success(self, claude_service, mock_process):
        """
        测试：CLI 可用应该返回 True

        场景：--version 返回成功
        期望：返回 True
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"claude-code version 1.0.0", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.test_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_connection_failure_non_zero_exit(self, claude_service, mock_process):
        """
        测试：CLI 返回非零退出码应该返回 False

        场景：--version 返回失败
        期望：返回 False
        """
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Command not found")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_connection_timeout(self, claude_service):
        """
        测试：连接超时应该返回 False

        场景：--version 执行超时
        期望：返回 False
        """
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = asyncio.TimeoutError()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_connection_exception_handling(self, claude_service):
        """
        测试：异常应该返回 False

        场景：执行抛出异常
        期望：返回 False
        """
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            result = await claude_service.test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_connection_logs_version(self, claude_service, mock_process, caplog):
        """
        测试：成功时应该记录版本信息

        场景：--version 成功
        期望：记录包含版本的日志
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"claude-code 1.2.3", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("INFO"):
                await claude_service.test_connection()

                assert any("Claude CLI 可用" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_connection_logs_failure(self, claude_service, mock_process, caplog):
        """
        测试：失败时应该记录错误

        场景：--version 失败
        期望：记录错误日志
        """
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Command failed")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("ERROR"):
                await claude_service.test_connection()

                assert any(
                    "Claude CLI 不可用" in record.message
                    or "Claude CLI 连接测试失败" in record.message
                    for record in caplog.records
                    if record.levelname == "ERROR"
                )


# =============================================================================
# Integration Tests
# =============================================================================


class TestClaudeServiceIntegration:
    """ClaudeService 集成测试"""

    @pytest.mark.asyncio
    async def test_full_develop_workflow(self, claude_service, mock_process):
        """
        测试：完整的开发工作流

        场景：从构建 prompt 到执行 CLI
        期望：所有步骤正确执行
        """
        # Mock 配置
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Development complete", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=100,
                issue_title="Integration Test",
                issue_url="https://github.com/test/test/issues/100",
                issue_body="Test integration workflow",
            )

            # 验证完整流程
            assert result["success"] is True
            assert "Development complete" in result["output"]
            assert result["execution_time"] > 0

    @pytest.mark.asyncio
    async def test_retry_workflow_with_timeout(self, claude_service):
        """
        测试：包含超时的重试工作流

        场景：第1次超时，第2次成功
        期望：正确处理超时并重试
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            # 第1次超时，第2次成功
            mock_execute.side_effect = [
                asyncio.TimeoutError(),
                {"success": True, "output": "Success", "errors": "", "returncode": 0},
            ]

            with patch("asyncio.sleep"):  # Mock sleep 以加速测试
                result = await claude_service.develop_feature(
                    issue_number=200,
                    issue_title="Timeout Retry Test",
                    issue_url="https://github.com/test/test/issues/200",
                    issue_body="Test",
                )

                assert result["success"] is True
                assert mock_execute.call_count == 2


# =============================================================================
# Additional Edge Cases and Error Handling Tests
# =============================================================================


class TestClaudeServiceEdgeCases:
    """测试边缘情况和特殊场景"""

    @pytest.mark.asyncio
    async def test_develop_feature_with_empty_issue_body(self, claude_service, mock_process):
        """
        测试：空 Issue body 应该正常处理

        场景：issue_body 为空
        期望：成功执行，prompt 中包含默认提示
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=1,
                issue_title="Empty Body Test",
                issue_url="https://github.com/test/test/issues/1",
                issue_body="",  # 空 body
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_develop_feature_with_special_characters(self, claude_service, mock_process):
        """
        测试：特殊字符应该正确处理

        场景：Issue 标题和内容包含特殊字符
        期望：特殊字符被正确传递和处理
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=2,
                issue_title="Test with 特殊字符 & symbols <>'\"",
                issue_url="https://github.com/test/test/issues/2",
                issue_body="Body with emojis 🎉 \n\nNew lines\n\tTabs",
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_develop_feature_with_very_long_issue_body(self, claude_service, mock_process):
        """
        测试：超长 Issue body 应该正常处理

        场景：Issue body 非常长（10000+ 字符）
        期望：能够正常传递给 CLI
        """
        long_body = "This is a long issue body.\n" * 500  # ~12000 字符

        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service.develop_feature(
                issue_number=3,
                issue_title="Long Issue Test",
                issue_url="https://github.com/test/test/issues/3",
                issue_body=long_body,
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_develop_feature_partial_success_then_failure(self, claude_service):
        """
        测试：部分成功后最终失败的处理

        场景：第1次返回非零退出码，第2次返回零退出码但后续失败
        期望：返回最后一次失败的结果
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.side_effect = [
                {"success": False, "errors": "First error", "returncode": 1, "output": ""},
                {"success": False, "errors": "Second error", "returncode": 2, "output": "Partial"},
                {"success": False, "errors": "Final error", "returncode": 1, "output": ""},
            ]

            result = await claude_service.develop_feature(
                issue_number=4,
                issue_title="Partial Success Test",
                issue_url="https://github.com/test/test/issues/4",
                issue_body="Test",
            )

            assert result["success"] is False
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_claude_with_large_output(self, claude_service, mock_process):
        """
        测试：大量输出应该正确处理

        场景：CLI 产生大量输出（10MB+）
        期望：输出被正确捕获和记录
        """
        large_output = b"x" * (10 * 1024 * 1024)  # 10MB

        mock_process.returncode = 0
        mock_process.communicate.return_value = (large_output, b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await claude_service._execute_claude("Test prompt")

            assert result["success"] is True
            assert len(result["output"]) == len(large_output.decode())

    @pytest.mark.asyncio
    async def test_execute_claude_timeout_kills_process(self, claude_service, mock_process):
        """
        测试：超时后应该终止进程

        场景：communicate 超时
        期望：调用 kill() 和 wait() 清理进程
        """
        mock_process.communicate.side_effect = asyncio.TimeoutError()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(asyncio.TimeoutError):
                await claude_service._execute_claude("Test prompt")

            # 验证进程被终止
            mock_process.kill.assert_called_once()
            mock_process.wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_develop_feature_concurrent_execution(self, claude_service, mock_process):
        """
        测试：并发执行多个任务应该各自独立

        场景：同时启动多个 develop_feature 调用
        期望：每个任务独立执行，互不干扰
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # 并发执行3个任务
            tasks = [
                claude_service.develop_feature(
                    issue_number=i,
                    issue_title=f"Concurrent Task {i}",
                    issue_url=f"https://github.com/test/test/issues/{i}",
                    issue_body=f"Body {i}",
                )
                for i in range(1, 4)
            ]

            results = await asyncio.gather(*tasks)

            # 验证所有任务都成功
            assert len(results) == 3
            for result in results:
                assert result["success"] is True

    def test_build_prompt_with_unicode_content(self, claude_service):
        """
        测试：Unicode 内容应该正确处理

        场景：Issue 包含多语言内容（中文、日文、阿拉伯文等）
        期望：Unicode 内容被正确包含在 prompt 中
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/5",
            issue_title="Unicode 测试 🎉",
            issue_body="中文内容\n日本語\nاللغة العربية\nΕλληνικά",
            issue_number=5,
        )

        assert "中文内容" in prompt
        assert "日本語" in prompt
        assert "اللغة العربية" in prompt
        assert "Ελληνικά" in prompt
        assert "🎉" in prompt

    @pytest.mark.asyncio
    async def test_connection_logs_correctly_on_success(self, claude_service, mock_process, caplog):
        """
        测试：连接成功应该记录正确的日志

        场景：test_connection 成功
        期望：记录版本信息
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"claude-code version 2.0.0", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with caplog.at_level("INFO"):
                result = await claude_service.test_connection()

                assert result is True
                assert any("Claude CLI 可用" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_connection_with_version_parsing(self, claude_service, mock_process):
        """
        测试：版本信息应该被正确解析

        场景：不同格式的版本输出
        期望：成功解析并记录
        """
        test_cases = [
            b"claude-code version 1.0.0",
            b"claude-code 2.3.4",
            b"@anthropic/claude-code/3.0.0",
        ]

        for version_output in test_cases:
            mock_process.returncode = 0
            mock_process.communicate.return_value = (version_output, b"")

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await claude_service.test_connection()
                assert result is True

    @pytest.mark.asyncio
    async def test_develop_feature_max_retries_equals_one(self, claude_service):
        """
        测试：max_retries=1 应该只尝试一次

        场景：设置 max_retries=1
        期望：只执行一次，不重试
        """
        claude_service.max_retries = 1

        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": "Error",
                "returncode": 1,
                "output": "",
            }

            result = await claude_service.develop_feature(
                issue_number=6,
                issue_title="No Retry Test",
                issue_url="https://github.com/test/test/issues/6",
                issue_body="Test",
            )

            assert result["success"] is False
            assert mock_execute.call_count == 1  # 只调用一次

    @pytest.mark.asyncio
    async def test_develop_feature_custom_timeout(self, claude_service, mock_process):
        """
        测试：自定义超时时间应该生效

        场景：设置自定义超时时间
        期望：使用自定义的超时时间
        """
        claude_service.timeout = 60  # 60秒超时

        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("asyncio.wait_for") as mock_wait:
                mock_wait.return_value = (b"Success", b"")

                await claude_service.develop_feature(
                    issue_number=7,
                    issue_title="Custom Timeout Test",
                    issue_url="https://github.com/test/test/issues/7",
                    issue_body="Test",
                )

                # 验证使用了自定义超时
                assert mock_wait.call_args[1]["timeout"] == 60

    def test_service_attributes_are_correctly_set(self, claude_service, mock_config):
        """
        测试：服务属性应该正确设置

        场景：初始化服务
        期望：所有属性都从配置正确读取
        """
        assert claude_service.repo_path == mock_config.repository.path
        assert claude_service.claude_cli_path == mock_config.claude.cli_path
        assert claude_service.timeout == mock_config.claude.timeout
        assert claude_service.max_retries == mock_config.claude.max_retries

    @pytest.mark.asyncio
    async def test_execute_claude_command_construction(self, claude_service, mock_process):
        """
        测试：CLI 命令应该正确构造

        场景：执行 Claude CLI
        期望：命令参数正确
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_subprocess.return_value = mock_process

            await claude_service._execute_claude("Test prompt")

            # 验证命令构造
            call_args = mock_subprocess.call_args
            args = call_args[0]  # 所有位置参数

            # args[0] 应该是第一个参数（命令路径），而不是字符
            assert args[0] == claude_service.claude_cli_path
            assert "--cwd" in args
            assert str(claude_service.repo_path) in args

    @pytest.mark.asyncio
    async def test_develop_feature_execution_time_includes_retries(self, claude_service):
        """
        测试：执行时间应该包含重试时间

        场景：第1次失败，等待后第2次成功
        期望：execution_time 包含等待时间
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.side_effect = [
                {"success": False, "errors": "Error", "returncode": 1, "output": ""},
                {"success": True, "output": "Success", "errors": "", "returncode": 0},
            ]

            with patch("asyncio.sleep") as mock_sleep:
                mock_sleep.return_value = asyncio.sleep(0)  # 不实际等待

                result = await claude_service.develop_feature(
                    issue_number=8,
                    issue_title="Execution Time Test",
                    issue_url="https://github.com/test/test/issues/8",
                    issue_body="Test",
                )

                assert result["success"] is True
                assert result["execution_time"] > 0
                # 验证 sleep 被调用（第1次失败后，第2次成功前）
                # max_retries=3, 第1次失败后会 sleep，第2次成功
                assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_multiple_timeout_scenarios(self, claude_service):
        """
        测试：多次超时的处理

        场景：连续多次超时
        期望：正确记录并最终返回失败
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.side_effect = asyncio.TimeoutError()

            with patch("asyncio.sleep"):  # Mock sleep
                result = await claude_service.develop_feature(
                    issue_number=9,
                    issue_title="Multiple Timeout Test",
                    issue_url="https://github.com/test/test/issues/9",
                    issue_body="Test",
                )

                assert result["success"] is False
                assert "超时" in result["errors"]
                assert mock_execute.call_count == claude_service.max_retries

    @pytest.mark.asyncio
    async def test_mixed_errors_in_retries(self, claude_service):
        """
        测试：混合错误类型的处理

        场景：第1次超时，第2次异常，第3次失败
        期望：正确处理不同类型的错误
        """
        with patch.object(claude_service, "_execute_claude") as mock_execute:
            mock_execute.side_effect = [
                asyncio.TimeoutError(),  # 第1次超时
                Exception("Network error"),  # 第2次异常
                {
                    "success": False,
                    "errors": "API error",
                    "returncode": 1,
                    "output": "",
                },  # 第3次失败
            ]

            with patch("asyncio.sleep"):
                result = await claude_service.develop_feature(
                    issue_number=10,
                    issue_title="Mixed Errors Test",
                    issue_url="https://github.com/test/test/issues/10",
                    issue_body="Test",
                )

                assert result["success"] is False
                assert mock_execute.call_count == claude_service.max_retries
