"""
Dashboard API - Web UI 服务
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse, summary="任务监控页面")
async def dashboard(request: Request):
    """
    任务监控 Dashboard

    返回 HTML 页面，展示任务列表和统计信息
    """
    logger.debug("访问 Dashboard")
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/tasks/{task_id}", response_class=HTMLResponse, summary="任务详情页面")
async def task_detail(request: Request, task_id: str):
    """
    任务详情页面

    返回 HTML 页面，展示任务详细信息和实时日志
    """
    logger.debug(f"访问任务详情: {task_id}")
    return templates.TemplateResponse("task_detail.html", {"request": request})
