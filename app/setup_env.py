#!/usr/bin/env python3
"""
交互式环境配置脚本

用于创建和配置 .env 文件，支持：
- GitHub 配置（Token、仓库信息、Webhook Secret）
- 本地代码仓库路径
- ngrok 配置（可选，用于 GitHub Webhook）

使用方法：
    python scripts/setup_env.py
"""

import os
import secrets
import sys
from pathlib import Path
from typing import Optional


class Colors:
    """终端颜色常量 - 明亮莫兰迪色系"""

    # 明亮莫兰迪色系 - 清新、明亮、柔和
    HEADER = "\033[38;5;177m"      # 明亮莫兰迪粉紫
    OKBLUE = "\033[38;5;117m"      # 明亮莫兰迪天蓝
    OKCYAN = "\033[38;5;152m"      # 明亮莫兰迪青绿
    OKGREEN = "\033[38;5;158m"     # 明亮莫兰迪薄荷绿
    WARNING = "\033[38;5;228m"     # 明亮莫兰迪暖黄
    FAIL = "\033[38;5;211m"        # 明亮莫兰迪玫瑰红
    INFO = "\033[38;5;145m"        # 明亮莫兰迪薰衣草
    ENDC = "\033[0m"               # 重置颜色
    BOLD = "\033[1m"               # 粗体
    UNDERLINE = "\033[4m"          # 下划线


