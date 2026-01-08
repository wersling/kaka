"""
Webhook 验证工具

实现 GitHub Webhook 签名验证和其他安全检查
"""

import hashlib
import hmac
import ipaddress
import os
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def verify_webhook_signature(
    payload: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None,
) -> bool:
    """
    验证 GitHub Webhook HMAC-SHA256 签名

    Args:
        payload: 请求体（原始字节）
        signature_header: X-Hub-Signature-256 头部值
        secret: Webhook 密钥，如果未提供则从环境变量读取

    Returns:
        bool: 签名是否有效

    Raises:
        ValueError: 如果缺少必要的配置
    """
    if not payload:
        logger.error("Webhook 验证失败: 空的 payload")
        return False

    if not signature_header:
        logger.error("Webhook 验证失败: 缺少签名头部")
        return False

    # 获取密钥
    webhook_secret = secret or os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("Webhook 验证失败: 未配置 GITHUB_WEBHOOK_SECRET")
        raise ValueError("GITHUB_WEBHOOK_SECRET 未配置")

    # 检查签名格式
    if not signature_header.startswith("sha256="):
        logger.error(f"Webhook 验证失败: 无效的签名格式: {signature_header[:20]}...")
        return False

    # 计算预期签名
    expected_signature = _calculate_signature(payload, webhook_secret)

    # 使用恒定时间比较防止时序攻击
    is_valid = hmac.compare_digest(expected_signature, signature_header)

    if not is_valid:
        logger.warning(
            f"Webhook 验证失败: 签名不匹配. "
            f"预期: {expected_signature[:20]}... "
            f"收到: {signature_header[:20]}..."
        )
    else:
        logger.debug("Webhook 签名验证成功")

    return is_valid


def _calculate_signature(payload: bytes, secret: str) -> str:
    """
    计算载荷的 HMAC-SHA256 签名

    Args:
        payload: 请求体
        secret: Webhook 密钥

    Returns:
        str: 格式为 "sha256=<hex_signature>" 的签名
    """
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def validate_ip_address(ip: str, whitelist: list[str]) -> bool:
    """
    验证 IP 地址是否在白名单中（支持 CIDR 表示法）

    Args:
        ip: 客户端 IP 地址
        whitelist: IP 白名单（支持 CIDR 表示法，如 "192.168.1.0/24"）

    Returns:
        bool: IP 是否允许
    """
    if not whitelist:
        # 如果白名单为空，则允许所有 IP
        logger.debug("IP 白名单为空，允许所有访问")
        return True

    try:
        client_ip = ipaddress.ip_address(ip)
    except ValueError:
        logger.warning(f"无效的 IP 地址: {ip}")
        return False

    for allowed in whitelist:
        try:
            # 支持单个 IP 和 CIDR 范围
            if "/" in allowed:
                network = ipaddress.ip_network(allowed, strict=False)
                if client_ip in network:
                    logger.debug(f"IP 在白名单中: {ip} (匹配 {allowed})")
                    return True
            else:
                if client_ip == ipaddress.ip_address(allowed):
                    logger.debug(f"IP 在白名单中: {ip}")
                    return True
        except ValueError:
            logger.warning(f"白名单中无效的 IP/CIDR: {allowed}")
            continue

    logger.warning(f"IP 不在白名单中: {ip}")
    return False


def validate_github_event(event_type: str) -> bool:
    """
    验证 GitHub 事件类型是否受支持

    Args:
        event_type: 事件类型（如 "issues", "issue_comment"）

    Returns:
        bool: 事件类型是否支持
    """
    supported_events = ["issues", "issue_comment", "ping"]

    if event_type in supported_events:
        logger.debug(f"支持的事件类型: {event_type}")
        return True

    logger.warning(f"不支持的事件类型: {event_type}")
    return False


def validate_issue_trigger(
    action: str,
    labels: list[str],
    trigger_label: str,
) -> bool:
    """
    验证 Issue 事件是否满足触发条件

    Args:
        action: 事件动作（如 "labeled", "unlabeled"）
        labels: Issue 的所有标签名列表
        trigger_label: 触发标签名

    Returns:
        bool: 是否应该触发
    """
    # 只在添加标签时触发
    if action != "labeled":
        logger.debug(f"Issue 事件动作不是 'labeled': {action}")
        return False

    # 检查是否包含触发标签
    if trigger_label in labels:
        logger.info(f"检测到触发标签: {trigger_label}")
        return True

    logger.debug(f"未检测到触发标签: {trigger_label}")
    return False


def validate_comment_trigger(
    comment_body: str,
    trigger_command: str,
) -> bool:
    """
    验证评论是否包含触发命令

    Args:
        comment_body: 评论内容
        trigger_command: 触发命令（如 "/ai develop"）

    Returns:
        bool: 是否应该触发
    """
    if not comment_body:
        logger.debug("评论内容为空")
        return False

    # 不区分大小写匹配
    if trigger_command.lower() in comment_body.lower():
        logger.info(f"检测到触发命令: {trigger_command}")
        return True

    logger.debug(f"评论中未包含触发命令: {trigger_command}")
    return False


def sanitize_log_data(data: dict, sensitive_keys: Optional[set[str]] = None) -> dict:
    """
    清理日志数据，完全隐藏敏感信息

    Args:
        data: 原始数据
        sensitive_keys: 敏感字段名集合

    Returns:
        dict: 清理后的数据
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "token",
            "password",
            "secret",
            "api_key",
            "webhook_secret",
            "authorization",
            "signature",
        }

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            # 完全隐藏敏感值，不显示任何字符
            sanitized[key] = "****"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value, sensitive_keys)
        else:
            sanitized[key] = value

    return sanitized
