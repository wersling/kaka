"""
AI 开发调度服务 - FastAPI 应用入口

接收 GitHub Webhook 事件，触发 Claude Code CLI 进行自动化开发
"""

import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.health import router as health_router
from app.config import init_config, get_config, Config
from app.utils.logger import get_logger, setup_from_config
from app.core.error_handlers import setup_exception_handlers

# 初始化一个临时日志（后续会被正式配置替换）
logger = get_logger(__name__)


def setup_logging() -> logging.Logger:
    """
    设置日志系统

    在应用启动前调用，确保所有日志都能正确输出到文件
    包括应用日志、Uvicorn 访问日志和所有 traceback

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    global logger

    try:
        # 初始化配置
        config = init_config()

        # 确保 logs 目录存在
        log_file = Path(config.logging.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件处理器（用于所有日志）
        file_handler = RotatingFileHandler(
            config.logging.file,
            maxBytes=config.logging.max_bytes,
            backupCount=config.logging.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # 捕获所有级别的日志
        file_formatter = logging.Formatter(config.logging.format)
        file_handler.setFormatter(file_formatter)

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.logging.level.upper()))
        console_formatter = logging.Formatter(config.logging.format)
        console_handler.setFormatter(console_formatter)

        # 配置根日志记录器（捕获所有日志，包括 Uvicorn）
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # 设置为 DEBUG 以捕获所有日志

        # 清除根记录器的现有处理器
        root_logger.handlers.clear()

        # 添加处理器到根记录器
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # 设置应用特定的日志记录器
        logger_instance = setup_from_config(config)

        # 更新全局 logger
        logger = logger_instance

        # 同时更新模块级别的 logger
        this_module = sys.modules[__name__]
        this_module.logger = logger_instance

        # 配置 Uvicorn 日志记录器
        uvicorn_loggers = [
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
        ]

        for uvicorn_logger_name in uvicorn_loggers:
            uvicorn_logger = logging.getLogger(uvicorn_logger_name)
            uvicorn_logger.setLevel(logging.INFO)
            uvicorn_logger.handlers.clear()
            uvicorn_logger.propagate = True  # 传播到根记录器

        return logger_instance

    except Exception as e:
        # 如果配置加载失败，使用默认配置
        # 确保 logs 目录存在
        Path("logs").mkdir(parents=True, exist_ok=True)

        # 创建基本的日志配置
        logging.basicConfig(
            level=logging.DEBUG,  # 捕获所有日志
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("logs/ai-scheduler.log", encoding="utf-8"),
                logging.StreamHandler()
            ],
            force=True  # 强制重新配置
        )

        logger = logging.getLogger(__name__)
        logger.warning(f"使用默认日志配置，配置加载失败: {e}")
        return logger


class TimingMiddleware(BaseHTTPMiddleware):
    """请求计时中间件"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
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
    # 获取配置（日志已在模块加载时设置）
    config = get_config()

    # 启动时执行
    logger.info("=" * 60)
    logger.info("🚀 AI 开发调度服务启动中...")
    logger.info("=" * 60)
    logger.info(f"✅ 配置加载成功")
    logger.info(f"✅ 日志系统初始化完成 (级别: {config.logging.level})")

    # 初始化数据库
    from app.db.database import init_db
    try:
        init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}", exc_info=True)
        raise

    # 初始化并发管理器
    from app.utils.concurrency import ConcurrencyManager
    try:
        ConcurrencyManager.initialize(config.task.max_concurrent)
        logger.info(f"✅ 并发管理器初始化完成 (最大并发: {config.task.max_concurrent})")
    except Exception as e:
        logger.error(f"❌ 并发管理器初始化失败: {e}", exc_info=True)
        raise

    # 记录配置信息
    logger.info(f"📋 仓库: {config.github.repo_full_name}")
    logger.info(f"📂 本地路径: {config.repository.path}")
    logger.info(f"🏷️  触发标签: {config.github.trigger_label}")
    logger.info(f"💬 触发命令: {config.github.trigger_command}")

    logger.info("=" * 60)
    logger.info("✅ 服务启动完成")
    logger.info("=" * 60)

    yield

    # 关闭时执行
    logger.info("🛑 服务关闭中...")
    logger.info("✅ 服务已关闭")


# 在创建应用前设置日志系统
setup_logging()

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

# 初始化速率限制器
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],  # 默认限制：每分钟 60 次请求
    storage_uri="memory://",  # 使用内存存储（适合单实例部署）
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# 添加 CORS 中间件（安全配置，从配置文件读取允许的来源）
def get_cors_origins() -> list[str]:
    """获取 CORS 允许的来源列表"""
    try:
        from app.config import get_config
        config = get_config()
        return config.security.cors_origins
    except (AttributeError, ImportError, RuntimeError):
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

# 注册任务监控路由
from app.api.tasks import router as tasks_router
from app.api.dashboard import router as dashboard_router
from app.api.logs import router as logs_router
app.include_router(tasks_router, prefix="/api", tags=["Tasks"])
app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(logs_router, prefix="/api", tags=["Logs"])


# 设置统一的异常处理器
setup_exception_handlers(app)


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
@app.get("/webhook/github", tags=["Webhook"])
async def github_webhook_get() -> dict[str, str]:
    """
    GitHub Webhook 验证端点（GET）

    GitHub 在创建 Webhook 时会发送 GET 请求验证 URL。
    返回 200 以通过验证。
    """
    return {
        "message": "Webhook endpoint is ready",
        "method": "POST",
        "content_type": "application/json",
    }


@app.post("/webhook/github", tags=["Webhook"])
@limiter.limit("10/minute")  # Webhook 端点：每分钟最多 10 次请求
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
) -> dict[str, Any]:
    """
    GitHub Webhook 接收端点（POST）

    接收 GitHub 事件并触发 AI 开发流程
    """
    try:
        # 获取原始 payload
        payload = await request.body()

        # 验证签名
        from app.utils.validators import verify_webhook_signature
        from app.config import get_config

        config = get_config()

        # 详细日志记录签名验证过程（不泄露敏感信息）
        if x_hub_signature_256:
            sig_format = x_hub_signature_256.split('=')[0] if '=' in x_hub_signature_256 else 'unknown'
            sig_length = len(x_hub_signature_256.split('=')[1]) if '=' in x_hub_signature_256 else 0
            logger.debug(
                f"Webhook 签名验证: format={sig_format}, length={sig_length}"
            )
        else:
            logger.warning("Webhook 签名缺失：未提供 X-Hub-Signature-256 头")

        if not verify_webhook_signature(
            payload,
            x_hub_signature_256,
            config.github.webhook_secret,
        ):
            logger.warning(
                f"Webhook 签名验证失败: "
                f"提供的签名{'存在' if x_hub_signature_256 else '缺失'}, "
                f"验证未通过"
            )
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

        # 立即返回响应 (202 Accepted)
        return Response(
            content=json.dumps({
                "status": "accepted",
                "message": "Webhook 已接收，正在后台处理",
                "delivery_id": x_github_delivery,
                "event_type": event_type,
            }),
            status_code=status.HTTP_202_ACCEPTED,
            media_type="application/json",
        )

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
