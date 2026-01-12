"""
Real-time Logs API - Server-Sent Events 实时日志流
"""

import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Task, TaskLog, TaskStatus
from app.services.task_service import TaskService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/tasks/{task_id}/logs/stream")
async def stream_task_logs(
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events 实时日志流

    返回任务的实时日志流，使用 SSE 协议推送

    Args:
        task_id: 任务 ID

    Returns:
        StreamingResponse: SSE 流式响应
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件"""
        task_service = TaskService(db)
        last_log_id = 0

        try:
            while True:
                # 查询新日志
                new_logs = (
                    db.query(TaskLog)
                    .filter(TaskLog.task_id == task_id, TaskLog.id > last_log_id)
                    .order_by(TaskLog.id)
                    .all()
                )

                for log in new_logs:
                    # 发送 SSE 事件
                    event_data = json.dumps(log.to_dict(), ensure_ascii=False)
                    yield f"data: {event_data}\n\n"
                    last_log_id = log.id

                # 检查任务是否完成
                task = task_service.get_task_by_id(task_id)
                if not task:
                    # 任务不存在
                    yield 'event: error\ndata: {"message": "任务不存在"}\n\n'
                    break

                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    # 任务已完成
                    logger.info(f"任务 {task_id} 已完成，关闭日志流")
                    yield 'event: done\ndata: {"message": "任务已完成"}\n\n'
                    break

                # 等待 1 秒后再次查询
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"日志流异常: {e}", exc_info=True)
            yield f'event: error\ndata: {{"message": "日志流异常: {str(e)}"}}\n\n'
        finally:
            task_service.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )
