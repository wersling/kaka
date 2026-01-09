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

任务要求：
1. 分析需求，理解代码库结构
2. 生成或修改代码以实现功能
3. 运行测试确保功能正常
4. 提交代码（commit message 格式："AI: {issue_title}"）

请按照以下步骤执行：
- 步骤 1: 理解需求，阅读相关代码
- 步骤 2: 探索代码库，找到需要修改的文件
- 步骤 3: 实现功能或修复问题
- 步骤 4: 运行测试验证（如果有测试）
- 步骤 5: 使用 git commit 提交变更

**重要：任务完成后，请生成开发总结**

在完成所有开发和测试后，请在最后生成一个结构化的开发总结，使用以下格式：

```
=== AI 开发总结 ===

## 执行概述
[简要描述执行的任务和整体结果]

## 变更文件
[列出所有被修改的文件，包括新增、修改和删除的文件]
- 新增: 文件路径
- 修改: 文件路径 (变更说明)

## 技术方案
[说明采用的技术方案和实现思路]

## 主要变更
[详细说明主要的代码变更，包括关键逻辑和修改点]

## 测试验证
[说明如何测试验证，以及测试结果]

## 风险评估
[评估可能的风险和注意事项]

=== 总结结束 ===
```

注意事项：
- 遵循项目现有的代码风格
- 添加必要的文档和注释
- 确保代码质量（类型提示、错误处理等）
- 如果遇到问题，请在 commit message 中说明
- **必须生成上述开发总结，这是 PR 描述的关键内容**

开始执行任务。"""

        return prompt

    def _extract_development_summary(self, output: str) -> str:
        """
        从 Claude 输出中提取开发总结

        Args:
            output: Claude 的完整输出

        Returns:
            str: 提取的开发总结，如果未找到则返回默认信息
        """
        import re

        # 查找开发总结标记
        start_marker = "=== AI 开发总结 ==="
        end_marker = "=== 总结结束 ==="

        start_idx = output.find(start_marker)
        if start_idx == -1:
            # 未找到总结，返回空字符串
            return ""

        end_idx = output.find(end_marker, start_idx)
        if end_idx == -1:
            # 没有结束标记，取从开始到结尾
            summary = output[start_idx + len(start_marker):].strip()
        else:
            summary = output[start_idx + len(start_marker):end_idx].strip()

        # 清理总结内容
        summary = summary.strip()

        # 如果总结为空或过短，返回默认信息
        if len(summary) < 50:
            return ""

        return summary

    async def develop_feature(
        self,
        issue_number: int,
        issue_title: str,
        issue_url: str,
        issue_body: str,
    ) -> dict[str, any]:
        """
        调用 Claude Code CLI 进行开发

        Args:
            issue_number: Issue 编号
            issue_title: Issue 标题
            issue_url: Issue URL
            issue_body: Issue 内容

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
            try:
                self.logger.info(f"执行尝试 {attempt}/{self.max_retries}")

                result = await self._execute_claude(prompt)

                execution_time = time.time() - start_time

                # 成功执行
                if result["success"]:
                    self.logger.info(
                        f"✅ AI 开发任务完成: Issue #{issue_number} "
                        f"(耗时: {execution_time:.1f}s)"
                    )
                    result["execution_time"] = execution_time

                    # 提取开发总结
                    summary = self._extract_development_summary(result.get("output", ""))
                    result["development_summary"] = summary

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

    async def _execute_claude(self, prompt: str) -> dict[str, any]:
        """
        执行 Claude Code CLI

        Args:
            prompt: 发送给 Claude 的提示词

        Returns:
            dict: 执行结果

        Raises:
            asyncio.TimeoutError: 执行超时
            Exception: 执行失败
        """
        prompt_file = None
        try:
            # 将 prompt 写入临时文件
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
            ) as f:
                f.write(prompt)
                prompt_file = f.name

            self.logger.debug(f"Prompt 已写入临时文件: {prompt_file}")

            # 构建命令
            cmd = [
                self.claude_cli_path,
            ]

            # 如果配置了跳过权限检查，添加参数
            if self.dangerously_skip_permissions:
                cmd.append("--dangerously-skip-permissions")
                self.logger.debug("已启用 --dangerously-skip-permissions 模式")

            # 如果有 prompt 文件，添加到命令
            # 注意：工作目录通过 subprocess 的 cwd 参数设置
            # 这里假设 claude CLI 接受从 stdin 读取

            self.logger.debug(f"执行命令: {' '.join(cmd)}")

            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.repo_path),
            )

            # 写入 prompt 到 stdin
            stdin_input = prompt.encode()

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=stdin_input),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise

            # 解码输出
            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")

            # 记录输出
            if output:
                self.logger.debug(f"Claude 输出:\n{output[:500]}")
            if errors:
                self.logger.warning(f"Claude 错误:\n{errors[:500]}")

            return {
                "success": process.returncode == 0,
                "output": output,
                "errors": errors,
                "returncode": process.returncode,
            }

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
            # 清理临时文件（安全修复：确保敏感prompt被删除）
            if prompt_file and os.path.exists(prompt_file):
                try:
                    os.remove(prompt_file)
                    self.logger.debug(f"已清理临时文件: {prompt_file}")
                except Exception as e:
                    # 记录警告但不要抛出异常（清理失败不影响主流程）
                    self.logger.warning(f"清理临时文件失败: {e}")

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
