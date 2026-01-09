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
            rate_limit = self.github.get_rate_limit()
            core_rate = rate_limit.resources.core
            self.logger.info(
                f"GitHub API 连接成功: {user.login} "
                f"(限额: {core_rate.remaining}/{core_rate.limit} 剩余)"
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
        execution_time: float = 0,
        development_summary: str = "",
    ) -> dict[str, any]:
        """
        创建 Pull Request

        Args:
            branch_name: 特性分支名
            issue_number: Issue 编号
            issue_title: Issue 标题
            issue_body: Issue 内容
            base_branch: 目标分支，默认为仓库默认分支
            execution_time: 执行时间（秒）
            development_summary: AI 开发总结

        Returns:
            dict: PR 信息
                - pr_number (int): PR 编号
                - url (str): PR URL
                - html_url (str): PR HTML URL
                - state (str): PR 状态
                或 None（如果没有提交）
        """
        try:
            from app.config import get_config

            config = get_config()

            repo = self._get_repo()
            base = base_branch or config.repository.default_branch

            self.logger.info(
                f"准备创建 PR: {branch_name} -> {base} "
                f"(关联 Issue #{issue_number})"
            )

            # 检查分支之间是否有提交差异
            try:
                # 获取分支的比较信息
                comparison = repo.compare(base, branch_name)

                # 检查是否有提交（ahead_by > 0 表示有新提交）
                if comparison.ahead_by == 0:
                    # 没有新提交，无法创建 PR
                    self.logger.warning(
                        f"⚠️  无法创建 PR: 分支 '{branch_name}' 与 '{base}' 之间没有新的提交\n"
                        f"可能原因:\n"
                        f"  1. Claude CLI 执行失败，未产生任何代码变更\n"
                        f"  2. Claude CLI 判断任务无法完成，没有提交代码\n"
                        f"  3. 分支创建失败或未正确切换\n"
                        f"建议: 请检查 Claude CLI 的执行日志以了解详细原因"
                    )
                    return None

                self.logger.info(
                    f"检测到 {comparison.ahead_by} 个新提交，继续创建 PR"
                )

            except GithubException as e:
                # 如果比较失败，仍然尝试创建 PR（让后续代码处理错误）
                self.logger.warning(f"无法比较分支差异: {e}，将继续尝试创建 PR")

            # 构建 PR 标题和描述
            pr_title = f"Kaka: {issue_title}"
            pr_body = self._build_pr_body(
                issue_number, issue_title, issue_body, execution_time, development_summary
            )

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
            # 检查是否是 "No commits" 错误
            if e.status == 422 and "No commits between" in str(e):
                self.logger.warning(
                    f"⚠️  无法创建 PR: 分支 '{branch_name}' 与目标分支之间没有提交差异\n"
                    f"GitHub API 错误: {e.data.get('message', '未知错误')}\n"
                    f"可能原因: Claude CLI 执行后未产生代码提交\n"
                    f"建议: 请检查 Claude CLI 的执行输出和日志"
                )
                return None
            else:
                # 其他 GitHub API 错误
                self.logger.error(
                    f"创建 PR 失败 (GitHub API 错误 {e.status}): {e.data.get('message', str(e))}",
                    exc_info=False  # 不打印完整 traceback
                )
                raise

    def _build_pr_body(
        self,
        issue_number: int,
        issue_title: str,
        issue_body: str,
        execution_time: float = 0,
        development_summary: str = "",
    ) -> str:
        """
        构建 PR 描述

        Args:
            issue_number: Issue 编号
            issue_title: Issue 标题
            issue_body: Issue 内容
            execution_time: 执行时间（秒）
            development_summary: AI 开发总结

        Returns:
            str: PR 描述
        """
        from app.config import get_config

        config = get_config()
        repo_owner = config.github.repo_owner

        # 格式化执行时间
        time_str = f"{execution_time:.1f}秒" if execution_time > 0 else "未知"

        # 构建 PR 描述
        pr_body = f"""
**关联 Issue**: #{issue_number} | **用时**: {time_str}

---

## 原 Issue：{issue_title}

```
{issue_body or "无详细描述"}
```

"""

        # 如果有 AI 开发总结，添加到 PR 描述中
        if development_summary:
            pr_body += f"""---

## Kaka 开发总结

{development_summary}

---

@{repo_owner} 请 review 后决策是否 PR，谢谢！
"""

        return pr_body

    def _get_current_timestamp(self) -> str:
        """
        获取当前时间戳字符串

        Returns:
            str: 格式化的时间戳
        """
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_comment_to_issue(
        self,
        issue_number: int,
        comment: str,
    ) -> bool:
        """
        在 Issue 添加评论

        Args:
            issue_number: Issue 编号
            comment: 评论内容

        Returns:
            bool: 是否成功添加评论
        """
        try:
            repo = self._get_repo()
            issue = repo.get_issue(issue_number)

            issue.create_comment(comment)

            self.logger.info(f"✅ 已在 Issue #{issue_number} 添加评论")
            return True

        except GithubException as e:
            # 检查是否是权限问题
            if e.status == 403:
                self.logger.error(
                    f"❌ GitHub Token 权限不足 (Issue #{issue_number})\n"
                    f"错误: {e.data.get('message', '未知错误')}\n"
                    f"解决方法:\n"
                    f"  1. 前往 https://github.com/settings/tokens\n"
                    f"  2. 编辑或生成新的 Personal Access Token\n"
                    f"  3. 确保授予以下权限:\n"
                    f"     - repo (完整仓库访问权限)\n"
                    f"     - public_repo (如果是公开仓库)\n"
                    f"  4. 更新 .env 文件中的 GITHUB_TOKEN",
                    exc_info=False,
                )
            else:
                self.logger.error(
                    f"添加评论失败 (Issue #{issue_number}): {e}",
                    exc_info=True,
                )
            return False

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
            core = limits.resources.core

            return {
                "remaining": core.remaining,
                "limit": core.limit,
                "reset": core.reset.timestamp(),
                "used": core.limit - core.remaining,
            }
        except Exception as e:
            self.logger.error(f"获取限额信息失败: {e}", exc_info=True)
            return {}
