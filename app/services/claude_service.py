"""
Claude Code CLI 服务

调用 Claude Code CLI 进行 AI 开发
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from app.utils.logger import LoggerMixin, get_logger

logger = get_logger(__name__)


class ClaudeService(LoggerMixin):
    """
    Claude Code CLI 调用服务

    负责调用 Claude Code CLI 进行 AI 开发任务
    """

    def __init__(
        self,
        repo_path: Optional[Path] = None,
        claude_cli_path: Optional[str] = None,
    ):
        """
        初始化 Claude 服务

        Args:
            repo_path: 仓库路径，如果为 None 则从配置读取
            claude_cli_path: Claude CLI 路径，如果为 None 则从配置读取
        """
        from app.config import get_config

        config = get_config()

        self.repo_path = repo_path or config.repository.path
        self.claude_cli_path = claude_cli_path or config.claude.cli_path
        self.timeout = config.claude.timeout
        self.max_retries = config.claude.max_retries
        self.dangerously_skip_permissions = config.claude.dangerously_skip_permissions

        self.logger.info(
            f"Claude 服务初始化: "
            f"CLI={self.claude_cli_path}, "
            f"超时={self.timeout}s, "
            f"重试={self.max_retries}, "
            f"跳过权限检查={self.dangerously_skip_permissions}"
        )

    def _build_prompt(
        self,
        issue_url: str,
        issue_title: str,
        issue_body: str,
        issue_number: int,
    ) -> str:
        """
        构建发送给 Claude 的提示词

        Args:
            issue_url: Issue URL
            issue_title: Issue 标题
            issue_body: Issue 内容
            issue_number: Issue 编号

        Returns:
            str: 构建好的提示词
        """
        from app.config import get_config

        config = get_config()

        prompt = f"""请分析以下 GitHub Issue 并完成开发任务：

Issue #{issue_number}: {issue_title}
Issue URL: {issue_url}

Issue 内容:
{issue_body or "（无详细描述）"}

请在开发完成后，使用 git commit 提交变更

**重要：任务完成后的输出将作为 PR 描述的开发总结**

