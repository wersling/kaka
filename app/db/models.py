"""
Database Models for Task Monitoring
使用 SQLAlchemy ORM 定义数据表结构
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum


class TaskStatus(enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(object):
    """任务表 - 存储所有AI开发任务"""
    __tablename__ = "tasks"

    # 主键和基本信息
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), unique=True, nullable=False, index=True)  # task-{issue_number}-{timestamp}
    issue_number = Column(Integer, nullable=False, index=True)
    issue_title = Column(String(500), nullable=False)
    issue_url = Column(String(1000), nullable=False)
    issue_body = Column(Text, nullable=True)

    # 分支信息
    branch_name = Column(String(255), nullable=False)

    # 状态管理
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 执行结果
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=True)  # 秒

    # PR 信息
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(1000), nullable=True)

    # 开发总结
    development_summary = Column(Text, nullable=True)

    # 重试信息
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)

    # 关联日志
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "issue_number": self.issue_number,
            "issue_title": self.issue_title,
            "issue_url": self.issue_url,
            "branch_name": self.branch_name,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "development_summary": self.development_summary,
            "retry_count": self.retry_count,
        }


class TaskLog(object):
    """任务日志表 - 存储任务执行日志"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)

    # 日志信息
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联
    task = relationship("Task", back_populates="logs")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# 导出 Base 用于创建表
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# 重新定义模型继承 Base
class Task(Base):
    """任务表 - 存储所有AI开发任务"""
    __tablename__ = "tasks"

    # 主键和基本信息
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), unique=True, nullable=False, index=True)  # task-{issue_number}-{timestamp}
    issue_number = Column(Integer, nullable=False, index=True)
    issue_title = Column(String(500), nullable=False)
    issue_url = Column(String(1000), nullable=False)
    issue_body = Column(Text, nullable=True)

    # 分支信息
    branch_name = Column(String(255), nullable=False)

    # 状态管理
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 执行结果
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=True)  # 秒

    # PR 信息
    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(1000), nullable=True)

    # 开发总结
    development_summary = Column(Text, nullable=True)

    # 重试信息
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)

    # 关联日志
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "issue_number": self.issue_number,
            "issue_title": self.issue_title,
            "issue_url": self.issue_url,
            "branch_name": self.branch_name,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "development_summary": self.development_summary,
            "retry_count": self.retry_count,
        }


class TaskLog(Base):
    """任务日志表 - 存储任务执行日志"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)

    # 日志信息
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联
    task = relationship("Task", back_populates="logs")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
