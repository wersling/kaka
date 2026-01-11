"""
并发控制管理器

管理任务并发执行的全局信号量
"""

import asyncio
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConcurrencyManager:
    """
    并发管理器

    使用信号量（Semaphore）控制并发任务数量
    """

    _instance: Optional["ConcurrencyManager"] = None
    _semaphore: Optional[asyncio.Semaphore] = None
    _max_concurrent: int = 1
    _current_running: int = 0
    _lock: asyncio.Lock = asyncio.Lock()  # 保护计数器的锁（异步锁）

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, max_concurrent: int = 1) -> None:
        """
        初始化并发管理器

        Args:
            max_concurrent: 最大并发数
        """
        if cls._semaphore is None:
            cls._max_concurrent = max_concurrent
            cls._semaphore = asyncio.Semaphore(max_concurrent)
            logger.info(f"✅ 并发管理器初始化完成 (最大并发: {max_concurrent})")
        else:
            logger.warning("并发管理器已经初始化，跳过")

    @classmethod
    def get_semaphore(cls) -> asyncio.Semaphore:
        """
        获取信号量实例

        Returns:
            asyncio.Semaphore: 信号量实例

        Raises:
            RuntimeError: 如果未初始化
        """
        if cls._semaphore is None:
            raise RuntimeError("并发管理器未初始化，请先调用 initialize()")
        return cls._semaphore

    @classmethod
    async def acquire(cls) -> None:
        """
        获取并发许可（阻塞直到有可用资源）

        会自动增加当前运行计数
        """
        await cls._semaphore.acquire()
        async with cls._lock:  # 异步锁保护计数器
            cls._current_running += 1
        logger.debug(f"🔓 获取并发许可 (当前运行: {cls._current_running}/{cls._max_concurrent})")

    @classmethod
    async def release(cls) -> None:
        """
        释放并发许可

        会自动减少当前运行计数
        """
        async with cls._lock:  # 异步锁保护计数器
            # 确保计数器不会变成负数（防御性编程）
            if cls._current_running > 0:
                cls._current_running -= 1
            else:
                logger.warning(f"⚠️ 尝试释放许可但计数器已经是0，可能是过度释放")
        cls._semaphore.release()
        logger.debug(f"🔒 释放并发许可 (当前运行: {cls._current_running}/{cls._max_concurrent})")

    @classmethod
    def get_stats(cls) -> dict:
        """
        获取并发统计信息

        Returns:
            dict: 包含 max_concurrent 和 current_running
        """
        return {
            "max_concurrent": cls._max_concurrent,
            "current_running": cls._current_running,
            "available": cls._max_concurrent - cls._current_running,
        }

    async def __aenter__(self):
        """异步上下文管理器入口（实例方法）"""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口（实例方法）"""
        await self.release()


# 便捷函数
async def acquire_concurrency() -> None:
    """获取并发许可"""
    await ConcurrencyManager.acquire()


async def release_concurrency() -> None:
    """释放并发许可"""
    await ConcurrencyManager.release()


def get_concurrency_stats() -> dict:
    """获取并发统计"""
    return ConcurrencyManager.get_stats()
