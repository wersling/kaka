# Kaka Auto 发布指南

本文档说明如何将 Kaka Auto 发布到 PyPI。

## 📋 前置条件

### 1. 安装构建工具

```bash
pip install build twine
```

### 2. 准备 PyPI 账号

- **官方 PyPI**：访问 https://pypi.org/account/register/ 注册账号
- **TestPyPI**：访问 https://test.pypi.org/account/register/ 注册测试账号
- 启用双因素认证（2FA）
- 生成 API Token（推荐）或配置账号密码

### 3. 配置认证

**方式 A：使用 API Token（推荐）**

创建 `~/.pypirc` 文件：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...你的API Token...

[testpypi]
username = __token__
password = pypi-...你的TestPyPI API Token...
repository = https://test.pypi.org/legacy/
```

**方式 B：使用用户名密码**

```ini
[pypi]
username = your-username
password = your-password

[testpypi]
username = your-test-username
password = your-test-password
repository = https://test.pypi.org/legacy/
```

## 🚀 发布流程

### 步骤 1：更新版本号

编辑 [pyproject.toml](../pyproject.toml) 中的版本号：

```toml
[project]
name = "kaka"
version = "0.1.0"  # 修改为新版本
```

### 步骤 2：更新 CHANGELOG

编辑 [CHANGELOG.md](../CHANGELOG.md)，添加新版本变更记录。

### 步骤 3：清理旧的构建

```bash
rm -rf dist/ build/ *.egg-info
```

### 步骤 4：构建分发包

```bash
python -m build
```

这将生成：
- `dist/kama-{version}.tar.gz` - 源码包
- `dist/kaka-{version}-py3-none-any.whl` - wheel 包

### 步骤 5：检查包

```bash
twine check dist/*
```

确保没有错误或警告。

### 步骤 6：测试本地安装

```bash
# 创建新的虚拟环境测试
python3 -m venv test_env
source test_env/bin/activate

# 安装构建的包
pip install dist/kaka-{version}-py3-none-any.whl

# 验证命令行工具
kaka --help
kaka-dev --help
ai-scheduler --help

# 清理测试环境
deactivate
rm -rf test_env
```

### 步骤 7：发布到 TestPyPI（推荐先测试）

**⚠️ 重要提示：setuptools 80.x 和 twine 6.2.0 兼容性问题**

如果您使用 setuptools 80.x 和 twine 6.2.0，可能会遇到以下错误：
```
InvalidDistribution: Invalid distribution metadata: unrecognized or malformed field 'license-file'
```

这是已知问题。解决方法是在构建后手动修改包的元数据。项目提供了自动化脚本：

```bash
# 构建后运行修复脚本
python scripts/fix_package_metadata.py

# 然后再上传
twine upload --verbose --repository testpypi dist/*
```

**如果不想修复元数据，可以降级 setuptools**：
```bash
pip install "setuptools<75"
```

正常上传流程：
```bash
# 上传到 TestPyPI
twine upload --verbose --repository testpypi dist/*

# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ kaka-auto

# 验证安装
kaka --help
```

### 步骤 8：发布到官方 PyPI

```bash
# 如果需要，先运行元数据修复脚本
python scripts/fix_package_metadata.py

# 上传到 PyPI
twine upload dist/*

# 验证发布
pip install kaka-auto
```

发布成功后，包将出现在：
- https://pypi.org/project/kaka-auto/

## 📝 版本管理规范

Kaka 遵循 [Semantic Versioning](https://semver.org/)：

- **主版本号（Major）**：不兼容的 API 变更
- **次版本号（Minor）**：向后兼容的功能新增
- **修订号（Patch）**：向后兼容的问题修复

示例：
- `0.1.0` → `0.2.0`：新功能
- `0.1.0` → `0.1.1`：Bug 修复
- `0.1.0` → `1.0.0`：不兼容变更

## 🔍 常见问题排查

### 问题 1：上传时提示包名已存在

**原因**：PyPI 上的包名是唯一的，且不能覆盖已发布的版本。

**解决**：
- 检查是否使用了正确的版本号
- 如果是测试版本，建议使用 `0.x.0.dev0` 格式

### 问题 2：twine check 警告

**原因**：包的元数据有问题。

**解决**：
- 确保 `pyproject.toml` 中的所有必需字段都已填写
- 确保 README.md、LICENSE 等文件存在

**注意**：setuptools 的新版本与旧版 twine 可能存在兼容性问题，可以忽略 `license-expression` 和 `license-file` 警告，这不影响实际发布。

### 问题 3：安装后找不到命令行工具

**原因**：入口点配置有问题。

**解决**：
- 检查 `pyproject.toml` 中的 `[project.scripts]` 配置
- 确保目标函数存在且可调用

### 问题 4：从 TestPyPI 安装失败

**原因**：TestPyPI 不依赖官方 PyPI，可能导致依赖缺失。

**解决**：
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple kaka
```

## 🎯 发布后验证清单

- [ ] PyPI 页面正常显示（https://pypi.org/project/kaka-auto/）
- [ ] README、License 等信息正确显示
- [ ] 可以通过 `pip install kaka-auto` 安装
- [ ] 所有命令行工具正常工作
- [ ] Python 包可以正常导入
- [ ] CHANGELOG 已更新
- [ ] GitHub Release 已创建（可选）

## 📚 参考资料

- [Python 打包用户指南](https://packaging.python.org/)
- [PyPI 发布指南](https://pypi.org/help/#publishing)
- [twine 文档](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)
