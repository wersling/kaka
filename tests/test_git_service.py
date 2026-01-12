"""
GitService 完整单元测试套件

测试覆盖所有 Git 操作功能，包括：
- GitService 初始化
- 分支管理（创建、切换、拉取）
- 提交变更
- 推送到远程
- 状态检查
- 变更管理（丢弃、差异查看）
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import pytest

from app.services.git_service import GitService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """
    提供测试用的配置对象

    Mock 配置对象，包含仓库、任务等配置
    """
    config = MagicMock()
    config.repository.path = Path("/tmp/test_repo")
    config.repository.default_branch = "main"
    config.repository.remote_name = "origin"
    config.task.branch_template = "ai/feature-{issue_number}-{timestamp}"
    return config


@pytest.fixture
def mock_repo():
    """
    提供 Mock 的 Git Repo 对象

    模拟 GitPython 的 Repo 对象
    """
    repo = MagicMock()
    repo.path = Path("/tmp/test_repo")
    repo.remotes = {"origin": MagicMock()}
    repo.heads = {"main": MagicMock()}
    repo.active_branch.name = "main"
    repo.is_dirty.return_value = False
    repo.untracked_files = []
    return repo


@pytest.fixture
def git_service(tmpdir, mock_repo, mock_config):
    """
    提供 GitService 实例，使用 Mock 的 Repo 对象

    不需要真实的 Git 仓库，避免测试时的文件系统操作
    """
    # 创建临时目录用于 repo_path
    test_path = Path(tmpdir) / "test_repo"
    test_path.mkdir()
    (test_path / ".git").mkdir()

    # Patch git.Repo 来返回我们的 mock
    with patch("git.Repo", return_value=mock_repo):
        service = GitService(repo_path=test_path)

    # 保存 mock_repo 和 mock_config 供测试使用
    service._mock_repo = mock_repo
    service._mock_config = mock_config

    yield service

    # 清理
    import shutil

    if test_path.exists():
        shutil.rmtree(test_path)


@pytest.fixture
def git_service_real_repo(tmpdir, mock_config):
    """
    提供使用真实 Git 仓库的 GitService 实例

    创建真实的临时 Git 仓库用于集成测试
    """
    # 初始化真实的 Git 仓库
    repo_path = Path(tmpdir) / "test_repo"
    repo_path.mkdir()
    repo = git.Repo.init(repo_path)

    # 配置 Git
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    # 创建初始提交
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    # 创建 main 分支的 HEAD
    repo.head.reference = repo.heads["main"]

    # 添加远程仓库（使用 dummy URL）
    remote = repo.create_remote("origin", "git@github.com:test/test.git")

    mock_config.repository.path = repo_path

    service = GitService(repo_path=repo_path)
    yield service, repo, repo_path

    # 清理
    import shutil

    if repo_path.exists():
        shutil.rmtree(repo_path)


# =============================================================================
# TestGitServiceInitialization 测试
# =============================================================================


class TestGitServiceInitialization:
    """测试 GitService 初始化"""

    def test_init_with_valid_repo_path(self, tmpdir):
        """
        测试：使用有效的仓库路径初始化应该成功

        场景：提供一个包含 .git 目录的有效路径
        期望：成功创建 GitService 实例
        """
        # 创建临时 Git 仓库
        repo_path = Path(tmpdir) / "valid_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        with patch("git.Repo") as mock_git_repo:
            mock_repo = MagicMock()
            mock_git_repo.return_value = mock_repo

            service = GitService(repo_path=repo_path)

            assert service.repo_path == repo_path
            assert service.repo == mock_repo
            mock_git_repo.assert_called_once_with(repo_path)

    def test_init_with_invalid_path_raises_value_error(self, tmpdir):
        """
        测试：无效路径（不存在 .git 目录）应该抛出 ValueError

        场景：提供一个不包含 .git 目录的路径
        期望：抛出 ValueError，提示不是有效的 Git 仓库
        """
        # 创建临时目录但不初始化 Git
        invalid_path = Path(tmpdir) / "invalid_repo"
        invalid_path.mkdir()

        with pytest.raises(ValueError) as exc_info:
            GitService(repo_path=invalid_path)

        assert "不是有效的 Git 仓库" in str(exc_info.value)

    def test_init_with_nonexistent_path_raises_value_error(self):
        """
        测试：不存在的路径应该抛出 ValueError

        场景：提供一个文件系统中不存在的路径
        期望：抛出 ValueError，提示不是有效的 Git 仓库
        """
        nonexistent_path = Path("/tmp/nonexistent_repo_12345")

        with pytest.raises(ValueError) as exc_info:
            GitService(repo_path=nonexistent_path)

        assert "不是有效的 Git 仓库" in str(exc_info.value)

    def test_init_with_path_expansion(self, tmpdir):
        """
        测试：路径应该展开用户目录（~）并解析为绝对路径

        场景：使用包含 ~ 的路径
        期望：路径被正确展开为绝对路径
        """
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        with patch("git.Repo"):
            service = GitService(repo_path=Path(repo_path))
            # 验证路径被展开和解析
            assert service.repo_path == repo_path

    def test_init_from_config_when_path_not_provided(self, tmpdir):
        """
        测试：未提供路径时应该从配置读取

        场景：repo_path 参数为 None
        期望：从 get_config() 读取仓库路径
        """
        repo_path = Path(tmpdir) / "config_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        config_mock = MagicMock()
        config_mock.repository.path = repo_path

        with patch("git.Repo"):
            with patch("app.config.get_config", return_value=config_mock):
                service = GitService(repo_path=None)
                assert service.repo_path == repo_path

    def test_init_with_git_exception_raises_value_error(self, tmpdir):
        """
        测试：git.Repo 抛出异常时应该转换为 ValueError

        场景：git.Repo 初始化失败
        期望：抛出 ValueError，包含原始错误信息
        """
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        with patch("git.Repo", side_effect=git.GitError("Git command failed")):
            with pytest.raises(ValueError) as exc_info:
                GitService(repo_path=repo_path)

            assert "无法打开 Git 仓库" in str(exc_info.value)
            assert "Git command failed" in str(exc_info.value)


# =============================================================================
# TestCreateFeatureBranch 测试
# =============================================================================


class TestCreateFeatureBranch:
    """测试创建特性分支功能"""

    def test_create_branch_successfully(self, git_service):
        """
        测试：成功创建特性分支

        场景：提供有效的 issue_number
        期望：分支名格式正确，分支被创建并切换
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        # Mock 分支创建和切换
        mock_main_branch = MagicMock()
        mock_new_branch = MagicMock()

        # 存储创建的分支名
        created_branch_name = None

        def mock_create_head(name):
            nonlocal created_branch_name
            created_branch_name = name
            mock_new_branch.name = name
            return mock_new_branch

        mock_repo.create_head.side_effect = mock_create_head

        # 创建动态的 heads mock
        mock_heads_dict = {"main": mock_main_branch}

        def get_head(name):
            if name == "main":
                return mock_main_branch
            elif name == created_branch_name:
                return mock_new_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": MagicMock()}

        with patch("app.config.get_config", return_value=mock_config):
            result_branch_name = git_service.create_feature_branch(issue_number=123)

            # 验证分支名格式
            assert result_branch_name.startswith("ai/feature-123-")
            # 验证创建了分支
            mock_repo.create_head.assert_called_once()
            # 验证切换到新分支
            mock_new_branch.checkout.assert_called_once()

    def test_create_branch_with_custom_base_branch(self, git_service):
        """
        测试：使用自定义基础分支创建特性分支

        场景：提供 base_branch 参数
        期望：基于指定的基础分支创建新分支
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_develop_branch = MagicMock()
        mock_new_branch = MagicMock()

        created_branch_name = None

        def mock_create_head(name):
            nonlocal created_branch_name
            created_branch_name = name
            mock_new_branch.name = name
            return mock_new_branch

        mock_repo.create_head.side_effect = mock_create_head

        mock_heads_dict = {"develop": mock_develop_branch}

        def get_head(name):
            if name == "develop":
                return mock_develop_branch
            elif name == created_branch_name:
                return mock_new_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": MagicMock()}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.create_feature_branch(issue_number=456, base_branch="develop")

            # 验证切换到基础分支
            mock_develop_branch.checkout.assert_called_once()

    def test_create_branch_pulls_latest_code(self, git_service):
        """
        测试：创建分支前应该拉取最新代码

        场景：创建新分支
        期望：在创建前执行 git pull
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_main_branch = MagicMock()
        mock_new_branch = MagicMock()
        mock_origin = MagicMock()

        created_branch_name = None

        def mock_create_head(name):
            nonlocal created_branch_name
            created_branch_name = name
            mock_new_branch.name = name
            return mock_new_branch

        mock_repo.create_head.side_effect = mock_create_head

        def get_head(name):
            if name == "main":
                return mock_main_branch
            elif name == created_branch_name:
                return mock_new_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": mock_origin}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.create_feature_branch(issue_number=789)

            # 验证拉取了最新代码
            mock_origin.pull.assert_called_once_with("main")

    def test_create_branch_checks_out_to_new_branch(self, git_service):
        """
        测试：创建分支后应该切换到新分支

        场景：分支创建成功
        期望：自动切换到新创建的分支
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_main_branch = MagicMock()
        mock_new_branch = MagicMock()

        created_branch_name = None

        def mock_create_head(name):
            nonlocal created_branch_name
            created_branch_name = name
            mock_new_branch.name = name
            return mock_new_branch

        mock_repo.create_head.side_effect = mock_create_head

        def get_head(name):
            if name == "main":
                return mock_main_branch
            elif name == created_branch_name:
                return mock_new_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": MagicMock()}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.create_feature_branch(issue_number=123)

            # 验证切换到新分支
            mock_new_branch.checkout.assert_called_once()

    def test_create_branch_with_timestamp(self, git_service):
        """
        测试：分支名应该包含时间戳

        场景：创建特性分支
        期望：分支名包含当前时间戳，确保唯一性
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_main_branch = MagicMock()
        mock_new_branch = MagicMock()

        # 固定时间戳
        fixed_timestamp = 1234567890

        def mock_create_head(name):
            mock_new_branch.name = name
            return mock_new_branch

        mock_repo.create_head.side_effect = mock_create_head

        def get_head(name):
            if name == "main":
                return mock_main_branch
            elif name == f"ai/feature-123-{fixed_timestamp}":
                return mock_new_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": MagicMock()}

        with patch("time.time", return_value=fixed_timestamp):
            with patch("app.config.get_config", return_value=mock_config):
                result_branch_name = git_service.create_feature_branch(issue_number=123)

                assert result_branch_name == f"ai/feature-123-{fixed_timestamp}"

    def test_create_branch_logs_correctly(self, git_service, caplog):
        """
        测试：创建分支时应该记录正确的日志

        场景：创建分支
        期望：日志包含分支名和基础分支信息
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_main_branch = MagicMock()
        mock_new_branch = MagicMock()

        created_branch_name = None

        def mock_create_head(name):
            nonlocal created_branch_name
            created_branch_name = name
            mock_new_branch.name = name
            return mock_new_branch

        mock_repo.create_head.side_effect = mock_create_head

        def get_head(name):
            if name == "main":
                return mock_main_branch
            elif name == created_branch_name:
                return mock_new_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": MagicMock()}

        with patch("app.config.get_config", return_value=mock_config):
            with caplog.at_level("INFO"):
                git_service.create_feature_branch(issue_number=123)

                # 验证日志输出
                assert any("创建特性分支" in record.message for record in caplog.records)
                assert any("特性分支创建成功" in record.message for record in caplog.records)

    def test_create_branch_exception_handling(self, git_service):
        """
        测试：创建分支失败时应该抛出异常

        场景：git 操作失败
        期望：抛出异常并记录错误日志
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_main_branch = MagicMock()
        mock_main_branch.checkout.side_effect = git.GitError("Checkout failed")

        def get_head(name):
            if name == "main":
                return mock_main_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": MagicMock()}

        with patch("app.config.get_config", return_value=mock_config):
            with pytest.raises(git.GitError):
                git_service.create_feature_branch(issue_number=123)

    def test_create_branch_with_pull_failure(self, git_service):
        """
        测试：拉取最新代码失败时应该抛出异常

        场景：pull 操作失败
        期望：抛出异常并记录错误
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_main_branch = MagicMock()
        mock_origin = MagicMock()
        mock_origin.pull.side_effect = git.GitError("Pull failed")

        def get_head(name):
            if name == "main":
                return mock_main_branch
            raise KeyError(name)

        mock_repo.heads = MagicMock()
        mock_repo.heads.__getitem__ = lambda self, name: get_head(name)
        mock_repo.remotes = {"origin": mock_origin}

        with patch("app.config.get_config", return_value=mock_config):
            with pytest.raises(git.GitError):
                git_service.create_feature_branch(issue_number=123)


# =============================================================================
# TestCommitChanges 测试
# =============================================================================


class TestCommitChanges:
    """测试提交变更功能"""

    def test_commit_with_changes_successfully(self, git_service):
        """
        测试：有变更时应该成功提交

        场景：工作区有未提交的变更
        期望：返回 True，提交成功
        """
        mock_repo = git_service._mock_repo

        # Mock 有变更
        mock_repo.is_dirty.return_value = True
        mock_repo.index.diff.return_value = [MagicMock()]  # 有暂存的变更
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123def456"
        mock_repo.index.commit.return_value = mock_commit

        result = git_service.commit_changes(message="Test commit")

        assert result is True
        mock_repo.index.commit.assert_called_once_with("Test commit")

    def test_commit_without_changes_returns_false(self, git_service):
        """
        测试：无变更时应该返回 False

        场景：工作区干净，没有未提交的变更
        期望：返回 False，不执行提交
        """
        mock_repo = git_service._mock_repo

        # Mock 无变更
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []

        result = git_service.commit_changes(message="Test commit")

        assert result is False
        mock_repo.index.commit.assert_not_called()

    def test_commit_with_add_all_flag(self, git_service):
        """
        测试：add_all=True 应该添加所有变更

        场景：设置 add_all=True
        期望：调用 git add 添加所有变更
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = ["new_file.txt"]
        mock_repo.index.diff.return_value = [MagicMock()]
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.index.commit.return_value = mock_commit

        git_service.commit_changes(message="Add files", add_all=True)

        # 验证添加了文件
        mock_repo.index.add.assert_called()

    def test_commit_without_add_all_flag(self, git_service):
        """
        测试：add_all=False 不应该自动添加变更

        场景：设置 add_all=False
        期望：不调用 git add
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = True
        mock_repo.index.diff.return_value = [MagicMock()]
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.index.commit.return_value = mock_commit

        git_service.commit_changes(message="Commit without add", add_all=False)

        # 验证没有调用 add
        mock_repo.index.add.assert_not_called()

    def test_commit_with_untracked_files(self, git_service):
        """
        测试：应该添加未跟踪的文件

        场景：有未跟踪的文件
        期望：未跟踪的文件被添加到索引
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = ["new_file.py", "another_file.txt"]
        mock_repo.index.diff.return_value = [MagicMock()]
        mock_commit = MagicMock()
        mock_commit.hexsha = "def456"
        mock_repo.index.commit.return_value = mock_commit

        git_service.commit_changes(message="Add new files", add_all=True)

        # 验证添加了未跟踪的文件
        assert mock_repo.index.add.call_count >= 2

    def test_commit_with_untracked_file_add_failure(self, git_service):
        """
        测试：添加未跟踪文件失败时应该忽略并继续

        场景：某些未跟踪文件无法添加
        期望：忽略错误，继续处理其他文件
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = ["good_file.py", "bad_file.py"]

        # Mock add 方法，对 bad_file.py 抛出异常
        def mock_add_side_effect(files):
            if "bad_file.py" in str(files):
                raise Exception("Cannot add file")

        mock_repo.index.add.side_effect = mock_add_side_effect
        mock_repo.index.diff.return_value = [MagicMock()]
        mock_commit = MagicMock()
        mock_commit.hexsha = "xyz789"
        mock_repo.index.commit.return_value = mock_commit

        # 不应该抛出异常
        result = git_service.commit_changes(message="Add files", add_all=True)
        assert result is True
        mock_repo.index.commit.assert_called_once()

    def test_commit_with_correct_message(self, git_service):
        """
        测试：提交消息应该正确传递

        场景：提供提交消息
        期望：commit 使用正确的消息
        """
        mock_repo = git_service._mock_repo

        test_message = "Feat: Add new feature"
        mock_repo.is_dirty.return_value = True
        mock_repo.index.diff.return_value = [MagicMock()]
        mock_commit = MagicMock()
        mock_commit.hexsha = "xyz789"
        mock_repo.index.commit.return_value = mock_commit

        git_service.commit_changes(message=test_message)

        mock_repo.index.commit.assert_called_once_with(test_message)

    def test_commit_without_staged_changes_returns_false(self, git_service):
        """
        测试：无暂存变更时应该返回 False

        场景：添加后没有暂存的变更
        期望：返回 False，不执行提交
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = True
        mock_repo.index.diff.return_value = []  # 无暂存变更

        result = git_service.commit_changes(message="Test commit", add_all=True)

        assert result is False
        mock_repo.index.commit.assert_not_called()

    def test_commit_logs_correctly(self, git_service, caplog):
        """
        测试：提交时应该记录正确的日志

        场景：执行提交
        期望：日志包含提交信息和简短哈希
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = True
        mock_repo.index.diff.return_value = [MagicMock()]
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123def456"
        mock_repo.index.commit.return_value = mock_commit

        with caplog.at_level("INFO"):
            git_service.commit_changes(message="Test commit")

            # 验证日志包含提交哈希前7位
            assert any("abc123d" in record.message for record in caplog.records)
            assert any("Test commit" in record.message for record in caplog.records)

    def test_commit_exception_handling(self, git_service):
        """
        测试：提交失败时应该抛出异常

        场景：git commit 操作失败
        期望：抛出异常并记录错误日志
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = True
        mock_repo.index.diff.return_value = [MagicMock()]
        mock_repo.index.commit.side_effect = git.GitError("Commit failed")

        with pytest.raises(git.GitError):
            git_service.commit_changes(message="Test commit")


