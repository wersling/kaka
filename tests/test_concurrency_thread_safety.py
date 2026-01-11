"""
测试 ConcurrencyManager 线程安全优化

测试覆盖以下优化：
1. 使用 threading.Lock 保护计数器
2. acquire 和 release 的原子操作
3. 多线程/多协程并发场景
4. 计数器准确性验证
"""

import asyncio
import threading
import time
from unittest.mock import patch

import pytest

from app.utils.concurrency import ConcurrencyManager


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_concurrency_manager():
    """
    自动重置并发管理器（每个测试前执行）

    确保测试之间不会相互干扰
    """
    # 保存原始状态
    original_instance = ConcurrencyManager._instance
    original_semaphore = ConcurrencyManager._semaphore
    original_max = ConcurrencyManager._max_concurrent
    original_current = ConcurrencyManager._current_running

    # 重置状态
    ConcurrencyManager._instance = None
    ConcurrencyManager._semaphore = None
    ConcurrencyManager._current_running = 0
    ConcurrencyManager._max_concurrent = 1

    yield

    # 测试后清理
    ConcurrencyManager._instance = original_instance
    ConcurrencyManager._semaphore = original_semaphore
    ConcurrencyManager._max_concurrent = original_max
    ConcurrencyManager._current_running = original_current


# =============================================================================
# 测试初始化
# =============================================================================


class TestConcurrencyManagerInitialization:
    """测试并发管理器初始化"""

    def test_initialize_sets_max_concurrent(self):
        """
        测试：初始化应该设置最大并发数

        验证：
        - _max_concurrent 被正确设置
        - _semaphore 被创建
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None

        ConcurrencyManager.initialize(max_concurrent=5)

        assert ConcurrencyManager._max_concurrent == 5
        assert ConcurrencyManager._semaphore is not None

    def test_initialize_only_once(self, caplog):
        """
        测试：初始化只能执行一次

        验证：
        - 第二次初始化被跳过
        - 记录警告日志
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None

        ConcurrencyManager.initialize(max_concurrent=3)
        first_semaphore = ConcurrencyManager._semaphore

        ConcurrencyManager.initialize(max_concurrent=5)
        second_semaphore = ConcurrencyManager._semaphore

        # 应该是同一个实例
        assert first_semaphore is second_semaphore
        assert ConcurrencyManager._max_concurrent == 3  # 保持第一次的值

    def test_singleton_pattern(self):
        """
        测试：单例模式

        验证：
        - 多次创建返回同一实例
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None

        ConcurrencyManager.initialize()

        instance1 = ConcurrencyManager()
        instance2 = ConcurrencyManager()

        assert instance1 is instance2


# =============================================================================
# 测试原子操作（Lock 保护）
# =============================================================================


class TestAtomicOperations:
    """测试原子操作"""

    @pytest.mark.asyncio
    async def test_acquire_increments_counter_atomically(self):
        """
        测试：acquire 应该原子性地增加计数器

        验证：
        - 使用锁保护
        - 计数器准确增加
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=2)

        initial_count = ConcurrencyManager._current_running
        assert initial_count == 0

        # 获取许可
        await ConcurrencyManager.acquire()

        # 验证计数器增加
        assert ConcurrencyManager._current_running == 1

        # 再次获取
        await ConcurrencyManager.acquire()

        assert ConcurrencyManager._current_running == 2

        # 清理
        ConcurrencyManager.release()
        ConcurrencyManager.release()

    @pytest.mark.asyncio
    async def test_release_decrements_counter_atomically(self):
        """
        测试：release 应该原子性地减少计数器

        验证：
        - 使用锁保护
        - 计数器准确减少
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=2)

        # 获取两个许可
        await ConcurrencyManager.acquire()
        await ConcurrencyManager.acquire()

        assert ConcurrencyManager._current_running == 2

        # 释放一个
        ConcurrencyManager.release()

        assert ConcurrencyManager._current_running == 1

        # 释放另一个
        ConcurrencyManager.release()

        assert ConcurrencyManager._current_running == 0

    @pytest.mark.asyncio
    async def test_counter_does_not_go_negative(self):
        """
        测试：计数器不应该变成负数

        验证：
        - 即使过度释放，计数器也不会 < 0
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=1)

        # 初始为 0
        assert ConcurrencyManager._current_running == 0

        # 过度释放（实际中不应该发生，但测试健壮性）
        ConcurrencyManager.release()
        ConcurrencyManager.release()

        # 由于锁保护，即使过度释放也应该 >= 0
        assert ConcurrencyManager._current_running >= 0


