"""
配置管理 API 测试

测试 app/api/config.py 模块的所有端点：
- GET /api/config/status - 获取配置状态
- GET /api/config/webhook-url - 获取 Webhook URL
"""

import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
class TestConfigStatusAPI:
    """测试配置状态 API"""

    async def test_get_config_status_success(self, async_client):
        """测试成功获取配置状态"""
        response = await async_client.get("/api/config/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "configured" in data
        assert "missing_keys" in data
        assert "webhook_url" in data
        assert "repo_info" in data

    async def test_get_config_status_includes_webhook_url(self, async_client):
        """测试配置状态包含 Webhook URL"""
        response = await async_client.get("/api/config/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Webhook URL 应该包含主机名和路径
        if data.get("webhook_url"):
            assert "webhook/github" in data["webhook_url"]
            assert "http" in data["webhook_url"]

    async def test_get_config_status_includes_repo_info(self, async_client):
        """测试配置状态包含仓库信息"""
        response = await async_client.get("/api/config/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data.get("repo_info"):
            repo_info = data["repo_info"]
            assert "repo_full_name" in repo_info
            assert "repo_path" in repo_info
            assert "default_branch" in repo_info

    async def test_get_config_status_unconfigured(self, async_client):
        """测试未配置时的状态响应"""
        with patch("app.api.config.get_config", side_effect=Exception("配置未找到")):
            response = await async_client.get("/api/config/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # 未配置时应该返回 false
            assert data["configured"] is False
            assert len(data["missing_keys"]) > 0
            assert data["webhook_url"] is None
            assert data["repo_info"] is None


@pytest.mark.asyncio
class TestWebhookURLAPI:
    """测试 Webhook URL API"""

    async def test_get_webhook_url_success(self, async_client):
        """测试成功获取 Webhook URL"""
        response = await async_client.get("/api/config/webhook-url")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "url" in data
        assert "secret" in data

        # 验证 URL 格式
        assert "webhook/github" in data["url"]
        assert data["url"].startswith("http")

        # 验证 secret 存在
        assert len(data["secret"]) > 0

    async def test_get_webhook_url_format(self, async_client):
        """测试 Webhook URL 格式正确性"""
        response = await async_client.get("/api/config/webhook-url")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        url = data["url"]

        # URL 应该包含协议
        assert url.startswith("http://") or url.startswith("https://")

        # URL 应该包含端点路径
        assert "/webhook/github" in url

    async def test_get_webhook_url_config_error(self, async_client):
        """测试配置错误时的处理"""
        with patch("app.api.config.get_config", side_effect=Exception("配置错误")):
            response = await async_client.get("/api/config/webhook-url")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()

            assert "detail" in data


@pytest.mark.asyncio
class TestConfigAPIIntegration:
    """配置 API 集成测试"""

    async def test_config_endpoints_consistency(self, async_client):
        """测试配置端点之间的一致性"""
        # 获取配置状态
        status_response = await async_client.get("/api/config/status")
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()

        # 获取 Webhook URL
        webhook_response = await async_client.get("/api/config/webhook-url")
        assert webhook_response.status_code == status.HTTP_200_OK
        webhook_data = webhook_response.json()

        # 如果配置正常，两个端点返回的 webhook URL 应该一致
        if status_data.get("webhook_url") and status_data.get("configured"):
            assert status_data["webhook_url"] == webhook_data["url"]

    async def test_config_status_response_model(self, async_client):
        """测试配置状态响应模型符合规范"""
        response = await async_client.get("/api/config/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证必需字段
        required_fields = ["configured", "missing_keys", "webhook_url", "repo_info"]
        for field in required_fields:
            assert field in data

        # 验证字段类型
        assert isinstance(data["configured"], bool)
        assert isinstance(data["missing_keys"], list)
        assert data["webhook_url"] is None or isinstance(data["webhook_url"], str)
        assert data["repo_info"] is None or isinstance(data["repo_info"], dict)

    async def test_webhook_url_response_model(self, async_client):
        """测试 Webhook URL 响应模型符合规范"""
        response = await async_client.get("/api/config/webhook-url")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证必需字段
        assert "url" in data
        assert "secret" in data

        # 验证字段类型
        assert isinstance(data["url"], str)
        assert isinstance(data["secret"], str)
        assert len(data["url"]) > 0
        assert len(data["secret"]) > 0


@pytest.mark.asyncio
class TestConfigAPIErrors:
    """配置 API 错误处理测试"""

    async def test_config_status_internal_error(self, async_client):
        """测试配置状态内部错误处理"""
        with patch("app.api.config.get_config", side_effect=RuntimeError("内部错误")):
            response = await async_client.get("/api/config/status")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_webhook_url_internal_error(self, async_client):
        """测试 Webhook URL 内部错误处理"""
        with patch("app.api.config.get_config", side_effect=RuntimeError("内部错误")):
            response = await async_client.get("/api/config/webhook-url")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_config_status_exception_handling(self, async_client):
        """测试异常情况下的处理"""
        # Mock 生成 webhook URL 时抛出异常
        with patch("app.utils.webhook.generate_webhook_url", side_effect=Exception("生成失败")):
            response = await async_client.get("/api/config/status")

            # 应该返回错误
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