# =============================================================================
# TestPushToRemote 测试
# =============================================================================


class TestPushToRemote:
    """测试推送到远程功能"""

    def test_push_successfully(self, git_service):
        """
        测试：成功推送到远程

        场景：推送当前分支
        期望：调用 push 并成功
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_push_info = MagicMock()
        mock_push_info.flags = 0  # 无错误标志
        mock_remote.push.return_value = [mock_push_info]
        mock_repo.remotes = {"origin": mock_remote}
        mock_repo.active_branch.name = "feature-branch"

        with patch("app.config.get_config", return_value=mock_config):
            git_service.push_to_remote()

            mock_remote.push.assert_called_once_with("feature-branch", force=False)

    def test_push_specific_branch(self, git_service):
        """
        测试：推送指定分支

        场景：提供 branch_name 参数
        期望：推送指定的分支而不是当前分支
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_push_info = MagicMock()
        mock_push_info.flags = 0
        mock_remote.push.return_value = [mock_push_info]
        mock_repo.remotes = {"origin": mock_remote}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.push_to_remote(branch_name="custom-branch")

            mock_remote.push.assert_called_once_with("custom-branch", force=False)

    def test_push_with_force_flag(self, git_service):
        """
        测试：强制推送应该设置 force=True

        场景：设置 force=True
        期望：使用强制推送
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_push_info = MagicMock()
        mock_push_info.flags = 0
        mock_remote.push.return_value = [mock_push_info]
        mock_repo.remotes = {"origin": mock_remote}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.push_to_remote(branch_name="feature", force=True)

            mock_remote.push.assert_called_once_with("feature", force=True)

    def test_push_with_custom_remote(self, git_service):
        """
        测试：推送到自定义远程

        场景：提供 remote_name 参数
        期望：推送到指定的远程仓库
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_push_info = MagicMock()
        mock_push_info.flags = 0
        mock_remote.push.return_value = [mock_push_info]
        mock_repo.remotes = {"upstream": mock_remote, "origin": MagicMock()}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.push_to_remote(branch_name="feature", remote_name="upstream")

            mock_remote.push.assert_called_once_with("feature", force=False)

    def test_push_error_handling(self, git_service):
        """
        测试：推送失败时应该抛出异常

        场景：push 返回错误标志
        期望：抛出异常
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_push_info = MagicMock()
        # ERROR flag in git is (1 << 0) = 1
        mock_push_info.flags = 1
        mock_push_info.summary = "rejected"
        mock_remote.push.return_value = [mock_push_info]
        mock_repo.remotes = {"origin": mock_remote}

        with patch("app.config.get_config", return_value=mock_config):
            with pytest.raises(Exception) as exc_info:
                git_service.push_to_remote(branch_name="feature")

                assert "推送失败" in str(exc_info.value)

    def test_push_uses_current_branch_by_default(self, git_service):
        """
        测试：未指定分支时应该推送当前分支

        场景：不提供 branch_name 参数
        期望：推送当前活动分支
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_push_info = MagicMock()
        mock_push_info.flags = 0
        mock_remote.push.return_value = [mock_push_info]
        mock_repo.remotes = {"origin": mock_remote}
        mock_repo.active_branch.name = "current-branch"

        with patch("app.config.get_config", return_value=mock_config):
            git_service.push_to_remote()

            mock_remote.push.assert_called_once_with("current-branch", force=False)

    def test_push_logs_correctly(self, git_service, caplog):
        """
        测试：推送时应该记录正确的日志

        场景：执行推送
        期望：日志包含推送的分支名
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_push_info = MagicMock()
        mock_push_info.flags = 0
        mock_remote.push.return_value = [mock_push_info]
        mock_repo.remotes = {"origin": mock_remote}
        mock_repo.active_branch.name = "test-branch"

        with patch("app.config.get_config", return_value=mock_config):
            with caplog.at_level("INFO"):
                git_service.push_to_remote()

                assert any("推送分支到远程" in record.message for record in caplog.records)
                assert any("推送成功" in record.message for record in caplog.records)

    def test_push_with_network_error(self, git_service):
        """
        测试：网络错误时应该抛出异常

        场景：推送时网络连接失败
        期望：抛出异常并记录错误
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_remote.push.side_effect = git.GitCommandError("push", "Network error")
        mock_repo.remotes = {"origin": mock_remote}

        with patch("app.config.get_config", return_value=mock_config):
            with pytest.raises(git.GitCommandError):
                git_service.push_to_remote(branch_name="feature")

    def test_push_with_remote_not_found(self, git_service):
        """
        测试：远程仓库不存在时应该抛出异常

        场景：配置的远程名称不存在
        期望：抛出异常
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        # 空的 remotes 字典
        mock_repo.remotes = {}

        with patch("app.config.get_config", return_value=mock_config):
            with pytest.raises(KeyError):
                git_service.push_to_remote(branch_name="feature")


# =============================================================================
# TestHasChanges 测试
# =============================================================================


class TestHasChanges:
    """测试检查变更功能"""

    def test_has_changes_with_dirty_working_tree(self, git_service):
        """
        测试：工作区有变更时应该返回 True

        场景：is_dirty() 返回 True
        期望：返回 True
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = True

        result = git_service.has_changes()

        assert result is True

    def test_has_changes_with_untracked_files(self, git_service):
        """
        测试：有未跟踪文件时应该返回 True

        场景：有未跟踪的文件
        期望：返回 True
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = ["new_file.py"]

        result = git_service.has_changes()

        assert result is True

    def test_has_changes_with_clean_repository(self, git_service):
        """
        测试：工作区干净时应该返回 False

        场景：无未提交变更，无未跟踪文件
        期望：返回 False
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []

        result = git_service.has_changes()

        assert result is False

    def test_has_changes_with_both_dirty_and_untracked(self, git_service):
        """
        测试：既有工作区变更又有未跟踪文件时应该返回 True

        场景：is_dirty() 和 untracked_files 都有值
        期望：返回 True
        """
        mock_repo = git_service._mock_repo

        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = ["new_file.py"]

        result = git_service.has_changes()

        assert result is True


