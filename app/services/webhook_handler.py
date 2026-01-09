"""
Webhook 处理器

处理 GitHub Webhook 事件，协调各个服务完成开发任务
"""

from typing import Any, Optional

from app.models.github_events import (
    DevelopmentTask,
    IssueCommentEvent,
    IssueEvent,
    TaskResult,
)
from app.services.claude_service import ClaudeService
from app.services.git_service import GitService
from app.services.github_service import GitHubService
from app.utils.logger import LoggerMixin, get_logger
from app.utils.validators import (
    sanitize_log_data,
    validate_comment_trigger,
    validate_issue_trigger,
)

logger = get_logger(__name__)


class WebhookHandler(LoggerMixin):
    """
    Webhook 事件处理器

    接收 GitHub Webhook 事件，协调各服务完成自动化开发任务
    """

    def __init__(self):
        """初始化 Webhook 处理器"""
        self.git_service: Optional[GitService] = None
        self.claude_service: Optional[ClaudeService] = None
        self.github_service: Optional[GitHubService] = None

        self.logger.info("Webhook 处理器初始化")

    def _init_services(self) -> None:
        """延迟初始化服务（避免在模块加载时初始化）"""
        if self.git_service is None:
            self.git_service = GitService()
            self.logger.info("Git 服务已初始化")

        if self.claude_service is None:
            self.claude_service = ClaudeService()
            self.logger.info("Claude 服务已初始化")

        if self.github_service is None:
            self.github_service = GitHubService()
            self.logger.info("GitHub 服务已初始化")

    async def handle_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> Optional[TaskResult]:
        """
        处理 GitHub Webhook 事件

        Args:
            event_type: 事件类型（issues, issue_comment 等）
            data: 事件数据

        Returns:
            TaskResult: 处理结果，如果事件不满足触发条件则返回 None
        """
        self.logger.info(f"收到 Webhook 事件: {event_type}")

        # 记录事件数据（脱敏）
        sanitized_data = sanitize_log_data(data)
        self.logger.debug(f"事件数据: {sanitized_data}")

        try:
            # 路由到对应的处理器
            if event_type == "issues":
                return await self._handle_issue_event(data)
            elif event_type == "issue_comment":
                return await self._handle_comment_event(data)
            elif event_type == "ping":
                self.logger.info("收到 ping 事件")
                return TaskResult(
                    success=True,
                    task_id="ping",
                    details={"message": "pong"},
                )
            else:
                self.logger.warning(f"不支持的事件类型: {event_type}")
                return None

        except Exception as e:
            self.logger.error(
                f"处理事件失败: {event_type}",
                exc_info=True,
            )
            return TaskResult(
                success=False,
                task_id="error",
                error_message=str(e),
            )

    async def _handle_issue_event(self, data: dict[str, Any]) -> Optional[TaskResult]:
        """
        处理 Issue 事件

        Args:
            data: Issue 事件数据

        Returns:
            TaskResult: 处理结果
        """
        try:
            # 解析事件
            event = IssueEvent(**data)
            action = event.action
            issue = event.issue

            self.logger.info(
                f"Issue 事件: action={action}, "
                f"issue=#{issue.number} - {issue.title}"
            )

            # 检查触发条件
            from app.config import get_config

            config = get_config()

            labels = [label.name for label in issue.labels]
            should_trigger = validate_issue_trigger(
                action,
                labels,
                config.github.trigger_label,
            )

            if not should_trigger:
                self.logger.debug(
                    f"Issue #{issue.number} 不满足触发条件"
                )
                return None

            # 触发 AI 开发
            return await self._trigger_ai_development(
                issue_number=issue.number,
                issue_title=issue.title,
                issue_url=issue.html_url,
                issue_body=issue.body or "",
            )

        except Exception as e:
            self.logger.error(f"处理 Issue 事件失败: {e}", exc_info=True)
            return TaskResult(
                success=False,
                task_id="error",
                error_message=str(e),
            )

    async def _handle_comment_event(self, data: dict[str, Any]) -> Optional[TaskResult]:
        """
        处理 Issue 评论事件

        Args:
            data: 评论事件数据

        Returns:
            TaskResult: 处理结果
        """
        try:
            # 解析事件
            event = IssueCommentEvent(**data)
            action = event.action
            comment = event.comment
            issue = event.issue

            self.logger.info(
                f"Issue 评论事件: action={action}, "
                f"issue=#{issue.number}"
            )

            # 只处理新创建的评论
            if action != "created":
                self.logger.debug(f"Ignore comment action: {action}")
                return None

            # 检查触发条件
            from app.config import get_config

            config = get_config()

            should_trigger = validate_comment_trigger(
                comment.body,
                config.github.trigger_command,
            )

            if not should_trigger:
                self.logger.debug(
                    f"评论不包含触发命令: {config.github.trigger_command}"
                )
                return None

            # 触发 AI 开发
            return await self._trigger_ai_development(
                issue_number=issue.number,
                issue_title=issue.title,
                issue_url=issue.html_url,
                issue_body=issue.body or "",
            )

        except Exception as e:
            self.logger.error(f"处理评论事件失败: {e}", exc_info=True)
            return TaskResult(
                success=False,
                task_id="error",
                error_message=str(e),
            )

    async def _trigger_ai_development(
        self,
        issue_number: int,
        issue_title: str,
        issue_url: str,
        issue_body: str,
        existing_branch: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> TaskResult:
        """
        触发 AI 开发流程

        Args:
            issue_number: Issue 编号
            issue_title: Issue 标题
            issue_url: Issue URL
            issue_body: Issue 内容

        Returns:
            TaskResult: 执行结果
        """
        import time
        from app.services.task_service import TaskService
        from app.db.models import TaskStatus

        # 如果没有提供 task_id，创建新的
        is_retry = task_id is not None
        if not task_id:
            task_id = f"task-{issue_number}-{int(time.time())}"

        self.logger.info(f"开始 AI 开发任务: {task_id} (重试: {is_retry})")

        # 初始化任务服务
        task_service = TaskService()

        try:
            if not is_retry:
                # 新任务场景
                try:
                    # 初始化服务
                    self._init_services()

                    # 1. 创建特性分支
                    self.logger.info(f"步骤 1/5: 创建特性分支")
                    branch_name = self.git_service.create_feature_branch(issue_number)
                    self.logger.info(f"✅ 分支创建成功: {branch_name}")

                    # 创建任务记录
                    task_service.create_task(
                        task_id=task_id,
                        issue_number=issue_number,
                        issue_title=issue_title,
                        issue_url=issue_url,
                        issue_body=issue_body,
                        branch_name=branch_name,
                    )

                    # 更新状态为运行中
                    task_service.update_task_status(task_id, TaskStatus.RUNNING)
                    task_service.add_task_log(task_id, "INFO", f"步骤 1/5: 创建特性分支完成:{branch_name}")

                except Exception as e:
                    self.logger.error(f"初始化任务失败: {e}", exc_info=True)
                    raise
            else:
                # 重试场景
                branch_name = existing_branch
                self.logger.info(f"重试任务: {task_id}, 使用现有分支: {branch_name}")
                self._init_services()

                # 检查分支是否存在
                if not self.git_service.branch_exists(branch_name):
                    self.logger.warning(f"分支不存在，重新创建: {branch_name}")
                    branch_name = self.git_service.create_feature_branch(issue_number)
                    task_service.add_task_log(task_id, "INFO", f"分支不存在，已重新创建: {branch_name}")
                else:
                    self.git_service.checkout_branch(branch_name)
                    task_service.add_task_log(task_id, "INFO", f"切换到现有分支: {branch_name}")

                # 更新状态为运行中
                task_service.update_task_status(task_id, TaskStatus.RUNNING)
                task_service.add_task_log(task_id, "INFO", "开始重试任务")

            # 2. 调用 Claude Code 进行开发
            self.logger.info(f"步骤 2/5: 调用 Claude Code CLI")
            task_service.add_task_log(task_id, "INFO", "步骤 2/5: 调用 Claude Code CLI")

            claude_result = await self.claude_service.develop_feature(
                issue_number=issue_number,
                issue_title=issue_title,
                issue_url=issue_url,
                issue_body=issue_body,
                task_service=task_service,
                task_id=task_id,
            )

            # 检查任务是否被取消
            if claude_result.get("cancelled"):
                self.logger.info(f"任务已被用户取消: {task_id}")
                task_service.add_task_log(task_id, "INFO", "任务已被用户取消")

                # 通知用户任务已取消
                self.github_service.add_comment_to_issue(
                    issue_number=issue_number,
                    comment=f"⏹️  AI 开发任务已取消",
                )

                return TaskResult(
                    success=False,
                    task_id=task_id,
                    branch_name=branch_name,
                    error_message="任务已被取消",
                    cancelled=True,
                )

            if not claude_result["success"]:
                error_msg = claude_result.get("errors", "Unknown error")
                self.logger.error(f"Claude 开发失败: {error_msg}")

                # 更新任务状态为失败
                task_service.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error_message=error_msg,
                    success=False,
                )

                # 通知用户失败（非阻塞）
                success = self.github_service.add_comment_to_issue(
                    issue_number=issue_number,
                    comment=f"❌ AI 开发失败: {error_msg}",
                )
                if not success:
                    self.logger.warning(
                        f"向 Issue #{issue_number} 发送失败通知失败"
                    )

                return TaskResult(
                    success=False,
                    task_id=task_id,
                    branch_name=branch_name,
                    error_message=error_msg,
                )

            self.logger.info(f"✅ Claude 开发完成")
            task_service.add_task_log(task_id, "INFO", "✅ Claude 开发完成")

            # 3. 提交变更（Claude 应该已经提交，这里检查并提交剩余变更）
            self.logger.info(f"步骤 3/5: 检查并提交变更")
            task_service.add_task_log(task_id, "INFO", "步骤 3/5: 检查并提交变更")
            from app.config import get_config

            config = get_config()
            commit_message = config.task.commit_template.format(
                issue_title=issue_title
            )

            # 如果有未提交的变更，进行提交
            if self.git_service.has_changes():
                self.git_service.commit_changes(commit_message)
                self.logger.info(f"✅ 变更已提交")
                task_service.add_task_log(task_id, "INFO", "✅ 变更已提交")
            else:
                self.logger.info(f"没有额外的变更需要提交")
                task_service.add_task_log(task_id, "INFO", "没有额外的变更需要提交")

            # 4. 推送到远程
            self.logger.info(f"步骤 4/5: 推送到远程")
            task_service.add_task_log(task_id, "INFO", "步骤 4/5: 推送到远程")
            self.git_service.push_to_remote(branch_name)
            self.logger.info(f"✅ 推送成功")
            task_service.add_task_log(task_id, "INFO", "✅ 推送成功")

            # 5. 创建 PR
            self.logger.info(f"步骤 5/5: 创建 Pull Request")
            task_service.add_task_log(task_id, "INFO", "步骤 5/5: 创建 Pull Request")
            execution_time = claude_result.get("execution_time", 0)
            development_summary = claude_result.get("development_summary", "")

            if not development_summary:
                self.logger.warning("未找到 AI 开发总结，PR 描述将不包含详细信息")
                task_service.add_task_log(task_id, "WARNING", "未找到 AI 开发总结")

            pr_info = self.github_service.create_pull_request(
                branch_name=branch_name,
                issue_number=issue_number,
                issue_title=issue_title,
                issue_body=issue_body,
                execution_time=execution_time,
                development_summary=development_summary,
            )

            # 检查 PR 创建是否成功（返回 None 表示没有提交）
            if not pr_info:
                error_msg = "未创建 PR：分支与主分支之间没有代码提交差异，可能 Claude CLI 执行失败或未产生代码变更"

                self.logger.warning(f"⚠️  {error_msg}")
                task_service.add_task_log(task_id, "WARNING", error_msg)

                # 更新任务状态为失败
                task_service.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error_message=error_msg,
                    success=False,
                    execution_time=execution_time,
                )

                # 通知用户
                self.github_service.add_comment_to_issue(
                    issue_number=issue_number,
                    comment=f"⚠️  AI 开发未完成: {error_msg}\n\n请检查 Claude CLI 的执行日志以了解详细原因。",
                )

                # 返回失败结果
                return TaskResult(
                    success=False,
                    task_id=task_id,
                    branch_name=branch_name,
                    error_message=error_msg,
                )

            self.logger.info(
                f"✅ PR 创建成功: #{pr_info['pr_number']} - {pr_info['html_url']}"
            )
            task_service.add_task_log(
                task_id,
                "INFO",
                f"✅ PR 创建成功: #{pr_info['pr_number']} - {pr_info['html_url']}"
            )

            # 在 Issue 中评论 PR 链接（非阻塞）
            execution_time = claude_result.get("execution_time", 0)
            success = self.github_service.add_comment_to_issue(
                issue_number=issue_number,
                comment=f"✅ AI 开发完成！已创建 PR: #{pr_info['pr_number']}，用时：{execution_time:.1f}秒",
            )
            if not success:
                self.logger.warning(
                    f"向 Issue #{issue_number} 发送 PR 链接失败"
                )

            # 更新任务状态为完成
            task_service.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                success=True,
                execution_time=execution_time,
                pr_number=pr_info["pr_number"],
                pr_url=pr_info["html_url"],
                development_summary=development_summary,
            )

            # 返回成功结果
            return TaskResult(
                success=True,
                task_id=task_id,
                branch_name=branch_name,
                pr_url=pr_info["html_url"],
                details={
                    "pr_number": pr_info["pr_number"],
                    "execution_time": claude_result.get("execution_time"),
                },
            )

        except Exception as e:
            self.logger.error(f"AI 开发流程异常: {e}", exc_info=True)

            # 更新任务状态为失败
            try:
                task_service.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error_message=str(e),
                    success=False,
                )
            except:
                pass  # 如果更新状态失败，不影响后续处理

            # 尝试通知用户（非阻塞）
            if self.github_service:
                self.github_service.add_comment_to_issue(
                    issue_number=issue_number,
                    comment=f"❌ AI 开发流程异常: {str(e)}",
                )

            return TaskResult(
                success=False,
                task_id=task_id,
                error_message=str(e),
            )

        finally:
            # 关闭任务服务
            task_service.close()
