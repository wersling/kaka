"""
Process Manager
管理正在运行的 Claude CLI 进程，支持取消操作
"""

import asyncio
import signal
from typing import Dict, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessManager:
    """
    进程管理器

    管理正在运行的任务进程，支持取消操作
    """

    def __init__(self):
        """初始化进程管理器"""
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        logger.info("进程管理器初始化")

    def register_process(
        self,
        task_id: str,
        process: asyncio.subprocess.Process,
    ) -> None:
        """
        注册任务进程

        Args:
            task_id: 任务 ID
            process: 子进程对象
        """
        self._processes[task_id] = process
        logger.info(f"注册进程: task_id={task_id}, pid={process.pid}")

    def unregister_process(self, task_id: str) -> None:
        """
        注销任务进程

        Args:
            task_id: 任务 ID
        """
        if task_id in self._processes:
            process = self._processes.pop(task_id)
            logger.info(f"注销进程: task_id={task_id}, pid={process.pid}")

    async def terminate_process(self, task_id: str) -> bool:
        """
        终止任务进程

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功终止
        """
        process = self._processes.get(task_id)
        if not process:
            logger.warning(f"进程不存在: task_id={task_id}")
            return False

        try:
            # 检查进程是否还在运行
            if process.returncode is not None:
                logger.info(
                    f"进程已结束: task_id={task_id}, pid={process.pid}, "
                    f"returncode={process.returncode}"
                )
                self.unregister_process(task_id)
                return False

            # 尝试优雅终止（SIGTERM）
            logger.info(f"终止进程: task_id={task_id}, pid={process.pid}")
            process.terminate()

            # 等待进程结束（最多 5 秒）
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
                logger.info(f"进程已优雅终止: task_id={task_id}, pid={process.pid}")
                self.unregister_process(task_id)
                return True
            except asyncio.TimeoutError:
                # 如果优雅终止失败，强制杀死（SIGKILL）
                logger.warning(
                    f"进程未响应 SIGTERM，强制终止: task_id={task_id}, pid={process.pid}"
                )
                process.kill()
                await process.wait()
                logger.info(f"进程已强制终止: task_id={task_id}, pid={process.pid}")
                self.unregister_process(task_id)
                return True

        except ProcessLookupError:
            logger.warning(f"进程不存在（已结束）: task_id={task_id}")
            self.unregister_process(task_id)
            return False
        except Exception as e:
            logger.error(f"终止进程失败: task_id={task_id}, error={e}", exc_info=True)
            return False

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """
        获取任务进程

        Args:
            task_id: 任务 ID

        Returns:
            Optional[Process]: 进程对象，如果不存在则返回 None
        """
        return self._processes.get(task_id)

    def is_process_running(self, task_id: str) -> bool:
        """
        检查任务进程是否正在运行

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否正在运行
        """
        process = self._processes.get(task_id)
        if not process:
            return False

        # 如果进程已结束，清理注册
        if process.returncode is not None:
            self.unregister_process(task_id)
            return False

        return True

    def get_all_running_tasks(self) -> Dict[str, int]:
        """
        获取所有正在运行的任务

        Returns:
            Dict[str, int]: 任务 ID 到进程 ID 的映射
        """
        running_tasks = {}
        for task_id, process in list(self._processes.items()):
            if process.returncode is None:
                running_tasks[task_id] = process.pid
            else:
                # 清理已结束的进程
                self.unregister_process(task_id)

        return running_tasks

    def cleanup(self) -> None:
        """清理所有进程（用于服务关闭时）"""
        logger.info(f"清理所有进程，共 {len(self._processes)} 个")
        for task_id, process in list(self._processes.items()):
            try:
                if process.returncode is None:
                    logger.warning(f"强制终止进程: task_id={task_id}, pid={process.pid}")
                    process.kill()
            except Exception as e:
                logger.error(f"清理进程失败: task_id={task_id}, error={e}")

        self._processes.clear()


# 全局进程管理器实例
process_manager = ProcessManager()