# =============================================================================
# TestGetCurrentBranch 测试
# =============================================================================


class TestGetCurrentBranch:
    """测试获取当前分支功能"""

    def test_get_current_branch_successfully(self, git_service):
        """
        测试：成功获取当前分支名

        场景：在特定分支上
        期望：返回正确的分支名
        """
        mock_repo = git_service._mock_repo

        mock_repo.active_branch.name = "feature-branch"

        result = git_service.get_current_branch()

        assert result == "feature-branch"

    def test_get_current_branch_on_main(self, git_service):
        """
        测试：在 main 分支时返回正确名称

        场景：当前分支为 main
        期望：返回 "main"
        """
        mock_repo = git_service._mock_repo

        mock_repo.active_branch.name = "main"

        result = git_service.get_current_branch()

        assert result == "main"


# =============================================================================
# TestGetStatus 测试
# =============================================================================


class TestGetStatus:
    """测试获取仓库状态功能"""

    def test_get_status_returns_complete_info(self, git_service):
        """
        测试：返回完整的状态信息

        场景：仓库有各种状态
        期望：返回包含所有状态字段的字典
        """
        mock_repo = git_service._mock_repo

        mock_repo.active_branch.name = "feature"
        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = ["file1.py", "file2.py"]
        mock_repo.index.diff.side_effect = [
            [MagicMock(), MagicMock()],  # staged changes
            [MagicMock()],  # unstaged changes
        ]
        mock_repo.heads = {"main": MagicMock(), "feature": MagicMock()}

        status = git_service.get_status()

        assert status["current_branch"] == "feature"
        assert status["is_dirty"] is True
        assert status["untracked_files"] == 2
        assert status["staged_changes"] == 2
        assert status["unstaged_changes"] == 1
        assert status["branch_count"] == 2

    def test_get_status_with_clean_repo(self, git_service):
        """
        测试：干净仓库的状态

        场景：仓库无变更
        期望：返回反映干净状态的信息
        """
        mock_repo = git_service._mock_repo

        mock_repo.active_branch.name = "main"
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []
        mock_repo.index.diff.side_effect = [[], []]
        mock_repo.heads = {"main": MagicMock()}

        status = git_service.get_status()

        assert status["current_branch"] == "main"
        assert status["is_dirty"] is False
        assert status["untracked_files"] == 0
        assert status["staged_changes"] == 0
        assert status["unstaged_changes"] == 0

    def test_get_status_exception_handling(self, git_service):
        """
        测试：获取状态失败时应该返回空字典

        场景：git 操作抛出异常
        期望：返回空字典并记录错误
        """
        mock_repo = git_service._mock_repo

        # Mock len() 抛出异常，这会导致 try-except 捕获
        mock_repo.heads = MagicMock()
        mock_repo.heads.__len__.side_effect = Exception("Test error")

        status = git_service.get_status()

        assert status == {}

    def test_get_status_logs_error_on_failure(self, git_service, caplog):
        """
        测试：获取状态失败时应该记录错误日志

        场景：操作抛出异常
        期望：记录 ERROR 级别日志
        """
        mock_repo = git_service._mock_repo

        # Mock 返回空字典触发异常日志
        mock_repo.active_branch.name = "main"
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []
        mock_repo.index.diff.side_effect = Exception("Diff error")

        with caplog.at_level("ERROR"):
            status = git_service.get_status()

            # 应该返回空字典
            assert status == {}
            # 应该记录错误日志
            assert any("获取状态失败" in record.message for record in caplog.records)


