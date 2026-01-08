"""
GitHub API 服务

提供 GitHub API 操作，包括 PR 创建、评论等
"""

from typing import Optional

from github import Github
from github.GithubException import GithubException
from github.Issue import Issue as PyGithubIssue
from github.PullRequest import PullRequest as PyGithubPullRequest

from app.utils.logger import LoggerMixin, get_logger

logger = get_logger(__name__)


class GitHubService(LoggerMixin):
    """
    GitHub API 服务

    提供 GitHub API 的常用操作
    """

    def __init__(self, token: Optional[str] = None):
        """
        初始化 GitHub 服务

        Args:
            token: GitHub Personal Access Token，如果为 None 则从配置读取
        """
        from app.config import get_config

        config = get_config()

        self.token = token or config.github.token
        self.github = Github(self.token)

        # 测试连接
        try:
            user = self.github.get_user()
            self.logger.info(
                f"GitHub API 连接成功: {user.login} "
                f"(限额: {user.rate_limiting_remaining_hits} 剩余)"
            )
        except Exception as e:
            self.logger.error(f"GitHub API 连接失败: {e}", exc_info=True)
            raise

    def _get_repo(self):
        """获取仓库对象"""
        from app.config import get_config

        config = get_config()
        return self.github.get_repo(config.github.repo_full_name)

    def create_pull_request(
        self,
        branch_name: str,
        issue_number: int,
        issue_title: str,
        issue_body: str,
        base_branch: Optional[str] = None,
    ) -> dict[str, any]:
        """
        创建 Pull Request

        Args:
            branch_name: 特性分支名
            issue_number: Issue 编号
            issue_title: Issue 标题
            issue_body: Issue 内容
            base_branch: 目标分支，默认为仓库默认分支

        Returns:
            dict: PR 信息
                - pr_number (int): PR 编号
                - url (str): PR URL
                - html_url (str): PR HTML URL
                - state (str): PR 状态
        """
        try:
            from app.config import get_config

            config = get_config()

            repo = self._get_repo()
            base = base_branch or config.repository.default_branch

            self.logger.info(
                f"创建 PR: {branch_name} -> {base} "
                f"(关联 Issue #{issue_number})"
            )

            # 构建 PR 标题和描述
            pr_title = f"🤖 AI: {issue_title}"
            pr_body = self._build_pr_body(issue_number, issue_body)

            # 创建 PR
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=base,
            )

            self.logger.info(f"✅ PR 创建成功: #{pr.number} - {pr.html_url}")

            return {
                "pr_number": pr.number,
                "url": pr.url,
                "html_url": pr.html_url,
                "state": pr.state,
                "title": pr.title,
            }

        except GithubException as e:
            self.logger.error(f"创建 PR 失败: {e}", exc_info=True)
            raise

    def _build_pr_body(self, issue_number: int, issue_body: str) -> str:
        """
        构建 PR 描述

        Args:
            issue_number: Issue 编号
            issue_body: Issue 内容

        Returns:
            str: PR 描述
        """
        from app.config import get_config

        config = get_config()

        repo_owner = config.github.repo_owner
        repo_name = config.github.repo_name

        return f"""## 🤖 AI 自动生成的 Pull Request

**关联 Issue**: #{issue_number}

### 变更说明
本 PR 由 AI 自动分析和生成，已完成以下工作：
- ✅ 需求分析
- ✅ 代码实现
- ✅ 测试验证
- ✅ 代码提交

### 原 Issue 内容
```
{issue_body or "无详细描述"}
```

### 审核要点
请人工审核以下内容：
- 📋 代码质量和安全性
- ✅ 功能完整性
- 🧪 测试覆盖率
- 📝 文档是否完善
- 🎯 是否符合项目规范

### 如何测试
1. Checkout 此分支
2. 运行测试（如果有）
3. 手动测试相关功能
4. 检查代码变更

@{repo_owner} 请 review 后合并

---
*由 AI 开发调度服务自动生成*
"""

    def add_comment_to_issue(
        self,
        issue_number: int,
        comment: str,
    ) -> None:
        """
        在 Issue 添加评论

        Args:
            issue_number: Issue 编号
            comment: 评论内容
        """
        try:
            repo = self._get_repo()
            issue = repo.get_issue(issue_number)

            issue.create_comment(comment)

            self.logger.info(f"✅ 已在 Issue #{issue_number} 添加评论")

        except GithubException as e:
            self.logger.error(
                f"添加评论失败 (Issue #{issue_number}): {e}",
                exc_info=True,
            )
            raise

    def add_comment_to_pr(
        self,
        pr_number: int,
        comment: str,
    ) -> None:
        """
        在 PR 添加评论

        Args:
            pr_number: PR 编号
            comment: 评论内容
        """
        try:
            repo = self._get_repo()
            pr = repo.get_pull(pr_number)

            pr.create_issue_comment(comment)

            self.logger.info(f"✅ 已在 PR #{pr_number} 添加评论")

        except GithubException as e:
            self.logger.error(
                f"添加评论失败 (PR #{pr_number}): {e}",
                exc_info=True,
            )
            raise

    def update_issue_labels(
        self,
        issue_number: int,
        labels: list[str],
    ) -> None:
        """
        更新 Issue 标签

        Args:
            issue_number: Issue 编号
            labels: 标签列表
        """
        try:
            repo = self._get_repo()
            issue = repo.get_issue(issue_number)

            issue.set_labels(*labels)

            self.logger.info(
                f"✅ 已更新 Issue #{issue_number} 标签: {', '.join(labels)}"
            )

        except GithubException as e:
            self.logger.error(
                f"更新标签失败 (Issue #{issue_number}): {e}",
                exc_info=True,
            )
            raise

    def close_issue(
        self,
        issue_number: int,
        comment: Optional[str] = None,
    ) -> None:
        """
        关闭 Issue

        Args:
            issue_number: Issue 编号
            comment: 可选的关闭评论
        """
        try:
            repo = self._get_repo()
            issue = repo.get_issue(number=issue_number)

            # 添加评论（如果有）
            if comment:
                issue.create_comment(comment)

            # 关闭 Issue
            issue.edit(state="closed")

            self.logger.info(f"✅ 已关闭 Issue #{issue_number}")

        except GithubException as e:
            self.logger.error(
                f"关闭 Issue 失败 (#{issue_number}): {e}",
                exc_info=True,
            )
            raise

    def get_issue(self, issue_number: int) -> PyGithubIssue:
        """
        获取 Issue 对象

        Args:
            issue_number: Issue 编号

        Returns:
            PyGithubIssue: Issue 对象
        """
        try:
            repo = self._get_repo()
            return repo.get_issue(issue_number)
        except GithubException as e:
            self.logger.error(
                f"获取 Issue 失败 (#{issue_number}): {e}",
                exc_info=True,
            )
            raise

    def get_pull_request(self, pr_number: int) -> PyGithubPullRequest:
        """
        获取 PR 对象

        Args:
            pr_number: PR 编号

        Returns:
            PyGithubPullRequest: PR 对象
        """
        try:
            repo = self._get_repo()
            return repo.get_pull(pr_number)
        except GithubException as e:
            self.logger.error(
                f"获取 PR 失败 (#{pr_number}): {e}",
                exc_info=True,
            )
            raise

    def get_rate_limit(self) -> dict[str, any]:
        """
        获取 API 限额信息

        Returns:
            dict: 限额信息
                - remaining (int): 剩余请求数
                - limit (int): 总限额
                - reset (int): 重置时间（Unix 时间戳）
        """
        try:
            limits = self.github.get_rate_limit()
            core = limits.core

            return {
                "remaining": core.remaining,
                "limit": core.limit,
                "reset": core.reset.timestamp(),
                "used": core.limit - core.remaining,
            }
        except Exception as e:
            self.logger.error(f"获取限额信息失败: {e}", exc_info=True)
            return {}
