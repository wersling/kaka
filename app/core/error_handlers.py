"""
统一异常处理器

为 FastAPI 应用注册自定义异常处理器
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.utils.logger import get_logger

logger = get_logger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    为 FastAPI 应用设置统一的异常处理器

    Args:
        app: FastAPI 应用实例
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """
        处理应用自定义异常

        Args:
            request: 请求对象
            exc: 应用异常

        Returns:
            JSONResponse: 错误响应
        """
        logger.error(
            f"应用异常: {request.method} {request.url.path} - "
            f"{exc.code.value}: {exc.message}",
            extra={
                "error_code": exc.code.value,
                "status_code": exc.status_code,
                "details": exc.details,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        处理 HTTP 异常

        Args:
            request: 请求对象
            exc: HTTP 异常

        Returns:
            JSONResponse: 错误响应
        """
        logger.error(
            f"HTTP 异常: {request.method} {request.url.path} - "
            f"{exc.status_code}: {exc.detail}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "status_code": exc.status_code,
                "path": request.url.path,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        处理请求验证异常

        Args:
            request: 请求对象
            exc: 验证异常

        Returns:
            JSONResponse: 错误响应
        """
        # 格式化错误信息，确保所有对象都是可序列化的
        formatted_errors = []
        for error in exc.errors():
            formatted_error = {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            formatted_errors.append(formatted_error)

        logger.error(
            f"验证错误: {request.method} {request.url.path} - {formatted_errors}"
        )

        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "请求验证失败",
                "status_code": 422,
                "details": formatted_errors,
                "path": request.url.path,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        处理未捕获的异常

        Args:
            request: 请求对象
            exc: 未捕获的异常

        Returns:
            JSONResponse: 错误响应
        """
        logger.error(
            f"未处理的异常: {request.method} {request.url.path}",
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": "内部服务器错误",
                "status_code": 500,
                "path": request.url.path,
            },
        )


__all__ = ["setup_exception_handlers"]
