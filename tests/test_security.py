"""
Webhook 签名安全测试 - P0 级别

测试 GitHub Webhook 签名验证的各种攻击场景，包括：
- 签名伪造攻击
- 签名重放攻击
- 签名篡改攻击
- 时序攻击
- 边界条件和极端情况
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from app.utils.validators import (
    _calculate_signature,
    verify_webhook_signature,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def webhook_secret():
    """测试用的 webhook 密钥"""
    return "test_webhook_secret_12345"


@pytest.fixture
def valid_payload():
    """有效的 webhook payload"""
    return b'{"action": "labeled", "issue": {"id": 123, "number": 456}}'


@pytest.fixture
def valid_signature(valid_payload, webhook_secret):
    """有效的签名"""
    return _calculate_signature(valid_payload, webhook_secret)


# =============================================================================
# 签名伪造攻击测试
# =============================================================================


class TestSignatureForgeryAttacks:
    """测试签名伪造攻击防护"""

    def test_forged_signature_rejected(self, valid_payload, webhook_secret):
        """
        测试：伪造的签名应该被拒绝

        场景：攻击者尝试随机生成一个伪造的签名
        期望：验证失败，返回 False
        严重性：P0 - 关键安全漏洞
        """
        forged_signature = "sha256=" + "a" * 64

        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header=forged_signature,
            secret=webhook_secret,
        )

        assert result is False, "伪造的签名应该被拒绝"

    def test_signature_with_wrong_secret_rejected(
        self, valid_payload, webhook_secret
    ):
        """
        测试：使用错误密钥生成的签名应该被拒绝

        场景：攻击者不知道正确的 webhook 密钥，使用自己的密钥生成签名
        期望：验证失败
        严重性：P0 - 密钥泄露防护
        """
        wrong_secret = "wrong_secret_key"
        forged_signature = _calculate_signature(valid_payload, wrong_secret)

        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header=forged_signature,
            secret=webhook_secret,
        )

        assert result is False, "使用错误密钥的签名应该被拒绝"

    @pytest.mark.parametrize(
        "forged_sig",
        [
            "sha256=0000000000000000000000000000000000000000000000000000000000000000",
            "sha256=ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "sha256=" + "0" * 64,
            "sha256=" + "f" * 64,
        ],
    )
    def test_common_forged_patterns_rejected(
        self, forged_sig, valid_payload, webhook_secret
    ):
        """
        测试：常见的伪造签名模式应该被拒绝

        场景：测试一些常见的、容易被猜到的签名模式
        期望：全部被拒绝
        严重性：P0
        """
        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header=forged_sig,
            secret=webhook_secret,
        )

        assert result is False, f"伪造签名模式 {forged_sig[:20]}... 应该被拒绝"


# =============================================================================
# 签名重放攻击测试
# =============================================================================


class TestSignatureReplayAttacks:
    """测试签名重放攻击防护"""

    def test_replay_attack_detected(
        self, valid_payload, valid_signature, webhook_secret
    ):
        """
        测试：重放攻击检测（基础）

        注意：当前实现可能没有时间戳检查，但需要记录这个潜在风险
        场景：攻击者捕获并重放之前的合法请求
        期望：验证通过（当前实现），但应该记录风险
        严重性：P0 - 需要额外的防护机制
        """
        # 模拟重放：使用相同的 payload 和签名
        result1 = verify_webhook_signature(
            payload=valid_payload,
            signature_header=valid_signature,
            secret=webhook_secret,
        )

        result2 = verify_webhook_signature(
            payload=valid_payload,
            signature_header=valid_signature,
            secret=webhook_secret,
        )

        # 当前实现会两次都通过（因为没有时间戳检查）
        # 这是潜在的安全风险，需要在生产环境中添加 nonce/timestamp 机制
        assert result1 is True
        assert result2 is True
        # TODO: 实现时间戳验证机制来防护重放攻击

    def test_payload_tampering_in_replay(
        self, valid_payload, webhook_secret
    ):
        """
        测试：重放时篡改 payload 应该被检测

        场景：攻击者重放请求但修改了 payload 内容
        期望：验证失败
        严重性：P0
        """
        original_signature = _calculate_signature(valid_payload, webhook_secret)

        # 篡改 payload
        tampered_payload = b'{"action": "unlabeled", "issue": {"id": 999}}'

        result = verify_webhook_signature(
            payload=tampered_payload,
            signature_header=original_signature,
            secret=webhook_secret,
        )

        assert result is False, "篡改后的 payload 重放应该被拒绝"

    @pytest.mark.parametrize(
        "tamper_func",
        [
            lambda p: p[:-1] + b"x",  # 修改最后一个字符
            lambda p: p + b"\x00",  # 添加空字节
            lambda p: b"x" + p[1:],  # 修改第一个字符
            lambda p: p.replace(b"labeled", b"unlabeled"),  # 修改关键字段
        ],
    )
    def test_various_payload_tampering_detected(
        self, tamper_func, valid_payload, webhook_secret
    ):
        """
        测试：各种 payload 篡改方式都应该被检测

        场景：使用不同的方法篡改 payload
        期望：全部被拒绝
        严重性：P0
        """
        original_signature = _calculate_signature(valid_payload, webhook_secret)
        tampered_payload = tamper_func(valid_payload)

        result = verify_webhook_signature(
            payload=tampered_payload,
            signature_header=original_signature,
            secret=webhook_secret,
        )

        assert result is False


# =============================================================================
# 签名篡改攻击测试
# =============================================================================


class TestSignatureTamperingAttacks:
    """测试签名篡改攻击防护"""

    def test_signature_bit_flip_rejected(self, valid_payload, webhook_secret):
        """
        测试：签名位翻转攻击应该被拒绝

        场景：修改签名的某些位，尝试生成有效的签名
        期望：验证失败
        严重性：P0
        """
        valid_signature = _calculate_signature(valid_payload, webhook_secret)

        # 位翻转：将最后一个字符从 'f' 改为 'e'
        tampered_signature = valid_signature[:-1] + "e"

        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header=tampered_signature,
            secret=webhook_secret,
        )

        assert result is False, "位翻转的签名应该被拒绝"

    def test_signature_prefix_tampering_rejected(
        self, valid_payload, webhook_secret
    ):
        """
        测试：签名前缀篡改应该被拒绝

        场景：修改签名的 "sha256=" 前缀
        期望：验证失败
        严重性：P0
        """
        valid_signature = _calculate_signature(valid_payload, webhook_secret)

        # 尝试不同的前缀
        tampered_prefixes = [
            "sha1=" + valid_signature[7:],  # 错误的算法
            "SHA256=" + valid_signature[7:],  # 大写（如果验证区分大小写）
            "md5=" + valid_signature[7:],  # 完全不同的算法
        ]

        for tampered_sig in tampered_prefixes:
            result = verify_webhook_signature(
                payload=valid_payload,
                signature_header=tampered_sig,
                secret=webhook_secret,
            )

            assert (
                result is False
            ), f"篡改前缀的签名 {tampered_sig[:10]}... 应该被拒绝"

    def test_signature_length_tampering_rejected(
        self, valid_payload, webhook_secret
    ):
        """
        测试：签名长度篡改应该被拒绝

        场景：修改签名的长度
        期望：验证失败
        严重性：P0
        """
        valid_signature = _calculate_signature(valid_payload, webhook_secret)

        # 截断签名
        truncated_sig = valid_signature[:50]
        result1 = verify_webhook_signature(
            payload=valid_payload,
            signature_header=truncated_sig,
            secret=webhook_secret,
        )
        assert result1 is False, "截断的签名应该被拒绝"

        # 扩展签名
        extended_sig = valid_signature + "a" * 10
        result2 = verify_webhook_signature(
            payload=valid_payload,
            signature_header=extended_sig,
            secret=webhook_secret,
        )
        assert result2 is False, "扩展的签名应该被拒绝"


# =============================================================================
# 空签名/None 测试
# =============================================================================


class TestEmptyOrNoneSignature:
    """测试空签名或缺失签名的场景"""

    def test_none_signature_rejected(self, valid_payload, webhook_secret):
        """
        测试：None 签名应该被拒绝

        场景：请求中没有签名头部
        期望：返回 False
        严重性：P0
        """
        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header=None,
            secret=webhook_secret,
        )

        assert result is False

    def test_empty_string_signature_rejected(
        self, valid_payload, webhook_secret
    ):
        """
        测试：空字符串签名应该被拒绝

        场景：签名头部为空字符串
        期望：返回 False
        严重性：P0
        """
        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header="",
            secret=webhook_secret,
        )

        assert result is False

    def test_whitespace_only_signature_rejected(
        self, valid_payload, webhook_secret
    ):
        """
        测试：仅包含空格的签名应该被拒绝

        场景：签名头部只包含空格字符
        期望：返回 False
        严重性：P0
        """
        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header="   ",
            secret=webhook_secret,
        )

        assert result is False

    @pytest.mark.parametrize(
        "invalid_sig",
        [
            "sha256=",  # 只有前缀，没有签名值
            "sha256=   ",  # 前缀加空格
            "sha256=\n\t",  # 前缀加换行符和制表符
        ],
    )
    def test_signature_without_hash_rejected(
        self, invalid_sig, valid_payload, webhook_secret
    ):
        """
        测试：没有哈希值的签名应该被拒绝

        场景：签名格式正确但没有实际的哈希值
        期望：返回 False
        严重性：P0
        """
        result = verify_webhook_signature(
            payload=valid_payload,
            signature_header=invalid_sig,
            secret=webhook_secret,
        )

        assert result is False


# =============================================================================
# 时序攻击防护测试
# =============================================================================


class TestTimingAttackProtection:
    """测试时序攻击防护机制"""

    def test_constant_time_comparison_used(
        self, valid_payload, valid_signature, webhook_secret
    ):
        """
        测试：应该使用恒定时间比较

        场景：验证 hmac.compare_digest 是否被使用
        期望：使用恒定时间比较，防止通过时间差推断签名
        严重性：P1 - 重要安全特性
        """
        with patch("hmac.compare_digest") as mock_compare:
            mock_compare.return_value = False

            verify_webhook_signature(
                payload=valid_payload,
                signature_header=valid_signature,
                secret=webhook_secret,
            )

            # 验证使用了 hmac.compare_digest
            mock_compare.assert_called_once()

    def test_timing_consistency(self, valid_payload, webhook_secret):
        """
        测试：验证时间应该一致，不因签名不同而有显著差异

        场景：测量不同签名验证的时间
        期望：时间差异在可接受范围内（< 1ms）
        严重性：P1
        """
        # 生成有效和无效签名
        valid_signature = _calculate_signature(valid_payload, webhook_secret)
        invalid_signature = "sha256=" + "0" * 64

        # 预热
        for _ in range(10):
            verify_webhook_signature(
                payload=valid_payload,
                signature_header=valid_signature,
                secret=webhook_secret,
            )

        # 测量有效签名验证时间
        iterations = 100
        start_valid = time.perf_counter()
        for _ in range(iterations):
            verify_webhook_signature(
                payload=valid_payload,
                signature_header=valid_signature,
                secret=webhook_secret,
            )
        end_valid = time.perf_counter()
        valid_time = (end_valid - start_valid) / iterations

        # 测量无效签名验证时间
        start_invalid = time.perf_counter()
        for _ in range(iterations):
            verify_webhook_signature(
                payload=valid_payload,
                signature_header=invalid_signature,
                secret=webhook_secret,
            )
        end_invalid = time.perf_counter()
        invalid_time = (end_invalid - start_invalid) / iterations

        # 时间差异应该很小（< 1ms）
        time_diff = abs(valid_time - invalid_time) * 1000  # 转换为毫秒

        assert (
            time_diff < 1.0
        ), f"时间差异过大: {time_diff:.3f}ms，可能存在时序攻击风险"


# =============================================================================
# 密钥安全测试
# =============================================================================


class TestSecretSecurity:
    """测试密钥安全"""

    def test_secret_not_exposed_in_logs(
        self, valid_payload, valid_signature, webhook_secret, caplog
    ):
        """
        测试：密钥不应该暴露在日志中

        场景：验证失败时检查日志输出
        期望：日志中不包含 webhook 密钥
        严重性：P0
        """
        with caplog.at_level("ERROR"):
            verify_webhook_signature(
                payload=valid_payload,
                signature_header="invalid_signature",
                secret=webhook_secret,
            )

        # 检查日志中不包含密钥
        for record in caplog.records:
            assert webhook_secret not in record.message, "密钥不应该出现在日志中"
            # 签名的哈希值部分可以出现（因为已经是哈希）
            # 但原始密钥绝对不应该出现

    def test_empty_secret_rejected(self, valid_payload):
        """
        测试：空密钥应该被拒绝或抛出异常

        场景：webhook_secret 为空字符串
        期望：抛出 ValueError 或返回 False
        严重性：P0
        """
        with pytest.raises(ValueError):
            verify_webhook_signature(
                payload=valid_payload,
                signature_header="sha256=" + "a" * 64,
                secret="",
            )

    def test_weak_secret_detection_warning(self, valid_payload):
        """
        测试：检测弱密钥（警告级别）

        场景：使用明显弱小的密钥（如 "secret", "password"）
        注意：当前实现可能不检测，但应该记录建议
        期望：至少验证能正常工作
        严重性：P2 - 安全建议
        """
        weak_secrets = ["secret", "password", "123456", "test"]

        for weak_secret in weak_secrets:
            signature = _calculate_signature(valid_payload, weak_secret)

            # 验证应该能工作（虽然密钥很弱）
            result = verify_webhook_signature(
                payload=valid_payload,
                signature_header=signature,
                secret=weak_secret,
            )

            assert result is True

            # TODO: 添加密钥强度检测和警告


# =============================================================================
# 并发和竞态条件测试
# =============================================================================


class TestConcurrencyAndRaceConditions:
    """测试并发场景和竞态条件"""

    def test_concurrent_verification_thread_safety(
        self, valid_payload, valid_signature, webhook_secret
    ):
        """
        测试：并发验证应该是线程安全的

        场景：多个线程同时验证签名
        期望：所有验证都正确完成
        严重性：P1
        """
        import threading

        results = []
        errors = []

        def verify():
            try:
                result = verify_webhook_signature(
                    payload=valid_payload,
                    signature_header=valid_signature,
                    secret=webhook_secret,
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = [threading.Thread(target=verify) for _ in range(50)]

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发验证出现错误: {errors}"
        assert len(results) == 50
        assert all(results), "所有验证都应该成功"


# =============================================================================
# 边界条件和极端情况
# =============================================================================


class TestEdgeCases:
    """测试边界条件和极端情况"""

    def test_very_large_payload(self, webhook_secret):
        """
        测试：非常大的 payload（10MB）

        场景：处理大型 webhook payload
        期望：正确处理，没有性能问题或内存泄漏
        严重性：P1
        """
        # 创建 10MB payload
        large_payload = b'{"data": "' + b"x" * (10 * 1024 * 1024) + b'"}'
        signature = _calculate_signature(large_payload, webhook_secret)

        result = verify_webhook_signature(
            payload=large_payload,
            signature_header=signature,
            secret=webhook_secret,
        )

        assert result is True

    def test_unicode_payload(self, webhook_secret):
        """
        测试：包含各种 Unicode 字符的 payload

        场景：payload 包含 emoji、多语言文本等
        期望：正确处理
        严重性：P1
        """
        unicode_payload = '{"emoji": "😀🎉", "chinese": "中文", "arabic": "العربية"}'.encode()

        signature = _calculate_signature(unicode_payload, webhook_secret)

        result = verify_webhook_signature(
            payload=unicode_payload,
            signature_header=signature,
            secret=webhook_secret,
        )

        assert result is True

    def test_special_characters_in_secret(self, valid_payload):
        """
        测试：密钥包含特殊字符

        场景：密钥包含各种特殊字符
        期望：正确处理
        严重性：P1
        """
        special_secrets = [
            "secret!@#$%^&*()",
            "secret\n\t\r",
            "secret\u200b\u200c\u200d",  # 零宽字符
            "秘钥中文密码",  # 非ASCII字符
        ]

        for secret in special_secrets:
            signature = _calculate_signature(valid_payload, secret)

            result = verify_webhook_signature(
                payload=valid_payload,
                signature_header=signature,
                secret=secret,
            )

            assert result is True, f"密钥 {secret[:10]}... 验证失败"
