"""
Pytest 配置文件

配置测试 fixtures 和插件
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.config import Config, GitHubConfig, RepositoryConfig


# =============================================================================
# Pytest 配置
# =============================================================================


def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line("markers", "asyncio: mark test as async")


# =============================================================================
# 异步客户端 fixture
# =============================================================================


@pytest.fixture
async def async_client():
    """提供异步测试客户端"""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# =============================================================================
# 测试配置 fixture
# =============================================================================


@pytest.fixture
def test_config():
    """
    提供测试用的配置对象

    使用虚拟值避免依赖真实的环境变量和配置文件
    """
    # 创建临时目录作为测试仓库路径
    import tempfile
    import git

    temp_dir = tempfile.mkdtemp()

    # 先初始化 Git 仓库
    try:
        repo = git.Repo.init(temp_dir)
        # 配置仓库
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # 创建初始提交
        test_file = Path(temp_dir) / "README.md"
        test_file.write_text("# Test Repository\n")

        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")
    except Exception:
        pass

    config = Config(
        github=GitHubConfig(
            webhook_secret="test_secret_12345",
            token="ghp_test_token_12345",
            repo_owner="testowner",
            repo_name="testrepo",
            trigger_label="ai-dev",
            trigger_command="/ai develop",
        ),
        repository=RepositoryConfig(
            path=Path(temp_dir),
            default_branch="main",
            remote_name="origin",
        ),
    )

    return config


@pytest.fixture
def mock_config(test_config):
    """
    Mock 配置加载，使用测试配置

    在测试中使用这个 fixture 来避免依赖真实配置
    """
    with patch("app.config.get_config", return_value=test_config):
        with patch("app.config.load_config", return_value=test_config):
            yield test_config


# =============================================================================
# Mock 外部服务 fixture
# =============================================================================


@pytest.fixture
def mock_env_vars():
    """
    设置测试环境变量

    提供测试所需的环境变量，避免测试失败
    """
    import os

    env_vars = {
        "GITHUB_WEBHOOK_SECRET": "test_secret_12345",
        "GITHUB_TOKEN": "ghp_test_token_12345",
        "GITHUB_REPO_OWNER": "testowner",
        "GITHUB_REPO_NAME": "testrepo",
        "REPO_PATH": "/tmp/test_repo",
        "ANTHROPIC_API_KEY": "sk-ant-test-key-12345",
    }

    # 设置环境变量
    old_env = {}
    for key, value in env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield env_vars

    # 恢复原始环境变量
    for key, old_value in old_env.items():
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value


# =============================================================================
# 自动应用 mock
# =============================================================================


@pytest.fixture(autouse=True)
def auto_mock_config(mock_env_vars, mock_config):
    """
    自动应用配置 mock 到所有测试

    这个 fixture 会被自动应用到所有测试函数，
    避免在每个测试中手动 mock 配置
    """
    # mock_config 已经 patch 了 get_config 和 load_config
    # 这里只需要确保 fixture 被加载
    yield


# =============================================================================
# 测试仓库 fixture
# =============================================================================


@pytest.fixture
def test_repo_path():
    """
    创建临时的测试 Git 仓库

    返回临时仓库路径，测试完成后自动清理
    """
    import tempfile
    import shutil
    import git

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="test_repo_")

    try:
        # 初始化 Git 仓库
        repo = git.Repo.init(temp_dir)

        # 配置仓库
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # 创建初始提交
        test_file = Path(temp_dir) / "README.md"
        test_file.write_text("# Test Repository\n")

        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        yield Path(temp_dir)

    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