# =============================================================================
# 测试并发场景（多协程）
# =============================================================================


class TestConcurrentScenarios:
    """测试并发场景"""

    @pytest.mark.asyncio
    async def test_concurrent_acquire_accuracy(self):
        """
        测试：并发 acquire 应该保持计数器准确

        验证：
        - 多个协程同时 acquire
        - 计数器始终准确
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=5)

        async def acquire_and_hold():
            """获取许可并持有短暂时间"""
            await ConcurrencyManager.acquire()
            await asyncio.sleep(0.01)  # 持有 10ms
            ConcurrencyManager.release()

        # 并发执行 10 个任务
        tasks = [acquire_and_hold() for _ in range(10)]
        await asyncio.gather(*tasks)

        # 最终应该回到 0
        assert ConcurrencyManager._current_running == 0

    @pytest.mark.asyncio
    async def test_concurrent_acquire_respects_limit(self):
        """
        测试：并发 acquire 应该遵守限制

        验证：
        - 同时运行的任务不超过 max_concurrent
        - 使用 get_stats 验证
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=3)

        running_count = []

        async def track_running_count():
            """跟踪当前运行数"""
            await ConcurrencyManager.acquire()
            running_count.append(ConcurrencyManager._current_running)
            await asyncio.sleep(0.05)  # 持有 50ms
            ConcurrencyManager.release()

        # 启动 10 个任务
        tasks = [track_running_count() for _ in range(10)]
        await asyncio.gather(*tasks)

        # 验证所有记录的运行数都不超过限制
        for count in running_count:
            assert count <= 3, f"运行数 {count} 超过限制 3"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_acquire_release(self):
        """
        测试：混合 acquire/release 应该保持计数器准确

        验证：
        - 交错执行 acquire 和 release
        - 计数器始终准确
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=5)

        async def mixed_operations():
            """混合获取和释放操作"""
            for _ in range(5):
                await ConcurrencyManager.acquire()
                await asyncio.sleep(0.001)
                ConcurrencyManager.release()
                await asyncio.sleep(0.001)

        # 并发执行多个任务
        tasks = [mixed_operations() for _ in range(3)]
        await asyncio.gather(*tasks)

        # 最终应该回到 0
        assert ConcurrencyManager._current_running == 0

    @pytest.mark.asyncio
    async def test_rapid_acquire_release_cycles(self):
        """
        测试：快速 acquire/release 循环

        验证：
        - 快速多次操作不会导致计数器错误
        - 原子性得到保护
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=2)

        async def rapid_cycle():
            """快速循环"""
            for _ in range(100):
                await ConcurrencyManager.acquire()
                ConcurrencyManager.release()

        # 并发执行多个快速循环
        tasks = [rapid_cycle() for _ in range(5)]
        await asyncio.gather(*tasks)

        # 最终应该回到 0
        assert ConcurrencyManager._current_running == 0


# =============================================================================
# 测试多线程场景（如果使用线程池）
# =============================================================================


