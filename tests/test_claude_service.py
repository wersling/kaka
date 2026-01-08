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

        prompt = claude_service._build_prompt(
            issue_url, issue_title, issue_body, issue_number
        )

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

    def test_build_prompt_includes_task_requirements(self, claude_service):
        """
        测试：prompt 应该包含任务要求

        场景：构建 prompt
        期望：包含 4 个主要任务要求
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/789",
            issue_title="Test",
            issue_body="Body",
            issue_number=789,
        )

        assert "1. 分析需求，理解代码库结构" in prompt
        assert "2. 生成或修改代码以实现功能" in prompt
        assert "3. 运行测试确保功能正常" in prompt
        assert "4. 提交代码" in prompt

    def test_build_prompt_includes_step_by_step_instructions(self, claude_service):
        """
        测试：prompt 应该包含分步说明

        场景：构建 prompt
        期望：包含 5 个步骤
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/101",
            issue_title="Test",
            issue_body="Body",
            issue_number=101,
        )

        assert "- 步骤 1: 理解需求，阅读相关代码" in prompt
        assert "- 步骤 2: 探索代码库，找到需要修改的文件" in prompt
        assert "- 步骤 3: 实现功能或修复问题" in prompt
        assert "- 步骤 4: 运行测试验证（如果有测试）" in prompt
        assert "- 步骤 5: 使用 git commit 提交变更" in prompt

    def test_build_prompt_includes_notes(self, claude_service):
        """
        测试：prompt 应该包含注意事项

        场景：构建 prompt
        期望：包含代码风格、文档、质量等注意事项
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/202",
            issue_title="Test",
            issue_body="Body",
            issue_number=202,
        )

        assert "- 遵循项目现有的代码风格" in prompt
        assert "- 添加必要的文档和注释" in prompt
        assert "- 确保代码质量（类型提示、错误处理等）" in prompt
        assert "- 如果遇到问题，请在 commit message 中说明" in prompt

    def test_build_prompt_includes_commit_message_template(self, claude_service):
        """
        测试：prompt 应该包含 commit message 模板

        场景：构建 prompt
        期望：包含 "AI: {issue_title}" 格式的 commit message
        """
        issue_title = "Fix Authentication Bug"
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/303",
            issue_title=issue_title,
            issue_body="Body",
            issue_number=303,
        )

        assert f'commit message 格式："AI: {issue_title}"' in prompt

    def test_build_prompt_correct_format(self, claude_service):
        """
        测试：prompt 格式应该正确

        场景：构建完整的 prompt
        期望：包含正确的标题、分隔符和结构
        """
        prompt = claude_service._build_prompt(
            issue_url="https://github.com/test/test/issues/404",
            issue_title="Error Handling",
            issue_body="Add error handling",
            issue_number=404,
        )

        # 验证主要标题
        assert "请分析以下 GitHub Issue 并完成开发任务：" in prompt
        assert "Issue 内容:" in prompt
        assert "任务要求：" in prompt
        assert "请按照以下步骤执行：" in prompt
        assert "注意事项：" in prompt
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
        期望：返回成功结果，包含所有字段
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success output", b"")

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

    @pytest.mark.asyncio
    async def test_develop_feature_returns_all_required_fields(self, claude_service, mock_process):
        """
        测试：返回结果应该包含所有必需字段

        场景：执行开发任务
        期望：返回包含 success, output, errors, returncode, execution_time
        """
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Output", b"")

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

                assert any("Claude 输出:" in record.message for record in caplog.records if record.levelname == "DEBUG")

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

                assert any("Claude 错误:" in record.message for record in caplog.records if record.levelname == "WARNING")


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

                assert any("Claude CLI 不可用" in record.message or "Claude CLI 连接测试失败" in record.message
                          for record in caplog.records if record.levelname == "ERROR")


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