# =============================================================================
# TestCheckoutBranch 测试
# =============================================================================


class TestCheckoutBranch:
    """测试切换分支功能"""

    def test_checkout_branch_successfully(self, git_service):
        """
        测试：成功切换到目标分支

        场景：提供有效的分支名
        期望：切换到目标分支
        """
        mock_repo = git_service._mock_repo

        mock_branch = MagicMock()
        mock_branch.name = "target-branch"
        mock_repo.heads = {"target-branch": mock_branch}

        git_service.checkout_branch(branch_name="target-branch")

        mock_branch.checkout.assert_called_once()

    def test_checkout_branch_logs_correctly(self, git_service, caplog):
        """
        测试：切换分支时应该记录正确的日志

        场景：执行分支切换
        期望：日志包含分支名
        """
        mock_repo = git_service._mock_repo

        mock_branch = MagicMock()
        mock_branch.name = "new-feature"
        mock_repo.heads = {"new-feature": mock_branch}

        with caplog.at_level("INFO"):
            git_service.checkout_branch(branch_name="new-feature")

            assert any("切换分支" in record.message for record in caplog.records)
            assert any("已切换到分支" in record.message for record in caplog.records)

    def test_checkout_branch_exception_handling(self, git_service):
        """
        测试：切换分支失败时应该抛出异常

        场景：分支不存在
        期望：抛出异常并记录错误
        """
        mock_repo = git_service._mock_repo

        # 使用 MagicMock 的 side_effect
        mock_heads_dict = MagicMock()
        mock_heads_dict.__getitem__.side_effect = KeyError("Branch not found")
        mock_repo.heads = mock_heads_dict

        with pytest.raises(KeyError):
            git_service.checkout_branch(branch_name="nonexistent")


