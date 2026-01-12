"""
配置管理模块

负责加载和管理应用程序配置，支持 YAML 配置文件和环境变量。
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class ServerConfig(BaseModel):
    """服务器配置"""

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1


class GitHubConfig(BaseModel):
    """GitHub 配置"""

    webhook_secret: str
    token: str
    repo_owner: str
    repo_name: str
    trigger_label: str = "ai-dev"
    trigger_command: str = "/ai develop"

    @field_validator("webhook_secret", "token", mode="before")
    @classmethod
    def validate_required_env(cls, v: str, info: dict) -> str:
        """验证必需的环境变量"""
        field_name = info.field_name
        if not v or v.startswith("${"):
            # 提供更友好的错误消息，包含字段名映射
            field_display_name = {
                "webhook_secret": "GITHUB_WEBHOOK_SECRET",
                "token": "GITHUB_TOKEN",
            }.get(field_name, field_name)

            raise ValueError(
                f"{field_display_name} 未配置或为空。"
                f"请在 .env 文件中设置 {field_display_name} 环境变量。"
            )
        return v

    @property
    def repo_full_name(self) -> str:
        """获取完整的仓库名称"""
        return f"{self.repo_owner}/{self.repo_name}"


class RepositoryConfig(BaseModel):
    """代码仓库配置"""

    path: Path
    default_branch: str = "main"
    remote_name: str = "origin"

    @field_validator("path", mode="before")
    @classmethod
    def validate_path(cls, v: str) -> Path:
        """验证仓库路径"""
        if not v or v.startswith("${"):
            raise ValueError("REPO_PATH 未配置。" "请在 .env 文件中设置 REPO_PATH 环境变量。")
        path = Path(v).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"仓库路径不存在: {path}")
        if not (path / ".git").exists():
            raise ValueError(f"路径不是有效的 Git 仓库: {path}")
        return path


class ClaudeConfig(BaseModel):
    """Claude Code 配置"""

    timeout: int = 1800  # 30 分钟
    max_retries: int = 2
    auto_test: bool = True
    cli_path: str = "claude"
    cwd: Optional[Path] = None
    dangerously_skip_permissions: bool = True  # 跳过权限检查

    @field_validator("cwd", mode="before")
    @classmethod
    def validate_cwd(cls, v: Optional[str]) -> Optional[Path]:
        """验证工作目录"""
        if v is None:
            return None
        return Path(v).expanduser().resolve()


class TaskConfig(BaseModel):
    """任务配置"""

    branch_template: str = "ai/feature-{issue_number}-{timestamp}"
    commit_template: str = "AI: {issue_title}"
    max_concurrent: int = 1
    queue_size: int = 10


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = "INFO"
    file: str = "logs/kaka.log"
    max_bytes: int = 10485760  # 10 MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    console: bool = True
    json_output: bool = Field(default=False, alias="json")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}. 必须是 {valid_levels} 之一")
        return v_upper


class SecurityConfig(BaseModel):
    """安全配置"""

    enable_basic_auth: bool = False
    basic_auth_username: Optional[str] = None
    basic_auth_password: Optional[str] = None
    ip_whitelist: list[str] = []
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]  # 默认仅允许本地开发


class PerformanceConfig(BaseModel):
    """性能配置"""

    enable_cache: bool = True
    cache_ttl: int = 3600
    enable_metrics: bool = True
    metrics_path: str = "/metrics"


class NotificationConfig(BaseModel):
    """通知配置"""

    enabled: bool = False
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#ai-dev"
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class Config(BaseModel):
    """应用程序主配置"""

    server: ServerConfig = Field(default_factory=ServerConfig)
    github: GitHubConfig
    repository: RepositoryConfig
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    task: TaskConfig = Field(default_factory=TaskConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)


def load_env_var(value: str) -> str:
    """
    从环境变量加载值

    支持的格式:
    - ${VAR_NAME}
    - ${VAR_NAME:default_value}
    """
    if not isinstance(value, str):
        return value

    # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default}
    pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"

    def replace_env(match: re.Match) -> str:
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ""
        return os.getenv(var_name, default_value)

    return re.sub(pattern, replace_env, value)


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认为 config/config.yaml

    Returns:
        Config: 配置对象

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置验证失败
    """
    if config_path is None:
        config_path = Path("config/config.yaml")

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    # 加载 YAML 文件
    with open(config_path, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # 解析 YAML
    raw_config = yaml.safe_load(yaml_content)

    # 替换环境变量
    env_config = _replace_env_vars(raw_config)

    # 验证并创建配置对象
    try:
        return Config(**env_config)
    except Exception as e:
        raise ValueError(f"配置验证失败: {e}") from e


def _replace_env_vars(obj: Any) -> Any:
    """递归替换对象中的环境变量引用"""

    if isinstance(obj, dict):
        return {k: _replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        return load_env_var(obj)
    else:
        return obj


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例

    Returns:
        Config: 配置对象

    Raises:
        RuntimeError: 配置未初始化
    """
    global _config
    if _config is None:
        # 尝试从默认路径加载
        try:
            _config = load_config()
        except Exception as e:
            raise RuntimeError(f"配置未初始化，且无法从默认路径加载: {e}") from e
    return _config


def init_config(config_path: Optional[Path] = None) -> Config:
    """
    初始化全局配置

    Args:
        config_path: 配置文件路径

    Returns:
        Config: 配置对象
    """
    global _config
    _config = load_config(config_path)
    return _config
