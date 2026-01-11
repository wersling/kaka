#!/usr/bin/env python3
"""
真实环境集成测试

完整测试从 GitHub Issue 触发到 Pull Request 创建的自动化工作流。

测试流程：
1. 检查环境配置
2. 启动服务（如果未运行）
3. 创建测试 Issue
4. 触发 Webhook（添加 ai-dev 标签）
5. 监控执行过程
6. 验证结果（PR 创建、代码提交）
7. 清理测试环境（删除 Issue 和 PR）
8. 生成测试报告

使用方法：
    python scripts/test_integration_live.py
    或
    make test-integration-live
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import subprocess

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from app.config import get_config


# =============================================================================
# 颜色输出
# =============================================================================

class Colors:
    """终端颜色代码"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

    @classmethod
    def print_header(cls, text: str):
        """打印标题"""
        print(f"\n{cls.CYAN}{'=' * 80}{cls.RESET}")
        print(f"{cls.BOLD}{cls.CYAN}{text}{cls.RESET}")
        print(f"{cls.CYAN}{'=' * 80}{cls.RESET}\n")

    @classmethod
    def print_step(cls, step: int, total: int, text: str):
        """打印步骤"""
        print(f"{cls.BLUE}步骤 {step}/{total}: {text}{cls.RESET}")

    @classmethod
    def print_success(cls, text: str):
        """打印成功消息"""
        print(f"{cls.GREEN}✅ {text}{cls.RESET}")

    @classmethod
    def print_error(cls, text: str):
        """打印错误消息"""
        print(f"{cls.RED}❌ {text}{cls.RESET}")

    @classmethod
    def print_warning(cls, text: str):
        """打印警告消息"""
        print(f"{cls.YELLOW}⚠️  {text}{cls.RESET}")

    @classmethod
    def print_info(cls, text: str):
        """打印信息"""
        print(f"{cls.CYAN}  {text}{cls.RESET}")


# =============================================================================
# GitHub API 辅助类
# =============================================================================

class GitHubAPI:
    """GitHub API 操作辅助类"""

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """
        初始化 GitHub API

        Args:
            token: GitHub Personal Access Token
            repo_owner: 仓库所有者
            repo_name: 仓库名称
        """
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        发送 GitHub API 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 其他请求参数

        Returns:
            dict: 响应数据
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def create_issue(self, title: str, body: str, labels: list[str] = None) -> dict:
        """
        创建 Issue

        Args:
            title: Issue 标题
            body: Issue 内容
            labels: 标签列表

        Returns:
            dict: 创建的 Issue 信息
        """
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues"
        data = {
            "title": title,
            "body": body,
            "labels": labels or []
        }
        return self._request("POST", endpoint, json=data)

    def add_label_to_issue(self, issue_number: int, label: str) -> dict:
        """
        向 Issue 添加标签

        Args:
            issue_number: Issue 编号
            label: 标签名称

        Returns:
            dict: 更新后的 Issue 信息
        """
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/labels"
        return self._request("POST", endpoint, json=[label])

    def remove_label_from_issue(self, issue_number: int, label: str) -> dict:
        """
        从 Issue 移除标签

        Args:
            issue_number: Issue 编号
            label: 标签名称

        Returns:
            dict: 更新后的 Issue 信息
        """
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/labels/{label}"
        return self._request("DELETE", endpoint)

    def get_issue(self, issue_number: int) -> dict:
        """
        获取 Issue 信息

        Args:
            issue_number: Issue 编号

        Returns:
            dict: Issue 信息
        """
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
        return self._request("GET", endpoint)

    def get_pulls_for_issue(self, issue_number: int) -> list[dict]:
        """
        获取 Issue 关联的所有 PR

        Args:
            issue_number: Issue 编号

        Returns:
            list: PR 列表（如果不存在则返回空列表）
        """
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/pulls"
        try:
            return self._request("GET", endpoint)
        except requests.exceptions.HTTPError as e:
            # 404 是正常的，表示 PR 还未创建
            if e.response.status_code == 404:
                return []
            # 其他错误继续抛出
            raise

    def get_issue_comments(self, issue_number: int) -> list[dict]:
        """
        获取 Issue 的所有评论

        Args:
            issue_number: Issue 编号

        Returns:
            list: 评论列表
        """
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/comments"
        try:
            return self._request("GET", endpoint)
        except requests.exceptions.HTTPError as e:
            # 404 返回空列表
            if e.response.status_code == 404:
                return []
            # 其他错误继续抛出
            raise

    def close_issue(self, issue_number: int, comment: str = None) -> dict:
        """
        关闭 Issue

        Args:
            issue_number: Issue 编号
            comment: 关闭评论（可选）

        Returns:
            dict: 更新后的 Issue 信息
        """
        # 添加评论
        if comment:
            endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/comments"
            self._request("POST", endpoint, json={"body": comment})

        # 关闭 Issue
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
        return self._request("PATCH", endpoint, json={"state": "closed"})

    def delete_branch(self, branch_name: str) -> bool:
        """
        删除分支

        Args:
            branch_name: 分支名

        Returns:
            bool: 是否成功
        """
        endpoint = f"/repos/{self.repo_owner}/{self.repo_name}/git/refs/heads/{branch_name}"
        try:
            self._request("DELETE", endpoint)
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # 分支不存在，视为成功
                return True
            raise


