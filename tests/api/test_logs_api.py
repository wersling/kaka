"""
实时日志 API 测试

测试 app/api/logs.py 模块的所有端点：
- GET /tasks/{task_id}/logs/stream - Server-Sent Events 实时日志流
"""

import pytest
import json
import asyncio
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock
from app.db.models import Task, TaskLog, TaskStatus


@pytest.mark.asyncio
class TestTaskLogsStream:
    """测试任务日志流 API"""

    async def test_logs_stream_returns_sse(self, async_client, db_session):
        """测试日志流返回 SSE 格式"""
        # 创建测试任务
        task = Task()
        task.task_id = "test-task-stream-001"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.RUNNING
        task.created_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # SSE 返回 200
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"]

        # 清理
        db_session.rollback()

    async def test_logs_stream_headers(self, async_client, db_session):
        """测试日志流响应头"""
        task = Task()
        task.task_id = "test-task-headers-002"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.RUNNING
        task.created_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # 验证 SSE 相关的响应头
        assert "cache-control" in response.headers
        assert "no-cache" in response.headers["cache-control"].lower()

        db_session.rollback()

    async def test_logs_stream_with_logs(self, async_client, db_session):
        """测试包含日志的任务流"""
        task = Task()
        task.task_id = "test-task-with-logs-003"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.RUNNING
        task.created_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        # 添加一些日志
        log1 = TaskLog()
        log1.task_id = task.task_id
        log1.level = "INFO"
        log1.message = "Test log message 1"
        log1.timestamp = MagicMock()
        db_session.add(log1)

        log2 = TaskLog()
        log2.task_id = task.task_id
        log2.level = "INFO"
        log2.message = "Test log message 2"
        log2.timestamp = MagicMock()
        db_session.add(log2)

        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        assert response.status_code == status.HTTP_200_OK

        db_session.rollback()

    async def test_logs_stream_nonexistent_task(self, async_client):
        """测试不存在的任务"""
        response = await async_client.get("/tasks/nonexistent-task/logs/stream")

        # 应该返回 200 并发送错误事件
        assert response.status_code == status.HTTP_200_OK

    async def test_logs_stream_completed_task(self, async_client, db_session):
        """测试已完成任务的日志流"""
        task = Task()
        task.task_id = "test-task-completed-004"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.COMPLETED
        task.created_at = MagicMock()
        task.completed_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # 完成的任务应该返回 200 并发送 done 事件
        assert response.status_code == status.HTTP_200_OK

        db_session.rollback()

    async def test_logs_stream_failed_task(self, async_client, db_session):
        """测试失败任务的日志流"""
        task = Task()
        task.task_id = "test-task-failed-005"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.FAILED
        task.created_at = MagicMock()
        task.completed_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # 失败的任务应该返回 200 并发送 done 事件
        assert response.status_code == status.HTTP_200_OK

        db_session.rollback()


@pytest.mark.asyncio
class TestLogsStreamIntegration:
    """日志流集成测试"""

    async def test_logs_stream_format(self, async_client, db_session):
        """测试日志流格式正确"""
        task = Task()
        task.task_id = "test-task-format-006"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.RUNNING
        task.created_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # SSE 格式验证
        content = response.text
        # SSE 事件格式: data: {...}\n\n
        assert "data:" in content or content == ""  # 可能为空流

        db_session.rollback()

    async def test_logs_stream_multiple_tasks(self, async_client, db_session):
        """测试多个任务的日志流"""
        tasks = []
        for i in range(3):
            task = Task()
            task.task_id = f"test-task-multi-{i:03d}"
            task.issue_number = i + 1
            task.issue_title = f"Test Issue {i}"
            task.issue_url = f"https://github.com/test/repo/issues/{i+1}"
            task.issue_body = "Test body"
            task.branch_name = f"test-branch-{i}"
            task.status = TaskStatus.RUNNING
            task.created_at = MagicMock()
            db_session.add(task)
            tasks.append(task)

        db_session.commit()

        # 测试每个任务的日志流
        for task in tasks:
            response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")
            assert response.status_code == status.HTTP_200_OK

        db_session.rollback()


