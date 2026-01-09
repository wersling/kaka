"""
validators.py 模块的完整单元测试套件

测试覆盖所有验证函数，包括：
- HMAC-SHA256 签名验证（完整的安全场景、边界条件和性能测试）
- IP 白名单验证
- Issue 事件触发条件验证
- 评论触发条件验证
- 敏感数据清理

测试覆盖率目标：100%
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from app.utils.validators import (
    _calculate_signature,
    sanitize_log_data,
    validate_comment_trigger,
    validate_github_event,
    validate_ip_address,
    validate_issue_trigger,
    verify_webhook_signature,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def webhook_secret():
    """提供测试用的 webhook 密钥"""
    return "test_webhook_secret_12345"


@pytest.fixture
def sample_payload():
    """提供测试用的 webhook payload"""
    return b'{"action": "labeled", "issue": {"id": 123}}'


@pytest.fixture
def sample_signature(webhook_secret, sample_payload):
    """计算有效的 HMAC-SHA256 签名"""
    return _calculate_signature(sample_payload, webhook_secret)


@pytest.fixture
def mock_ip_whitelist():
    """提供测试用的 IP 白名单"""
    return [
        "192.168.1.100",  # 单个 IP
        "10.0.0.0/24",  # CIDR 范围
        "172.16.0.0/16",  # CIDR 范围
    ]


@pytest.fixture
def sample_issue_data():
    """提供测试用的 Issue 数据"""
    return {
        "action": "labeled",
        "labels": ["bug", "enhancement", "ai-dev"],
        "trigger_label": "ai-dev",
    }


@pytest.fixture
def sample_comment_data():
    """提供测试用的评论数据"""
    return {
        "body": "This is a test comment\n/ai develop\nPlease help",
        "trigger_command": "/ai develop",
    }


@pytest.fixture
def sample_log_data():
    """提供测试用的日志数据（包含敏感信息）"""
    return {
        "username": "testuser",
        "token": "secret_token_abc123",
        "password": "my_password_456",
        "email": "user@example.com",
        "api_key": "key_xyz789",
        "nested": {
            "webhook_secret": "wh_secret_999",
            "normal_field": "normal_value",
            "deep": {
                "authorization": "Bearer token123",
                "other": "data",
            },
        },
        "signature": "sig_value",
    }


# =============================================================================
# verify_webhook_signature() 测试
# =============================================================================


class TestVerifyWebhookSignature:
    """测试 GitHub Webhook HMAC-SHA256 签名验证"""

    def test_valid_signature_verification(
        self, sample_payload, sample_signature, webhook_secret
    ):
        """
        测试：正确的签名应该通过验证

        场景：使用有效的 payload、签名和密钥进行验证
        期望：返回 True
        """
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=sample_signature,
            secret=webhook_secret,
        )
        assert result is True

    def test_invalid_signature_rejection(
        self, sample_payload, webhook_secret
    ):
        """
        测试：错误的签名应该被拒绝

        场景：提供不正确的签名
        期望：返回 False
        """
        invalid_signature = "sha256=invalid_signature_here"
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=invalid_signature,
            secret=webhook_secret,
        )
        assert result is False

    def test_missing_secret_raises_exception(
        self, sample_payload, sample_signature
    ):
        """
        测试：缺失密钥时应该抛出 ValueError 异常

        场景：没有提供 secret 参数且环境变量也未设置
        期望：抛出 ValueError 异常，提示未配置 GITHUB_WEBHOOK_SECRET
        """
        # 确保环境变量未设置
        with patch.dict(os.environ, clear=True):
            with pytest.raises(ValueError) as exc_info:
                verify_webhook_signature(
                    payload=sample_payload,
                    signature_header=sample_signature,
                    secret=None,
                )
            assert "GITHUB_WEBHOOK_SECRET 未配置" in str(exc_info.value)

    def test_missing_payload_returns_false(self, sample_signature):
        """
        测试：缺失 payload 时应该返回 False

        场景：payload 为空字节
        期望：返回 False
        """
        result = verify_webhook_signature(
            payload=b"",
            signature_header=sample_signature,
            secret="test_secret",
        )
        assert result is False

    def test_missing_signature_header_returns_false(
        self, sample_payload, webhook_secret
    ):
        """
        测试：缺失签名头部时应该返回 False

        场景：signature_header 为 None
        期望：返回 False
        """
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=None,
            secret=webhook_secret,
        )
        assert result is False

    def test_signature_format_validation(self, sample_payload, webhook_secret):
        """
        测试：无效的签名格式应该被拒绝

        场景：签名不以 "sha256=" 开头
        期望：返回 False
        """
        invalid_format_signature = "md5=some_hash_value"
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=invalid_format_signature,
            secret=webhook_secret,
        )
        assert result is False

    def test_secret_from_environment_variable(
        self, sample_payload, sample_signature, webhook_secret
    ):
        """
        测试：应该能够从环境变量读取密钥

        场景：不提供 secret 参数，但设置了环境变量
        期望：成功验证签名
        """
        with patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": webhook_secret}):
            result = verify_webhook_signature(
                payload=sample_payload,
                signature_header=sample_signature,
                secret=None,
            )
            assert result is True

    def test_timing_attack_protection(
        self, sample_payload, sample_signature, webhook_secret
    ):
        """
        测试：应该使用恒定时间比较防止时序攻击

        场景：验证函数使用 hmac.compare_digest
        期望：即使签名长度不同，比较时间也应该恒定
        """
        # 这个测试验证代码使用了 hmac.compare_digest
        # 实际的时序攻击测试需要更复杂的设置
        with patch("hmac.compare_digest") as mock_compare:
            mock_compare.return_value = False
            result = verify_webhook_signature(
                payload=sample_payload,
                signature_header=sample_signature,
                secret=webhook_secret,
            )
            mock_compare.assert_called_once()
            assert result is False

    # =========================================================================
    # 安全场景测试
    # =========================================================================

    def test_tampered_signature_rejection(
        self, sample_payload, webhook_secret
    ):
        """
        测试：篡改后的签名应该被拒绝

        场景：修改 payload 后的签名不应该通过验证
        期望：返回 False
        """
        # 计算 payload 的签名
        original_signature = _calculate_signature(
            sample_payload, webhook_secret
        )

        # 修改 payload
        tampered_payload = b'{"action": "unlabeled", "issue": {"id": 999}}'

        # 使用原始签名验证修改后的 payload
        result = verify_webhook_signature(
            payload=tampered_payload,
            signature_header=original_signature,
            secret=webhook_secret,
        )
        assert result is False

    @pytest.mark.parametrize(
        "invalid_signature",
        [
            "sha256=",  # 空签名
            "sha256=abc",  # 太短的签名
            "sha256=ggg" + "0" * 61,  # 包含无效十六进制字符
            "sha256=" + "x" * 64,  # 全部无效字符
            "sha256=" + "0" * 63,  # 长度不足
            "sha256=" + "0" * 65,  # 长度过长
        ],
    )
    def test_invalid_hex_characters_rejected(
        self, invalid_signature, sample_payload, webhook_secret
    ):
        """
        测试：无效的十六进制字符应该被拒绝

        场景：签名包含无效的十六进制字符或长度不正确
        期望：返回 False
        """
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=invalid_signature,
            secret=webhook_secret,
        )
        assert result is False

    def test_empty_string_signature_rejected(
        self, sample_payload, webhook_secret
    ):
        """
        测试：空字符串签名应该被拒绝

        场景：signature_header 为空字符串 ""
        期望：返回 False
        """
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header="",
            secret=webhook_secret,
        )
        assert result is False

    def test_wrong_signature_algorithm_rejected(
        self, sample_payload, webhook_secret
    ):
        """
        测试：错误的签名算法应该被拒绝

        场景：签名使用错误的算法前缀（如 sha1=）
        期望：返回 False
        """
        # 计算 SHA1 签名（如果实现的话）
        wrong_algorithm_signature = "sha1=" + "a" * 40
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=wrong_algorithm_signature,
            secret=webhook_secret,
        )
        assert result is False

    def test_none_signature_rejected(
        self, sample_payload, webhook_secret
    ):
        """
        测试：None 签名应该被拒绝

        场景：signature_header 为 None
        期望：返回 False
        """
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=None,
            secret=webhook_secret,
        )
        assert result is False

    def test_signature_with_extra_whitespace_rejected(
        self, sample_payload, webhook_secret
    ):
        """
        测试：包含额外空格的签名应该被拒绝

        场景：签名前后有空格
        期望：返回 False
        """
        valid_signature = _calculate_signature(sample_payload, webhook_secret)
        invalid_signature = f" {valid_signature} "
        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=invalid_signature,
            secret=webhook_secret,
        )
        assert result is False

    # =========================================================================
    # 边界条件测试
    # =========================================================================

    def test_empty_payload_rejected(self, webhook_secret):
        """
        测试：空 payload 应该被拒绝

        场景：payload 为空字节 b""
        期望：返回 False
        """
        signature = _calculate_signature(b"", webhook_secret)
        result = verify_webhook_signature(
            payload=b"",
            signature_header=signature,
            secret=webhook_secret,
        )
        assert result is False

    def test_large_payload_handled(self, webhook_secret):
        """
        测试：大 payload 应该能够处理

        场景：payload 为 1MB 数据
        期望：正确处理并验证签名
        """
        # 创建 1MB 的 payload
        large_payload = b'{"data": "' + b"x" * (1024 * 1024) + b'"}'
        signature = _calculate_signature(large_payload, webhook_secret)

        result = verify_webhook_signature(
            payload=large_payload,
            signature_header=signature,
            secret=webhook_secret,
        )
        assert result is True

    def test_special_characters_payload(self, webhook_secret):
        """
        测试：包含特殊字符的 payload

        场景：payload 包含特殊字符、换行、引号等
        期望：正确处理并验证签名
        """
        special_payload = b'{"text": "Hello\nWorld\t!@#$%^&*()"}'
        signature = _calculate_signature(special_payload, webhook_secret)

        result = verify_webhook_signature(
            payload=special_payload,
            signature_header=signature,
            secret=webhook_secret,
        )
        assert result is True

    def test_unicode_payload(self, webhook_secret):
        """
        测试：Unicode 字符的 payload

        场景：payload 包含多语言 Unicode 字符
        期望：正确处理并验证签名
        """
        unicode_payload = (
            b'{"text": "\xe4\xb8\xad\xe6\x96\x87 \xf0\x9f\x98\x80 '
            b'\xd0\x9f\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82"}'
        )
        signature = _calculate_signature(unicode_payload, webhook_secret)

        result = verify_webhook_signature(
            payload=unicode_payload,
            signature_header=signature,
            secret=webhook_secret,
        )
        assert result is True

    def test_binary_payload(self, webhook_secret):
        """
        测试：二进制 payload

        场景：payload 包含二进制数据
        期望：正确处理并验证签名
        """
        binary_payload = bytes(range(256))
        signature = _calculate_signature(binary_payload, webhook_secret)

        result = verify_webhook_signature(
            payload=binary_payload,
            signature_header=signature,
            secret=webhook_secret,
        )
        assert result is True

    def test_very_long_secret(self, sample_payload):
        """
        测试：非常长的密钥

        场景：secret 长度为 1000 字符
        期望：正确处理并验证签名
        """
        long_secret = "a" * 1000
        signature = _calculate_signature(sample_payload, long_secret)

        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=signature,
            secret=long_secret,
        )
        assert result is True

    def test_secret_with_special_characters(self, sample_payload):
        """
        测试：包含特殊字符的密钥

        场景：secret 包含特殊字符
        期望：正确处理并验证签名
        """
        special_secret = "test-secret!@#$%^&*()_+-=[]{}|;':,.<>?/~`"
        signature = _calculate_signature(sample_payload, special_secret)

        result = verify_webhook_signature(
            payload=sample_payload,
            signature_header=signature,
            secret=special_secret,
        )
        assert result is True

    # =========================================================================
    # 性能测试
    # =========================================================================

    def test_signature_verification_performance(
        self, sample_payload, webhook_secret
    ):
        """
        测试：签名验证性能基准

        场景：单次签名验证性能
        期望：验证时间 < 1ms
        """
        signature = _calculate_signature(sample_payload, webhook_secret)

        # 预热
        for _ in range(10):
            verify_webhook_signature(
                payload=sample_payload,
                signature_header=signature,
                secret=webhook_secret,
            )

        # 测量
        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            verify_webhook_signature(
                payload=sample_payload,
                signature_header=signature,
                secret=webhook_secret,
            )

        end_time = time.perf_counter()
        avg_time_ms = (end_time - start_time) / iterations * 1000

        # 验证平均时间 < 1ms
        assert (
            avg_time_ms < 1.0
        ), f"平均签名验证时间 {avg_time_ms:.3f}ms 超过 1ms 阈值"

    def test_batch_verification_performance(self, webhook_secret):
        """
        测试：批量签名验证性能

        场景：验证 100 个不同的签名
        期望：总时间合理（< 100ms）
        """
        payloads_and_signatures = []
        for i in range(100):
            payload = f'{{"id": {i}}}'.encode()
            signature = _calculate_signature(payload, webhook_secret)
            payloads_and_signatures.append((payload, signature))

        start_time = time.perf_counter()

        for payload, signature in payloads_and_signatures:
            verify_webhook_signature(
                payload=payload,
                signature_header=signature,
                secret=webhook_secret,
            )

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000

        # 验证总时间 < 100ms
        assert (
            total_time_ms < 100.0
        ), f"批量验证总时间 {total_time_ms:.2f}ms 超过 100ms 阈值"

    # =========================================================================
    # 编码测试
    # =========================================================================

    def test_utf8_encoding_handling(self, webhook_secret):
        """
        测试：UTF-8 编码处理

        场景：payload 为 UTF-8 编码的 Unicode 字符
        期望：正确处理并验证签名
        """
        # 包含各种 Unicode 字符的 payload
        utf8_payload = (
            b'{"message": "Hello \xc4\x87\xc4\x87\xc4\x87 " '
            b'\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82 " '
            b'\xe4\xb8\xad\xe6\x96\x87"}'
        )
        signature = _calculate_signature(utf8_payload, webhook_secret)

        result = verify_webhook_signature(
            payload=utf8_payload,
            signature_header=signature,
            secret=webhook_secret,
        )
        assert result is True

    def test_secret_encoding_consistency(self, sample_payload):
        """
        测试：密钥编码一致性

        场景：确保密钥编码在不同调用中保持一致
        期望：相同密钥产生相同签名
        """
        secret = "test_secret_with_Unicode_Ñ"
        sig1 = _calculate_signature(sample_payload, secret)
        sig2 = _calculate_signature(sample_payload, secret)

        assert sig1 == sig2, "相同密钥应该产生相同签名"


# =============================================================================
# _calculate_signature() 测试
# =============================================================================


class TestCalculateSignature:
    """测试 HMAC-SHA256 签名计算"""

    def test_signature_calculation(self, sample_payload, webhook_secret):
        """
        测试：签名计算应该正确

        场景：计算已知 payload 和 secret 的签名
        期望：返回格式正确的签名
        """
        signature = _calculate_signature(sample_payload, webhook_secret)
        assert signature.startswith("sha256=")
        assert len(signature) == 71  # "sha256=" (7) + 64 hex chars

    def test_signature_deterministic(self, sample_payload, webhook_secret):
        """
        测试：相同输入应该产生相同签名

        场景：多次计算相同 payload 和 secret 的签名
        期望：所有签名都相同
        """
        sig1 = _calculate_signature(sample_payload, webhook_secret)
        sig2 = _calculate_signature(sample_payload, webhook_secret)
        sig3 = _calculate_signature(sample_payload, webhook_secret)
        assert sig1 == sig2 == sig3

    def test_signature_different_for_different_payloads(self, webhook_secret):
        """
        测试：不同的 payload 应该产生不同的签名

        场景：计算不同 payload 的签名
        期望：所有签名都不同
        """
        payload1 = b'{"action": "labeled"}'
        payload2 = b'{"action": "unlabeled"}'
        sig1 = _calculate_signature(payload1, webhook_secret)
        sig2 = _calculate_signature(payload2, webhook_secret)
        assert sig1 != sig2

    def test_signature_different_for_different_secrets(self, sample_payload):
        """
        测试：不同的 secret 应该产生不同的签名

        场景：使用不同的 secret 计算签名
        期望：所有签名都不同
        """
        secret1 = "secret1"
        secret2 = "secret2"
        sig1 = _calculate_signature(sample_payload, secret1)
        sig2 = _calculate_signature(sample_payload, secret2)
        assert sig1 != sig2


# =============================================================================
# validate_ip_address() 测试
# =============================================================================


class TestValidateIPAddress:
    """测试 IP 白名单验证"""

    def test_single_ip_match(self, mock_ip_whitelist):
        """
        测试：单个 IP 地址精确匹配

        场景：IP 地址在白名单中（精确匹配）
        期望：返回 True
        """
        result = validate_ip_address("192.168.1.100", mock_ip_whitelist)
        assert result is True

    def test_cidr_range_match(self, mock_ip_whitelist):
        """
        测试：CIDR 范围匹配

        场景：IP 地址在 CIDR 范围内
        期望：返回 True
        """
        result = validate_ip_address("10.0.0.50", mock_ip_whitelist)
        assert result is True

    def test_cidr_range_boundary(self, mock_ip_whitelist):
        """
        测试：CIDR 范围边界匹配

        场景：测试 CIDR 范围的边界 IP
        期望：返回 True
        """
        # 10.0.0.0/24 的范围是 10.0.0.0 - 10.0.0.255
        assert validate_ip_address("10.0.0.0", mock_ip_whitelist) is True
        assert validate_ip_address("10.0.0.255", mock_ip_whitelist) is True
        # 超出范围
        assert validate_ip_address("10.0.1.0", mock_ip_whitelist) is False

    def test_empty_whitelist_allows_all(self):
        """
        测试：空白名单应该允许所有 IP

        场景：白名单为空列表
        期望：返回 True
        """
        result = validate_ip_address("8.8.8.8", [])
        assert result is True

    def test_ip_not_in_whitelist_rejected(self, mock_ip_whitelist):
        """
        测试：不在白名单中的 IP 应该被拒绝

        场景：IP 地址不在白名单中
        期望：返回 False
        """
        result = validate_ip_address("8.8.8.8", mock_ip_whitelist)
        assert result is False

    def test_invalid_ip_address_rejected(self, mock_ip_whitelist):
        """
        测试：无效的 IP 地址应该被拒绝

        场景：提供格式错误的 IP 地址
        期望：返回 False
        """
        result = validate_ip_address("invalid_ip", mock_ip_whitelist)
        assert result is False

    def test_ipv6_address_support(self):
        """
        测试：支持 IPv6 地址

        场景：使用 IPv6 地址和 CIDR 范围
        期望：正确处理 IPv6 地址
        """
        whitelist = ["2001:db8::/32"]
        assert validate_ip_address("2001:db8::1", whitelist) is True
        assert validate_ip_address("2001:db8:ffff::1", whitelist) is True
        assert validate_ip_address("2001:db9::1", whitelist) is False

    def test_invalid_cidr_in_whitelist_skipped(self):
        """
        测试：白名单中的无效 CIDR 应该被跳过

        场景：白名单包含无效的 CIDR 表示法
        期望：跳过无效条目，继续检查其他条目
        """
        whitelist = ["invalid_entry", "192.168.1.100"]
        result = validate_ip_address("192.168.1.100", whitelist)
        assert result is True

    def test_multiple_cidr_ranges(self):
        """
        测试：多个 CIDR 范围的正确处理

        场景：白名单包含多个 CIDR 范围
        期望：正确匹配任何一个范围
        """
        whitelist = ["10.0.0.0/24", "172.16.0.0/16", "192.168.0.0/16"]
        assert validate_ip_address("10.0.0.50", whitelist) is True
        assert validate_ip_address("172.16.5.10", whitelist) is True
        assert validate_ip_address("192.168.100.5", whitelist) is True
        assert validate_ip_address("8.8.8.8", whitelist) is False


# =============================================================================
# validate_github_event() 测试
# =============================================================================


class TestValidateGitHubEvent:
    """测试 GitHub 事件类型验证"""

    def test_supported_issues_event(self):
        """
        测试：支持的 issues 事件

        期望：返回 True
        """
        assert validate_github_event("issues") is True

    def test_supported_issue_comment_event(self):
        """
        测试：支持的 issue_comment 事件

        期望：返回 True
        """
        assert validate_github_event("issue_comment") is True

    def test_supported_ping_event(self):
        """
        测试：支持的 ping 事件

        期望：返回 True
        """
        assert validate_github_event("ping") is True

    def test_unsupported_event_rejected(self):
        """
        测试：不支持的事件类型应该被拒绝

        场景：提供不在支持列表中的事件类型
        期望：返回 False
        """
        assert validate_github_event("push") is False
        assert validate_github_event("pull_request") is False
        assert validate_github_event("unknown_event") is False


# =============================================================================
# validate_issue_trigger() 测试
# =============================================================================


class TestValidateIssueTrigger:
    """测试 Issue 触发条件验证"""

    def test_labeled_action_with_trigger_label(self, sample_issue_data):
        """
        测试：labeled 动作且包含触发标签应该通过

        场景：action 为 "labeled" 且 labels 包含触发标签
        期望：返回 True
        """
        result = validate_issue_trigger(
            action=sample_issue_data["action"],
            labels=sample_issue_data["labels"],
            trigger_label=sample_issue_data["trigger_label"],
        )
        assert result is True

    def test_unlabeled_action_rejected(self, sample_issue_data):
        """
        测试：非 labeled 动作应该被拒绝

        场景：action 为 "unlabeled"
        期望：返回 False
        """
        result = validate_issue_trigger(
            action="unlabeled",
            labels=sample_issue_data["labels"],
            trigger_label=sample_issue_data["trigger_label"],
        )
        assert result is False

    def test_other_actions_rejected(self, sample_issue_data):
        """
        测试：其他动作类型应该被拒绝

        场景：action 为 "opened", "edited", "closed" 等
        期望：返回 False
        """
        actions = ["opened", "edited", "closed", "reopened", "assigned"]
        for action in actions:
            result = validate_issue_trigger(
                action=action,
                labels=sample_issue_data["labels"],
                trigger_label=sample_issue_data["trigger_label"],
            )
            assert result is False

    def test_missing_trigger_label_rejected(self, sample_issue_data):
        """
        测试：不包含触发标签应该被拒绝

        场景：labels 列表不包含触发标签
        期望：返回 False
        """
        result = validate_issue_trigger(
            action="labeled",
            labels=["bug", "enhancement"],
            trigger_label="ai-dev",
        )
        assert result is False

    def test_empty_labels_list_rejected(self):
        """
        测试：空的标签列表应该被拒绝

        场景：labels 为空列表
        期望：返回 False
        """
        result = validate_issue_trigger(
            action="labeled",
            labels=[],
            trigger_label="ai-dev",
        )
        assert result is False

    def test_case_sensitive_label_matching(self):
        """
        测试：标签匹配应该区分大小写

        场景：触发标签的大小写与 labels 中的标签不匹配
        期望：返回 False（大小写敏感）
        """
        result = validate_issue_trigger(
            action="labeled",
            labels=["AI-Dev", "bug"],
            trigger_label="ai-dev",
        )
        assert result is False


# =============================================================================
# validate_comment_trigger() 测试
# =============================================================================


class TestValidateCommentTrigger:
    """测试评论触发条件验证"""

    def test_comment_contains_trigger_command(self, sample_comment_data):
        """
        测试：评论包含触发命令应该通过

        场景：评论内容中包含触发命令
        期望：返回 True
        """
        result = validate_comment_trigger(
            comment_body=sample_comment_data["body"],
            trigger_command=sample_comment_data["trigger_command"],
        )
        assert result is True

    def test_comment_missing_trigger_command(self, sample_comment_data):
        """
        测试：评论不包含触发命令应该被拒绝

        场景：评论内容中没有触发命令
        期望：返回 False
        """
        result = validate_comment_trigger(
            comment_body="This is just a normal comment",
            trigger_command=sample_comment_data["trigger_command"],
        )
        assert result is False

    def test_empty_comment_rejected(self):
        """
        测试：空评论应该被拒绝

        场景：comment_body 为空字符串
        期望：返回 False
        """
        result = validate_comment_trigger(
            comment_body="",
            trigger_command="/ai develop",
        )
        assert result is False

    def test_none_comment_rejected(self):
        """
        测试：None 评论应该被拒绝

        场景：comment_body 为 None
        期望：返回 False
        """
        result = validate_comment_trigger(
            comment_body=None,
            trigger_command="/ai develop",
        )
        assert result is False

    def test_case_insensitive_command_matching(self):
        """
        测试：命令匹配应该不区分大小写

        场景：评论中的命令与触发命令大小写不同
        期望：返回 True（不区分大小写）
        """
        result = validate_comment_trigger(
            comment_body="Please help with /AI DEVELOP",
            trigger_command="/ai develop",
        )
        assert result is True

    def test_trigger_command_at_start(self):
        """
        测试：触发命令在评论开头

        场景：评论以触发命令开头
        期望：返回 True
        """
        result = validate_comment_trigger(
            comment_body="/ai develop\nThis is a task",
            trigger_command="/ai develop",
        )
        assert result is True

    def test_trigger_command_at_end(self):
        """
        测试：触发命令在评论结尾

        场景：评论以触发命令结尾
        期望：返回 True
        """
        result = validate_comment_trigger(
            comment_body="Please help /ai develop",
            trigger_command="/ai develop",
        )
        assert result is True

    def test_trigger_command_in_middle(self):
        """
        测试：触发命令在评论中间

        场景：触发命令在评论中间位置
        期望：返回 True
        """
        result = validate_comment_trigger(
            comment_body="I need help\n/ai develop\nwith this issue",
            trigger_command="/ai develop",
        )
        assert result is True

    def test_partial_command_not_matched(self):
        """
        测试：部分命令不应该匹配

        场景：评论中只包含命令的一部分
        期望：返回 False
        """
        result = validate_comment_trigger(
            comment_body="I need /ai help",
            trigger_command="/ai develop",
        )
        assert result is False

    def test_command_with_extra_whitespace(self):
        """
        测试：命令包含额外空格

        场景：命令前后或中间有额外空格
        期望：返回 True（子串匹配）
        """
        result = validate_comment_trigger(
            comment_body="Please help with  /ai  develop  ",
            trigger_command="/ai develop",
        )
        assert result is False  # 因为子串匹配，空格会破坏匹配


# =============================================================================
# sanitize_log_data() 测试
# =============================================================================


class TestSanitizeLogData:
    """测试敏感数据清理"""

    def test_sensitive_fields_hidden(self, sample_log_data):
        """
        测试：敏感字段应该被完全隐藏

        场景：数据包含 token、password 等敏感字段
        期望：敏感字段值被替换为 "****"
        """
        result = sanitize_log_data(sample_log_data)

        assert result["token"] == "****"
        assert result["password"] == "****"
        assert result["api_key"] == "****"
        assert result["signature"] == "****"

    def test_non_sensitive_fields_preserved(self, sample_log_data):
        """
        测试：非敏感字段应该保留

        场景：数据包含 username、email 等非敏感字段
        期望：非敏感字段值保持不变
        """
        result = sanitize_log_data(sample_log_data)

        assert result["username"] == "testuser"
        assert result["email"] == "user@example.com"

    def test_nested_dict_sanitization(self, sample_log_data):
        """
        测试：嵌套字典中的敏感字段应该被隐藏

        场景：数据包含嵌套的字典结构
        期望：所有层级的敏感字段都被隐藏
        """
        result = sanitize_log_data(sample_log_data)

        assert result["nested"]["webhook_secret"] == "****"
        assert result["nested"]["normal_field"] == "normal_value"

    def test_deeply_nested_sanitization(self, sample_log_data):
        """
        测试：深层嵌套字典的敏感字段应该被隐藏

        场景：数据包含多层嵌套结构
        期望：深层嵌套的敏感字段也被隐藏
        """
        result = sanitize_log_data(sample_log_data)

        assert result["nested"]["deep"]["authorization"] == "****"
        assert result["nested"]["deep"]["other"] == "data"

    def test_case_insensitive_key_matching(self):
        """
        测试：键名匹配应该不区分大小写

        场景：敏感字段使用不同大小写
        期望：所有变体的敏感字段都被隐藏
        """
        data = {
            "Token": "value1",
            "API_KEY": "value2",
            "WebhookSecret": "value3",
        }
        result = sanitize_log_data(data)

        assert result["Token"] == "****"
        assert result["API_KEY"] == "****"
        assert result["WebhookSecret"] == "****"

    def test_custom_sensitive_keys(self):
        """
        测试：支持自定义敏感键集合

        场景：提供自定义的敏感键集合
        期望：只隐藏指定的敏感字段
        """
        data = {
            "custom_key": "secret_value",
            "another_key": "public_value",
            "token": "token_value",  # 默认敏感字段
        }
        custom_keys = {"custom_key"}

        result = sanitize_log_data(data, sensitive_keys=custom_keys)

        assert result["custom_key"] == "****"
        assert result["another_key"] == "public_value"
        assert result["token"] == "token_value"  # 未在自定义集合中

    def test_empty_dict_returns_empty(self):
        """
        测试：空字典应该返回空字典

        场景：输入为空字典
        期望：返回空字典
        """
        result = sanitize_log_data({})
        assert result == {}

    def test_list_values_preserved(self):
        """
        测试：列表值应该保留

        场景：数据包含列表类型的值
        期望：列表内容保持不变
        """
        data = {
            "tags": ["bug", "enhancement"],
            "token": "secret",
        }
        result = sanitize_log_data(data)

        assert result["tags"] == ["bug", "enhancement"]
        assert result["token"] == "****"

    def test_numeric_values_preserved(self):
        """
        测试：数值应该保留

        场景：数据包含整型和浮点型值
        期望：数值保持不变
        """
        data = {
            "count": 42,
            "price": 19.99,
            "secret": "hidden",
        }
        result = sanitize_log_data(data)

        assert result["count"] == 42
        assert result["price"] == 19.99
        assert result["secret"] == "****"

    def test_none_values_preserved(self):
        """
        测试：None 值应该保留

        场景：某些字段的值为 None
        期望：None 值保持不变
        """
        data = {
            "optional_field": None,
            "token": "secret",
        }
        result = sanitize_log_data(data)

        assert result["optional_field"] is None
        assert result["token"] == "****"

    def test_mixed_case_sensitive_keys(self):
        """
        测试：混合大小写的敏感键匹配

        场景：敏感键包含大小写混合
        期望：正确识别并隐藏
        """
        data = {
            "Authorization": "Bearer token",
            "WebHook_Secret": "wh_secret",
            "API_KEY": "api_key",
        }
        result = sanitize_log_data(data)

        assert result["Authorization"] == "****"
        assert result["WebHook_Secret"] == "****"
        assert result["API_KEY"] == "****"

    def test_partial_key_matching(self):
        """
        测试：敏感键的部分匹配

        场景：键名包含敏感词作为子串
        期望：包含敏感词的键都被隐藏
        """
        data = {
            "access_token": "token_value",
            "refresh_token": "refresh_value",
            "token_type": "Bearer",
            "my_token_field": "my_value",
        }
        result = sanitize_log_data(data)

        # 所有包含 "token" 的键都应该被隐藏
        assert result["access_token"] == "****"
        assert result["refresh_token"] == "****"
        assert result["token_type"] == "****"
        assert result["my_token_field"] == "****"

    def test_boolean_values_preserved(self):
        """
        测试：布尔值应该保留

        场景：数据包含布尔类型的值
        期望：布尔值保持不变
        """
        data = {
            "is_active": True,
            "is_deleted": False,
            "secret": "hidden",
        }
        result = sanitize_log_data(data)

        assert result["is_active"] is True
        assert result["is_deleted"] is False
        assert result["secret"] == "****"
