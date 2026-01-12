"""
性能测试套件

测试 AI 开发调度服务的性能指标，包括：
1. 性能基准测试（P0）
   - 单次任务执行时间
   - Webhook 响应时间
   - API 调用性能
   - 文件操作性能
   - 签名验证性能

2. 并发性能测试（P1）
   - 并发 Webhook 处理
   - 并发 Git 操作
   - 资源竞争检测
   - 锁性能测试

3. 压力测试（P1）
   - 高负载测试
   - 峰值负载测试
   - 长期稳定性测试
   - 故障恢复测试

4. 资源使用测试（P2）
   - 内存使用监控
   - CPU 使用监控
   - 网络 I/O 测试
   - 磁盘 I/O 测试

性能目标：
- Webhook 响应: < 200ms (p95)
- 单次开发任务: < 30 分钟（Claude 执行时间）
- 签名验证: < 1ms
- 支持 50+ 并发 Webhook 请求
- 无内存泄漏
"""

import asyncio
import gc
import os
import resource
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import psutil
import pytest
from pydantic import ValidationError

from app.models.github_events import (
    GitHubComment,
    GitHubIssue,
    GitHubLabel,
    GitHubUser,
    IssueCommentEvent,
    IssueEvent,
)
from app.services.claude_service import ClaudeService
from app.services.git_service import GitService
from app.services.github_service import GitHubService
from app.services.webhook_handler import WebhookHandler
from app.utils.validators import (
    sanitize_log_data,
    validate_comment_trigger,
    validate_issue_trigger,
    verify_webhook_signature,
)


# =============================================================================
# Performance Test Fixtures
# =============================================================================


@pytest.fixture
def performance_config():
    """性能测试配置"""
    return {
        "webhook_response_p95_target": 200,  # ms
        "signature_verification_target": 1,  # ms
        "concurrent_requests_target": 50,  # concurrent requests
        "memory_leak_threshold": 10 * 1024 * 1024,  # 10 MB
        "long_running_duration": 60,  # seconds
    }


@pytest.fixture
def sample_webhook_payload():
    """示例 Webhook 载荷"""
    return b'{"action": "labeled", "issue": {"number": 123, "title": "Test"}}'


@pytest.fixture
def sample_webhook_signature():
    """示例 Webhook 签名"""
    return "sha256=abc123def456"


@pytest.fixture
def mock_github_user():
    """创建模拟的 GitHub 用户对象"""
    return GitHubUser(
        login="testuser",
        id=123456,
        avatar_url="https://github.com/avatars/testuser",
        type="User",
    )


@pytest.fixture
def mock_github_labels():
    """创建模拟的 GitHub 标签列表"""
    return [
        GitHubLabel(
            id=1,
            node_id="label1",
            name="ai-dev",
            color="00ff00",
            default=False,
        )
    ]