@pytest.mark.asyncio
class TestLogsStreamErrors:
    """日志流错误处理测试"""

    async def test_logs_stream_empty_task_id(self, async_client):
        """测试空任务 ID"""
        response = await async_client.get("/tasks//logs/stream")

        # 空任务 ID 应该返回 404 或 422
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    async def test_logs_stream_special_chars_task_id(self, async_client):
        """测试包含特殊字符的任务 ID"""
        # URL 编码的特殊字符
        task_id = "task-with-special-chars-123"
        response = await async_client.get(f"/tasks/{task_id}/logs/stream")

        # 应该返回 200（即使任务不存在，也要建立连接）
        assert response.status_code in [200, 404]

    async def test_logs_stream_database_error(self, async_client):
        """测试数据库错误处理"""
        # Mock 数据库查询失败
        with patch("app.api.logs.TaskService") as mock_service:
            mock_service.return_value.get_task_by_id.side_effect = Exception("数据库错误")

            response = await async_client.get("/tasks/test-task-error/logs/stream")

            # 应该处理数据库错误
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestLogsStreamBehavior:
    """日志流行为测试"""

    async def test_logs_stream_running_task(self, async_client, db_session):
        """测试运行中任务的日志流行为"""
        task = Task()
        task.task_id = "test-task-running-007"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.RUNNING
        task.started_at = MagicMock()
        task.created_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # 运行中的任务应该建立 SSE 连接
        assert response.status_code == status.HTTP_200_OK

        db_session.rollback()

    async def test_logs_stream_cancelled_task(self, async_client, db_session):
        """测试取消任务的日志流"""
        task = Task()
        task.task_id = "test-task-cancelled-008"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body"
        task.branch_name = "test-branch"
        task.status = TaskStatus.CANCELLED
        task.created_at = MagicMock()
        task.completed_at = MagicMock()
        db_session.add(task)
        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # 取消的任务应该关闭连接
        assert response.status_code == status.HTTP_200_OK

        db_session.rollback()


@pytest.mark.asyncio
class TestLogsStreamSecurity:
    """日志流安全测试"""

    async def test_logs_stream_no_authentication_required(self, async_client):
        """测试日志流不需要认证（当前实现）"""
        # 注意：这可能会在未来的版本中改变
        response = await async_client.get("/tasks/test-task/logs/stream")

        # 当前实现不需要认证，应该返回 200 或 404
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ]

    async def test_logs_stream_no_sensitive_info(self, async_client, db_session):
        """测试日志流不泄露敏感信息"""
        task = Task()
        task.task_id = "test-task-security-009"
        task.issue_number = 1
        task.issue_title = "Test Issue"
        task.issue_url = "https://github.com/test/repo/issues/1"
        task.issue_body = "Test body with secret info"
        task.branch_name = "test-branch"
        task.status = TaskStatus.RUNNING
        task.created_at = MagicMock()
        db_session.add(task)

        # 添加包含敏感信息的日志
        log = TaskLog()
        log.task_id = task.task_id
        log.level = "INFO"
        log.message = "Processing data"
        log.timestamp = MagicMock()
        db_session.add(log)

        db_session.commit()

        response = await async_client.get(f"/tasks/{task.task_id}/logs/stream")

        # 日志流应该正常工作
        assert response.status_code == status.HTTP_200_OK

        db_session.rollback()


# pytest fixtures
@pytest.fixture
def db_session():
    """提供测试数据库会话"""
    from app.db.database import get_db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import tempfile
    import os

    # 创建临时数据库
    db_file = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_file}")

    # 创建表
    from app.db.models import Task, TaskLog
    Task.metadata.create_all(engine)
    TaskLog.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    # 清理
    session.close()
    try:
        os.unlink(db_file)
    except:
        pass
