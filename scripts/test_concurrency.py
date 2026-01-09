#!/usr/bin/env python3
"""
测试并发控制功能

验证 ConcurrencyManager 的功能是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.concurrency import ConcurrencyManager, get_concurrency_stats
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_concurrency_manager():
    """测试并发管理器"""

    print("=" * 60)
    print("测试并发管理器")
    print("=" * 60)

    # 1. 测试初始化
    print("\n1️⃣  测试初始化...")
    ConcurrencyManager.initialize(max_concurrent=2)

    stats = ConcurrencyManager.get_stats()
    print(f"   初始化状态: {stats}")
    assert stats["max_concurrent"] == 2
    assert stats["current_running"] == 0
    assert stats["available"] == 2
    print("   ✅ 初始化成功")

    # 2. 测试获取许可
    print("\n2️⃣  测试获取许可...")

    async def task1():
        print("   🔄 任务1: 尝试获取许可...")
        await ConcurrencyManager.acquire()
        stats = ConcurrencyManager.get_stats()
        print(f"   📊 任务1: 当前状态 {stats}")
        assert stats["current_running"] == 1
        assert stats["available"] == 1
        print("   ✅ 任务1: 获取成功")
        await asyncio.sleep(0.5)
        ConcurrencyManager.release()
        print("   🔓 任务1: 释放许可")

    async def task2():
        print("   🔄 任务2: 尝试获取许可...")
        await ConcurrencyManager.acquire()
        stats = ConcurrencyManager.get_stats()
        print(f"   📊 任务2: 当前状态 {stats}")
        assert stats["current_running"] == 2
        assert stats["available"] == 0
        print("   ✅ 任务2: 获取成功")
        await asyncio.sleep(0.5)
        ConcurrencyManager.release()
        print("   🔓 任务2: 释放许可")

    # 并发执行两个任务
    await asyncio.gather(task1(), task2())

    stats = ConcurrencyManager.get_stats()
    print(f"   📊 最终状态: {stats}")
    assert stats["current_running"] == 0
    assert stats["available"] == 2
    print("   ✅ 许可获取/释放成功")

    # 3. 测试并发限制（超过限制的任务应该等待）
    print("\n3️⃣  测试并发限制...")

    task_durations = []

    async def limited_task(name: str, duration: float):
        """带并发限制的任务"""
        start = asyncio.get_event_loop().time()

        print(f"   🔄 {name}: 尝试获取许可...")
        async with ConcurrencyManager():
            elapsed = asyncio.get_event_loop().time() - start
            print(f"   ✅ {name}: 获取许可成功 (等待时间: {elapsed:.2f}s)")
            stats = ConcurrencyManager.get_stats()
            print(f"   📊 {name}: 当前状态 {stats}")

            await asyncio.sleep(duration)
            task_durations.append({
                "name": name,
                "wait_time": elapsed,
            })
            print(f"   🔓 {name}: 释放许可")

    # 启动 3 个任务，但 max_concurrent=2
    # 第 3 个任务应该等待前面的任务完成
    print("   启动 3 个任务（最大并发=2）...")

    start_time = asyncio.get_event_loop().time()
    await asyncio.gather(
        limited_task("任务1", 0.3),
        limited_task("任务2", 0.3),
        limited_task("任务3", 0.3),
    )
    total_time = asyncio.get_event_loop().time() - start_time

    print(f"\n   📊 任务执行统计:")
    for task_info in task_durations:
        print(f"      - {task_info['name']}: 等待时间 {task_info['wait_time']:.2f}s")

    print(f"   ⏱️  总执行时间: {total_time:.2f}s")

    # 验证：第 3 个任务应该等待了约 0.3s（因为前两个任务占用了许可）
    task3_wait = task_durations[2]["wait_time"]
    if task3_wait > 0.2:
        print(f"   ✅ 并发限制生效（任务3 等待了 {task3_wait:.2f}s）")
    else:
        print(f"   ⚠️  警告: 并发限制可能未生效（任务3 仅等待了 {task3_wait:.2f}s）")

    # 4. 测试上下文管理器
    print("\n4️⃣  测试上下文管理器...")

    async with ConcurrencyManager():
        stats = ConcurrencyManager.get_stats()
        print(f"   📊 上下文内: {stats}")
        assert stats["current_running"] == 1

    stats = ConcurrencyManager.get_stats()
    print(f"   📊 上下文外: {stats}")
    assert stats["current_running"] == 0
    print("   ✅ 上下文管理器正常")

    # 5. 测试便捷函数
    print("\n5️⃣  测试便捷函数...")
    from app.utils.concurrency import acquire_concurrency, release_concurrency

    await acquire_concurrency()
    stats = get_concurrency_stats()
    print(f"   📊 acquire 后: {stats}")
    assert stats["current_running"] == 1

    release_concurrency()
    stats = get_concurrency_stats()
    print(f"   📊 release 后: {stats}")
    assert stats["current_running"] == 0
    print("   ✅ 便捷函数正常")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


async def test_concurrent_webhook_simulation():
    """模拟多个并发 webhook 请求"""

    print("\n" + "=" * 60)
    print("模拟多个并发 Webhook 请求")
    print("=" * 60)

    # 初始化并发管理器（max_concurrent=1）
    ConcurrencyManager.initialize(max_concurrent=1)
    print(f"   设置最大并发: 1\n")

    execution_order = []

    async def simulate_webhook(issue_number: int):
        """模拟 webhook 处理"""
        execution_order.append(f"开始 Issue #{issue_number}")

        print(f"   🔄 Issue #{issue_number}: 尝试获取并发锁...")
        async with ConcurrencyManager():
            print(f"   ✅ Issue #{issue_number}: 获取锁成功")
            stats = ConcurrencyManager.get_stats()
            print(f"   📊 Issue #{issue_number}: {stats}")

            # 模拟任务执行
            await asyncio.sleep(0.5)

            print(f"   🔓 Issue #{issue_number}: 释放锁")
            execution_order.append(f"完成 Issue #{issue_number}")

    # 同时触发 3 个 webhook
    print("   同时触发 3 个 Webhook...\n")
    start_time = asyncio.get_event_loop().time()

    await asyncio.gather(
        simulate_webhook(10),
        simulate_webhook(11),
        simulate_webhook(12),
    )

    total_time = asyncio.get_event_loop().time() - start_time

    print(f"\n   执行顺序:")
    for i, event in enumerate(execution_order, 1):
        print(f"      {i}. {event}")

    print(f"\n   ⏱️  总执行时间: {total_time:.2f}s")

    # 验证：由于 max_concurrent=1，总时间应该约为 1.5s（3个任务串行执行）
    if total_time >= 1.4:
        print("   ✅ 并发控制正常（任务串行执行）")
    else:
        print(f"   ⚠️  警告: 执行时间过短，可能存在并发问题")

    print("=" * 60)


if __name__ == "__main__":
    print("\n🧪 并发控制测试\n")

    # 运行测试（在同一个事件循环中）
    asyncio.run(test_concurrency_manager())

    # 重新初始化并发管理器用于第二个测试
    # 注意：必须在新的事件循环中重新创建信号量
    print("\n" + "=" * 60)
    print("重置并发管理器用于第二次测试...")
    print("=" * 60)

    # 清理旧的信号量
    ConcurrencyManager._semaphore = None
    ConcurrencyManager._instance = None
    ConcurrencyManager._current_running = 0

    asyncio.run(test_concurrent_webhook_simulation())

    print("\n✅ 测试完成！\n")
