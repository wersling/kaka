"""
Git 操作服务

提供 Git 仓库操作功能，包括分支管理、提交和推送
"""

import time
from pathlib import Path
from typing import Any, Optional

import git
from app.utils.logger import LoggerMixin, get_logger

logger = get_logger(__name__)


class GitService(LoggerMixin):
    """
    Git 操作服务

    提供 Git 仓库的常用操作，包括分支管理、提交和推送
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        初始化 Git 服务

        Args:
            repo_path: Git 仓库路径，如果为 None 则从配置读取

        Raises:
            ValueError: 如果路径不是有效的 Git 仓库
        """
        if repo_path is None:
            from app.config import get_config
            config = get_config()
            repo_path = config.repository.path

        self.repo_path = Path(repo_path).expanduser().resolve()

        # 验证是否是 Git 仓库
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"不是有效的 Git 仓库: {self.repo_path}")

        try:
            self.repo = git.Repo(self.repo_path)
            self.logger.info(f"Git 服务初始化成功: {self.repo_path}")
        except Exception as e:
            raise ValueError(f"无法打开 Git 仓库: {e}") from e

    def create_feature_branch(
        self,
        issue_number: int,
        base_branch: Optional[str] = None,
    ) -> str:
        """
        创建特性分支

        Args:
            issue_number: Issue 编号
            base_branch: 基础分支名，默认使用配置的默认分支

        Returns:
            str: 创建的分支名

        Raises:
            Exception: 创建分支失败
        """
        try:
            from app.config import get_config

            config = get_config()
            default_branch = base_branch or config.repository.default_branch
            remote_name = config.repository.remote_name

            # 生成分支名
            timestamp = int(time.time())
            branch_name = config.task.branch_template.format(
                issue_number=issue_number,
                timestamp=timestamp,
            )

            self.logger.info(
                f"创建特性分支: {branch_name} (基于 {default_branch})"
            )

            # 获取远程
            origin = self.repo.remotes[remote_name]

            # 检查本地是否存在默认分支
            local_branch_exists = default_branch in [h.name for h in self.repo.heads]

            if not local_branch_exists:
                self.logger.warning(
                    f"本地分支 '{default_branch}' 不存在，尝试从远程创建"
                )
                # 尝试从远程获取并创建本地分支
                try:
                    # 获取远程的所有分支
                    remote_refs = origin.refs
                    remote_default_branch = f"{remote_name}/{default_branch}"

                    if remote_default_branch in [r.name for r in remote_refs]:
                        # 从远程创建本地分支
                        self.logger.info(f"从远程创建本地分支: {default_branch}")
                        remote_ref = origin.refs[default_branch]
                        local_branch = self.repo.create_head(
                            default_branch, remote_ref
                        )
                        local_branch.set_tracking_branch(remote_ref)
                        local_branch.checkout()
                    else:
                        # 尝试使用远程的默认分支
                        self.logger.warning(
                            f"远程分支 '{default_branch}' 不存在，尝试获取远程默认分支"
                        )
                        # 获取远程仓库的默认分支
                        origin.fetch()
                        # 检查远程有哪些分支
                        available_branches = [
                            r.name.replace(f"{remote_name}/", "")
                            for r in remote_refs
                            if r.name.startswith(f"{remote_name}/")
                        ]
                        if available_branches:
                            # 使用第一个可用的分支
                            actual_default = available_branches[0]
                            self.logger.info(
                                f"使用远程分支 '{actual_default}' 作为默认分支"
                            )
                            remote_ref = origin.refs[actual_default]
                            local_branch = self.repo.create_head(
                                actual_default, remote_ref
                            )
                            local_branch.set_tracking_branch(remote_ref)
                            local_branch.checkout()
                            default_branch = actual_default
                        else:
                            raise Exception(
                                f"远程仓库没有任何可用的分支。请确保远程仓库已正确初始化。"
                            )
                except Exception as e:
                    raise Exception(
                        f"无法从远程创建本地分支: {e}。"
                        f"请确保远程仓库存在且可访问。"
                    ) from e
            else:
                # 确保在默认分支
                self.repo.heads[default_branch].checkout()

            # 拉取最新代码
            self.logger.info(f"拉取最新代码: {default_branch}")
            origin.pull(default_branch)

            # 创建并切换到新分支
            self.repo.create_head(branch_name)
            self.repo.heads[branch_name].checkout()

            self.logger.info(f"✅ 特性分支创建成功: {branch_name}")
            return branch_name

        except Exception as e:
            self.logger.error(f"创建特性分支失败: {e}", exc_info=True)
            raise

    def commit_changes(
        self,
        message: str,
        add_all: bool = True,
    ) -> bool:
        """
        提交变更

        Args:
            message: 提交消息
            add_all: 是否添加所有变更到暂存区（git add -A）
                     - True: 添加所有变更（默认）
                     - False: 只提交已暂存的变更，不添加新变更

        Returns:
            bool: 是否有提交（True）或没有变更需要提交（False）

        Raises:
            Exception: 提交失败
        """
        try:
            self.logger.info(f"准备提交变更: {message}")

            # 检查是否有变更
            has_changes = self.repo.is_dirty() or self.repo.untracked_files

            if add_all:
                # 添加所有变更到暂存区
                if not has_changes:
                    self.logger.info("没有变更需要提交")
                    return False

                self.logger.debug(f"添加所有变更到暂存区")
                self.repo.index.add("*")
                # 添加未跟踪的文件
                for file_path in self.repo.untracked_files:
                    try:
                        self.repo.index.add(file_path)
                    except Exception:
                        # 忽略无法添加的文件（如 .gitignore 中的文件）
                        pass
            else:
                # 不添加新变更，只检查是否有已暂存的变更
                if not self.repo.index.diff("HEAD"):
                    self.logger.info("没有暂存的变更需要提交 (add_all=False)")
                    return False

            # 检查是否有暂存的变更
            if not self.repo.index.diff("HEAD"):
                self.logger.info("没有暂存的变更需要提交")
                return False

            # 提交
            commit = self.repo.index.commit(message)
            self.logger.info(
                f"✅ 提交成功: {commit.hexsha[:7]} - {message}"
            )

            return True

        except Exception as e:
            self.logger.error(f"提交变更失败: {e}", exc_info=True)
            raise

    def push_to_remote(
        self,
        branch_name: Optional[str] = None,
        remote_name: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """
        推送分支到远程

        Args:
            branch_name: 分支名，默认为当前分支
            remote_name: 远程名称，默认从配置读取
            force: 是否强制推送

        Raises:
            Exception: 推送失败
        """
        try:
            from app.config import get_config

            config = get_config()

            # 获取分支名
            if branch_name is None:
                branch_name = self.repo.active_branch.name

            # 获取远程名称
            if remote_name is None:
                remote_name = config.repository.remote_name

            self.logger.info(f"推送分支到远程: {branch_name}")

            # 推送
            remote = self.repo.remotes[remote_name]
            push_info = remote.push(branch_name, force=force)

            # 检查推送结果
            for info in push_info:
                # 检查是否有错误标志
                if info.flags & (1 << 0):  # ERROR flag = 1 << 0
                    raise Exception(f"推送失败: {info.summary}")

            self.logger.info(f"✅ 推送成功: {branch_name}")

        except Exception as e:
            self.logger.error(f"推送失败: {e}", exc_info=True)
            raise

    def has_changes(self) -> bool:
        """
        检查是否有未提交的变更

        Returns:
            bool: 是否有变更
        """
        return self.repo.is_dirty() or bool(self.repo.untracked_files)

    def get_current_branch(self) -> str:
        """
        获取当前分支名

        Returns:
            str: 当前分支名
        """
        return self.repo.active_branch.name

    def get_status(self) -> dict[str, Any]:
        """
        获取仓库状态

        Returns:
            dict: 包含分支、变更等状态信息
        """
        try:
            return {
                "current_branch": self.get_current_branch(),
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": len(self.repo.untracked_files),
                "staged_changes": len(self.repo.index.diff("HEAD")),
                "unstaged_changes": len(self.repo.index.diff(None)),
                "branch_count": len(self.repo.heads),
            }
        except Exception as e:
            self.logger.error(f"获取状态失败: {e}", exc_info=True)
            return {}

    def branch_exists(self, branch_name: str) -> bool:
        """
        检查分支是否存在

        Args:
            branch_name: 分支名

        Returns:
            bool: 分支是否存在
        """
        try:
            return branch_name in self.repo.heads
        except Exception as e:
            self.logger.error(f"检查分支失败: {e}", exc_info=True)
            return False

    def checkout_branch(self, branch_name: str) -> None:
        """
        切换分支

        Args:
            branch_name: 目标分支名

        Raises:
            Exception: 切换失败
        """
        try:
            self.logger.info(f"切换分支: {branch_name}")
            self.repo.heads[branch_name].checkout()
            self.logger.info(f"✅ 已切换到分支: {branch_name}")
        except Exception as e:
            self.logger.error(f"切换分支失败: {e}", exc_info=True)
            raise

    def pull_latest(
        self,
        branch_name: Optional[str] = None,
        remote_name: Optional[str] = None,
    ) -> None:
        """
        拉取最新代码

        Args:
            branch_name: 分支名，默认为当前分支
            remote_name: 远程名称，默认从配置读取

        Raises:
            Exception: 拉取失败
        """
        try:
            from app.config import get_config

            config = get_config()

            if branch_name is None:
                branch_name = self.get_current_branch()

            if remote_name is None:
                remote_name = config.repository.remote_name

            self.logger.info(f"拉取最新代码: {branch_name}")

            remote = self.repo.remotes[remote_name]
            remote.pull(branch_name)

            self.logger.info(f"✅ 拉取成功: {branch_name}")

        except Exception as e:
            self.logger.error(f"拉取失败: {e}", exc_info=True)
            raise

    def discard_changes(self) -> None:
        """
        丢弃所有未提交的变更

        Raises:
            Exception: 操作失败
        """
        try:
            self.logger.warning("丢弃所有未提交的变更")

            # 丢弃未暂存的变更
            self.repo.index.reset(working_tree=True)

            # 丢弃未暂存的删除
            self.repo.index.reset(working_tree=True, head=True)

            self.logger.info("✅ 变更已丢弃")

        except Exception as e:
            self.logger.error(f"丢弃变更失败: {e}", exc_info=True)
            raise

    def get_diff(self, cached: bool = False) -> str:
        """
        获取差异

        Args:
            cached: 是否只显示已暂存的变更

        Returns:
            str: 差异内容
        """
        try:
            diff = self.repo.index.diff(
                "HEAD" if cached else None,
                create_patch=True,
            )
            return "\n".join(str(d) for d in diff)
        except Exception as e:
            self.logger.error(f"获取差异失败: {e}", exc_info=True)
            return ""