# =============================================================================
# TestPullLatest 测试
# =============================================================================


class TestPullLatest:
    """测试拉取最新代码功能"""

    def test_pull_latest_successfully(self, git_service):
        """
        测试：成功拉取最新代码

        场景：拉取当前分支
        期望：执行 pull 操作
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_repo.remotes = {"origin": mock_remote}

        with patch.object(git_service, "get_current_branch", return_value="main"):
            with patch("app.config.get_config", return_value=mock_config):
                git_service.pull_latest()

                mock_remote.pull.assert_called_once_with("main")

    def test_pull_specific_branch(self, git_service):
        """
        测试：拉取指定分支

        场景：提供 branch_name 参数
        期望：拉取指定的分支
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_repo.remotes = {"origin": mock_remote}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.pull_latest(branch_name="develop")

            mock_remote.pull.assert_called_once_with("develop")

    def test_pull_from_custom_remote(self, git_service):
        """
        测试：从自定义远程拉取

        场景：提供 remote_name 参数
        期望：从指定的远程拉取
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_repo.remotes = {"upstream": mock_remote}

        with patch("app.config.get_config", return_value=mock_config):
            git_service.pull_latest(branch_name="main", remote_name="upstream")

            mock_remote.pull.assert_called_once_with("main")

    def test_pull_uses_current_branch_by_default(self, git_service):
        """
        测试：未指定分支时拉取当前分支

        场景：不提供 branch_name 参数
        期望：拉取当前活动分支
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_repo.remotes = {"origin": mock_remote}
        mock_repo.active_branch.name = "feature"

        with patch.object(git_service, "get_current_branch", return_value="feature"):
            with patch("app.config.get_config", return_value=mock_config):
                git_service.pull_latest()

                mock_remote.pull.assert_called_once_with("feature")

    def test_pull_logs_correctly(self, git_service, caplog):
        """
        测试：拉取时应该记录正确的日志

        场景：执行拉取
        期望：日志包含分支名
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_repo.remotes = {"origin": mock_remote}

        with patch.object(git_service, "get_current_branch", return_value="main"):
            with patch("app.config.get_config", return_value=mock_config):
                with caplog.at_level("INFO"):
                    git_service.pull_latest()

                    assert any("拉取最新代码" in record.message for record in caplog.records)
                    assert any("拉取成功" in record.message for record in caplog.records)

    def test_pull_exception_handling(self, git_service):
        """
        测试：拉取失败时应该抛出异常

        场景：pull 操作失败
        期望：抛出异常并记录错误
        """
        mock_repo = git_service._mock_repo
        mock_config = git_service._mock_config

        mock_remote = MagicMock()
        mock_remote.pull.side_effect = git.GitError("Pull failed")
        mock_repo.remotes = {"origin": mock_remote}

        with patch("app.config.get_config", return_value=mock_config):
            with pytest.raises(git.GitError):
                git_service.pull_latest()


# =============================================================================
# TestDiscardChanges 测试
# =============================================================================


class TestDiscardChanges:
    """测试丢弃变更功能"""

    def test_discard_changes_successfully(self, git_service):
        """
        测试：成功丢弃所有未提交的变更

        场景：工作区有变更
        期望：变更被丢弃
        """
        mock_repo = git_service._mock_repo

        git_service.discard_changes()

        # 验证调用了 reset
        assert mock_repo.index.reset.call_count == 2

    def test_discard_changes_calls_reset_with_working_tree(self, git_service):
        """
        测试：应该调用 reset(working_tree=True)

        场景：丢弃变更
        期望：正确调用 reset 方法
        """
        mock_repo = git_service._mock_repo

        git_service.discard_changes()

        mock_repo.index.reset.assert_any_call(working_tree=True)
        mock_repo.index.reset.assert_any_call(working_tree=True, head=True)

    def test_discard_changes_logs_warning(self, git_service, caplog):
        """
        测试：丢弃变更时应该记录警告日志

        场景：执行丢弃操作
        期望：记录 WARNING 级别日志
        """
        mock_repo = git_service._mock_repo

        with caplog.at_level("WARNING"):
            git_service.discard_changes()

            assert any("丢弃所有未提交的变更" in record.message for record in caplog.records)

    def test_discard_changes_logs_success(self, git_service, caplog):
        """
        测试：成功丢弃后应该记录成功日志

        场景：丢弃操作成功
        期望：记录成功信息
        """
        mock_repo = git_service._mock_repo

        with caplog.at_level("INFO"):
            git_service.discard_changes()

            assert any("变更已丢弃" in record.message for record in caplog.records)

    def test_discard_changes_exception_handling(self, git_service):
        """
        测试：丢弃失败时应该抛出异常

        场景：reset 操作失败
        期望：抛出异常并记录错误
        """
        mock_repo = git_service._mock_repo

        mock_repo.index.reset.side_effect = git.GitError("Reset failed")

        with pytest.raises(git.GitError):
            git_service.discard_changes()


# =============================================================================
# TestGetDiff 测试
# =============================================================================


class TestGetDiff:
    """测试获取差异功能"""

    def test_get_diff_with_cached_changes(self, git_service):
        """
        测试：获取已暂存的变更差异

        场景：cached=True
        期望：返回已暂存变更的差异
        """
        mock_repo = git_service._mock_repo

        mock_diff = MagicMock()
        mock_diff.__str__ = lambda self: "diff --git a/file.py b/file.py"
        mock_repo.index.diff.return_value = [mock_diff]

        diff = git_service.get_diff(cached=True)

        assert "diff --git a/file.py b/file.py" in diff
        mock_repo.index.diff.assert_called_once_with("HEAD", create_patch=True)

    def test_get_diff_with_unstaged_changes(self, git_service):
        """
        测试：获取未暂存的变更差异

        场景：cached=False
        期望：返回未暂存变更的差异
        """
        mock_repo = git_service._mock_repo

        mock_diff = MagicMock()
        mock_diff.__str__ = lambda self: "diff --git a/file.py b/file.py"
        mock_repo.index.diff.return_value = [mock_diff]

        diff = git_service.get_diff(cached=False)

        mock_repo.index.diff.assert_called_once_with(None, create_patch=True)

    def test_get_diff_returns_empty_string_on_error(self, git_service):
        """
        测试：获取差异失败时应该返回空字符串

        场景：diff 操作抛出异常
        期望：返回空字符串并记录错误
        """
        mock_repo = git_service._mock_repo

        mock_repo.index.diff.side_effect = git.GitError("Diff failed")

        diff = git_service.get_diff()

        assert diff == ""

    def test_get_diff_with_multiple_changes(self, git_service):
        """
        测试：多个文件的差异应该被合并

        场景：有多个文件的变更
        期望：返回包含所有文件差异的字符串
        """
        mock_repo = git_service._mock_repo

        mock_diff1 = MagicMock()
        mock_diff1.__str__ = lambda self: "diff --git a/file1.py"
        mock_diff2 = MagicMock()
        mock_diff2.__str__ = lambda self: "diff --git a/file2.py"
        mock_repo.index.diff.return_value = [mock_diff1, mock_diff2]

        diff = git_service.get_diff()

        assert "diff --git a/file1.py" in diff
        assert "diff --git a/file2.py" in diff

    def test_get_diff_logs_error_on_failure(self, git_service, caplog):
        """
        测试：获取差异失败时应该记录错误日志

        场景：操作抛出异常
        期望：记录 ERROR 级别日志
        """
        mock_repo = git_service._mock_repo

        mock_repo.index.diff.side_effect = Exception("Test error")

        with caplog.at_level("ERROR"):
            git_service.get_diff()

            assert any("获取差异失败" in record.message for record in caplog.records)


# =============================================================================
# TestRealGitOperations 集成测试
# =============================================================================


class TestRealGitOperations:
    """
    使用真实 Git 仓库的集成测试

    这些测试使用真实的 Git 操作，但使用临时目录
    """

    def test_real_commit_and_status_check(self, git_service_real_repo):
        """
        测试：真实的提交和状态检查

        场景：创建文件、提交、检查状态
        期望：所有操作按预期工作
        """
        service, repo, repo_path = git_service_real_repo

        # 创建新文件
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")

        # 检查有变更
        assert service.has_changes() is True

        # 提交变更
        result = service.commit_changes(message="Add test file")
        assert result is True

        # 检查无变更
        assert service.has_changes() is False

    def test_real_branch_creation(self, git_service_real_repo):
        """
        测试：真实的分支创建

        场景：创建新分支
        期望：分支被创建并切换
        """
        service, repo, repo_path = git_service_real_repo

        # Mock 远程操作（不需要真实的远程）
        with patch("app.config.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.repository.default_branch = "main"
            mock_config.repository.remote_name = "origin"
            mock_config.task.branch_template = "ai/feature-{issue_number}-{timestamp}"
            mock_get_config.return_value = mock_config

            # Mock pull 操作
            with patch.object(git.Remote, "pull"):
                branch_name = service.create_feature_branch(issue_number=999)

                # 验证分支名格式
                assert branch_name.startswith("ai/feature-999-")

                # 验证当前分支
                current_branch = service.get_current_branch()
                assert current_branch == branch_name

    def test_real_status_returns_correct_info(self, git_service_real_repo):
        """
        测试：真实仓库的状态信息

        场景：获取仓库状态
        期望：返回准确的状态信息
        """
        service, repo, repo_path = git_service_real_repo

        status = service.get_status()

        assert "current_branch" in status
        assert status["current_branch"] == "main"
        assert status["is_dirty"] is False
        assert status["untracked_files"] == 0

    def test_real_checkout_branch(self, git_service_real_repo):
        """
        测试：真实的分支切换

        场景：切换分支
        期望：成功切换到目标分支
        """
        service, repo, repo_path = git_service_real_repo

        # 创建新分支
        new_branch = repo.create_head("test-branch")
        new_branch.checkout()

        # 切换回 main
        service.checkout_branch(branch_name="main")

        assert service.get_current_branch() == "main"

    def test_real_discard_changes(self, git_service_real_repo):
        """
        测试：真实的丢弃变更操作

        场景：修改文件后丢弃
        期望：变更被成功丢弃
        """
        service, repo, repo_path = git_service_real_repo

        # 修改文件
        test_file = repo_path / "README.md"
        original_content = test_file.read_text()
        test_file.write_text("modified content")

        # 确认有变更
        assert service.has_changes() is True

        # 丢弃变更
        service.discard_changes()

        # 确认无变更
        assert service.has_changes() is False
        assert test_file.read_text() == original_content

    def test_real_get_diff(self, git_service_real_repo):
        """
        测试：真实的差异获取

        场景：修改文件后获取差异
        期望：返回正确的差异内容
        """
        service, repo, repo_path = git_service_real_repo

        # 修改文件
        test_file = repo_path / "README.md"
        test_file.write_text("new content")

        # 暂存变更
        repo.index.add(["README.md"])

        # 获取已暂存的差异
        diff = service.get_diff(cached=True)

        # 应该包含差异信息
        assert len(diff) > 0
        assert "README.md" in diff or "readme" in diff.lower()

    def test_real_commit_without_add_all(self, git_service_real_repo):
        """
        测试：不使用 add_all 的提交

        场景：修改文件但不添加
        期望：返回 False 因为没有暂存的变更
        """
        service, repo, repo_path = git_service_real_repo

        # 修改文件
        test_file = repo_path / "README.md"
        test_file.write_text("modified")

        # 提交但不添加
        result = service.commit_changes(message="Test commit", add_all=False)

        # 应该返回 False 因为没有暂存的变更
        assert result is False