def print_header(text: str) -> None:
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^10}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(text: str) -> None:
    """打印成功消息"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """打印错误消息"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """打印警告消息"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """打印信息消息"""
    print(f"{Colors.INFO}ℹ {text}{Colors.ENDC}")


def input_required(prompt: str, default: Optional[str] = None) -> str:
    """
    必填输入，带验证

    Args:
        prompt: 提示文本
        default: 默认值

    Returns:
        用户输入的值
    """
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip() or default
        else:
            user_input = input(f"{prompt}: ").strip()

        if user_input:
            return user_input

        print_error("此项为必填，请输入有效值。")


def input_yes_no(prompt: str, default: bool = False) -> bool:
    """
    是/否选择

    Args:
        prompt: 提示文本
        default: 默认值

    Returns:
        用户选择（True/False）
    """
    default_str = "Y/n" if default else "y/N"
    while True:
        user_input = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not user_input:
            return default

        if user_input in ["y", "yes", "是", "Y"]:
            return True
        elif user_input in ["n", "no", "否", "N"]:
            return False

        print_error("请输入 y/yes 或 n/no")


def generate_webhook_secret() -> str:
    """生成安全的 Webhook Secret"""
    return secrets.token_hex(32)


async def validate_github_token_with_api(token: str) -> tuple[bool, str]:
    """
    验证 GitHub Token（通过 API 调用）

    Args:
        token: GitHub Token

    Returns:
        (是否有效, 错误消息)
    """
    try:
        from app.services.github_service import GitHubService

        github = GitHubService(token)
        is_valid = await github.authenticate()

        if is_valid:
            return True, ""
        else:
            return False, "Token 验证失败：无效或权限不足"

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Bad credentials" in error_msg:
            return False, "Token 无效，请检查是否正确"
        elif "403" in error_msg:
            return False, "Token 权限不足，请确认具有 repo 权限"
        else:
            return False, f"验证失败: {error_msg}"


def validate_github_token(token: str) -> bool:
    """
    验证 GitHub Token 格式

    Args:
        token: GitHub Token

    Returns:
        是否有效
    """
    # Classic token 格式：ghp_ 后跟至少 32 个字符
    if token.startswith("ghp_") and len(token) >= 36:
        return True

    # Fine-grained token 格式：github_pat_ 后跟至少 62 个字符
    if token.startswith("github_pat_") and len(token) >= 73:
        return True

    return False


def validate_repo_path(path: str) -> tuple[bool, str]:
    """
    验证仓库路径

    Args:
        path: 仓库路径

    Returns:
        (是否有效, 错误消息)
    """
    try:
        # 先使用 os.path.expanduser()，它比 Path.expanduser() 更健壮
        # 能够处理 HOME 环境变量未设置的情况
        expanded = os.path.expanduser(path)
        path_obj = Path(expanded).resolve()
    except (RuntimeError, OSError) as e:
        return False, f"无法展开路径: {e}"

    if not path_obj.exists():
        return False, f"路径不存在: {path_obj}"

    if not (path_obj / ".git").exists():
        return False, f"不是有效的 Git 仓库（缺少 .git 目录）: {path_obj}"

    return True, ""


async def setup_github_config() -> dict:
    """
    配置 GitHub 相关设置

    Returns:
        GitHub 配置字典
    """
    print_header("GitHub 配置")

    config = {}

    # GitHub Token
    print_info("GitHub Personal Access Token (PAT)")
    print("  获取方式：")
    print("    1. 访问 https://github.com")
    print("    2. 点击头像 → Settings → Developer settings")
    print("    3. Personal access tokens → Fine-grained tokens")
    print("    4. 生成新 token，需要以下权限：")
    print("       ✓ Contents (Read and write)")
    print("       ✓ Pull requests (Read and write)")
    print("       ✓ Issues (Read and write)")
    print()

    while True:
        token = input_required("请输入 GitHub Token (以 ghp_ 或 github_pat_ 开头)")

        # 先验证格式
        if not validate_github_token(token):
            print_error("GitHub Token 格式无效")
            print_info("Classic token 格式: ghp_XXXXXXXXXXXXXXXX (至少 36 字符)")
            print_info("Fine-grained token 格式: github_pat_XXXXXXXXXXXXXXXX (至少 73 字符)")
            continue

        # 再验证 API
        print_info("正在验证 Token...")
        is_valid, error_msg = await validate_github_token_with_api(token)

        if is_valid:
            config["GITHUB_TOKEN"] = token
            print_success("GitHub Token 验证通过")
            break
        else:
            print_error(f"GitHub Token 验证失败: {error_msg}")

    print()

    # 仓库信息
    print_info("GitHub 仓库信息")
    print("  示例：https://github.com/octocat/Hello-World")
    print()

    # 提供两种输入方式
    use_url = input_yes_no("是否通过 GitHub URL 配置？", default=True)

    if use_url:
        # 通过 URL 解析
        while True:
            url = input_required(
                "请输入 GitHub 仓库 URL (例如: https://github.com/octocat/Hello-World)"
            ).strip()

            # 移除末尾的 .git
            if url.endswith(".git"):
                url = url[:-4]

            # 解析 URL
            # 支持 https://github.com/owner/repo 和 github.com/owner/repo 格式
            import re

            pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+)/?"
            match = re.match(pattern, url)

            if match:
                config["GITHUB_REPO_OWNER"] = match.group(1)
                config["GITHUB_REPO_NAME"] = match.group(2)
                print_success(
                    f"解析成功: {config['GITHUB_REPO_OWNER']} / {config['GITHUB_REPO_NAME']}"
                )
                break
            else:
                print_error("无法解析 GitHub URL，请检查格式是否正确")
                print_info("正确格式示例: https://github.com/octocat/Hello-World")

                retry = input_yes_no("是否重新输入？", default=True)
                if not retry:
                    # 切换到手动输入
                    print_info("切换到手动输入模式")
                    break
    else:
        # 手动输入
        print_info("手动输入仓库信息")
        print()

    # 如果通过 URL 解析失败或用户选择手动输入
    if "GITHUB_REPO_OWNER" not in config:
        config["GITHUB_REPO_OWNER"] = input_required("请输入仓库所有者用户名 (GITHUB_REPO_OWNER)")
        config["GITHUB_REPO_NAME"] = input_required("请输入仓库名称 (GITHUB_REPO_NAME)")

    print()

    # Webhook Secret
    print_info("GitHub Webhook Secret")
    print("  用于验证 GitHub Webhook 请求的来源")
    print("  建议使用自动生成的强随机密钥")
    print()

    use_auto_secret = input_yes_no("是否自动生成 Webhook Secret？", default=True)

    if use_auto_secret:
        config["GITHUB_WEBHOOK_SECRET"] = generate_webhook_secret()
        print_success(f"已自动生成 Webhook Secret: {config['GITHUB_WEBHOOK_SECRET'][:16]}...")
    else:
        while True:
            secret = input_required("请输入 Webhook Secret (至少 64 个字符)")
            if len(secret) >= 64:
                config["GITHUB_WEBHOOK_SECRET"] = secret
                print_success("Webhook Secret 已设置")
                break
            else:
                print_error("Webhook Secret 长度不足，至少需要 64 个字符")

    print()

    return config


async def setup_repo_path() -> dict:
    """
    配置本地代码仓库路径

    Returns:
        仓库路径配置字典
    """
    print_header("本地代码仓库配置")

    config = {}

    print_info("本地 Git 仓库路径")
    print("  需要本地有对应的 Git 仓库，Claude Code 将在此路径进行开发")
    print("  路径必须是绝对路径")
    print()

    while True:
        path = input_required("请输入本地仓库路径 (REPO_PATH)")
        is_valid, error_msg = validate_repo_path(path)

        if is_valid:
            # 使用 os.path.expanduser() 确保路径展开健壮性
            expanded_path = os.path.expanduser(path)
            config["REPO_PATH"] = str(Path(expanded_path).resolve())
            print_success(f"仓库路径验证通过: {config['REPO_PATH']}")
            break
        else:
            print_error(error_msg)
            retry = input_yes_no("是否重新输入？", default=True)
            if not retry:
                print_warning("跳过仓库路径配置（您需要稍后手动配置）")
                break

    print()

    return config


async def setup_ngrok() -> dict:
    """
    配置 ngrok（可选）

    Returns:
        ngrok 配置字典
    """
    print_header("ngrok 配置（可选）")

    config = {}

    print_info("ngrok 简介")
    print("  ngrok 可以将本地服务暴露到公网，用于接收 GitHub Webhook")
    print("  如果您不使用 ngrok，需要手动配置 GitHub Webhook URL")
    print()

    use_ngrok = input_yes_no("是否需要配置 ngrok？", default=False)

    if not use_ngrok:
        print_info("跳过 ngrok 配置")
        print()
        return config

    # ngrok auth token
    print_info("ngrok Authtoken")
    print("  获取方式：")
    print("    1. 访问 https://dashboard.ngrok.com/get-started/your-authtoken")
    print("    2. 登录后复制 authtoken")
    print()

    config["NGROK_AUTH_TOKEN"] = input_required("请输入 ngrok authtoken")

    # ngrok domain (可选)
    print_info("ngrok 固定域名（可选）")
    print("  如果有付费的 ngrok 固定域名，可以在此配置")
    print("  免费版本每次启动域名会变化，可以留空")
    print()

    domain = input("请输入 ngrok 固定域名（可选，直接回车跳过）: ").strip()
    if domain:
        config["NGROK_DOMAIN"] = domain

    print()
    print_success("ngrok 配置完成")

    return config


def write_env_file(config: dict, env_file: Path) -> None:
    """
    写入 .env 文件

    Args:
        config: 配置字典
        env_file: .env 文件路径
    """
    print_header("生成 .env 文件")

    # 确保文件存在
    if env_file.exists():
        print_warning(f".env 文件已存在: {env_file}")
        overwrite = input_yes_no("是否覆盖？", default=False)
        if not overwrite:
            print_info("已取消写入")
            return

        # 备份现有文件
        backup_file = env_file.with_suffix(".backup")
        import shutil

        shutil.copy(env_file, backup_file)
        print_success(f"已备份现有配置到: {backup_file}")

    # 写入配置
    with open(env_file, "w", encoding="utf-8") as f:
        f.write("# ============================================================================\n")
        f.write("# AI 开发调度服务 - 环境变量配置\n")
        f.write("# ============================================================================\n")
        f.write("#\n")
        f.write("# 此文件由 scripts/setup_env.py 自动生成\n")
        f.write(
            "# 生成时间: "
            + __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + "\n"
        )
        f.write("#\n")
        f.write("# ⚠️  重要提醒：\n")
        f.write("#   - 永远不要将 .env 文件提交到 Git 仓库\n")
        f.write("#   - 确保 .env 已添加到 .gitignore\n")
        f.write("#   - 定期轮换 API 密钥和 Token\n")
        f.write("#\n")
        f.write(
            "# ============================================================================\n\n"
        )

        # GitHub 配置
        f.write("# ----------------------------------------------------------------------------\n")
        f.write("# GitHub 配置\n")
        f.write(
            "# ----------------------------------------------------------------------------\n\n"
        )
        f.write(f"GITHUB_WEBHOOK_SECRET={config.get('GITHUB_WEBHOOK_SECRET', '')}\n")
        f.write(f"GITHUB_TOKEN={config.get('GITHUB_TOKEN', '')}\n")
        f.write(f"GITHUB_REPO_OWNER={config.get('GITHUB_REPO_OWNER', '')}\n")
        f.write(f"GITHUB_REPO_NAME={config.get('GITHUB_REPO_NAME', '')}\n\n")

        # 仓库路径
        f.write("# ----------------------------------------------------------------------------\n")
        f.write("# 本地代码仓库路径\n")
        f.write(
            "# ----------------------------------------------------------------------------\n\n"
        )
        f.write(f"REPO_PATH={config.get('REPO_PATH', '')}\n\n")

        # ngrok 配置（如果有）
        if "NGROK_AUTH_TOKEN" in config:
            f.write(
                "# ----------------------------------------------------------------------------\n"
            )
            f.write("# ngrok 配置\n")
            f.write(
                "# ----------------------------------------------------------------------------\n\n"
            )
            f.write(f"NGROK_AUTH_TOKEN={config.get('NGROK_AUTH_TOKEN', '')}\n")
            if "NGROK_DOMAIN" in config:
                f.write(f"NGROK_DOMAIN={config.get('NGROK_DOMAIN', '')}\n")
            f.write("\n")

    print_success(f".env 文件已生成: {env_file}")
    print_warning(f"请确保文件权限正确: chmod 600 {env_file}")


def print_github_webhook_guide(config: dict) -> None:
    """打印 GitHub Webhook 配置详细指南"""
    print_header("GitHub Webhook 配置指南")

    webhook_secret = config.get("GITHUB_WEBHOOK_SECRET", "")
    repo_owner = config.get("GITHUB_REPO_OWNER", "")
    repo_name = config.get("GITHUB_REPO_NAME", "")

    print_info("步骤 1: 访问 GitHub 仓库设置")
    print(f"   1. 打开浏览器，访问: https://github.com/{repo_owner}/{repo_name}")
    print("   2. 点击仓库上方的【Settings】标签")
    print("   3. 在左侧菜单中找到【Webhooks】并点击")
    print()

    print_info("步骤 2: 添加新 Webhook")
    print("   1. 点击【Add webhook】按钮")
    print()

    print_info("步骤 3: 配置 Webhook 信息")
    print()

    # Webhook URL
    if "NGROK_AUTH_TOKEN" in config:
        print(f"   {Colors.BOLD}Payload URL{Colors.ENDC}")
        print("     格式: https://<your-ngrok-domain>/webhook/github")
        if "NGROK_DOMAIN" in config:
            print(f"     示例: https://{config.get('NGROK_DOMAIN')}/webhook/github")
        else:
            print("     示例: https://abc123.ngrok.io/webhook/github")
            print("     （启动 ngrok 后会显示你的域名，类似 abc123.ngrok.io）")
        print()
    else:
        print(f"   {Colors.BOLD}Payload URL{Colors.ENDC}")
        print("     格式: http://your-server:8000/webhook/github")
        print("     示例: http://localhost:8000/webhook/github")
        print()

    # Content type
    print(f"   {Colors.BOLD}Content type{Colors.ENDC}")
    print("     选择: application/json")
    print()

    # Secret
    print(f"   {Colors.BOLD}Secret{Colors.ENDC}")
    print(f"     粘贴以下内容（已自动生成）：")
    print(f"     {Colors.OKGREEN}{webhook_secret}{Colors.ENDC}")
    print()
    print_warning("     ⚠️  请妥善保管此密钥，不要泄露给他人！")
    print()

    # Events
    print(f"   {Colors.BOLD}Events{Colors.ENDC}")
    print("     选择: Let me select individual events")
    print("     勾选以下事件：")
    print(f"     {Colors.OKGREEN}☑ Issues{Colors.ENDC}")
    print(f"     {Colors.OKGREEN}☑ Issue comments{Colors.ENDC}")
    print()

    # Active
    print(f"   {Colors.BOLD}Active{Colors.ENDC}")
    print(f"     {Colors.OKGREEN}☑ Active{Colors.ENDC} （默认已勾选）")
    print()

    print_info("步骤 4: 保存配置")
    print("   1. 滚动到页面底部，点击【Add webhook】按钮")
    print("   2. 如果看到绿色勾选标记，说明 Webhook 配置成功！")
    print()

    print_info("步骤 5: 测试 Webhook")
    print("   1. 在 Webhook 列表中找到刚创建的 Webhook")
    print("   2. 点击进入，查看【Recent Deliveries】")
    print("   3. 如果没有测试记录，可以：")
    print("      - 点击【Redeliver】测试最近的事件")
    print("      - 或在仓库中创建新 Issue 触发 Webhook")
    print()


def print_next_steps(config: dict) -> None:
    """打印后续步骤"""
    print_header("配置完成")

    print_success("环境配置已成功创建！")
    print()

    print("后续步骤：")
    print()

    print("1️⃣  验证配置")
    print('   $ python -c "from app.config import load_config; print(load_config())"')
    print()

    print("2️⃣  启动服务")
    print("   $ kaka start")
    print()

    # 如果配置了 ngrok
    repo_full = f"{config.get('GITHUB_REPO_OWNER', '')}/{config.get('GITHUB_REPO_NAME', '')}"
    if "NGROK_AUTH_TOKEN" in config:
        print("3️⃣  启动 ngrok（新终端）")
        print("   $ ngrok http 8000")
        print("   复制显示的转发 URL（例如 https://abc123.ngrok.io）")
        print()
        print("4️⃣  配置 GitHub Webhook")
        print("   （详细指南请见下方）")
        print()
        print("5️⃣  测试功能")
    else:
        print("3️⃣  配置 GitHub Webhook")
        print("   （详细指南请见下方）")
        print()
        print("4️⃣  测试功能")
    print(f"   在 GitHub 仓库 {repo_full} 中创建测试 Issue")
    print("   添加标签 'ai-dev' 或评论 '/ai develop'")
    print()

    print("─" * 70)
    print()

    # 打印详细的 Webhook 配置指南
    print_github_webhook_guide(config)

    print("─" * 70)
    print()

    print("参考文档：")
    print("  📖 README.md: 完整使用指南")
    print("  📖 .env.example: 配置说明")
    print("  📖 docs/SETUP_ENV.md: 环境配置详细文档")
    print()


async def main():
    """主函数"""
    print_header("Kaka：环境配置向导")

    print_info("本向导将帮助您配置 .env 文件")
    print("  所需配置项：")
    print("    ✓ GitHub Token（将进行实际 API 验证）")
    print("    ✓ GitHub 仓库信息")
    print("    ✓ GitHub Webhook Secret")
    print("    ✓ 本地代码仓库路径")
    print("    ○ ngrok 配置（可选）")
    print()

    # 确认开始
    ready = input_yes_no("是否开始配置？", default=True)
    if not ready:
        print_info("已取消配置")
        sys.exit(0)

    print()

    # 收集所有配置
    config = {}

    # GitHub 配置
    github_config = await setup_github_config()
    config.update(github_config)

    # 仓库路径
    repo_config = await setup_repo_path()
    config.update(repo_config)

    # ngrok（可选）
    ngrok_config = await setup_ngrok()
    config.update(ngrok_config)

    # 写入 .env 文件
    env_file = Path(__file__).parent.parent / ".env"
    write_env_file(config, env_file)

    # 打印后续步骤
    print_next_steps(config)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print_warning("\n配置已取消")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"配置失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def test_morandi_colors():
    """测试明亮莫兰迪色系效果"""
    print("\n" + "=" * 70)
    print("明亮莫兰迪色系测试 (Bright Morandi Color Scheme)")
    print("=" * 70 + "\n")

    print(f"{Colors.HEADER}明亮莫兰迪粉紫 (HEADER){Colors.ENDC}")
    print(f"{Colors.OKBLUE}明亮莫兰迪天蓝 (OKBLUE){Colors.ENDC}")
    print(f"{Colors.OKCYAN}明亮莫兰迪青绿 (OKCYAN){Colors.ENDC}")
    print(f"{Colors.OKGREEN}明亮莫兰迪薄荷绿 (OKGREEN){Colors.ENDC}")
    print(f"{Colors.WARNING}明亮莫兰迪暖黄 (WARNING){Colors.ENDC}")
    print(f"{Colors.FAIL}明亮莫兰迪玫瑰红 (FAIL){Colors.ENDC}")
    print(f"{Colors.INFO}明亮莫兰迪薰衣草 (INFO){Colors.ENDC}")

    print("\n" + "-" * 70 + "\n")

    print("实际使用效果：\n")
    print_header("这是一个标题 (HEADER)")
    print_success("这是一个成功消息 (SUCCESS)")
    print_error("这是一个错误消息 (ERROR)")
    print_warning("这是一个警告消息 (WARNING)")
    print_info("这是一个信息消息 (INFO)")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    # 如果传入 --test-colors 参数，则测试颜色
    if len(sys.argv) > 1 and sys.argv[1] == "--test-colors":
        test_morandi_colors()
        sys.exit(0)

    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print_warning("\n配置已取消")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"配置失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