开始执行任务。"""

        return prompt

    async def develop_feature(
        self,
        issue_number: int,
        issue_title: str,
        issue_url: str,
        issue_body: str,
        task_service=None,
        task_id: str = None,
    ) -> dict[str, any]:
        """
        调用 Claude Code CLI 进行开发

        Args:
            issue_number: Issue 编号
            issue_title: Issue 标题
            issue_url: Issue URL
            issue_body: Issue 内容
            task_service: 任务服务（可选，用于实时日志）
            task_id: 任务 ID（可选，用于实时日志）

        Returns:
            dict: 执行结果
                - success (bool): 是否成功
                - output (str): 标准输出
                - errors (str): 错误输出
                - returncode (int): 返回码
                - execution_time (float): 执行时间（秒）
        """
        import time

        start_time = time.time()
        prompt = self._build_prompt(issue_url, issue_title, issue_body, issue_number)

        self.logger.info(f"开始 AI 开发任务: Issue #{issue_number} - {issue_title}")

        # 尝试多次执行（重试机制）
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            # 检查任务是否已被取消
            if task_service and task_id:
                task = task_service.get_task_by_id(task_id)
                if task and task.status.value == "cancelled":
                    self.logger.warning(f"任务已被取消，停止执行: {task_id}")
                    return {
                        "success": False,
                        "output": "",
                        "errors": "任务已被取消",
                        "returncode": -1,
                        "execution_time": time.time() - start_time,
                        "cancelled": True,
                    }

            try:
                self.logger.info(f"执行尝试 {attempt}/{self.max_retries}")

                # 记录重试日志
                if task_service and task_id:
                    task_service.add_task_log(
                        task_id,
                        "INFO",
                        f"Claude CLI 执行尝试 {attempt}/{self.max_retries}"
                    )

                result = await self._execute_claude(
                    prompt,
                    task_service=task_service,
                    task_id=task_id,
                )

                execution_time = time.time() - start_time

                # 成功执行
                if result["success"]:
                    self.logger.info(
                        f"✅ AI 开发任务完成: Issue #{issue_number} "
                        f"(耗时: {execution_time:.1f}s)"
                    )
                    result["execution_time"] = execution_time

                    # 直接使用 output 作为开发总结
                    output = result.get("output", "").strip()
                    result["development_summary"] = output

                    return result
                else:
                    # 非成功，记录错误以便重试
                    last_error = result.get("errors", "Unknown error")
                    self.logger.warning(
                        f"尝试 {attempt} 失败: {last_error[:200]}"
                    )

            except asyncio.TimeoutError:
                last_error = f"执行超时（>{self.timeout}秒）"
                self.logger.error(f"尝试 {attempt} 超时")
            except Exception as e:
                last_error = str(e)
                self.logger.error(
                    f"尝试 {attempt} 异常: {e}",
                    exc_info=True,
                )

            # 如果不是最后一次尝试，等待一段时间后重试
            if attempt < self.max_retries:
                wait_time = min(2**attempt, 10)  # 指数退避，最多 10 秒
                self.logger.info(f"等待 {wait_time}s 后重试...")
                await asyncio.sleep(wait_time)

        # 所有尝试都失败了
        execution_time = time.time() - start_time
        self.logger.error(
            f"❌ AI 开发任务失败: Issue #{issue_number} "
            f"(总耗时: {execution_time:.1f}s)"
        )

        return {
            "success": False,
            "output": "",
            "errors": last_error or "执行失败",
            "returncode": -1,
            "execution_time": execution_time,
        }

    async def _execute_claude(
        self,
        prompt: str,
        task_service=None,
        task_id: str = None,
    ) -> dict[str, any]:
        """
        执行 Claude Code CLI (使用 stream-json 格式)

        Args:
            prompt: 发送给 Claude 的提示词
            task_service: 任务服务（可选，用于实时日志）
            task_id: 任务 ID（可选，用于实时日志）

        Returns:
            dict: 执行结果
                - success (bool): 是否成功
                - output (str): AI 输出内容（从 assistant 消息聚合）
                - errors (str): 错误输出
                - returncode (int): 返回码
                - result (dict): 完整的 result 消息
                - tools_used (list): 使用的工具列表
                - cost_usd (float): API 调用成本
                - duration_ms (int): 执行时长（毫秒）
                - num_turns (int): 对话轮数

        Raises:
            asyncio.TimeoutError: 执行超时
            Exception: 执行失败
        """
        import json

        try:
            # 构建命令
            cmd = [self.claude_cli_path]
            cmd.extend(["-p", prompt])  # 直接传递 prompt
            cmd.extend(["--output-format", "stream-json"])  # 使用流式 JSON 输出
            cmd.extend(["--verbose"])  # 启用详细日志
            # cmd.extend(["--max-turns", str(3)])  # 限制最大对话轮数

            # 如果配置了跳过权限检查，添加参数
            if self.dangerously_skip_permissions:
                cmd.append("--dangerously-skip-permissions")
                self.logger.debug("已启用 --dangerously-skip-permissions 模式")

            self.logger.debug(f"执行命令: {' '.join(cmd)}")

            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024 * 512,  # 512MB 缓冲区
                cwd=str(self.repo_path),
            )

            # 写入 prompt 到 stdin
            stdin_input = prompt.encode()

            try:
                # 异步写入 stdin 并获取输出
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input=stdin_input),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise

            # 解码输出
            stdout_content = stdout_bytes.decode("utf-8", errors="replace")
            stderr_content = stderr_bytes.decode("utf-8", errors="replace")

            # 记录输出摘要
            lines_count = len(stdout_content.strip().split("\n")) if stdout_content.strip() else 0
            self.logger.debug(f"stdout 行数: {lines_count}, 长度: {len(stdout_content)}")

            # 解析 stream-json 行
            assistant_messages = []
            result_message = None
            tools_used = []
            parsing_errors = []
            message_type_counts = {}

            for line in stdout_content.strip().split("\n"):
                if not line.strip():
                    continue

                try:
                    msg = json.loads(line)
                    msg_type = msg.get("type")

                    # 统计消息类型
                    message_type_counts[msg_type] = message_type_counts.get(msg_type, 0) + 1

                    if msg_type == "assistant":
                        # 提取 assistant 消息的文本内容
                        message = msg.get("message", {})
                        content_blocks = message.get("content", [])

                        for block in content_blocks:
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                assistant_messages.append(text)
                                self.logger.debug(f"提取到 assistant 文本块，长度: {len(text)}")
                            elif block.get("type") == "tool_use":
                                tools_used.append({
                                    "name": block.get("name"),
                                    "id": block.get("id"),
                                })
                                self.logger.debug(f"提取到 tool_use: {block.get('name')}")

                    elif msg_type == "result":
                        # 最终结果消息
                        result_message = msg
                        self.logger.debug(f"提取到 result 消息")

                    elif msg_type == "error":
                        # 错误消息
                        error_msg = msg.get("message", "Unknown error")
                        parsing_errors.append(f"Error: {error_msg}")
                        self.logger.error(f"错误消息: {error_msg}")

                except json.JSONDecodeError as e:
                    parsing_errors.append(f"JSON decode error: {e}")
                    self.logger.warning(f"无法解析 JSON 行: {line[:200]}")

            # 记录解析统计
            self.logger.info(
                f"解析 stream-json 完成: "
                f"消息类型统计={message_type_counts}, "
                f"assistant 文本块={len(assistant_messages)}, "
                f"tool_use={len(tools_used)}, "
                f"解析错误={len(parsing_errors)}"
            )

            # 记录错误输出
            if stderr_content:
                self.logger.warning(f"Claude stderr:\n{stderr_content[:5000]}")

            # 记录解析错误
            if parsing_errors:
                self.logger.warning(f"解析错误: {parsing_errors[:5]}")

            # 聚合 assistant 输出
            output = "\n".join(assistant_messages).strip()
            self.logger.info(f"聚合 assistant 输出: 文本块数={len(assistant_messages)}, 总长度={len(output)}")

            # 提取结果信息
            result_data = {
                "success": process.returncode == 0,
                "output": output,
                "errors": stderr_content,
                "returncode": process.returncode,
                "result": result_message,
                "tools_used": tools_used,
            }

            # 从 result 消息中提取额外信息
            if result_message:
                result_data.update({
                    "cost_usd": result_message.get("cost_usd", 0.0),
                    "duration_ms": result_message.get("duration_ms", 0),
                    "num_turns": result_message.get("num_turns", 0),
                    "session_id": result_message.get("session_id", ""),
                })
                self.logger.info(
                    f"Claude 执行完成: "
                    f"成本=${result_message.get('cost_usd', 0):.4f}, "
                    f"时长={result_message.get('duration_ms', 0)}ms, "
                    f"轮数={result_message.get('num_turns', 0)}"
                )

            # 记录输出摘要
            if output:
                self.logger.debug(f"Claude 输出:\n{output[:]}...")

            return result_data

        except asyncio.TimeoutError:
            self.logger.error(f"Claude CLI 执行超时（{self.timeout}秒）")
            raise
        except FileNotFoundError:
            error_msg = (
                f"Claude CLI 未找到: {self.claude_cli_path}. "
                f"请确保 Claude Code CLI 已正确安装并添加到 PATH"
            )
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            self.logger.error(f"执行 Claude CLI 失败: {e}", exc_info=True)
            raise
        finally:
            self.logger.debug("Claude CLI 执行完成")

    async def test_connection(self) -> bool:
        """
        测试 Claude CLI 是否可用

        Returns:
            bool: 是否可用
        """
        try:
            # 尝试获取版本
            process = await asyncio.create_subprocess_exec(
                self.claude_cli_path,
                "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=5,
            )

            if process.returncode == 0:
                version = stdout.decode().strip()
                self.logger.info(f"Claude CLI 可用: {version}")
                return True
            else:
                self.logger.error(f"Claude CLI 不可用: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"Claude CLI 连接测试失败: {e}")
            return False