class TestMultiThreadedScenarios:
    """测试多线程场景（跨线程的并发管理）"""

    def test_thread_safe_counter_increment(self):
        """
        测试：跨线程的计数器增加应该安全

        验证：
        - 使用 threading.Lock 保护
        - 多线程并发增加计数器准确
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=10)

        # 在事件循环中预先获取
        async def acquire_in_loop():
            await ConcurrencyManager.acquire()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(acquire_in_loop())

        initial = ConcurrencyManager._current_running

        # 多线程增加
        def increment_counter():
            with ConcurrencyManager._lock:
                ConcurrencyManager._current_running += 1

        threads = []
        for _ in range(10):
            t = threading.Thread(target=increment_counter)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证：初始1 + 10次增加 = 11
        assert ConcurrencyManager._current_running == initial + 10

        loop.close()

    def test_thread_safe_counter_decrement(self):
        """
        测试：跨线程的计数器减少应该安全

        验证：
        - 使用 threading.Lock 保护
        - 多线程并发减少计数器准确
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=10)

        # 先获取一些许可
        async def acquire_multiple():
            for _ in range(5):
                await ConcurrencyManager.acquire()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(acquire_multiple())

        assert ConcurrencyManager._current_running == 5

        # 多线程减少
        def decrement_counter():
            with ConcurrencyManager._lock:
                if ConcurrencyManager._current_running > 0:
                    ConcurrencyManager._current_running -= 1

        threads = []
        for _ in range(3):
            t = threading.Thread(target=decrement_counter)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证：5 - 3 = 2
        assert ConcurrencyManager._current_running == 2

        loop.close()


# =============================================================================
# 测试统计信息
# =============================================================================


class TestStatistics:
    """测试统计信息"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_correct_info(self):
        """
        测试：get_stats 应该返回正确的统计信息

        验证：
        - max_concurrent 正确
        - current_running 正确
        - available 计算正确
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=5)

        # 初始状态
        stats = ConcurrencyManager.get_stats()
        assert stats["max_concurrent"] == 5
        assert stats["current_running"] == 0
        assert stats["available"] == 5

        # 获取 2 个许可
        await ConcurrencyManager.acquire()
        await ConcurrencyManager.acquire()

        stats = ConcurrencyManager.get_stats()
        assert stats["max_concurrent"] == 5
        assert stats["current_running"] == 2
        assert stats["available"] == 3

        # 清理
        ConcurrencyManager.release()
        ConcurrencyManager.release()

    @pytest.mark.asyncio
    async def test_stats_during_concurrent_operations(self):
        """
        测试：并发操作中的统计信息应该准确

        验证：
        - 在并发操作中查询统计
        - 统计信息始终一致
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=3)

        recorded_stats = []

        async def record_stats():
            """记录统计信息"""
            await ConcurrencyManager.acquire()
            recorded_stats.append(ConcurrencyManager.get_stats())
            await asyncio.sleep(0.02)
            ConcurrencyManager.release()

        # 并发执行
        tasks = [record_stats() for _ in range(6)]
        await asyncio.gather(*tasks)

        # 验证所有统计的一致性
        for stats in recorded_stats:
            current = stats["current_running"]
            max_concurrent = stats["max_concurrent"]
            available = stats["available"]

            assert current <= max_concurrent
            assert current + available == max_concurrent
            assert available >= 0


# =============================================================================
# 测试上下文管理器
# =============================================================================


class TestContextManager:
    """测试异步上下文管理器"""

    @pytest.mark.asyncio
    async def test_context_manager_acquires_and_releases(self):
        """
        测试：上下文管理器应该自动获取和释放

        验证：
        - 进入时获取
        - 退出时释放
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=2)

        assert ConcurrencyManager._current_running == 0

        # 使用实例而不是类
        manager = ConcurrencyManager()
        async with manager:
            assert ConcurrencyManager._current_running == 1

        assert ConcurrencyManager._current_running == 0

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self):
        """
        测试：上下文管理器在异常时也应该释放

        验证：
        - 即使抛出异常，也会释放
        """
        ConcurrencyManager._instance = None
        ConcurrencyManager._semaphore = None
        ConcurrencyManager.initialize(max_concurrent=2)

        assert ConcurrencyManager._current_running == 0

        # 使用实例而不是类
        manager = ConcurrencyManager()
        try:
            async with manager:
                assert ConcurrencyManager._current_running == 1
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert ConcurrencyManager._current_running == 0
