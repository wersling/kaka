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


@router.get("/", response_class=HTMLResponse, summary="首页")
async def index(request: Request):
    """首页 - 重定向到增强版 Dashboard"""
    logger.debug("访问首页")
    return templates.TemplateResponse("dashboard_enhanced.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse, summary="任务监控页面（增强版）")
async def dashboard(request: Request):
    """
    任务监控 Dashboard（增强版）

    返回 HTML 页面，展示任务列表和统计信息
    """
    logger.debug("访问增强版 Dashboard")
    return templates.TemplateResponse("dashboard_enhanced.html", {"request": request})


@router.get("/dashboard-legacy", response_class=HTMLResponse, summary="任务监控页面（原版）")
async def dashboard_legacy(request: Request):
    """原版 Dashboard（保留用于向后兼容）"""
    logger.debug("访问原版 Dashboard")
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/config", response_class=HTMLResponse, summary="配置向导")
async def config_wizard(request: Request):
    """
    配置向导页面

    首次使用时的配置向导
    """
    logger.debug("访问配置向导")
    return templates.TemplateResponse("config_wizard.html", {"request": request})


@router.get("/tasks/{task_id}", response_class=HTMLResponse, summary="任务详情页面")
async def task_detail(request: Request, task_id: str):
    """
    任务详情页面

    返回 HTML 页面，展示任务详细信息和实时日志
    """
    logger.debug(f"访问任务详情: {task_id}")
    return templates.TemplateResponse("task_detail.html", {"request": request})
