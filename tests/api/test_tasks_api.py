"""
任务监控 API 测试

测试 app/api/tasks.py 模块的所有端点：
- GET /tasks - 获取任务列表
- GET /tasks/stats - 获取任务统计
- GET /concurrency/stats - 获取并发状态
- GET /tasks/{task_id} - 获取任务详情
- GET /tasks/issue/{issue_number} - 根据 Issue 获取任务
- POST /tasks/{task_id}/cancel - 取消任务
- POST /tasks/{task_id}/retry - 重试任务
"""

import pytest
from fastapi import status
from unittest.mock import patch, MagicMock
from app.db.models import Task, TaskStatus


@pytest.mark.asyncio
class TestTasksListAPI:
    """测试任务列表 API"""

    async def test_get_tasks_success(self, async_client):
        """测试成功获取任务列表"""
        response = await async_client.get("/tasks")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "tasks" in data
        assert "total" in data
        assert "stats" in data

        # 验证数据类型
        assert isinstance(data["tasks"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["stats"], dict)

    async def test_get_tasks_with_status_filter(self, async_client):
        """测试按状态筛选任务"""
        status_filter = "completed"
        response = await async_client.get(f"/tasks?status={status_filter}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "tasks" in data
        # 所有返回的任务都应该匹配状态（如果有任务的话）
        for task in data.get("tasks", []):
            assert task["status"] == status_filter

    async def test_get_tasks_with_invalid_status(self, async_client):
        """测试无效的状态筛选"""
        response = await async_client.get("/tasks?status=invalid_status")

        # 应该返回 400 错误
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_get_tasks_with_limit(self, async_client):
        """测试限制返回数量"""
        limit = 5
        response = await async_client.get(f"/tasks?limit={limit}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 返回的任务数量不应该超过 limit
        assert data["total"] <= limit

    async def test_get_tasks_with_offset(self, async_client):
        """测试分页偏移"""
        offset = 10
        response = await async_client.get(f"/tasks?offset={offset}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "tasks" in data

    async def test_get_tasks_limit_validation(self, async_client):
        """测试 limit 参数验证"""
        # 超过最大值
        response = await async_client.get("/tasks?limit=2000")

        # 应该返回 422 验证错误
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_tasks_negative_limit(self, async_client):
        """测试负数 limit"""
        response = await async_client.get("/tasks?limit=-1")

        # 应该返回 422 验证错误
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_tasks_negative_offset(self, async_client):
        """测试负数 offset"""
        response = await async_client.get("/tasks?offset=-1")

        # 应该返回 422 验证错误
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestTaskStatsAPI:
    """测试任务统计 API"""

    async def test_get_task_stats_success(self, async_client):
        """测试成功获取任务统计"""
        response = await async_client.get("/tasks/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证统计字段
        expected_fields = ["total", "pending", "running", "completed", "failed", "cancelled"]
        for field in expected_fields:
            assert field in data

        # 验证数据类型
        for field in expected_fields:
            assert isinstance(data[field], int)

    async def test_task_stats_non_negative(self, async_client):
        """测试统计数据非负"""
        response = await async_client.get("/tasks/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 所有统计值应该 >= 0
        for key, value in data.items():
            assert value >= 0, f"{key} 应该 >= 0，但得到 {value}"

    async def test_task_stats_consistency(self, async_client):
        """测试统计数据一致性"""
        response = await async_client.get("/tasks/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # total 应该等于所有状态之和
        total = data["total"]
        sum_by_status = (
            data["pending"] +
            data["running"] +
            data["completed"] +
            data["failed"] +
            data["cancelled"]
        )

        assert total == sum_by_status, f"total ({total}) != 各状态之和 ({sum_by_status})"


@pytest.mark.asyncio
class TestConcurrencyStatsAPI:
    """测试并发统计 API"""

    async def test_get_concurrency_stats_success(self, async_client):
        """测试成功获取并发统计"""
        response = await async_client.get("/concurrency/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证统计字段
        assert "max_concurrent" in data
        assert "current_running" in data
        assert "available" in data

    async def test_concurrency_stats_values(self, async_client):
        """测试并发统计值"""
        response = await async_client.get("/concurrency/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证数据类型和范围
        assert isinstance(data["max_concurrent"], int)
        assert isinstance(data["current_running"], int)
        assert isinstance(data["available"], int)

        assert data["max_concurrent"] > 0
        assert data["current_running"] >= 0
        assert data["available"] >= 0

    async def test_concurrency_stats_consistency(self, async_client):
        """测试并发统计数据一致性"""
        response = await async_client.get("/concurrency/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # available 应该等于 max_concurrent - current_running
        expected_available = data["max_concurrent"] - data["current_running"]
        assert data["available"] == expected_available


@pytest.mark.asyncio
class TestTaskDetailAPI:
    """测试任务详情 API"""

    async def test_get_task_detail_success(self, async_client):
        """测试成功获取任务详情"""
        # Mock 返回任务
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.task_id = "test-task-001"
            mock_task.to_dict.return_value = {
                "task_id": "test-task-001",
                "status": "running",
                "issue_number": 1
            }

            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = mock_task
            mock_instance.get_task_logs.return_value = []
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks/test-task-001")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "task" in data
            assert "logs" in data

    async def test_get_task_detail_not_found(self, async_client):
        """测试任务不存在"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = None
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks/nonexistent-task")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_task_detail_includes_logs(self, async_client):
        """测试任务详情包含日志"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.task_id = "test-task-002"

            mock_log = MagicMock()
            mock_log.to_dict.return_value = {
                "level": "INFO",
                "message": "Test log"
            }

            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = mock_task
            mock_instance.get_task_logs.return_value = [mock_log]
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks/test-task-002")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "logs" in data
            assert isinstance(data["logs"], list)


@pytest.mark.asyncio
class TestTasksByIssueAPI:
    """测试根据 Issue 获取任务 API"""

    async def test_get_tasks_by_issue_success(self, async_client):
        """测试成功获取 Issue 任务"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.to_dict.return_value = {
                "task_id": "test-task-003",
                "issue_number": 42
            }

            mock_instance = MagicMock()
            mock_instance.get_tasks_by_issue.return_value = [mock_task]
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks/issue/42")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "issue_number" in data
            assert data["issue_number"] == 42
            assert "tasks" in data
            assert "total" in data

    async def test_get_tasks_by_issue_not_found(self, async_client):
        """测试 Issue 没有任务"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_tasks_by_issue.return_value = []
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks/issue/999")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["total"] == 0
            assert len(data["tasks"]) == 0

    async def test_get_tasks_by_issue_invalid_number(self, async_client):
        """测试无效的 Issue 编号"""
        response = await async_client.get("/tasks/issue/invalid")

        # 应该返回 422 验证错误
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestCancelTaskAPI:
    """测试取消任务 API"""

    async def test_cancel_pending_task_success(self, async_client):
        """测试成功取消待处理任务"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.task_id = "test-task-004"
            mock_task.status = TaskStatus.PENDING
            mock_task.to_dict.return_value = {
                "task_id": "test-task-004",
                "status": "cancelled"
            }

            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = mock_task
            mock_instance.update_task_status.return_value = mock_task
            mock_service.return_value = mock_instance

            response = await async_client.post("/tasks/test-task-004/cancel")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert "task" in data

    async def test_cancel_running_task(self, async_client):
        """测试取消运行中任务"""
        with patch("app.api.tasks.TaskService") as mock_service:
            with patch("app.api.tasks.process_manager") as mock_pm:
                mock_task = MagicMock()
                mock_task.task_id = "test-task-005"
                mock_task.status = TaskStatus.RUNNING
                mock_task.to_dict.return_value = {
                    "task_id": "test-task-005",
                    "status": "cancelled"
                }

                mock_instance = MagicMock()
                mock_instance.get_task_by_id.return_value = mock_task
                mock_instance.update_task_status.return_value = mock_task
                mock_service.return_value = mock_instance

                mock_pm.terminate_process = MagicMock(return_value=True)

                response = await async_client.post("/tasks/test-task-005/cancel")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                assert data["success"] is True
                assert data["process_terminated"] is True

    async def test_cancel_completed_task_fails(self, async_client):
        """测试取消已完成任务失败"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.task_id = "test-task-006"
            mock_task.status = TaskStatus.COMPLETED

            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = mock_task
            mock_service.return_value = mock_instance

            response = await async_client.post("/tasks/test-task-006/cancel")

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_cancel_nonexistent_task(self, async_client):
        """测试取消不存在的任务"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = None
            mock_service.return_value = mock_instance

            response = await async_client.post("/tasks/nonexistent-task/cancel")

            assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestRetryTaskAPI:
    """测试重试任务 API"""

    async def test_retry_failed_task_success(self, async_client):
        """测试成功重试失败任务"""
        with patch("app.api.tasks.TaskService") as mock_service:
            with patch("app.api.tasks.asyncio.get_event_loop") as mock_loop:
                mock_task = MagicMock()
                mock_task.task_id = "test-task-007"
                mock_task.status = TaskStatus.FAILED
                mock_task.retry_count = 1
                mock_task.max_retries = 3
                mock_task.issue_number = 1
                mock_task.issue_title = "Test"
                mock_task.issue_url = "http://test"
                mock_task.issue_body = "Body"
                mock_task.branch_name = "branch"
                mock_task.to_dict.return_value = {
                    "task_id": "test-task-007",
                    "status": "pending",
                    "retry_count": 1
                }

                mock_instance = MagicMock()
                mock_instance.get_task_by_id.return_value = mock_task
                mock_instance.retry_task.return_value = mock_task
                mock_service.return_value = mock_instance

                mock_event_loop = MagicMock()
                mock_event_loop.is_running.return_value = True
                mock_task_obj = MagicMock()
                mock_task_obj.done.return_value = False
                mock_event_loop.create_task.return_value = mock_task_obj
                mock_loop.return_value = mock_event_loop

                response = await async_client.post("/tasks/test-task-007/retry")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                assert data["success"] is True
                assert "task" in data

    async def test_retry_completed_task_fails(self, async_client):
        """测试重试已完成任务失败"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.task_id = "test-task-008"
            mock_task.status = TaskStatus.COMPLETED

            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = mock_task
            mock_service.return_value = mock_instance

            response = await async_client.post("/tasks/test-task-008/retry")

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_retry_max_retries_exceeded(self, async_client):
        """测试超过最大重试次数"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.task_id = "test-task-009"
            mock_task.status = TaskStatus.FAILED
            mock_task.retry_count = 3
            mock_task.max_retries = 3

            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = mock_task
            mock_service.return_value = mock_instance

            response = await async_client.post("/tasks/test-task-009/retry")

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_retry_nonexistent_task(self, async_client):
        """测试重试不存在的任务"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = None
            mock_service.return_value = mock_instance

            response = await async_client.post("/tasks/nonexistent-task/retry")

            assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestTasksAPIIntegration:
    """任务 API 集成测试"""

    async def test_tasks_and_stats_consistency(self, async_client):
        """测试任务列表和统计的一致性"""
        # 获取任务统计
        stats_response = await async_client.get("/tasks/stats")
        assert stats_response.status_code == status.HTTP_200_OK
        stats = stats_response.json()

        # 获取任务列表
        tasks_response = await async_client.get("/tasks")
        assert tasks_response.status_code == status.HTTP_200_OK
        tasks_data = tasks_response.json()

        # 验证数据结构
        assert "total" in stats
        assert "tasks" in tasks_data
        assert "total" in tasks_data

    async def test_all_endpoints_return_json(self, async_client):
        """测试所有端点返回 JSON"""
        endpoints = [
            "/tasks",
            "/tasks/stats",
            "/concurrency/stats",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            content_type = response.headers.get("content-type", "")

            # 所有端点应该返回 JSON
            assert "application/json" in content_type, f"{endpoint} 应该返回 JSON"


@pytest.mark.asyncio
class TestTasksAPIErrors:
    """任务 API 错误处理测试"""

    async def test_tasks_service_error(self, async_client):
        """测试任务服务错误处理"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_all_tasks.side_effect = Exception("服务错误")
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_stats_service_error(self, async_client):
        """测试统计服务错误处理"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_task_stats.side_effect = Exception("统计错误")
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks/stats")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
class TestTasksAPISecurity:
    """任务 API 安全测试"""

    async def test_tasks_no_sensitive_info(self, async_client):
        """测试任务列表不泄露敏感信息"""
        response = await async_client.get("/tasks")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 检查不应包含敏感信息
        data_str = str(data)
        # 可能包含路径，但不应该包含敏感目录
        assert "/home/" not in data_str
        assert "/root/" not in data_str

    async def test_task_detail_no_secrets(self, async_client):
        """测试任务详情不泄露密钥"""
        with patch("app.api.tasks.TaskService") as mock_service:
            mock_task = MagicMock()
            mock_task.task_id = "test-task-security"

            mock_instance = MagicMock()
            mock_instance.get_task_by_id.return_value = mock_task
            mock_instance.get_task_logs.return_value = []
            mock_service.return_value = mock_instance

            response = await async_client.get("/tasks/test-task-security")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # 检查不应包含敏感信息
            data_str = str(data)
            assert "password" not in data_str.lower()
            assert "token" not in data_str.lower()
            assert "secret" not in data_str.lower()
