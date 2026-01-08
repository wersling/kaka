"""
日志工具模块

提供统一的日志配置和接口
"""

import functools
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import structlog


def setup_logger(
    name: str = "ai-scheduler",
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10485760,  # 10 MB
    backup_count: int = 5,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    console: bool = True,
    json_logs: bool = False,
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量
        log_format: 日志格式字符串
        console: 是否输出到控制台
        json_logs: 是否使用 JSON 格式日志

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()  # 清除现有处理器
    logger.propagate = False  # 防止传播到父记录器

    # 创建格式化器
    if json_logs:
        # 使用 structlog 处理 JSON 格式
        configure_structlog(name, level)
        return logging.getLogger(name)
    else:
        formatter = logging.Formatter(log_format)

    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def configure_structlog(name: str, level: str) -> None:
    """
    配置 structlog 用于 JSON 格式日志

    Args:
        name: 日志记录器名称
        level: 日志级别
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器实例

    Args:
        name: 日志记录器名称，默认使用根记录器

    Returns:
        logging.Logger: 日志记录器实例
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger("ai-scheduler")


class LoggerMixin:
    """
    日志记录器混入类

    为类提供便捷的日志记录功能
    """

    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        return get_logger(self.__class__.__name__)


def log_function_call(logger: Optional[logging.Logger] = None):
    """
    函数调用日志装饰器

    Args:
        logger: 日志记录器，如果未提供则使用默认记录器
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or get_logger()
            _logger.debug(
                f"调用函数: {func.__name__}, 参数: args={args}, kwargs={kwargs}"
            )
            try:
                result = func(*args, **kwargs)
                _logger.debug(f"函数 {func.__name__} 执行成功")
                return result
            except Exception as e:
                _logger.error(f"函数 {func.__name__} 执行失败: {e}", exc_info=True)
                raise

        return wrapper

    return decorator


def log_async_function_call(logger: Optional[logging.Logger] = None):
    """
    异步函数调用日志装饰器

    Args:
        logger: 日志记录器，如果未提供则使用默认记录器
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _logger = logger or get_logger()
            _logger.debug(
                f"调用异步函数: {func.__name__}, 参数: args={args}, kwargs={kwargs}"
            )
            try:
                result = await func(*args, **kwargs)
                _logger.debug(f"异步函数 {func.__name__} 执行成功")
                return result
            except Exception as e:
                _logger.error(f"异步函数 {func.__name__} 执行失败: {e}", exc_info=True)
                raise

        return wrapper

    return decorator


# 预配置的日志记录器
def setup_from_config(config) -> logging.Logger:
    """
    从配置对象设置日志记录器

    Args:
        config: 配置对象（来自 app.config）

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return setup_logger(
        name="ai-scheduler",
        level=config.logging.level,
        log_file=config.logging.file,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
        log_format=config.logging.format,
        console=config.logging.console,
        json_logs=config.logging.json,
    )
