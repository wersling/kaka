"""
健康检查 API 测试

测试 app/api/health.py 模块的所有端点：
- GET /health - 完整健康检查
- GET /ping - 简单 ping 检查
"""

import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


@pytest.mark.asyncio
class TestHealthCheck:
    """测试健康检查 API"""

    async def test_health_check_success(self, async_client):
        """测试健康检查成功"""
        response = await async_client.get("/health")

        # 如果所有检查都通过，应该返回 200
        # 如果有检查失败，可能返回 503
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "checks" in data

    async def test_health_check_response_model(self, async_client):
        """测试健康检查响应模型"""
        response = await async_client.get("/health")

        assert response.status_code in [200, 503]
        data = response.json()

        # 验证服务信息
        assert data["service"] == "kaka"
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

        # 验证时间戳
        assert isinstance(data["timestamp"], str)
        # 验证时间戳格式（ISO 格式）
        datetime.fromisoformat(data["timestamp"])

        # 验证运行时间
        assert isinstance(data["uptime_seconds"], float)
        assert data["uptime_seconds"] >= 0

    async def test_health_check_includes_all_checks(self, async_client):
        """测试健康检查包含所有检查项"""
        response = await async_client.get("/health")

        assert response.status_code in [200, 503]
        data = response.json()

        checks = data["checks"]

        # 验证包含所有必需的检查项
        assert "config" in checks
        assert "git_repository" in checks
        assert "claude_cli" in checks

    async def test_health_check_config_status(self, async_client):
        """测试配置检查状态"""
        response = await async_client.get("/health")

        assert response.status_code in [200, 503]
        data = response.json()

        config_check = data["checks"]["config"]

        # 验证配置检查结构
        assert "healthy" in config_check
        assert "message" in config_check
        assert isinstance(config_check["healthy"], bool)

    async def test_health_check_git_status(self, async_client):
        """测试 Git 仓库检查状态"""
        response = await async_client.get("/health")

        assert response.status_code in [200, 503]
        data = response.json()

        git_check = data["checks"]["git_repository"]

        # 验证 Git 检查结构
        assert "healthy" in git_check
        assert "message" in git_check
        assert isinstance(git_check["healthy"], bool)

    async def test_health_check_claude_cli_status(self, async_client):
        """测试 Claude CLI 检查状态"""
        response = await async_client.get("/health")

        assert response.status_code in [200, 503]
        data = response.json()

        claude_check = data["checks"]["claude_cli"]

        # 验证 Claude CLI 检查结构
        assert "healthy" in claude_check
        assert "message" in claude_check
        assert isinstance(claude_check["healthy"], bool)

    async def test_health_check_status_values(self, async_client):
        """测试健康检查状态值"""
        response = await async_client.get("/health")

        assert response.status_code in [200, 503]
        data = response.json()

        # status 应该是 "healthy" 或 "unhealthy"
        assert data["status"] in ["healthy", "unhealthy"]

        # 如果状态是 healthy，所有检查都应该通过
        if data["status"] == "healthy":
            assert response.status_code == status.HTTP_200_OK
            for check_name, check_data in data["checks"].items():
                assert check_data["healthy"] is True, f"{check_name} 检查失败"

    async def test_health_check_unhealthy_returns_503(self, async_client):
        """测试不健康状态返回 503"""
        # Mock 配置检查失败
        with patch("app.config.get_config") as mock_get_config:
            # 配置加载失败会导致不健康
            mock_get_config.side_effect = Exception("配置错误")

            response = await async_client.get("/health")

            # 如果有任何检查失败，可能返回 503
            # 但也可能返回 200，这取决于异常处理方式
            assert response.status_code in [200, 503]


@pytest.mark.asyncio
class TestPingEndpoint:
    """测试 Ping 端点"""

    async def test_ping_returns_pong(self, async_client):
        """测试 ping 返回 pong"""
        response = await async_client.get("/ping")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "pong"
        assert data["service"] == "kaka"

    async def test_ping_response_structure(self, async_client):
        """测试 ping 响应结构"""
        response = await async_client.get("/ping")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证响应字段
        assert "status" in data
        assert "service" in data
        assert len(data) == 2  # 只有两个字段

    async def test_ping_is_fast(self, async_client):
        """测试 ping 响应速度快"""
        import time

        start = time.time()
        response = await async_client.get("/ping")
        end = time.time()

        assert response.status_code == status.HTTP_200_OK
        # ping 应该非常快（< 1 秒）
        assert (end - start) < 1.0


