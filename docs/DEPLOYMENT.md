# 部署指南

本文档说明如何在生产环境中部署 Kaka AI Dev。

## 目录

- [Docker 部署](#docker-部署)
- [进程管理器](#进程管理器)
- [Nginx 反向代理](#nginx-反向代理)
- [性能优化](#性能优化)
- [安全加固](#安全加固)

---

## Docker 部署

### 1. 创建 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 安装 Claude Code CLI
RUN npm install -g @anthropic/claude-code

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  ai-scheduler:
    build: .
    container_name: kaka-ai-dev
    ports:
      - "8000:8000"
    environment:
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_REPO_OWNER=${GITHUB_REPO_OWNER}
      - GITHUB_REPO_NAME=${GITHUB_REPO_NAME}
      - REPO_PATH=/app/repo
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./repo:/app/repo
    restart: unless-stopped
```

### 3. 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 进程管理器

### Supervisor

创建 `/etc/supervisor/conf.d/kaka-ai-dev.conf`：

```ini
[program:kaka-ai-dev]
command=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/path/to/kaka
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/kaka-ai-dev.log
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start kaka-ai-dev
```

### Systemd

创建 `/etc/systemd/system/kaka-ai-dev.service`：

```ini
[Unit]
Description=Kaka AI Dev Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/kaka
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable kaka-ai-dev
sudo systemctl start kaka-ai-dev
sudo systemctl status kaka-ai-dev
```

---

## Nginx 反向代理

创建 `/etc/nginx/sites-available/kaka-ai-dev`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /webhook/github {
        proxy_pass http://127.0.0.1:8000/webhook/github;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/kaka-ai-dev /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL/HTTPS 配置

使用 Let's Encrypt 获取免费证书：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 性能优化

### 1. 使用 Gunicorn + Uvicorn Workers

```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

### 2. 启用缓存

在 `config.yaml` 中：

```yaml
performance:
  enable_cache: true
  cache_ttl: 3600
```

### 3. 调整日志级别

生产环境使用 `INFO` 或 `WARNING`：

```yaml
logging:
  level: "INFO"
```

### 4. 配置 CORS 限制

仅允许特定域名：

```yaml
security:
  cors_origins:
    - "https://your-domain.com"
```

---

## 安全加固

### 1. 使用强密钥

```bash
# 生成 64 字符的随机密钥
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. 限制 IP 白名单

```yaml
security:
  ip_whitelist:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
```

### 3. 启用基本认证

```yaml
security:
  enable_basic_auth: true
  basic_auth_username: "${BASIC_AUTH_USERNAME}"
  basic_auth_password: "${BASIC_AUTH_PASSWORD}"
```

### 4. 配置防火墙

```bash
# 仅允许特定端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 5. 定期更新依赖

```bash
# 更新 pip
pip install --upgrade pip

# 更新依赖
pip install --upgrade -r requirements.txt
```

---

## 下一步

- [安全建议](SECURITY.md) - 详细安全指南
- [故障排查](TROUBLESHOOTING.md) - 问题解决
