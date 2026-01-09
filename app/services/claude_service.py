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
        执行 Claude Code CLI

        Args:
            prompt: 发送给 Claude 的提示词
            task_service: 任务服务（可选，用于实时日志）
            task_id: 任务 ID（可选，用于实时日志）

        Returns:
            dict: 执行结果

        Raises:
            asyncio.TimeoutError: 执行超时
            Exception: 执行失败
        """
        process = None
        try:
            # 构建命令 - 使用 -p 参数传递 prompt，避免流式模式限制
            cmd = [
                self.claude_cli_path,
                "-p",
                prompt,
            ]

            # 如果配置了跳过权限检查，添加参数
            if self.dangerously_skip_permissions:
                cmd.append("--dangerously-skip-permissions")
                self.logger.debug("已启用 --dangerously-skip-permissions 模式")

            # 打印完整的命令（用于调试）
            cmd_str = " ".join([f'"{arg}"' if " " in arg else arg for arg in cmd])
            self.logger.info(f"🔧 执行 Claude CLI 命令: {cmd_str}")

            # 执行命令 - 不使用 stdin，避免流式模式
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.repo_path),
            )

            # 注册进程到进程管理器（如果提供了 task_id）
            if task_id:
                from app.services.process_manager import process_manager
                process_manager.register_process(task_id, process)
                self.logger.debug(f"进程已注册到管理器: task_id={task_id}, pid={process.pid}")

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise
            except asyncio.CancelledError:
                # 任务被取消
                self.logger.info(f"任务被取消，终止进程: task_id={task_id}")
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                raise

            # 解码输出
            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")

            # 注意：不再实时记录 Claude 输出到数据库，只记录系统级别日志

            # 记录输出到日志（增加长度限制以便查看完整错误）
            if output:
                # 如果输出是 JSON 格式的错误，记录完整输出
                if '"error"' in output or '"permission_denial"' in output or 'error_during_execution' in output:
                    self.logger.error(f"Claude 输出（完整）:\n{output}")
                else:
                    self.logger.debug(f"Claude 输出:\n{output[:1000]}")
            if errors:
                self.logger.warning(f"Claude 错误:\n{errors[:1000]}")

            return {
                "success": process.returncode == 0,
                "output": output,
                "errors": errors,
                "returncode": process.returncode,
            }

        except asyncio.TimeoutError:
            # 记录超时错误
            if task_service and task_id:
                task_service.add_task_log(
                    task_id,
                    "ERROR",
                    f"Claude CLI 执行超时（{self.timeout}秒）"
                )
            self.logger.error(f"Claude CLI 执行超时（{self.timeout}秒）")
            raise
        except FileNotFoundError:
            error_msg = (
                f"Claude CLI 未找到: {self.claude_cli_path}. "
                f"请确保 Claude Code CLI 已正确安装并添加到 PATH"
            )
            if task_service and task_id:
                task_service.add_task_log(task_id, "ERROR", error_msg)
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"执行 Claude CLI 失败: {e}"
            if task_service and task_id:
                task_service.add_task_log(task_id, "ERROR", error_msg)
            self.logger.error(error_msg, exc_info=True)
            raise
        finally:
            # 无论成功还是失败，都注销进程
            if task_id and process:
                from app.services.process_manager import process_manager
                process_manager.unregister_process(task_id)
                self.logger.debug(f"进程已从管理器注销: task_id={task_id}")

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
