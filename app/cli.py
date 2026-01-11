"""
Kaka Dev CLI
命令行工具入口
"""

import click
import webbrowser
import threading
import time


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Kaka Dev - AI 开发调度服务

    通过 GitHub Webhook 自动调用 Claude Code CLI 进行开发
    """
    pass


@cli.command()
@click.option('--host', default='127.0.0.1', help='绑定的主机地址')
@click.option('--port', default=8000, type=int, help='绑定的端口')
@click.option('--reload', is_flag=True, help='启用自动重载（开发模式）')
def start(host, port, reload):
    """启动服务

    启动 FastAPI 服务器
    """
    import uvicorn

    click.echo(f"🚀 启动 Kaka Dev...")
    click.echo(f"")
    click.echo(f"📍 Dashboard: http://{host}:{port}/dashboard")
    click.echo(f"📍 API 文档: http://{host}:{port}/docs")
    click.echo(f"📍 Webhook: http://{host}:{port}/webhook/github")
    click.echo(f"")
    click.echo(f"按 Ctrl+C 停止服务")
    click.echo(f"")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


@cli.command()
def configure():
    """打开配置向导

    在浏览器中打开配置页面
    """
    import uvicorn
    from app.main import app

    click.echo(f"🚀 启动配置向导...")

    # 在后台启动服务器
    def run_server():
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="error"  # 减少日志输出
        )

    server = threading.Thread(target=run_server, daemon=True)
    server.start()

    # 等待服务器启动
    click.echo(f"⏳ 等待服务启动...")
    time.sleep(2)

    # 打开浏览器
    url = "http://127.0.0.1:8000/config"
    click.echo(f"🌐 打开浏览器: {url}")
    click.echo(f"")

    try:
        webbrowser.open(url)
    except Exception as e:
        click.echo(f"⚠️  无法自动打开浏览器: {e}")
        click.echo(f"请手动访问: {url}")

    click.echo(f"")
    click.echo(f"配置向导已在后台运行。按 Ctrl+C 退出。")

    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo(f"\n👋 配置向导已关闭")


@cli.command()
@click.argument('action', type=click.Choice(['export', 'import']))
def config(action):
    """导出或导入配置

    备份或恢复配置到 JSON 文件
    """
    import json
    from pathlib import Path

    if action == 'export':
        try:
            from app.config import get_config

            config = get_config()

            data = {
                "github": {
                    "token": config.github.token,
                    "repo_owner": config.github.repo_owner,
                    "repo_name": config.github.repo_name,
                    "webhook_secret": config.github.webhook_secret,
                },
                "repository": {
                    "path": str(config.repository.path),
                    "default_branch": config.repository.default_branch,
                },
                "claude": {
                    "api_key": config.claude.api_key if hasattr(config.claude, 'api_key') else "",
                }
            }

            config_file = Path.home() / 'kaka-config.json'
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            click.echo(f"✅ 配置已导出到: {config_file}")

        except Exception as e:
            click.echo(f"❌ 导出失败: {e}", err=True)

    elif action == 'import':
        config_file = Path.home() / 'kaka-config.json'

        if not config_file.exists():
            click.echo(f"❌ 配置文件不存在: {config_file}")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            click.echo(f"📋 配置内容:")
            click.echo(f"  仓库: {data['github']['repo_owner']}/{data['github']['repo_name']}")
            click.echo(f"  路径: {data['repository']['path']}")
            click.echo(f"")
            click.echo(f"请手动将这些配置添加到 .env 文件中")

        except Exception as e:
            click.echo(f"❌ 导入失败: {e}", err=True)


@cli.command()
def status():
    """查看配置状态

    检查当前配置是否完整
    """
    try:
        from app.config import get_config

        config = get_config()

        click.echo(f"✅ 配置状态: 已配置")
        click.echo(f"")
        click.echo(f"仓库: {config.github.repo_full_name}")
        click.echo(f"路径: {config.repository.path}")
        click.echo(f"分支: {config.repository.default_branch}")
        click.echo(f"触发标签: {config.github.trigger_label}")
        click.echo(f"最大并发: {config.task.max_concurrent}")

    except Exception as e:
        click.echo(f"❌ 配置状态: 未配置")
        click.echo(f"")
        click.echo(f"错误: {e}")
        click.echo(f"")
        click.echo(f"请运行: kaka configure")


@cli.command()
@click.option('--lines', default=20, help='显示的日志行数')
def logs(lines):
    """查看最近的日志

    显示最近的日志条目
    """
    from pathlib import Path

    log_file = Path("logs/ai-scheduler.log")

    if not log_file.exists():
        click.echo(f"❌ 日志文件不存在: {log_file}")
        return

    try:
        import subprocess

        subprocess.run(['tail', f'-n{lines}', str(log_file)])

    except Exception as e:
        click.echo(f"❌ 无法读取日志: {e}")


if __name__ == '__main__':
    cli()
