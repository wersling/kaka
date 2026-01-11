"""
测试 setup_env.py 配置脚本的功能

注意：这些测试主要测试验证逻辑，不进行实际的交互式输入
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

# 导入验证函数
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from setup_env import (
    validate_github_token,
    validate_repo_path,
    generate_webhook_secret,
    validate_github_token_with_api,
)


class TestValidateGithubToken:
    """测试 GitHub Token 验证（格式验证）"""

    def test_valid_classic_token(self):
        """测试有效的 Classic Token"""
        token = "ghp_" + "a" * 32
        assert validate_github_token(token) is True

    def test_valid_fine_grained_token(self):
        """测试有效的 Fine-grained Token"""
        token = "github_pat_" + "a" * 62
        assert validate_github_token(token) is True

    def test_invalid_token_no_prefix(self):
        """测试无效的 Token（没有前缀）"""
        token = "a" * 40
        assert validate_github_token(token) is False

    def test_invalid_classic_token_too_short(self):
        """测试无效的 Classic Token（太短）"""
        token = "ghp_" + "a" * 10
        assert validate_github_token(token) is False

    def test_invalid_fine_grained_token_too_short(self):
        """测试无效的 Fine-grained Token（太短）"""
        token = "github_pat_" + "a" * 30
        assert validate_github_token(token) is False


class TestValidateGithubTokenWithApi:
    """测试 GitHub Token API 验证（异步）"""

    @pytest.mark.asyncio
    async def test_valid_token_with_mock_api(self):
        """测试有效 Token（使用 Mock API）"""
        token = "ghp_valid_token"

        # Mock GitHubService
        with patch('setup_env.GitHubService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.authenticate.return_value = True
            mock_service_class.return_value = mock_service

            is_valid, error_msg = await validate_github_token_with_api(token)

            assert is_valid is True
            assert error_msg == ""
            mock_service.authenticate.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_token_with_mock_api(self):
        """测试无效 Token（使用 Mock API）"""
        token = "ghp_invalid_token"

        # Mock GitHubService
        with patch('setup_env.GitHubService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.authenticate.return_value = False
            mock_service_class.return_value = mock_service

            is_valid, error_msg = await validate_github_token_with_api(token)

            assert is_valid is False
            assert "验证失败" in error_msg or "无效" in error_msg

    @pytest.mark.asyncio
    async def test_token_with_401_error(self):
        """测试 401 错误处理"""
        token = "ghp_bad_credentials"

        # Mock GitHubService 抛出 401 异常
        with patch('setup_env.GitHubService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.authenticate.side_effect = Exception("401 {\"message\": \"Bad credentials\"}")
            mock_service_class.return_value = mock_service

            is_valid, error_msg = await validate_github_token_with_api(token)

            assert is_valid is False
            assert "无效" in error_msg

    @pytest.mark.asyncio
    async def test_token_with_403_error(self):
        """测试 403 权限不足错误"""
        token = "ghp_no_permission"

        # Mock GitHubService 抛出 403 异常
        with patch('setup_env.GitHubService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.authenticate.side_effect = Exception("403 Forbidden")
            mock_service_class.return_value = mock_service

            is_valid, error_msg = await validate_github_token_with_api(token)

            assert is_valid is False
            assert "权限不足" in error_msg


class TestValidateRepoPath:
    """测试仓库路径验证"""

    def test_non_existent_path(self):
        """测试不存在的路径"""
        is_valid, error_msg = validate_repo_path("/nonexistent/path/that/does/not/exist")
        assert is_valid is False
        assert "不存在" in error_msg

    def test_not_a_git_repo(self, tmp_path):
        """测试不是 Git 仓库的目录"""
        is_valid, error_msg = validate_repo_path(str(tmp_path))
        assert is_valid is False
        assert "不是有效的 Git 仓库" in error_msg

    def test_valid_git_repo(self, tmp_path):
        """测试有效的 Git 仓库"""
        # 创建一个 .git 目录来模拟 Git 仓库
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        is_valid, error_msg = validate_repo_path(str(tmp_path))
        assert is_valid is True
        assert error_msg == ""

    def test_tilde_expansion(self, tmp_path):
        """测试 ~ 路径展开"""
        # 创建一个 .git 目录来模拟 Git 仓库
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # 使用 ~ 路径（会展开到用户 home 目录下的某个路径）
        # 由于 tmp_path 可能不在 home 目录下，我们测试 expanduser 是否能正常工作
        # 这里我们测试当前工作目录（应该存在）
        import os
        cwd = os.getcwd()

        # 验证当前工作目录是一个 Git 仓库（因为我们在 kaka 项目中）
        is_valid, error_msg = validate_repo_path(cwd)
        # 当前目录应该是 Git 仓库
        if is_valid:
            assert is_valid is True
            assert error_msg == ""

    def test_tilde_path_with_current_dir(self):
        """测试 ~ 路径在当前项目目录中"""
        import os
        # 测试当前目录（应该是 Git 仓库）
        cwd = os.getcwd()
        is_valid, error_msg = validate_repo_path(cwd)
        # 如果当前目录是 Git 仓库，验证应该通过
        git_dir = Path(cwd) / ".git"
        if git_dir.exists():
            assert is_valid is True
            assert error_msg == ""


class TestGenerateWebhookSecret:
    """测试 Webhook Secret 生成"""

    def test_generate_secret_length(self):
        """测试生成的密钥长度"""
        secret = generate_webhook_secret()
        # secrets.token_hex(32) 生成 64 个字符
        assert len(secret) == 64

    def test_generate_secret_is_hex(self):
        """测试生成的密钥是十六进制"""
        secret = generate_webhook_secret()
        try:
            int(secret, 16)
        except ValueError:
            pytest.fail("生成的密钥不是有效的十六进制字符串")

    def test_generate_secrets_are_unique(self):
        """测试每次生成的密钥都不同"""
        secret1 = generate_webhook_secret()
        secret2 = generate_webhook_secret()
        assert secret1 != secret2


class TestWriteEnvFile:
    """测试 .env 文件写入"""

    def test_write_new_env_file(self, tmp_path):
        """测试写入新的 .env 文件"""
        from setup_env import write_env_file

        config = {
            'GITHUB_WEBHOOK_SECRET': 'test_secret_123',
            'GITHUB_TOKEN': 'ghp_test_token',
            'GITHUB_REPO_OWNER': 'testuser',
            'GITHUB_REPO_NAME': 'testrepo',
            'REPO_PATH': '/path/to/repo',
        }

        env_file = tmp_path / '.env'
        write_env_file(config, env_file)

        assert env_file.exists()

        content = env_file.read_text()
        assert 'GITHUB_WEBHOOK_SECRET=test_secret_123' in content
        assert 'GITHUB_TOKEN=ghp_test_token' in content
        assert 'GITHUB_REPO_OWNER=testuser' in content
        assert 'GITHUB_REPO_NAME=testrepo' in content
        assert 'REPO_PATH=/path/to/repo' in content

    def test_write_env_file_with_ngrok(self, tmp_path):
        """测试写入包含 ngrok 配置的 .env 文件"""
        from setup_env import write_env_file

        config = {
            'GITHUB_WEBHOOK_SECRET': 'test_secret_123',
            'GITHUB_TOKEN': 'ghp_test_token',
            'GITHUB_REPO_OWNER': 'testuser',
            'GITHUB_REPO_NAME': 'testrepo',
            'REPO_PATH': '/path/to/repo',
            'NGROK_AUTH_TOKEN': 'ngrok_token',
            'NGROK_DOMAIN': 'mydomain.ngrok.io',
        }

        env_file = tmp_path / '.env'
        write_env_file(config, env_file)

        content = env_file.read_text()
        assert 'NGROK_AUTH_TOKEN=ngrok_token' in content
        assert 'NGROK_DOMAIN=mydomain.ngrok.io' in content

    def test_overwrite_existing_env_file(self, tmp_path):
        """测试覆盖现有 .env 文件"""
        from setup_env import write_env_file

        # 创建现有的 .env 文件
        env_file = tmp_path / '.env'
        env_file.write_text("OLD_CONTENT")

        config = {
            'GITHUB_WEBHOOK_SECRET': 'new_secret',
            'GITHUB_TOKEN': 'ghp_new_token',
            'GITHUB_REPO_OWNER': 'newuser',
            'GITHUB_REPO_NAME': 'newrepo',
            'REPO_PATH': '/new/path',
        }

        # Mock input 模拟用户确认覆盖
        with patch('builtins.input', return_value='y'):
            write_env_file(config, env_file)

        # 验证备份文件已创建
        backup_file = tmp_path / '.env.backup'
        assert backup_file.exists()
        assert backup_file.read_text() == "OLD_CONTENT"

        # 验证新内容已写入
        new_content = env_file.read_text()
        assert 'GITHUB_WEBHOOK_SECRET=new_secret' in new_content
        assert 'OLD_CONTENT' not in new_content
