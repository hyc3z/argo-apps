# GitHub 仓库创建脚本

这个脚本用于在 qianxue-world 组织下创建新的 GitHub 仓库，并自动配置 secrets 和 variables。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 创建 GitHub Personal Access Token:
   - 访问 https://github.com/settings/tokens
   - 点击 "Generate new token" -> "Generate new token (classic)"
   - 选择以下权限:
     - `repo` (完整仓库访问权限)
     - `admin:org` (组织管理权限)
   - 生成并复制 token

2. 创建配置文件:
```bash
cd scripts
cp .env.example .env
# 编辑 .env 文件，填入你的凭证
```

脚本会自动从 `scripts/.env` 文件读取配置。

## 使用方法

### 方式 1: 命令行参数
```bash
cd scripts
python create_github_repo.py lovetest
```

### 方式 2: 交互式输入
```bash
cd scripts
python create_github_repo.py
# 然后输入项目名称
```

## 功能特性

脚本会自动完成以下操作:

1. 在 GitHub 的 qianxue-world 组织下创建新仓库
2. 从模板项目复制创建本地项目（可选）
3. 配置 Git remote 为新仓库的 SSH 地址
4. 运行 Node.js 脚本更新 K8s 项目名称
5. 自动提交并推送代码到 GitHub
6. 为仓库配置 Secrets 和 Variables

### Secrets (加密存储)
- `DOCKERHUB_TOKEN`: Docker Hub 访问令牌
- `DOCKERHUB_USERNAME`: Docker Hub 用户名
- `GH_TOKEN`: GitHub Token (用于 Actions)

### Variables (明文配置)
- `DOCKER_IMAGE_NAME`: Docker 镜像名称 (默认: 项目名)

## 注意事项

- 确保你的 GitHub token 有足够的权限
- 确保你是 qianxue-world 组织的成员且有创建仓库的权限
- Secrets 会被加密存储，无法读取
- Variables 是明文存储的配置值
