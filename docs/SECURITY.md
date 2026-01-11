# 安全建议

本文档提供安全加固建议，保护 Kaka AI Dev 系统安全。

## 目录

- [Webhook 安全](#webhook-安全)
- [API 安全](#api-安全)
- [数据安全](#数据安全)
- [网络安全](#网络安全)

---

## Webhook 安全

### 1. 始终验证签名

- ✅ 使用 HMAC-SHA256 验证所有 Webhook 请求
- ❌ 不要禁用签名验证（仅限开发环境）

### 2. 使用强密钥

```bash
# 生成 64 字符的随机密钥
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. 限制 IP 白名单（可选）

在 `config/config.yaml` 中配置：

```yaml
security:
  ip_whitelist:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
```

### 4. 定期轮换密钥

- 每 90 天轮换 Webhook Secret
- 生成新密钥后，记得更新 GitHub Webhook 配置

---

## API 安全

### 1. 使用最小权限原则

- GitHub Token 仅授予必要的权限
- 使用专用服务账号
- 定期审查 Token 权限

### 2. 启用基本认证（可选）

在 `config/config.yaml` 中配置：

```yaml
security:
  enable_basic_auth: true
  basic_auth_username: "${BASIC_AUTH_USERNAME}"
  basic_auth_password: "${BASIC_AUTH_PASSWORD}"
```

### 3. 限制 CORS 来源

```yaml
security:
  cors_origins:
    - "https://your-domain.com"
```

### 4. 启用速率限制

系统默认已启用速率限制：
- 默认限制: 60 次/分钟
- Webhook 限制: 10 次/分钟

可在 `app/main.py` 中调整。

---

## 数据安全

### 1. 保护敏感信息

- ✅ 使用环境变量存储密钥
- ✅ `.env` 文件已添加到 `.gitignore`
- ❌ 不要将 `.env` 文件提交到版本控制
- ❌ 不要在代码中硬编码密钥

### 2. .gitignore 配置

确保 `.gitignore` 包含：

```
# 环境变量
.env
.env.local
.env.*.local

# 日志
logs/
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 虚拟环境
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# macOS
.DS_Store

# 测试和覆盖率
.coverage
.pytest_cache/
htmlcov/
```

### 3. 定期轮换密钥

建议周期：

- **GitHub Token**: 每 90 天
- **Webhook Secret**: 每 90 天

### 4. 加密日志（可选）

生产环境建议：

```yaml
logging:
  format: "%(asctime)s - %(name)s - %(levelname)s - [ENCRYPTED]"
```

---

## 网络安全

### 1. 使用 HTTPS

- ✅ 生产环境必须使用 SSL/TLS 证书
- ✅ 使用 Let's Encrypt 获取免费证书
- ❌ 不要在生产环境使用 HTTP

### 2. 配置防火墙

```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 3. 使用 VPN（可选）

对于管理后台，建议：

- 仅允许 VPN 访问管理界面
- 配置 VPN 白名单
- 使用双因素认证

---

## 安全检查清单

### 部署前检查

- [ ] 所有密钥已使用强随机字符串生成
- [ ] `.env` 文件已添加到 `.gitignore`
- [ ] GitHub Token 仅授予必要权限
- [ ] Webhook Secret 已正确配置
- [ ] CORS 已正确配置
- [ ] 防火墙已正确配置
- [ ] SSL/TLS 证书已安装（生产环境）

### 定期检查（建议每月）

- [ ] 审查 GitHub Token 权限
- [ ] 检查访问日志是否有异常
- [ ] 更新依赖包到最新版本
- [ ] 轮换密钥（如到期）
- [ ] 检查防火墙规则

---

## 安全事件响应

### 发现安全漏洞时

1. **立即行动**：
   - 暂停服务
   - 轮换所有密钥
   - 检查访问日志

2. **调查**：
   - 确定漏洞范围
   - 分析访问日志
   - 确定影响范围

3. **修复**：
   - 更新到最新版本
   - 应用安全补丁
   - 加强安全配置

4. **通知**：
   - 通知相关方
   - 发布安全公告
   - 记录事件详情

### 报告安全漏洞

如果您发现安全漏洞，请通过私密方式报告：

- 发送邮件至：security@example.com
- 不要在公开 Issues 中报告

---

## 相关资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security/getting-started/securing-your-repository)
- [Python Security](https://docs.python.org/3/security/index.html)

---

## 下一步

- [配置说明](CONFIGURATION.md) - 详细配置
- [部署指南](DEPLOYMENT.md) - 生产部署
