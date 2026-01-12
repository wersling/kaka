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
from pydantic import ValidationError

# 初始化一个临时日志（后续会被正式配置替换）
logger = get_logger(__name__)


def setup_logging() -> logging.Logger:
    """
    设置日志系统

    在应用启动前调用，确保所有日志都能正确输出到文件
    包括应用日志、Uvicorn 访问日志和所有 traceback

    注意：此函数使用默认配置，不在模块加载时验证配置
    配置验证在 lifespan 中进行

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    global logger

    try:
        # 尝试初始化配置，但失败时使用默认配置
        # 不在这里抛出异常，让 lifespan 处理配置验证
        try:
            config = init_config()
            log_level = config.logging.level
            log_file = config.logging.file
            log_format = config.logging.format
            log_max_bytes = config.logging.max_bytes
            log_backup_count = config.logging.backup_count
        except Exception:
            # 配置加载失败，使用默认日志配置
            log_level = "INFO"
            log_file = "logs/kaka.log"
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            log_max_bytes = 10 * 1024 * 1024  # 10MB
            log_backup_count = 5

        # 确保 logs 目录存在
        log_file_path = Path(log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件处理器（用于所有日志）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_max_bytes,
            backupCount=log_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # 捕获所有级别的日志
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(log_format)
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
        # 如果配置加载成功，使用配置创建 logger
        try:
            logger_instance = setup_from_config(config)
        except Exception:
            # 配置对象无效，使用基本的 logger
            logger_instance = get_logger(__name__)

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
        # 如果日志设置完全失败，使用最基本的配置
        # 确保 logs 目录存在
        Path("logs").mkdir(parents=True, exist_ok=True)

        # 创建基本的日志配置
        logging.basicConfig(
            level=logging.DEBUG,  # 捕获所有日志
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("logs/kaka.log", encoding="utf-8"),
                logging.StreamHandler(),
            ],
            force=True,  # 强制重新配置
        )

        logger = logging.getLogger(__name__)
        logger.warning(f"使用基本日志配置: {e}")
        return logger


def parse_pydantic_error(error: Exception) -> list[str]:
    """
    解析 Pydantic 验证错误

    Args:
        error: 异常对象

    Returns:
        解析后的错误消息列表
    """
    error_str = str(error)
    errors = []

    # 检查是否是 Pydantic ValidationError
    if "validation error" in error_str.lower():
        try:
            # 尝试从错误字符串中提取字段名和错误消息
            # Pydantic 错误格式：Field_name\n  Error message
            lines = error_str.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # 查找字段行（例如：github.token）
                if "." in line and not line.startswith("For further"):
                    field_parts = line.split(".")
                    field_name = field_parts[-1] if field_parts else line

                    # 查找错误消息（通常在下一行或几行之后）
                    i += 1
                    error_messages = []
                    while i < len(lines):
                        next_line = lines[i].strip()
                        # 跳过空行和元数据行
                        if (
                            not next_line
                            or next_line.startswith("[type=")
                            or next_line.startswith("For further")
                        ):
                            i += 1
                            continue
                        # 找到错误消息
                        if "Value error" in next_line:
                            # 提取实际的错误消息（去掉 "Value error, " 前缀）
                            error_msg = next_line.split("Value error,")[-1].strip()
                            # 去除末尾的 Pydantic 元数据（例如：[type=value_error, ...]）
                            error_msg = error_msg.split(" [type=")[0].strip()
                            error_messages.append(error_msg)
                            i += 1
                            break
                        i += 1

                    # 组合错误消息
                    for msg in error_messages:
                        errors.append(f"❌ {msg}")
                else:
                    i += 1
        except Exception:
            # 如果解析失败，返回原始错误信息
            errors = [f"⚠️  {error_str}"]
    else:
        errors = [f"⚠️  {error_str}"]

    return errors if errors else [f"⚠️  {error_str}"]


def check_config_validity(config: Config) -> list[str]:
    """
    检查配置有效性

    Args:
        config: 配置对象

    Returns:
        错误消息列表（空列表表示配置有效）
    """
    errors = []

    # 检查 GitHub Token
    if not config.github.token or config.github.token.startswith("${"):
        errors.append("❌ GitHub Token 未配置或无效")
    elif not (
        config.github.token.startswith("ghp_") or config.github.token.startswith("github_pat_")
    ):
        errors.append("❌ GitHub Token 格式无效（应以 ghp_ 或 github_pat_ 开头）")

    # 检查仓库信息
    if not config.github.repo_owner or config.github.repo_owner.startswith("${"):
        errors.append("❌ GitHub 仓库所有者未配置")

    if not config.github.repo_name or config.github.repo_name.startswith("${"):
        errors.append("❌ GitHub 仓库名称未配置")

    # 检查本地仓库路径
    if not config.repository.path or str(config.repository.path).startswith("${"):
        errors.append("❌ 本地仓库路径未配置")
    else:
        repo_path = config.repository.path
        if not repo_path.exists():
            errors.append(f"❌ 本地仓库路径不存在: {repo_path}")
        elif not (repo_path / ".git").exists():
            errors.append(f"❌ 本地路径不是有效的 Git 仓库: {repo_path}")

    # 检查 Webhook Secret
    if not config.github.webhook_secret or config.github.webhook_secret.startswith("${"):
        errors.append("❌ GitHub Webhook Secret 未配置")

    return errors


def print_config_guide(errors: list[str]) -> None:
    """
    打印配置指南

    Args:
        errors: 错误消息列表（支持多行错误，用换行符分隔）
    """
    print("\n" + "=" * 70)
    print("⚠️  配置验证失败")
    print("=" * 70)
    print("\n检测到以下配置问题：\n")

    for error in errors:
        # 如果错误包含换行符，按行打印，保持缩进
        if "\n" in error:
            lines = error.split("\n")
            # 打印第一行（错误标题）
            print(f"  {lines[0]}")
            # 打印后续行（详细信息），保持原有缩进
            for line in lines[1:]:
                print(f"  {line}")
        else:
            print(f"  {error}")

    print("\n" + "-" * 70)
    print("\n📝 请运行以下命令进行配置：")
    print("\n  kaka configure")
    print("\n配置脚本将引导您完成以下步骤：")
    print("  1. 验证 GitHub Token（实际 API 调用验证）")
    print("  2. 配置 GitHub 仓库信息")
    print("  3. 设置本地仓库路径")
    print("  4. 生成 Webhook Secret")
    print("\n" + "=" * 70 + "\n")


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
    # 检查 .env 文件是否存在
    env_file = Path(".env")
    config = None
    config_errors = []

    if not env_file.exists():
        # 标记应用需要配置
        app.state.needs_configuration = True
        config_errors = ["📄 未找到 .env 配置文件", "   需要运行 'kaka configure' 创建配置文件"]
        logger.warning("未找到配置文件，应用需要配置")
    else:
        try:
            config = get_config()
            app.state.needs_configuration = False
        except Exception as e:
            # 标记应用需要配置
            app.state.needs_configuration = True
            error_msg = str(e)

            # 检查是否是配置文件不存在
            if "配置文件不存在" in error_msg or "FileNotFoundError" in error_msg:
                config_errors = [
                    "📄 未找到 config/config.yaml 配置文件",
                    f"   需要运行 'kaka configure' 创建配置文件",
                ]
            else:
                # 使用 parse_pydantic_error 解析验证错误
                config_errors = parse_pydantic_error(e)

            logger.warning(f"配置加载失败: {e}")

        # 如果加载成功，检查配置有效性
        if config:
            config_errors = check_config_validity(config)
            if config_errors:
                app.state.needs_configuration = True
                logger.warning("配置验证失败")

    # 如果需要配置，退出程序
    if config_errors:
        # 使用 print_config_guide 显示详细错误信息
        print_config_guide(config_errors)
        # 刷新输出缓冲区，确保消息显示
        sys.stdout.flush()
        sys.stderr.flush()
        # 直接退出程序，不启动服务
        import os

        os._exit(0)

    # 配置有效，继续正常启动流程

    # 启动时执行
    logger.info("=" * 60)
    logger.info("🚀 AI 开发调度服务启动中...")
    logger.info("=" * 60)
    logger.info(f"✅ 配置加载成功")
    logger.info(f"✅ 配置验证通过")
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
from app.api.config import router as config_router

app.include_router(tasks_router, prefix="/api", tags=["Tasks"])
app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(logs_router, prefix="/api", tags=["Logs"])
app.include_router(config_router, tags=["Config"])


# 设置统一的异常处理器
setup_exception_handlers(app)


# 根路径
@app.get("/", tags=["Root"], response_model=None)
async def root(request: Request) -> Response:
    """
    根路径

    返回服务基本信息或配置引导
    """
    # 检查应用是否需要配置
    if getattr(request.app.state, "needs_configuration", False):
        return JSONResponse(
            status_code=503,
            content={
                "service": "AI 开发调度服务",
                "version": "0.1.0",
                "status": "needs_configuration",
                "message": "应用需要配置才能正常运行",
                "setup_command": "kaka configure",
                "documentation": "配置脚本将引导您完成以下步骤：\n"
                "1. 验证 GitHub Token（实际 API 调用验证）\n"
                "2. 配置 GitHub 仓库信息\n"
                "3. 设置本地仓库路径\n"
                "4. 生成 Webhook Secret",
            },
        )

    return JSONResponse(
        content={
            "service": "AI 开发调度服务",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
        },
    )


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
            sig_format = (
                x_hub_signature_256.split("=")[0] if "=" in x_hub_signature_256 else "unknown"
            )
            sig_length = len(x_hub_signature_256.split("=")[1]) if "=" in x_hub_signature_256 else 0
            logger.debug(f"Webhook 签名验证: format={sig_format}, length={sig_length}")
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

        logger.info(f"收到 Webhook: delivery={x_github_delivery}, " f"event={event_type}")

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
                        f"事件处理完成: task_id={result.task_id}, " f"success={result.success}"
                    )
            except Exception as e:
                logger.error(f"事件处理异常: {e}", exc_info=True)

        # 创建后台任务
        asyncio.create_task(process_event())

        # 立即返回响应 (202 Accepted)
        return Response(
            content=json.dumps(
                {
                    "status": "accepted",
                    "message": "Webhook 已接收，正在后台处理",
                    "delivery_id": x_github_delivery,
                    "event_type": event_type,
                }
            ),
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
