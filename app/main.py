"""
AI 开发调度服务 - FastAPI 应用入口

接收 GitHub Webhook 事件，触发 Claude Code CLI 进行自动化开发
"""

import time
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.config import init_config, Config
from app.utils.logger import get_logger, setup_from_config

# 初始化日志
logger = get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """请求计时中间件"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Request]],
    ) -> Request:
        """处理请求并记录执行时间"""
        start_time = time.time()

        # 记录请求
        logger.info(f"➤ {request.method} {request.url.path}")

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # 记录响应
        logger.info(
            f"✓ {request.method} {request.url.path} "
            f"- {response.status_code} - {process_time:.3f}s"
        )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时初始化配置和日志
    关闭时清理资源
    """
    # 启动时执行
    logger.info("=" * 60)
    logger.info("🚀 AI 开发调度服务启动中...")
    logger.info("=" * 60)

    try:
        # 初始化配置
        config = init_config()
        logger.info("✅ 配置加载成功")

        # 设置日志
        logger_instance = setup_from_config(config)
        logger.info(f"✅ 日志系统初始化完成 (级别: {config.logging.level})")

        # 记录配置信息
        logger.info(f"📋 仓库: {config.github.repo_full_name}")
        logger.info(f"📂 本地路径: {config.repository.path}")
        logger.info(f"🏷️  触发标签: {config.github.trigger_label}")
        logger.info(f"💬 触发命令: {config.github.trigger_command}")

        logger.info("=" * 60)
        logger.info("✅ 服务启动完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}", exc_info=True)
        raise

    yield

    # 关闭时执行
    logger.info("🛑 服务关闭中...")
    logger.info("✅ 服务已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI 开发调度服务",
    description="通过 GitHub Webhook 触发 Claude Code CLI 自动化开发",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# 添加 CORS 中间件（安全配置，从配置文件读取允许的来源）
def get_cors_origins() -> list[str]:
    """获取 CORS 允许的来源列表"""
    try:
        from app.config import get_config
        config = get_config()
        return config.security.cors_origins
    except Exception:
        # 如果配置未加载，使用默认的本地开发地址
        return ["http://localhost:3000", "http://localhost:8000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),  # 从配置读取，生产环境必须限制
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# 添加请求计时中间件
app.add_middleware(TimingMiddleware)


# 注册路由
app.include_router(health_router, tags=["Health"])


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTP 异常"""
    logger.error(
        f"HTTP 异常: {request.method} {request.url.path} - "
        f"{exc.status_code}: {exc.detail}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """处理请求验证异常"""
    logger.error(
        f"验证错误: {request.method} {request.url.path} - {exc.errors()}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "请求验证失败",
            "details": exc.errors(),
            "status_code": 422,
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常"""
    logger.error(
        f"未处理的异常: {request.method} {request.url.path}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "内部服务器错误",
            "status_code": 500,
            "path": request.url.path,
        },
    )


# 根路径
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    根路径

    返回服务基本信息
    """
    return {
        "service": "AI 开发调度服务",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


# Webhook 端点
@app.post("/webhook/github", tags=["Webhook"])
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = None,
    x_github_event: str | None = None,
    x_github_delivery: str | None = None,
) -> dict[str, any]:
    """
    GitHub Webhook 接收端点

    接收 GitHub 事件并触发 AI 开发流程
    """
    try:
        # 获取原始 payload
        payload = await request.body()

        # 验证签名
        from app.utils.validators import verify_webhook_signature
        from app.config import get_config

        config = get_config()

        if not verify_webhook_signature(
            payload,
            x_hub_signature_256,
            config.github.webhook_secret,
        ):
            logger.warning("Webhook 签名验证失败")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

        # 解析事件数据
        event_data = await request.json()

        # 获取事件类型
        event_type = x_github_event or event_data.get("action", "unknown")

        logger.info(
            f"收到 Webhook: delivery={x_github_delivery}, "
            f"event={event_type}"
        )

        # 处理事件（异步，不阻塞响应）
        from app.services.webhook_handler import WebhookHandler

        handler = WebhookHandler()

        # 在后台执行处理，立即返回响应
        import asyncio

        async def process_event():
            try:
                result = await handler.handle_event(event_type, event_data)
                if result:
                    logger.info(
                        f"事件处理完成: task_id={result.task_id}, "
                        f"success={result.success}"
                    )
            except Exception as e:
                logger.error(f"事件处理异常: {e}", exc_info=True)

        # 创建后台任务
        asyncio.create_task(process_event())

        # 立即返回响应
        return {
            "status": "accepted",
            "message": "Webhook 已接收，正在后台处理",
            "delivery_id": x_github_delivery,
            "event_type": event_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook 处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


def main() -> None:
    """
    主函数入口

    用于直接运行此文件（例如: python app/main.py）
    """
    import uvicorn

    # 加载配置
    config = init_config()

    # 运行服务
    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        workers=config.server.workers,
        log_level=config.logging.level.lower(),
    )


if __name__ == "__main__":
    main()