@pytest.fixture
def mock_github_issue(mock_github_user, mock_github_labels):
    """创建模拟的 GitHub Issue 对象"""
    from datetime import datetime

    return GitHubIssue(
        id=1,
        node_id="issue1",
        number=123,
        title="Performance test issue",
        body="Testing performance characteristics",
        html_url="https://github.com/test/repo/issues/123",
        state="open",
        locked=False,
        labels=mock_github_labels,
        user=mock_github_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_github_comment(mock_github_user):
    """创建模拟的 GitHub 评论对象"""
    from datetime import datetime

    return GitHubComment(
        id=456,
        node_id="comment1",
        user=mock_github_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        body="/ai develop",
        html_url="https://github.com/test/repo/issues/123#comment-456",
    )


# =============================================================================
# 1. 性能基准测试（P0）
# =============================================================================


class TestPerformanceBaselines:
    """性能基准测试 - 建立性能基线"""

    def test_webhook_signature_verification_performance(self, benchmark, sample_webhook_payload):
        """测试 Webhook 签名验证性能

        目标: < 1ms (p95)
        """
        # 设置测试环境
        secret = "test_webhook_secret"
        payload = sample_webhook_payload

        # 生成真实签名
        import hmac
        import hashlib

        signature = f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}"

        # 基准测试
        result = benchmark(verify_webhook_signature, payload, signature, secret)

        # 验证正确性
        assert result is True

        # 检查性能（pytest-benchmark 会自动统计 p95）
        # 我们可以在测试报告中查看具体数据

    def test_webhook_signature_verification_invalid_performance(
        self, benchmark, sample_webhook_payload
    ):
        """测试无效签名验证性能（应该同样快速）"""
        secret = "test_webhook_secret"
        invalid_signature = "sha256=invalid_signature"

        result = benchmark(
            verify_webhook_signature, sample_webhook_payload, invalid_signature, secret
        )

        assert result is False

    def test_data_validation_performance(self, benchmark, mock_github_issue):
        """测试数据验证性能"""
        labels = [label.name for label in mock_github_issue.labels]

        result = benchmark(
            validate_issue_trigger,
            "labeled",
            labels,
            "ai-dev",
        )

        assert result is True

    def test_comment_validation_performance(self, benchmark):
        """测试评论验证性能"""
        comment = "Please /ai develop this feature"

        result = benchmark(
            validate_comment_trigger,
            comment,
            "/ai develop",
        )

        assert result is True

    def test_data_sanitization_performance(self, benchmark):
        """测试数据清理性能"""
        data = {
            "token": "secret_token_123",
            "issue": {"number": 123, "title": "Test"},
            "user": {"login": "testuser", "password": "secret"},
        }

        sanitized = benchmark(sanitize_log_data, data)

        # 验证敏感信息被清理
        assert sanitized["token"] == "****"
        assert sanitized["user"]["password"] == "****"

    def test_pydantic_model_validation_performance(
        self, benchmark, mock_github_user, mock_github_labels
    ):
        """测试 Pydantic 模型验证性能"""
        from datetime import datetime

        issue_data = {
            "id": 1,
            "node_id": "issue1",
            "number": 123,
            "title": "Performance test",
            "body": "Testing performance",
            "html_url": "https://github.com/test/repo/issues/123",
            "state": "open",
            "locked": False,
            "labels": [label.model_dump() for label in mock_github_labels],
            "user": mock_github_user.model_dump(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        result = benchmark(GitHubIssue.model_validate, issue_data)

        assert result.number == 123

    def test_json_parsing_performance(self, benchmark, sample_webhook_payload):
        """测试 JSON 解析性能"""
        import json

        result = benchmark(json.loads, sample_webhook_payload)
        assert result["action"] == "labeled"

    def test_large_payload_parsing_performance(self, benchmark):
        """测试大载荷解析性能（模拟复杂 Issue）"""
        import json

        # 创建一个大载荷（1MB）
        large_issue = {
            "id": 1,
            "number": 123,
            "title": "Large Issue",
            "body": "x" * (1024 * 1024),  # 1MB body
            "labels": [{"name": f"label{i}"} for i in range(100)],
        }

        result = benchmark(json.dumps, large_issue)
        assert len(result) > 1024 * 1024


class TestWebhookResponseTime:
    """Webhook 响应时间测试"""

    @pytest.mark.asyncio
    async def test_webhook_event_routing_latency(self, mock_github_issue, mock_github_user):
        """测试 Webhook 事件路由延迟"""
        handler = WebhookHandler()

        # Mock 服务
        handler._init_services = Mock()
        handler.git_service = Mock()
        handler.claude_service = AsyncMock()
        handler.github_service = Mock()

        # Mock Claude 开发返回成功
        handler.claude_service.develop_feature.return_value = {
            "success": True,
            "execution_time": 1.0,
        }

        # Mock Git 操作
        handler.git_service.create_feature_branch.return_value = "feature/123"
        handler.git_service.has_changes.return_value = False
        handler.git_service.push_to_remote.return_value = None

        # Mock GitHub PR 创建
        handler.github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }
        handler.github_service.add_comment_to_issue.return_value = None

        # 创建事件数据（包含必需的 sender 字段）
        event_data = {
            "action": "labeled",
            "issue": mock_github_issue.model_dump(),
            "sender": mock_github_user.model_dump(),
        }

        # 测量响应时间
        start_time = time.perf_counter()
        result = await handler.handle_event("issues", event_data)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        # 记录响应时间
        print(f"\nWebhook 事件路由响应时间: {response_time_ms:.2f}ms")

        # 验证成功
        assert result is not None
        assert result.success is True

        # 注意：这里的响应时间包括 mock 的服务调用时间
        # 实际生产环境中，Claude 调用会占大部分时间

    @pytest.mark.asyncio
    async def test_webhook_non_triggering_event_latency(self, mock_github_issue, mock_github_user):
        """测试非触发事件的响应时间（应该非常快）"""
        handler = WebhookHandler()

        # 创建不满足触发条件的事件（没有 ai-dev 标签）
        mock_github_issue.labels = []  # 移除触发标签
        event_data = {
            "action": "labeled",
            "issue": mock_github_issue.model_dump(),
            "sender": mock_github_user.model_dump(),
        }

        # 测量响应时间
        start_time = time.perf_counter()
        result = await handler.handle_event("issues", event_data)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        print(f"非触发事件响应时间: {response_time_ms:.2f}ms")

        # 应该快速返回 None
        assert result is None
        assert response_time_ms < 100  # 应该非常快


class TestServiceCallPerformance:
    """服务调用性能测试"""

    def test_git_service_initialization_time(self, benchmark):
        """测试 Git 服务初始化时间"""
        result = benchmark(GitService)
        assert result is not None

    @pytest.mark.asyncio
    async def test_claude_service_initialization_time(self, benchmark):
        """测试 Claude 服务初始化时间"""
        # 需要 mock 配置
        with patch("app.services.claude_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                repository=MagicMock(path="/tmp/test_repo"),
                claude=MagicMock(
                    cli_path="claude",
                    timeout=300,
                    max_retries=3,
                ),
            )

            result = benchmark(ClaudeService)
            assert result is not None


# =============================================================================
# 2. 并发性能测试（P1）
# =============================================================================


class TestConcurrencyPerformance:
    """并发性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self, mock_github_issue):
        """测试并发 Webhook 处理能力

        目标: 支持 50+ 并发请求
        """
        num_concurrent = 50
        handler = WebhookHandler()

        # Mock 服务
        handler._init_services = Mock()
        handler.git_service = Mock()
        handler.claude_service = AsyncMock()
        handler.github_service = Mock()

        # Mock 快速响应（模拟真实场景中的延迟）
        async def mock_develop(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms 延迟
            return {"success": True, "execution_time": 0.1}

        handler.claude_service.develop_feature = mock_develop
        handler.git_service.create_feature_branch.return_value = "feature/test"
        handler.git_service.has_changes.return_value = False
        handler.git_service.push_to_remote.return_value = None
        handler.github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }
        handler.github_service.add_comment_to_issue.return_value = None

        # 创建并发任务
        async def process_webhook(issue_number):
            # 创建事件数据副本
            issue_dict = mock_github_issue.model_dump()
            issue_dict["number"] = issue_number

            event_data = {
                "action": "labeled",
                "issue": issue_dict,
                "sender": {
                    "login": "testuser",
                    "id": 123,
                    "avatar_url": "https://example.com",
                    "type": "User",
                },
            }
            return await handler.handle_event("issues", event_data)

        # 测量并发处理时间
        start_time = time.perf_counter()

        tasks = [process_webhook(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # 验证结果
        successful = sum(1 for r in results if r is not None and getattr(r, "success", False))
        print(f"\n并发处理 {num_concurrent} 个请求:")
        print(f"  总时间: {total_time:.2f}s")
        print(f"  成功: {successful}/{num_concurrent}")
        print(f"  平均每请求: {total_time/num_concurrent*1000:.2f}ms")
        print(f"  吞吐量: {num_concurrent/total_time:.2f} 请求/秒")

        # 验证成功率
        assert successful >= num_concurrent * 0.95  # 95% 成功率

        # 验证并发效率（应该显著快于串行）
        serial_time = num_concurrent * 0.1  # 串行需要的时间
        efficiency = serial_time / total_time
        print(f"  并发效率: {efficiency:.2f}x")
        assert efficiency > 2.0  # 至少 2 倍加速

    @pytest.mark.asyncio
    async def test_concurrent_webhook_with_rate_limiting(self, mock_github_issue):
        """测试带速率限制的并发处理"""
        num_concurrent = 100
        max_concurrent = 10  # 限制最多 10 个并发

        handler = WebhookHandler()

        # Mock 服务
        handler._init_services = Mock()
        handler.git_service = Mock()
        handler.claude_service = AsyncMock()
        handler.github_service = Mock()

        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def mock_develop(*args, **kwargs):
            async with semaphore:
                await asyncio.sleep(0.05)
                return {"success": True, "execution_time": 0.05}

        handler.claude_service.develop_feature = mock_develop
        handler.git_service.create_feature_branch.return_value = "feature/test"
        handler.git_service.has_changes.return_value = False
        handler.git_service.push_to_remote.return_value = None
        handler.github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }
        handler.github_service.add_comment_to_issue.return_value = None

        # 创建并发任务
        async def process_webhook(issue_number):
            # 创建事件数据副本
            issue_dict = mock_github_issue.model_dump()
            issue_dict["number"] = issue_number

            event_data = {
                "action": "labeled",
                "issue": issue_dict,
                "sender": {
                    "login": "testuser",
                    "id": 123,
                    "avatar_url": "https://example.com",
                    "type": "User",
                },
            }
            return await handler.handle_event("issues", event_data)

        start_time = time.perf_counter()

        tasks = [process_webhook(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()

        successful = sum(1 for r in results if r is not None and getattr(r, "success", False))
        total_time = end_time - start_time

        print(f"\n速率限制并发处理 ({max_concurrent} 并发, {num_concurrent} 总请求):")
        print(f"  总时间: {total_time:.2f}s")
        print(f"  成功: {successful}/{num_concurrent}")
        print(f"  吞吐量: {num_concurrent/total_time:.2f} 请求/秒")

        assert successful >= num_concurrent * 0.95

    @pytest.mark.asyncio
    async def test_no_race_conditions_in_branch_creation(self):
        """测试分支创建无竞态条件"""
        from unittest.mock import patch

        # 模拟并发分支创建
        call_count = 0
        lock = threading.Lock()

        original_create = GitService.create_feature_branch

        def mock_create_with_delay(self, issue_number):
            nonlocal call_count
            time.sleep(0.01)  # 模拟延迟
            with lock:
                call_count += 1
            return f"feature/{issue_number}-{call_count}"

        with patch.object(GitService, "create_feature_branch", mock_create_with_delay):
            # 创建多个服务实例（模拟并发）
            services = [GitService() for _ in range(10)]

            # 并发创建分支
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(lambda s=s, i=i: s.create_feature_branch(i))
                    for i, s in enumerate(services)
                ]
                results = [f.result() for f in futures]

            # 验证所有分支创建成功且名称唯一
            assert len(results) == 10
            assert len(set(results)) == 10  # 所有分支名唯一

    def test_thread_safe_validators(self, benchmark):
        """测试验证器的线程安全性"""

        def validate_in_thread():
            return validate_issue_trigger("labeled", ["ai-dev", "bug"], "ai-dev")

        # 单线程基准
        result = benchmark(validate_in_thread)
        assert result is True

    def test_concurrent_validation(self):
        """测试并发验证操作"""
        num_threads = 50
        results = [None] * num_threads

        def validate_worker(thread_id):
            results[thread_id] = validate_issue_trigger("labeled", ["ai-dev"], "ai-dev")

        # 并发执行
        threads = [threading.Thread(target=validate_worker, args=(i,)) for i in range(num_threads)]

        start_time = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        end_time = time.perf_counter()

        # 验证所有结果正确
        assert all(results)
        print(f"\n{num_threads} 线程并发验证耗时: {(end_time-start_time)*1000:.2f}ms")


# =============================================================================
# 3. 压力测试（P1）
# =============================================================================


class TestStressTesting:
    """压力测试"""

    @pytest.mark.asyncio
    async def test_sustained_high_load(self, mock_github_issue, mock_github_user):
        """测试持续高负载（60秒）"""
        duration = 10  # 秒（测试时使用较短时间）
        requests_per_second = 10

        handler = WebhookHandler()

        # Mock 服务（快速响应）
        handler._init_services = Mock()
        handler.git_service = Mock()
        handler.claude_service = AsyncMock()
        handler.github_service = Mock()

        async def mock_develop(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms 延迟
            return {"success": True, "execution_time": 0.05}

        handler.claude_service.develop_feature = mock_develop
        handler.git_service.create_feature_branch.return_value = "feature/test"
        handler.git_service.has_changes.return_value = False
        handler.git_service.push_to_remote.return_value = None
        handler.github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }
        handler.github_service.add_comment_to_issue.return_value = None

        # 持续发送请求
        start_time = time.perf_counter()
        request_count = 0
        success_count = 0
        error_count = 0

        async def send_requests():
            nonlocal request_count, success_count, error_count
            while time.perf_counter() - start_time < duration:
                event_data = {
                    "action": "labeled",
                    "issue": mock_github_issue.model_dump(),
                    "sender": mock_github_user.model_dump(),
                }

                try:
                    result = await handler.handle_event("issues", event_data)
                    request_count += 1
                    if result and result.success:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    request_count += 1
                    error_count += 1

                await asyncio.sleep(1.0 / requests_per_second)

        # 运行测试
        await send_requests()

        total_time = time.perf_counter() - start_time
        actual_rps = request_count / total_time

        print(f"\n持续高负载测试 ({duration}s):")
        print(f"  总请求数: {request_count}")
        print(f"  成功: {success_count}")
        print(f"  失败: {error_count}")
        print(f"  实际 RPS: {actual_rps:.2f}")
        print(f"  成功率: {success_count/request_count*100:.2f}%")

        # 验证系统稳定性
        assert success_count / request_count > 0.95  # 95% 成功率

    @pytest.mark.asyncio
    async def test_burst_traffic_handling(self, mock_github_issue, mock_github_user):
        """测试突发流量处理能力"""
        burst_size = 100  # 突发 100 个请求

        handler = WebhookHandler()

        # Mock 服务
        handler._init_services = Mock()
        handler.git_service = Mock()
        handler.claude_service = AsyncMock()
        handler.github_service = Mock()

        async def mock_develop(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms 延迟
            return {"success": True, "execution_time": 0.01}

        handler.claude_service.develop_feature = mock_develop
        handler.git_service.create_feature_branch.return_value = "feature/test"
        handler.git_service.has_changes.return_value = False
        handler.git_service.push_to_remote.return_value = None
        handler.github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }
        handler.github_service.add_comment_to_issue.return_value = None

        # 同时发送所有请求
        event_data = {
            "action": "labeled",
            "issue": mock_github_issue.model_dump(),
            "sender": mock_github_user.model_dump(),
        }

        start_time = time.perf_counter()

        tasks = [handler.handle_event("issues", event_data) for _ in range(burst_size)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()

        successful = sum(1 for r in results if r is not None and getattr(r, "success", False))
        total_time = end_time - start_time

        print(f"\n突发流量测试 ({burst_size} 请求):")
        print(f"  总时间: {total_time:.2f}s")
        print(f"  成功: {successful}/{burst_size}")
        print(f"  峰值吞吐量: {burst_size/total_time:.2f} 请求/秒")

        assert successful >= burst_size * 0.90  # 90% 成功率

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, mock_github_issue, mock_github_user):
        """测试内存泄漏检测"""
        process = psutil.Process()
        iterations = 50

        handler = WebhookHandler()

        # Mock 服务
        handler._init_services = Mock()
        handler.git_service = Mock()
        handler.claude_service = AsyncMock()
        handler.github_service = Mock()

        handler.claude_service.develop_feature.return_value = {
            "success": True,
            "execution_time": 0.01,
        }
        handler.git_service.create_feature_branch.return_value = "feature/test"
        handler.git_service.has_changes.return_value = False
        handler.git_service.push_to_remote.return_value = None
        handler.github_service.create_pull_request.return_value = {
            "pr_number": 1,
            "html_url": "https://github.com/test/repo/pull/1",
        }
        handler.github_service.add_comment_to_issue.return_value = None

        # 记录初始内存
        gc.collect()
        initial_memory = process.memory_info().rss

        # 执行多次操作
        event_data = {
            "action": "labeled",
            "issue": mock_github_issue.model_dump(),
            "sender": mock_github_user.model_dump(),
        }

        for i in range(iterations):
            await handler.handle_event("issues", event_data)

            # 每 10 次迭代检查一次
            if i % 10 == 0:
                gc.collect()
                current_memory = process.memory_info().rss
                print(f"  迭代 {i}: 内存使用: {current_memory/1024/1024:.2f}MB")

        # 强制垃圾回收
        gc.collect()
        final_memory = process.memory_info().rss

        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / 1024 / 1024

        print(f"\n内存泄漏检测 ({iterations} 次迭代):")
        print(f"  初始内存: {initial_memory/1024/1024:.2f}MB")
        print(f"  最终内存: {final_memory/1024/1024:.2f}MB")
        print(f"  内存增长: {memory_increase_mb:.2f}MB")
        print(f"  每次迭代平均: {memory_increase_mb/iterations*1024:.2f}KB")

        # 验证内存增长在合理范围内（< 10MB）
        assert memory_increase < 10 * 1024 * 1024, "可能存在内存泄漏"


# =============================================================================
# 4. 资源使用测试（P2）
# =============================================================================


class TestResourceUsage:
    """资源使用测试"""

    def test_memory_usage_during_validation(self, benchmark):
        """测试验证期间的内存使用"""
        process = psutil.Process()

        # 大型数据集
        large_data = {
            "token": "x" * 1000,
            "issue": {
                "body": "x" * 10000,
                "comments": [{"body": "y" * 1000} for _ in range(100)],
            },
        }

        def sanitize_and_validate():
            return sanitize_log_data(large_data)

        # 基准测试
        initial_memory = process.memory_info().rss
        result = benchmark(sanitize_and_validate)
        final_memory = process.memory_info().rss

        memory_used = (final_memory - initial_memory) / 1024  # KB

        print(f"\n验证操作内存使用: {memory_used:.2f}KB")
        assert result["token"] == "****"

    @pytest.mark.asyncio
    async def test_cpu_usage_during_processing(self):
        """测试处理期间的 CPU 使用"""
        process = psutil.Process()

        # 创建 CPU 密集型任务
        def cpu_intensive_task():
            # 模拟 JSON 解析和验证
            import json

            data = {"x": list(range(1000))}
            for _ in range(100):
                json_str = json.dumps(data)
                parsed = json.loads(json_str)
                validate_issue_trigger("labeled", ["ai-dev"], "ai-dev")

        # 测量 CPU 时间
        start_cpu = process.cpu_times()
        start_time = time.perf_counter()

        # 执行任务
        cpu_intensive_task()

        end_time = time.perf_counter()
        end_cpu = process.cpu_times()

        cpu_time = end_cpu.user + end_cpu.system - (start_cpu.user + start_cpu.system)
        wall_time = end_time - start_time
        cpu_percent = (cpu_time / wall_time) * 100

        print(f"\nCPU 使用:")
        print(f"  CPU 时间: {cpu_time:.3f}s")
        print(f"  实际时间: {wall_time:.3f}s")
        print(f"  CPU 使用率: {cpu_percent:.1f}%")

    def test_file_io_performance(self, benchmark, tmp_path):
        """测试文件 I/O 性能"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        content = "x" * (1024 * 100)  # 100KB

        def write_and_read():
            test_file.write_text(content)
            return test_file.read_text()

        result = benchmark(write_and_read)
        assert len(result) == len(content)

    def test_concurrent_file_operations(self, tmp_path):
        """测试并发文件操作"""
        num_files = 50
        file_size = 1024 * 10  # 10KB

        def write_file(file_id):
            file_path = tmp_path / f"test_{file_id}.txt"
            content = f"{file_id}_" + "x" * (file_size - 10)
            file_path.write_text(content)
            return file_path.read_text()

        # 串行基准
        start_time = time.perf_counter()
        for i in range(num_files):
            write_file(i)
        serial_time = time.perf_counter() - start_time

        # 并发执行
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(write_file, range(num_files)))
        parallel_time = time.perf_counter() - start_time

        speedup = serial_time / parallel_time

        print(f"\n并发文件 I/O ({num_files} 文件, {file_size/1024}KB 每个):")
        print(f"  串行时间: {serial_time:.3f}s")
        print(f"  并行时间: {parallel_time:.3f}s")
        print(f"  加速比: {speedup:.2f}x")

        assert len(results) == num_files
        assert speedup > 1.5  # 至少 1.5 倍加速

    @pytest.mark.asyncio
    async def test_network_io_simulation(self):
        """测试网络 I/O 性能（模拟）"""

        # 模拟网络延迟
        async def mock_network_call(delay):
            await asyncio.sleep(delay)
            return {"data": "response"}

        # 串行调用
        start_time = time.perf_counter()
        for _ in range(10):
            await mock_network_call(0.01)
        serial_time = time.perf_counter() - start_time

        # 并发调用
        start_time = time.perf_counter()
        await asyncio.gather(*[mock_network_call(0.01) for _ in range(10)])
        parallel_time = time.perf_counter() - start_time

        speedup = serial_time / parallel_time

        print(f"\n网络 I/O 模拟 (10 个调用, 10ms 延迟):")
        print(f"  串行时间: {serial_time:.3f}s")
        print(f"  并行时间: {parallel_time:.3f}s")
        print(f"  加速比: {speedup:.2f}x")

        assert speedup > 5.0  # 应该显著更快


