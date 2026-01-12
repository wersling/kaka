"""
Task Management Service
管理任务的生命周期、状态转换和持久化
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import Task, TaskLog, TaskStatus
from app.db.database import get_db_session
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskService:
    """任务管理服务"""

    def __init__(self, db: Optional[Session] = None):
        """
        初始化任务服务

        Args:
            db: 数据库会话，如果为 None 则创建新会话
        """
        self.db = db or get_db_session()
        logger.debug("任务管理服务初始化")

    def create_task(
        self,
        task_id: str,
        issue_number: int,
        issue_title: str,
        issue_url: str,
        issue_body: str,
        branch_name: str,
    ) -> Task:
        """
        创建新任务

        Args:
            task_id: 任务 ID
            issue_number: Issue 编号
            issue_title: Issue 标题
            issue_url: Issue URL
            issue_body: Issue 内容
            branch_name: 分支名

        Returns:
            Task: 创建的任务对象
        """
        try:
            task = Task(
                task_id=task_id,
                issue_number=issue_number,
                issue_title=issue_title,
                issue_url=issue_url,
                issue_body=issue_body,
                branch_name=branch_name,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
            )

            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)

            logger.info(f"✅ 任务创建成功: {task_id}")
            self.add_task_log(task_id, "INFO", "任务创建")

            return task

        except Exception as e:
            self.db.rollback()
            logger.error(f"创建任务失败: {e}", exc_info=True)
            raise

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None,
        success: Optional[bool] = None,
        execution_time: Optional[float] = None,
        pr_number: Optional[int] = None,
        pr_url: Optional[str] = None,
        development_summary: Optional[str] = None,
    ) -> Optional[Task]:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 新状态
            error_message: 错误信息
            success: 是否成功
            execution_time: 执行时间
            pr_number: PR 编号
            pr_url: PR URL
            development_summary: 开发总结

        Returns:
            Task: 更新后的任务对象，如果任务不存在则返回 None
        """
        try:
            task = self.get_task_by_id(task_id)
            if not task:
                logger.warning(f"任务不存在: {task_id}")
                return None

            # 更新状态
            task.status = status

            # 根据状态更新时间戳
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.utcnow()
                self.add_task_log(task_id, "INFO", "任务开始执行")
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.utcnow()
                status_msg = {
                    TaskStatus.COMPLETED: "任务完成",
                    TaskStatus.FAILED: "任务失败",
                    TaskStatus.CANCELLED: "任务已取消",
                }
                self.add_task_log(task_id, "INFO", status_msg.get(status, "任务结束"))

            # 更新其他字段
            if error_message is not None:
                task.error_message = error_message
            if success is not None:
                task.success = success
            if execution_time is not None:
                task.execution_time = execution_time
            if pr_number is not None:
                task.pr_number = pr_number
            if pr_url is not None:
                task.pr_url = pr_url
            if development_summary is not None:
                task.development_summary = development_summary

            self.db.commit()
            self.db.refresh(task)

            logger.info(f"✅ 任务状态更新: {task_id} -> {status.value}")
            return task

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新任务状态失败: {e}", exc_info=True)
            raise

    def cancel_task(self, task_id: str) -> Optional[Task]:
        """
        取消正在运行的任务

        注意：此方法只更新任务状态，不终止进程。
        进程终止应在调用此方法之前由 API 层处理。

        Args:
            task_id: 任务 ID

        Returns:
            Task: 取消后的任务对象，如果任务不存在或无法取消则返回 None
        """
        try:
            task = self.get_task_by_id(task_id)
            if not task:
                return None

            # 只能取消 pending 或 running 状态的任务
            if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                logger.warning(f"任务无法取消: {task_id} (当前状态: {task.status.value})")
                return None

            return self.update_task_status(task_id, TaskStatus.CANCELLED)

        except Exception as e:
            logger.error(f"取消任务失败: {e}", exc_info=True)
            raise

    def retry_task(self, task_id: str) -> Optional[Task]:
        """
        重试失败或取消的任务

        Args:
            task_id: 任务 ID

        Returns:
            Task: 重试后的任务对象，如果任务不存在或无法重试则返回 None
        """
        try:
            task = self.get_task_by_id(task_id)
            if not task:
                return None

            # 只能重试失败或取消的任务
            if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                logger.warning(f"任务无法重试: {task_id} (当前状态: {task.status.value})")
                return None

            # 检查重试次数
            if task.retry_count >= task.max_retries:
                logger.warning(f"任务已达到最大重试次数: {task_id}")
                return None

            # 重置任务状态
            task.status = TaskStatus.PENDING
            task.retry_count += 1
            task.error_message = None
            task.started_at = None
            task.completed_at = None

            self.db.commit()
            self.db.refresh(task)

            logger.info(f"✅ 任务重试: {task_id} (第 {task.retry_count} 次)")
            self.add_task_log(task_id, "INFO", f"任务重试 (第 {task.retry_count} 次)")

            return task

        except Exception as e:
            self.db.rollback()
            logger.error(f"重试任务失败: {e}", exc_info=True)
            raise

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        根据 task_id 获取任务

        Args:
            task_id: 任务 ID

        Returns:
            Task: 任务对象，如果不存在则返回 None
        """
        return self.db.query(Task).filter(Task.task_id == task_id).first()

    def get_tasks_by_issue(self, issue_number: int) -> List[Task]:
        """
        根据 Issue 编号获取所有相关任务

        Args:
            issue_number: Issue 编号

        Returns:
            List[Task]: 任务列表
        """
        return (
            self.db.query(Task)
            .filter(Task.issue_number == issue_number)
            .order_by(desc(Task.created_at))
            .all()
        )

    def get_all_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """
        获取所有任务（支持分页和筛选）

        Args:
            status: 状态筛选，如果为 None 则返回所有状态
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[Task]: 任务列表
        """
        query = self.db.query(Task)

        if status:
            query = query.filter(Task.status == status)

        return query.order_by(desc(Task.created_at)).limit(limit).offset(offset).all()

    def get_task_logs(self, task_id: str, limit: int = 1000) -> List[TaskLog]:
        """
        获取任务日志

        Args:
            task_id: 任务 ID
            limit: 日志数量限制

        Returns:
            List[TaskLog]: 日志列表
        """
        return (
            self.db.query(TaskLog)
            .filter(TaskLog.task_id == task_id)
            .order_by(desc(TaskLog.timestamp))
            .limit(limit)
            .all()
        )

    def get_task_stats(self) -> Dict[str, int]:
        """
        获取任务统计信息

        Returns:
            Dict: 统计信息
        """
        total = self.db.query(Task).count()
        pending = self.db.query(Task).filter(Task.status == TaskStatus.PENDING).count()
        running = self.db.query(Task).filter(Task.status == TaskStatus.RUNNING).count()
        completed = self.db.query(Task).filter(Task.status == TaskStatus.COMPLETED).count()
        failed = self.db.query(Task).filter(Task.status == TaskStatus.FAILED).count()
        cancelled = self.db.query(Task).filter(Task.status == TaskStatus.CANCELLED).count()

        return {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
        }

    def add_task_log(self, task_id: str, level: str, message: str) -> None:
        """
        添加任务日志

        Args:
            task_id: 任务 ID
            level: 日志级别
            message: 日志消息
        """
        try:
            log = TaskLog(
                task_id=task_id,
                level=level,
                message=message,
                timestamp=datetime.utcnow(),
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"添加日志失败: {e}", exc_info=True)

    def close(self) -> None:
        """关闭数据库连接"""
        if self.db:
            self.db.close()