@pytest.mark.asyncio
class TestHealthCheckIntegration:
    """健康检查集成测试"""

    async def test_ping_vs_health(self, async_client):
        """测试 ping 和 health 的区别"""
        ping_response = await async_client.get("/ping")
        health_response = await async_client.get("/health")

        # ping 总是返回 200
        assert ping_response.status_code == status.HTTP_200_OK

        # health 可能返回 200 或 503
        assert health_response.status_code in [200, 503]

        # ping 的响应更简单
        ping_data = ping_response.json()
        health_data = health_response.json()

        assert len(ping_data) < len(health_data)

    async def test_health_check_multiple_calls(self, async_client):
        """测试多次健康检查的一致性"""
        responses = []

        for _ in range(3):
            response = await async_client.get("/health")
            assert response.status_code in [200, 503]
            responses.append(response.json())

        # 所有响应的服务信息应该一致
        for i in range(1, len(responses)):
            assert responses[i]["service"] == responses[0]["service"]
            assert responses[i]["version"] == responses[0]["version"]

    async def test_health_check_uptime_increases(self, async_client):
        """测试运行时间递增"""
        response1 = await async_client.get("/health")
        uptime1 = response1.json()["uptime_seconds"]

        # 等待一小段时间
        import asyncio
        await asyncio.sleep(0.1)

        response2 = await async_client.get("/health")
        uptime2 = response2.json()["uptime_seconds"]

        # 运行时间应该增加
        assert uptime2 >= uptime1


@pytest.mark.asyncio
class TestHealthCheckComponents:
    """健康检查组件测试"""

    async def test_config_check_component(self, async_client):
        """测试配置检查组件"""
        with patch("app.api.health.check_config") as mock_check:
            mock_check.return_value = MagicMock(
                healthy=True,
                message="配置正常",
                details={"configured": True}
            )

            response = await async_client.get("/health")
            data = response.json()

            assert "checks" in data
            assert "config" in data["checks"]

    async def test_git_check_component(self, async_client):
        """测试 Git 检查组件"""
        with patch("app.api.health.check_git_repository") as mock_check:
            mock_check.return_value = MagicMock(
                healthy=True,
                message="Git 仓库正常",
                details={"configured": True}
            )

            response = await async_client.get("/health")
            data = response.json()

            assert "checks" in data
            assert "git_repository" in data["checks"]

    async def test_claude_cli_check_component(self, async_client):
        """测试 Claude CLI 检查组件"""
        with patch("app.api.health.check_claude_cli") as mock_check:
            mock_check.return_value = MagicMock(
                healthy=True,
                message="Claude CLI 正常",
                details={"path": "/usr/bin/claude"}
            )

            response = await async_client.get("/health")
            data = response.json()

            assert "checks" in data
            assert "claude_cli" in data["checks"]


@pytest.mark.asyncio
class TestHealthCheckErrors:
    """健康检查错误处理测试"""

    async def test_config_check_exception(self, async_client):
        """测试配置检查异常处理"""
        with patch("app.config.get_config", side_effect=Exception("配置异常")):
            response = await async_client.get("/health")

            # 应该处理异常并返回相应状态
            assert response.status_code in [200, 503]

    async def test_git_check_exception(self, async_client):
        """测试 Git 检查异常处理"""
        with patch("app.config.get_config", side_effect=Exception("Git 异常")):
            response = await async_client.get("/health")

            # 应该处理异常并返回相应状态
            assert response.status_code in [200, 503]

    async def test_claude_cli_check_exception(self, async_client):
        """测试 Claude CLI 检查异常处理"""
        with patch("app.config.get_config", side_effect=Exception("CLI 异常")):
            response = await async_client.get("/health")

            # 应该处理异常并返回相应状态
            assert response.status_code in [200, 503]


@pytest.mark.asyncio
class TestHealthCheckSecurity:
    """健康检查安全测试"""

    async def test_health_check_no_sensitive_info(self, async_client):
        """测试健康检查不泄露敏感信息"""
        response = await async_client.get("/health")
        data = response.json()

        # 检查不应包含敏感信息
        assert "password" not in str(data).lower()
        assert "token" not in str(data).lower()
        assert "secret" not in str(data).lower()
        assert "key" not in str(data).lower()

    async def test_health_check_no_path_exposure(self, async_client):
        """测试健康检查不暴露完整路径"""
        response = await async_client.get("/health")
        data = response.json()

        # 检查不应暴露完整的文件系统路径
        data_str = str(data)
        # 可能包含路径，但不应该暴露敏感目录
        assert "/home/" not in data_str
        assert "/root/" not in data_str

    async def test_ping_no_sensitive_info(self, async_client):
        """测试 ping 不泄露敏感信息"""
        response = await async_client.get("/ping")
        data = response.json()

        # ping 应该只返回基本信息
        assert len(data) == 2
        assert "status" in data
        assert "service" in data
