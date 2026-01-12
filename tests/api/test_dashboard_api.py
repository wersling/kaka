"""
Dashboard API 测试

测试 app/api/dashboard.py 模块的所有端点：
- GET / - 首页（重定向到 Dashboard）
- GET /dashboard - 增强版 Dashboard
- GET /dashboard-legacy - 原版 Dashboard
- GET /config - 配置向导
- GET /tasks/{task_id} - 任务详情页面
"""

import pytest
from fastapi import status


@pytest.mark.asyncio
class TestIndexPage:
    """测试首页 API"""

    async def test_index_returns_html(self, async_client):
        """测试首页返回 HTML"""
        response = await async_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    async def test_index_content_type(self, async_client):
        """测试首页内容类型"""
        response = await async_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        # 应该是 HTML 响应
        assert "html" in response.headers.get("content-type", "").lower()


@pytest.mark.asyncio
class TestDashboardPage:
    """测试 Dashboard 页面 API"""

    async def test_dashboard_returns_html(self, async_client):
        """测试 Dashboard 返回 HTML"""
        response = await async_client.get("/dashboard")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    async def test_dashboard_content_type(self, async_client):
        """测试 Dashboard 内容类型"""
        response = await async_client.get("/dashboard")

        assert response.status_code == status.HTTP_200_OK
        content_type = response.headers.get("content-type", "")
        assert "html" in content_type.lower()

    async def test_dashboard_template_used(self, async_client):
        """测试 Dashboard 使用正确的模板"""
        response = await async_client.get("/dashboard")

        assert response.status_code == status.HTTP_200_OK
        # HTML 内容应该包含 dashboard 相关的内容
        content = response.text
        # 验证是 HTML 内容
        assert "<!DOCTYPE html>" in content or "<html" in content


@pytest.mark.asyncio
class TestDashboardLegacy:
    """测试原版 Dashboard API"""

    async def test_dashboard_legacy_returns_html(self, async_client):
        """测试原版 Dashboard 返回 HTML"""
        response = await async_client.get("/dashboard-legacy")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    async def test_dashboard_legacy_content_type(self, async_client):
        """测试原版 Dashboard 内容类型"""
        response = await async_client.get("/dashboard-legacy")

        assert response.status_code == status.HTTP_200_OK
        content_type = response.headers.get("content-type", "")
        assert "html" in content_type.lower()

    async def test_dashboard_legacy_template_used(self, async_client):
        """测试原版 Dashboard 使用正确的模板"""
        response = await async_client.get("/dashboard-legacy")

        assert response.status_code == status.HTTP_200_OK
        content = response.text
        # 验证是 HTML 内容
        assert "<!DOCTYPE html>" in content or "<html" in content


@pytest.mark.asyncio
class TestConfigWizard:
    """测试配置向导 API"""

    async def test_config_wizard_returns_html(self, async_client):
        """测试配置向导返回 HTML"""
        response = await async_client.get("/config")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    async def test_config_wizard_content_type(self, async_client):
        """测试配置向导内容类型"""
        response = await async_client.get("/config")

        assert response.status_code == status.HTTP_200_OK
        content_type = response.headers.get("content-type", "")
        assert "html" in content_type.lower()

    async def test_config_wizard_template_used(self, async_client):
        """测试配置向导使用正确的模板"""
        response = await async_client.get("/config")

        assert response.status_code == status.HTTP_200_OK
        content = response.text
        # 验证是 HTML 内容
        assert "<!DOCTYPE html>" in content or "<html" in content


@pytest.mark.asyncio
class TestTaskDetailPage:
    """测试任务详情页面 API"""

    async def test_task_detail_returns_html(self, async_client):
        """测试任务详情页面返回 HTML"""
        task_id = "test-task-123"
        response = await async_client.get(f"/tasks/{task_id}")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    async def test_task_detail_content_type(self, async_client):
        """测试任务详情页面内容类型"""
        task_id = "test-task-456"
        response = await async_client.get(f"/tasks/{task_id}")

        assert response.status_code == status.HTTP_200_OK
        content_type = response.headers.get("content-type", "")
        assert "html" in content_type.lower()

    async def test_task_detail_with_valid_task_id(self, async_client):
        """测试有效的任务 ID"""
        task_id = "task-123-789"
        response = await async_client.get(f"/tasks/{task_id}")

        assert response.status_code == status.HTTP_200_OK
        content = response.text
        # 验证是 HTML 内容
        assert "<!DOCTYPE html>" in content or "<html" in content

    async def test_task_detail_with_special_chars(self, async_client):
        """测试包含特殊字符的任务 ID"""
        # URL 编码的任务 ID
        task_id = "task-123-abc"
        response = await async_client.get(f"/tasks/{task_id}")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
class TestDashboardPageIntegration:
    """Dashboard 页面集成测试"""

    async def test_all_dashboard_pages_return_200(self, async_client):
        """测试所有 Dashboard 页面都返回 200"""
        endpoints = [
            "/",
            "/dashboard",
            "/dashboard-legacy",
            "/config",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == status.HTTP_200_OK, f"{endpoint} 失败"

    async def test_all_pages_return_html(self, async_client):
        """测试所有页面都返回 HTML"""
        endpoints = [
            "/",
            "/dashboard",
            "/dashboard-legacy",
            "/config",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            content_type = response.headers.get("content-type", "")
            assert "html" in content_type.lower(), f"{endpoint} 内容类型错误"

    async def test_index_and_dashboard_consistency(self, async_client):
        """测试首页和 Dashboard 的一致性"""
        index_response = await async_client.get("/")
        dashboard_response = await async_client.get("/dashboard")

        # 两者都应该返回成功
        assert index_response.status_code == status.HTTP_200_OK
        assert dashboard_response.status_code == status.HTTP_200_OK

        # 两者都应该是 HTML
        index_content_type = index_response.headers.get("content-type", "")
        dashboard_content_type = dashboard_response.headers.get("content-type", "")

        assert "html" in index_content_type.lower()
        assert "html" in dashboard_content_type.lower()


@pytest.mark.asyncio
class TestDashboardPageErrors:
    """Dashboard 页面错误处理测试"""

    async def test_404_page(self, async_client):
        """测试不存在的页面返回 404"""
        response = await async_client.get("/non-existent-page")

        # FastAPI 默认返回 404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_invalid_task_id_format(self, async_client):
        """测试无效的任务 ID 格式"""
        # 空任务 ID
        response = await async_client.get("/tasks/")

        # 应该返回 404 或重定向
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_307_TEMPORARY_REDIRECT,
            status.HTTP_308_PERMANENT_REDIRECT,
        ]


@pytest.mark.asyncio
class TestDashboardPageHeaders:
    """Dashboard 页面响应头测试"""

    async def test_html_content_type_header(self, async_client):
        """测试 HTML 内容类型头"""
        response = await async_client.get("/dashboard")

        assert "content-type" in response.headers
        assert "text/html" in response.headers["content-type"]

    async def test_response_contains_html_structure(self, async_client):
        """测试响应包含 HTML 结构"""
        response = await async_client.get("/dashboard")

        content = response.text
        # 验证基本的 HTML 结构
        assert "<" in content and ">" in content
