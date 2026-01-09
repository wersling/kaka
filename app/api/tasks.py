"""
Task Monitoring API
任务监控 REST API 端点
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Task, TaskStatus
from app.services.task_service import TaskService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    """
    获取 TaskService 实例（依赖注入）

    Args:
        db: 数据库会话（通过依赖注入自动获取）

    Returns:
        TaskService: 任务服务实例
    """
    return TaskService(db)


@router.get("/tasks", summary="获取任务列表")
async def get_tasks(
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    task_service: TaskService = Depends(get_task_service),
) -> dict:
    """
    获取任务列表（支持分页和筛选）

    参数:
        - status: 状态筛选 (pending/running/completed/failed/cancelled)
        - limit: 返回数量限制 (1-1000)
        - offset: 偏移量

    返回:
        - tasks: 任务列表
        - total: 总数
        - stats: 统计信息
    """
    try:

        # 解析状态
        task_status = None
        if status:
            try:
                task_status = TaskStatus(status.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态: {status}")

        # 获取任务
        tasks = task_service.get_all_tasks(status=task_status, limit=limit, offset=offset)

        # 获取统计信息
        stats = task_service.get_task_stats()

        return {
            "tasks": [task.to_dict() for task in tasks],
            "total": len(tasks),
            "stats": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/stats", summary="获取任务统计")
async def get_task_stats(
    task_service: TaskService = Depends(get_task_service),
) -> dict:
    """
    获取任务统计信息

    返回:
        - total: 总任务数
        - pending: 待处理
        - running: 运行中
        - completed: 已完成
        - failed: 失败
        - cancelled: 已取消
    """
    try:
        stats = task_service.get_task_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", summary="获取任务详情")
async def get_task_detail(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
) -> dict:
    """
    获取任务详情

    参数:
        - task_id: 任务 ID

    返回:
        - task: 任务详情
        - logs: 任务日志
    """
    try:
        task = task_service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        # 获取日志
        logs = task_service.get_task_logs(task_id)

        return {
            "task": task.to_dict(),
            "logs": [log.to_dict() for log in logs],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/issue/{issue_number}", summary="根据 Issue 获取任务")
async def get_tasks_by_issue(
    issue_number: int,
    task_service: TaskService = Depends(get_task_service),
) -> dict:
    """
    根据 Issue 编号获取所有相关任务

    参数:
        - issue_number: Issue 编号

    返回:
        - tasks: 任务列表
    """
    try:
        tasks = task_service.get_tasks_by_issue(issue_number)

        return {
            "issue_number": issue_number,
            "tasks": [task.to_dict() for task in tasks],
            "total": len(tasks),
        }

    except Exception as e:
        logger.error(f"获取 Issue 任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/cancel", summary="取消任务")
async def cancel_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
) -> dict:
    """
    取消正在执行的任务

    参数:
        - task_id: 任务 ID

    返回:
        - success: 是否成功
        - task: 更新后的任务
        - process_terminated: 进程是否被终止
    """
    import asyncio
    from app.services.process_manager import process_manager

    try:
        task = task_service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任务不存在: {task_id}"
            )

        # 只能取消 pending 或 running 状态的任务
        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise HTTPException(
                status_code=400,
                detail=f"任务无法取消: {task_id} (当前状态: {task.status.value})"
            )

        process_terminated = False

        # 如果任务正在运行，尝试终止进程
        if task.status == TaskStatus.RUNNING:
            logger.info(f"尝试终止任务进程: {task_id}")

            try:
                # 尝试终止进程
                process_terminated = await process_manager.terminate_process(task_id)

                if process_terminated:
                    logger.info(f"✅ 进程已终止: {task_id}")
                else:
                    logger.warning(f"⚠️  进程未找到或已结束: {task_id}")

            except Exception as e:
                logger.error(f"终止进程异常: {e}", exc_info=True)

        # 更新任务状态
        task = task_service.update_task_status(task_id, TaskStatus.CANCELLED)

        return {
            "success": True,
            "message": "任务已取消" + ("，进程已终止" if process_terminated else ""),
            "task": task.to_dict(),
            "process_terminated": process_terminated,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/retry", summary="重试失败任务")
async def retry_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
) -> dict:
    """
    重试失败的任务

    参数:
        - task_id: 任务 ID

    返回:
        - success: 是否成功
        - task: 重试后的任务
        - message: 提示信息
    """
    import asyncio

    try:
        task = task_service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任务不存在: {task_id}"
            )

        # 只能重试失败或取消的任务
        if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=400,
                detail=f"任务无法重试: {task_id} (当前状态: {task.status.value})"
            )

        # 检查重试次数
        if task.retry_count >= task.max_retries:
            raise HTTPException(
                status_code=400,
                detail=f"任务已达到最大重试次数: {task_id} (已重试 {task.retry_count} 次)"
            )

        # 重置任务状态为 pending
        task = task_service.retry_task(task_id)

        if not task:
            raise HTTPException(
                status_code=400,
                detail=f"重试失败: {task_id}"
            )

        # 触发任务重新执行（后台异步执行）
        async def retry_execution():
            """后台执行重试任务"""
            from app.services.webhook_handler import WebhookHandler

            try:
                logger.info(f"🔄 [重试] 开始初始化 WebhookHandler: {task_id}")
                handler = WebhookHandler()
                handler._init_services()  # 确保服务已初始化
                logger.info(f"🔄 [重试] WebhookHandler 已初始化: {task_id}")

                logger.info(f"🔄 [重试] 调用 _trigger_ai_development: {task_id}")
                await handler._trigger_ai_development(
                    issue_number=task.issue_number,
                    issue_title=task.issue_title,
                    issue_url=task.issue_url,
                    issue_body=task.issue_body,
                    existing_branch=task.branch_name,
                    task_id=task_id,  # 使用同一个 task_id
                )
                logger.info(f"✅ [重试] 任务执行完成: {task_id}")
            except Exception as e:
                logger.error(f"❌ [重试] 任务执行失败: {task_id}, error={e}", exc_info=True)

        # 获取当前事件循环并创建任务
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.info(f"📋 [重试] 事件循环正在运行，创建后台任务: {task_id}")
                background_task = loop.create_task(retry_execution())
                logger.info(f"✅ [重试] 后台任务已创建: {task_id}, task={background_task}, done={background_task.done()}")
            else:
                logger.error(f"❌ [重试] 事件循环未运行: {task_id}")
                raise HTTPException(
                    status_code=500,
                    detail=f"内部错误: 事件循环未运行"
                )
        except Exception as e:
            logger.error(f"❌ [重试] 创建后台任务失败: {task_id}, error={e}", exc_info=True)
            raise

        return {
            "success": True,
            "message": f"任务已重新加入队列 (第 {task.retry_count} 次重试)，正在后台执行...",
            "task": task.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重试任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