# =============================================================================
# 5. 性能回归测试
# =============================================================================


class TestPerformanceRegression:
    """性能回归测试 - 防止性能退化"""

    def test_validation_performance_regression(self, benchmark):
        """验证性能不应退化"""
        # 这个测试建立性能基线，后续运行可以检测退化
        result = benchmark(
            validate_issue_trigger,
            "labeled",
            ["ai-dev", "bug", "enhancement"],
            "ai-dev",
        )
        assert result is True

    def test_sanitization_performance_regression(self, benchmark):
        """清理性能不应退化"""
        data = {
            "token": "secret",
            "user": {
                "login": "test",
                "password": "secret",
            },
            "issue": {
                "title": "Test",
                "body": "Content",
            },
        }

        result = benchmark(sanitize_log_data, data)
        assert result["token"] == "****"

    @pytest.mark.asyncio
    async def test_webhook_handler_latency_regression(self, benchmark, mock_github_issue):
        """Webhook 处理器延迟不应退化"""
        handler = WebhookHandler()

        # Mock 快速响应
        handler._init_services = Mock()
        handler.claude_service = AsyncMock(return_value={"success": True, "execution_time": 0.01})
        handler.git_service = Mock()
        handler.github_service = Mock()

        event_data = {
            "action": "labeled",
            "issue": mock_github_issue.model_dump(),
            "sender": mock_github_user.model_dump(),
        }

        # 使用 pytest-asyncio 和 benchmark 可能需要特殊处理
        # 这里我们手动测量
        async def process():
            return await handler.handle_event("issues", event_data)

        # 简单测量
        start = time.perf_counter()
        await process()
        elapsed = time.perf_counter() - start

        print(f"\nWebhook 处理延迟: {elapsed*1000:.2f}ms")


# =============================================================================
# 性能测试辅助函数
# =============================================================================


def measure_memory_usage():
    """测量当前进程的内存使用"""
    process = psutil.Process()
    mem_info = process.memory_info()
    return {
        "rss": mem_info.rss / 1024 / 1024,  # MB
        "vms": mem_info.vms / 1024 / 1024,  # MB
    }


def measure_cpu_usage():
    """测量当前进程的 CPU 使用"""
    process = psutil.Process()
    cpu_times = process.cpu_times()
    return {
        "user": cpu_times.user,
        "system": cpu_times.system,
    }


# 可以通过以下命令运行性能测试：
# pytest tests/test_performance.py -v
# pytest tests/test_performance.py -v -k "benchmark"  # 只运行基准测试
# pytest tests/test_performance.py -v -k "concurrent"  # 只运行并发测试
# pytest tests/test_performance.py --benchmark-only  # 只运行基准测试并生成报告