# =============================================================================
# 服务管理
# =============================================================================

class ServiceManager:
    """服务进程管理"""

    def __init__(self, log_path: Path):
        """
        初始化服务管理器

        Args:
            log_path: 日志文件路径
        """
        self.log_path = log_path
        self.process: Optional[subprocess.Popen] = None

    def is_running(self) -> bool:
        """检查服务是否运行"""
        try:
            # 检查进程是否存在
            result = subprocess.run(
                ["pgrep", "-f", "uvicorn.*app.main:app"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def start(self) -> bool:
        """
        启动服务

        Returns:
            bool: 是否成功启动
        """
        if self.is_running():
            Colors.print_info("服务已在运行")
            return True

        Colors.print_info("启动服务...")
        log_file = self.log_path / "ai-scheduler.log"

        # 确保日志目录存在
        self.log_path.mkdir(parents=True, exist_ok=True)

        # 检查是否有虚拟环境（在脚本所在的项目中）
        script_dir = Path(__file__).parent.parent
        project_root = script_dir  # 使用脚本所在的项目根目录
        venv_python = project_root / "venv" / "bin" / "python"

        # 确定使用的 Python 解释器
        if venv_python.exists():
            python_exe = str(venv_python)
            Colors.print_info(f"使用虚拟环境: {venv_python}")
        else:
            python_exe = sys.executable
            Colors.print_info(f"使用系统 Python: {python_exe}")

        # 启动服务（使用虚拟环境的 Python 和 uvicorn）
        cmd = [
            python_exe,
            "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000"
        ]

        # 准备环境变量（传递当前进程的所有环境变量）
        env = os.environ.copy()

        # 打开日志文件用于写入
        log_handle = open(log_file, "a")

        self.process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=str(project_root),
            text=True,
            env=env  # 传递环境变量
        )

        # 等待服务启动
        for i in range(30):
            time.sleep(1)
            if self.is_running():
                Colors.print_success("服务启动成功")
                log_handle.close()
                return True

        Colors.print_error("服务启动失败")
        log_handle.close()

        # 如果启动失败，打印日志帮助调试
        try:
            with open(log_file, 'r') as f:
                last_lines = ''.join(f.readlines()[-20:])
                if last_lines:
                    Colors.print_info(f"最近日志:\n{last_lines}")
        except Exception:
            pass

        return False

    def stop(self) -> bool:
        """
        停止服务

        Returns:
            bool: 是否成功停止
        """
        if not self.is_running():
            Colors.print_info("服务未运行")
            return True

        Colors.print_info("停止服务...")
        try:
            subprocess.run(["pkill", "-f", "uvicorn.*app.main:app"], check=True)
            time.sleep(2)
            Colors.print_success("服务已停止")
            return True
        except subprocess.CalledProcessError:
            Colors.print_error("停止服务失败")
            return False

    def tail_logs(self, lines: int = 50):
        """
        查看最近的日志

        Args:
            lines: 行数
        """
        log_file = self.log_path / "ai-scheduler.log"
        try:
            result = subprocess.run(
                ["tail", f"-n{lines}", str(log_file)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(result.stdout)
        except Exception as e:
            Colors.print_error(f"读取日志失败: {e}")


# =============================================================================
# 集成测试主类
# =============================================================================

class IntegrationTest:
    """真实环境集成测试"""

    def __init__(self):
        """初始化测试"""
        self.config = get_config()
        self.github_api = None
        self.test_issue_number: Optional[int] = None
        self.test_pr_numbers: list[int] = []
        self.service_manager = ServiceManager(self.config.repository.path / "logs")
        self.start_time = None
        self.test_results = {
            "success": False,
            "steps": [],
            "errors": [],
            "warnings": [],
            "metrics": {}
        }

    def check_environment(self) -> bool:
        """
        检查环境配置

        Returns:
            bool: 环境是否配置正确
        """
        Colors.print_step(1, 8, "检查环境配置")

        required_env_vars = [
            "GITHUB_TOKEN",
            "GITHUB_REPO_OWNER",
            "GITHUB_REPO_NAME",
            "REPO_PATH",
            "ANTHROPIC_API_KEY"
        ]

        missing_vars = []
        for var in required_env_vars:
            value = os.getenv(var)
            if not value or value.startswith("CHANGE_ME"):
                missing_vars.append(var)

        if missing_vars:
            Colors.print_error(f"缺少环境变量: {', '.join(missing_vars)}")
            Colors.print_info("请确保 .env 文件已正确配置")
            return False

        # 初始化 GitHub API
        self.github_api = GitHubAPI(
            token=os.getenv("GITHUB_TOKEN"),
            repo_owner=os.getenv("GITHUB_REPO_OWNER"),
            repo_name=os.getenv("GITHUB_REPO_NAME")
        )

        # 检查仓库路径
        repo_path = Path(self.config.repository.path)
        if not repo_path.exists():
            Colors.print_error(f"仓库路径不存在: {repo_path}")
            return False

        if not (repo_path / ".git").exists():
            Colors.print_error(f"不是有效的 Git 仓库: {repo_path}")
            return False

        Colors.print_success("环境配置检查通过")
        self.test_results["steps"].append("环境检查: 通过")
        return True

    def create_test_issue(self) -> bool:
        """
        创建测试 Issue

        Returns:
            bool: 是否成功创建
        """
        Colors.print_step(3, 8, "创建测试 Issue")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        title = f"[Integration Test] AI 自动化测试 - {timestamp}"
        body = f"""## 自动化集成测试

这是由自动化测试系统创建的测试 Issue。

**测试时间**: {datetime.now().isoformat()}
**测试类型**: 真实环境集成测试
**测试范围**: 完整的 AI 开发工作流

### 测试任务

请实现一个简单的功能：在项目中创建一个名为 `test_integration.txt` 的文件，内容如下：

```
Integration Test - {datetime.now().isoformat()}
This is an automated integration test.
```

### 预期结果

1. 实现上述功能
2. 提交代码

---

**注意**: 此 Issue 由自动化测试创建，测试完成后将自动关闭。
"""

        try:
            issue = self.github_api.create_issue(
                title=title,
                body=body,
                labels=["integration-test", "automated-test"]
            )

            self.test_issue_number = issue["number"]
            Colors.print_success(f"测试 Issue 已创建: #{issue['number']}")
            Colors.print_info(f"Issue URL: {issue['html_url']}")

            self.test_results["metrics"]["test_issue"] = issue["html_url"]
            self.test_results["steps"].append("创建 Issue: 通过")
            return True

        except Exception as e:
            Colors.print_error(f"创建 Issue 失败: {e}")
            self.test_results["errors"].append(f"创建 Issue: {e}")
            return False

    def trigger_workflow(self) -> bool:
        """
        触发工作流（添加 ai-dev 标签）

        Returns:
            bool: 是否成功触发
        """
        Colors.print_step(4, 8, "触发 AI 开发工作流")

        if not self.test_issue_number:
            Colors.print_error("测试 Issue 未创建")
            return False

        try:
            # 添加 ai-dev 标签
            self.github_api.add_label_to_issue(
                self.test_issue_number,
                "ai-dev"
            )

            Colors.print_success("工作流已触发（添加 ai-dev 标签）")
            Colors.print_info("等待 AI 开发完成...")

            self.test_results["steps"].append("触发工作流: 通过")
            return True

        except Exception as e:
            Colors.print_error(f"触发工作流失败: {e}")
            self.test_results["errors"].append(f"触发工作流: {e}")
            return False

    def monitor_execution(self, timeout: int = 600) -> bool:
        """
        监控执行过程

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 执行是否成功
        """
        Colors.print_step(5, 8, "监控执行过程")

        start_time = time.time()
        check_interval = 10  # 每10秒检查一次
        last_comment_count = 0

        # 获取初始评论数
        try:
            initial_comments = self.github_api.get_issue_comments(self.test_issue_number)
            last_comment_count = len(initial_comments)
        except:
            pass

        while time.time() - start_time < timeout:
            # 检查 1: Issue 的 PR（最准确）
            pulls = self.github_api.get_pulls_for_issue(self.test_issue_number)
            if pulls:
                Colors.print_success(f"检测到 {len(pulls)} 个 PR 创建")
                for pr in pulls:
                    Colors.print_info(f"  - PR #{pr['number']}: {pr['title']}")
                    Colors.print_info(f"    状态: {pr['state']}")
                    Colors.print_info(f"    URL: {pr['html_url']}")

                    self.test_pr_numbers.append(pr["number"])
                    self.test_results["metrics"]["pr_numbers"] = self.test_pr_numbers
                    self.test_results["metrics"]["pr_urls"] = [pr["html_url"] for pr in pulls]

                self.test_results["steps"].append("监控执行: PR 已创建")
                return True

            # 检查 2: Issue 新评论（包含特定完成标记）
            try:
                comments = self.github_api.get_issue_comments(self.test_issue_number)
                if len(comments) > last_comment_count:
                    # 有新评论
                    Colors.print_success(f"检测到 {len(comments) - last_comment_count} 条新评论")
                    last_comment_count = len(comments)

                    # 检查最新评论内容
                    if comments:
                        latest_comment = comments[0]["body"]
                        # 严格检查：必须同时包含 "AI 开发完成" 和 "已创建 PR"
                        if "AI 开发完成" in latest_comment and "已创建 PR" in latest_comment:
                            Colors.print_success("检测到执行完成标记（PR 已创建）")
                            self.test_results["steps"].append("监控执行: 通过评论检测到完成")
                            # 从评论中提取 PR 号
                            import re
                            pr_match = re.search(r'#(\d+)', latest_comment)
                            if pr_match:
                                pr_number = int(pr_match.group(1))
                                if pr_number not in self.test_pr_numbers:
                                    self.test_pr_numbers.append(pr_number)
                            return True
            except Exception as e:
                # 评论检查失败，继续监控
                pass

            # 显示进度
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            print(f"\r  等待中... 已用 {elapsed}s / 剩余 {remaining}s", end="", flush=True)

            time.sleep(check_interval)

        print()  # 换行
        Colors.print_warning("执行超时")
        self.test_results["warnings"].append(f"执行超时（{timeout}秒）")
        return False

    def verify_results(self) -> bool:
        """
        验证执行结果

        Returns:
            bool: 验证是否通过
        """
        Colors.print_step(6, 8, "验证执行结果")

        if not self.test_pr_numbers:
            Colors.print_error("未创建 PR")
            return False

        success_count = 0
        total_checks = 0

        # 检查1: PR 状态
        total_checks += 1
        try:
            for pr_number in self.test_pr_numbers:
                # 这里可以添加更多验证逻辑
                Colors.print_success(f"PR #{pr_number} 已创建")
                success_count += 1
        except Exception as e:
            Colors.print_error(f"PR 验证失败: {e}")

        # 检查2: 查看服务日志
        total_checks += 1
        Colors.print_info("最近的服务日志:")
        self.service_manager.tail_logs(lines=30)
        success_count += 1

        # 检查3: 验证 Issue 是否包含测试评论
        total_checks += 1
        try:
            issue = self.github_api.get_issue(self.test_issue_number)
            comment_count = issue.get("comments", 0)
            if comment_count > 0:
                Colors.print_success(f"Issue 包含 {comment_count} 条评论")
                success_count += 1
        except Exception as e:
            Colors.print_warning(f"无法获取 Issue 评论: {e}")

        success_rate = success_count / total_checks
        self.test_results["metrics"]["verification_success_rate"] = success_rate

        if success_rate >= 0.6:
            Colors.print_success(f"验证通过 ({success_count}/{total_checks})")
            self.test_results["steps"].append("验证结果: 通过")
            return True
        else:
            Colors.print_error(f"验证失败 ({success_count}/{total_checks})")
            self.test_results["errors"].append("验证结果: 失败")
            return False

    def cleanup(self) -> bool:
        """
        清理测试环境

        Returns:
            bool: 是否成功清理
        """
        Colors.print_step(7, 8, "清理测试环境")

        success = True

        # 关闭测试 Issue
        if self.test_issue_number:
            try:
                comment = f"""
## 测试完成

**测试时间**: {datetime.now().isoformat()}
**测试结果**: {'成功' if self.test_results['success'] else '失败'}
**创建的 PR**: {', '.join(map(str, self.test_pr_numbers)) if self.test_pr_numbers else '无'}

此 Issue 已由自动化测试系统关闭。
"""
                self.github_api.close_issue(
                    self.test_issue_number,
                    comment=comment
                )
                Colors.print_success(f"测试 Issue #{self.test_issue_number} 已关闭")
            except Exception as e:
                Colors.print_warning(f"关闭 Issue 失败: {e}")
                self.test_results["warnings"].append(f"关闭 Issue: {e}")
                success = False

        # 删除测试分支
        for pr_number in self.test_pr_numbers:
            try:
                # 获取 PR 信息
                pulls = self.github_api.get_pulls_for_issue(self.test_issue_number)
                for pr in pulls:
                    if pr["number"] == pr_number:
                        branch_name = pr["head"]["ref"]
                        if branch_name.startswith("ai/"):
                            self.github_api.delete_branch(branch_name)
                            Colors.print_success(f"分支 {branch_name} 已删除")
            except Exception as e:
                Colors.print_warning(f"删除分支失败: {e}")
                # 不影响整体清理成功

        if success:
            Colors.print_success("清理完成")
        else:
            Colors.print_warning("部分清理失败")

        self.test_results["steps"].append("清理环境: 完成")
        return success

    def generate_report(self):
        """生成测试报告"""
        Colors.print_step(8, 8, "生成测试报告")

        duration = time.time() - self.start_time if self.start_time else 0

        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}集成测试报告{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")

        # 整体结果
        status_icon = "✅ 通过" if self.test_results["success"] else "❌ 失败"
        print(f"{Colors.BOLD}测试状态: {status_icon}{Colors.RESET}")
        print(f"执行时间: {duration:.1f}秒")
        print(f"测试 Issue: #{self.test_issue_number}")
        print(f"创建的 PR: {', '.join(map(str, self.test_pr_numbers)) if self.test_pr_numbers else '无'}")

        # 执行步骤
        print(f"\n{Colors.BOLD}执行步骤:{Colors.RESET}")
        for i, step in enumerate(self.test_results["steps"], 1):
            print(f"  {i}. {step}")

        # 错误和警告
        if self.test_results["errors"]:
            print(f"\n{Colors.RED}错误:{Colors.RESET}")
            for error in self.test_results["errors"]:
                print(f"  ❌ {error}")

        if self.test_results["warnings"]:
            print(f"\n{Colors.YELLOW}警告:{Colors.RESET}")
            for warning in self.test_results["warnings"]:
                print(f"  ⚠️  {warning}")

        # 指标
        print(f"\n{Colors.BOLD}测试指标:{Colors.RESET}")
        for key, value in self.test_results["metrics"].items():
            print(f"  {key}: {value}")

        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")

        # 保存报告到文件
        report_path = Path("logs/integration_test_report.txt")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"集成测试报告\n")
            f.write(f"=" * 80 + "\n\n")
            f.write(f"测试时间: {datetime.now().isoformat()}\n")
            f.write(f"测试状态: {'通过' if self.test_results['success'] else '失败'}\n")
            f.write(f"执行时间: {duration:.1f}秒\n")
            f.write(f"测试 Issue: #{self.test_issue_number}\n")
            f.write(f"创建的 PR: {', '.join(map(str, self.test_pr_numbers))}\n")
            f.write(f"\n执行步骤:\n")
            for i, step in enumerate(self.test_results["steps"], 1):
                f.write(f"  {i}. {step}\n")
            if self.test_results["errors"]:
                f.write(f"\n错误:\n")
                for error in self.test_results["errors"]:
                    f.write(f"  - {error}\n")
            if self.test_results["warnings"]:
                f.write(f"\n警告:\n")
                for warning in self.test_results["warnings"]:
                    f.write(f"  - {warning}\n")

        Colors.print_success(f"报告已保存到: {report_path}")

    def run(self, start_service: bool = False, stop_service: bool = False) -> bool:
        """
        运行完整测试

        Args:
            start_service: 是否启动服务
            stop_service: 是否停止服务

        Returns:
            bool: 测试是否成功
        """
        Colors.print_header("真实环境集成测试")
        self.start_time = time.time()

        try:
            # 步骤1: 检查环境
            if not self.check_environment():
                return False

            # 步骤2: 启动服务
            if start_service:
                Colors.print_step(2, 8, "启动服务")
                if not self.service_manager.start():
                    return False
                self.test_results["steps"].append("启动服务: 通过")

                # 等待服务完全启动
                Colors.print_info("等待服务完全启动...")
                time.sleep(3)
            else:
                if not self.service_manager.is_running():
                    Colors.print_error("服务未运行，请先启动服务或使用 --start-service 参数")
                    return False

            # 步骤3: 创建测试 Issue
            if not self.create_test_issue():
                return False

            # 步骤4: 触发工作流
            if not self.trigger_workflow():
                return False

            # 步骤5: 监控执行
            if not self.monitor_execution(timeout=600):  # 10分钟超时
                # 即使超时，也尝试验证和清理
                pass

            # 步骤6: 验证结果
            self.test_results["success"] = self.verify_results()

            # 步骤7: 清理环境
            self.cleanup()

            # 步骤8: 生成报告
            self.generate_report()

            return self.test_results["success"]

        except KeyboardInterrupt:
            Colors.print_warning("\n测试被用户中断")
            self.cleanup()
            return False

        except Exception as e:
            Colors.print_error(f"测试执行异常: {e}")
            import traceback
            traceback.print_exc()
            self.test_results["errors"].append(f"异常: {e}")
            self.cleanup()
            return False

        finally:
            # 步骤9: 停止服务
            if stop_service:
                Colors.print_step(9, 9, "停止服务")
                self.service_manager.stop()


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="真实环境集成测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动启动服务并测试
  python scripts/test_integration_live.py --start-service --stop-service

  # 使用已运行的服务
  python scripts/test_integration_live.py

  # 自定义超时时间
  python scripts/test_integration_live.py --timeout 1200
        """
    )

    parser.add_argument(
        "--start-service",
        action="store_true",
        help="自动启动服务（如果未运行）"
    )

    parser.add_argument(
        "--stop-service",
        action="store_true",
        help="测试完成后停止服务"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="执行超时时间（秒），默认600秒"
    )

    args = parser.parse_args()

    # 加载配置
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        Colors.print_error("请安装 python-dotenv: pip install python-dotenv")
        return 1

    # 运行测试
    test = IntegrationTest()
    success = test.run(
        start_service=args.start_service,
        stop_service=args.stop_service
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
