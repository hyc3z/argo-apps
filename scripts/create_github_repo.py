#!/usr/bin/env python3
"""
GitHub 仓库创建和配置脚本
在 qianxue-world 组织下创建新仓库，并配置 secrets 和 variables
"""

import os
import sys
import requests
from typing import Dict, List, Optional
import json
from pathlib import Path
import shutil
import subprocess


class GitHubRepoManager:
    def __init__(self, token: str, org: str = "qianxue-world"):
        """
        初始化 GitHub 仓库管理器
        
        Args:
            token: GitHub Personal Access Token
            org: GitHub 组织名称
        """
        self.token = token
        self.org = org
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    def create_repository(self, repo_name: str, description: str = "", 
                         private: bool = False) -> bool:
        """
        在组织下创建新仓库
        
        Args:
            repo_name: 仓库名称
            description: 仓库描述
            private: 是否为私有仓库
            
        Returns:
            bool: 创建是否成功
        """
        url = f"{self.base_url}/orgs/{self.org}/repos"
        data = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": False  # 不自动初始化 README，避免推送冲突
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            print(f"✓ 成功创建仓库: {self.org}/{repo_name}")
            return True
        elif response.status_code == 422:
            print(f"✗ 仓库已存在: {self.org}/{repo_name}")
            return False
        else:
            print(f"✗ 创建仓库失败: {response.status_code}")
            print(f"  错误信息: {response.json().get('message', 'Unknown error')}")
            return False
    
    def set_secret(self, repo_name: str, secret_name: str, secret_value: str) -> bool:
        """
        为仓库设置 secret
        
        Args:
            repo_name: 仓库名称
            secret_name: Secret 名称
            secret_value: Secret 值
            
        Returns:
            bool: 设置是否成功
        """
        # 首先获取仓库的公钥
        public_key_url = f"{self.base_url}/repos/{self.org}/{repo_name}/actions/secrets/public-key"
        response = requests.get(public_key_url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"✗ 获取公钥失败: {response.status_code}")
            return False
        
        public_key_data = response.json()
        public_key = public_key_data["key"]
        key_id = public_key_data["key_id"]
        
        # 加密 secret 值
        from base64 import b64encode
        from nacl import encoding, public
        
        public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key_obj)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_value = b64encode(encrypted).decode("utf-8")
        
        # 设置 secret
        secret_url = f"{self.base_url}/repos/{self.org}/{repo_name}/actions/secrets/{secret_name}"
        data = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        
        response = requests.put(secret_url, headers=self.headers, json=data)
        
        if response.status_code in [201, 204]:
            print(f"✓ 成功设置 secret: {secret_name}")
            return True
        else:
            print(f"✗ 设置 secret 失败: {response.status_code}")
            return False
    
    def set_variable(self, repo_name: str, variable_name: str, variable_value: str) -> bool:
        """
        为仓库设置 variable
        
        Args:
            repo_name: 仓库名称
            variable_name: Variable 名称
            variable_value: Variable 值
            
        Returns:
            bool: 设置是否成功
        """
        url = f"{self.base_url}/repos/{self.org}/{repo_name}/actions/variables"
        data = {
            "name": variable_name,
            "value": variable_value
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            print(f"✓ 成功设置 variable: {variable_name}")
            return True
        elif response.status_code == 409:
            # Variable 已存在，尝试更新
            update_url = f"{url}/{variable_name}"
            response = requests.patch(update_url, headers=self.headers, json={"value": variable_value})
            if response.status_code == 204:
                print(f"✓ 成功更新 variable: {variable_name}")
                return True
        
        print(f"✗ 设置 variable 失败: {response.status_code}")
        return False


def copy_template_project(template_path: str, new_project_name: str, target_dir: str = None) -> Path:
    """
    从模板项目复制创建新项目
    
    Args:
        template_path: 模板项目路径
        new_project_name: 新项目名称
        target_dir: 目标目录，默认为模板项目的父目录
        
    Returns:
        Path: 新项目的路径
    """
    template = Path(template_path).expanduser()
    
    if not template.exists():
        print(f"✗ 模板项目不存在: {template}")
        sys.exit(1)
    
    # 确定目标目录
    if target_dir:
        parent_dir = Path(target_dir).expanduser()
    else:
        parent_dir = template.parent
    
    new_project_path = parent_dir / new_project_name
    
    if new_project_path.exists():
        print(f"✗ 目标目录已存在: {new_project_path}")
        sys.exit(1)
    
    print(f"\n复制模板项目...")
    print(f"  从: {template}")
    print(f"  到: {new_project_path}")
    
    # 复制整个目录
    shutil.copytree(template, new_project_path, symlinks=True)
    print(f"✓ 项目复制完成")
    
    return new_project_path


def update_k8s_project_name(project_path: Path, repo_name: str) -> bool:
    """
    运行 Node.js 脚本更新 K8s 项目名称
    
    Args:
        project_path: 项目路径
        repo_name: 新项目名称
        
    Returns:
        bool: 执行是否成功
    """
    print(f"\n更新 K8s 项目名称...")
    
    try:
        # 进入项目目录
        os.chdir(project_path)
        
        # 检查脚本是否存在
        script_path = project_path / "scripts" / "update-k8s-project-name.js"
        if not script_path.exists():
            print(f"警告: 脚本不存在: {script_path}")
            return False
        
        # 运行 Node.js 脚本
        result = subprocess.run(
            ["node", "scripts/update-k8s-project-name.js", repo_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"✓ K8s 项目名称更新完成")
        if result.stdout:
            print(f"  输出: {result.stdout.strip()}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ 脚本执行失败: {e}")
        if e.stderr:
            print(f"  错误: {e.stderr}")
        return False
    except Exception as e:
        print(f"✗ 更新项目名称失败: {e}")
        return False


def setup_git_remote(project_path: Path, org: str, repo_name: str) -> bool:
    """
    设置 Git remote 为新仓库
    
    Args:
        project_path: 项目路径
        org: GitHub 组织名
        repo_name: 仓库名称
        
    Returns:
        bool: 设置是否成功
    """
    print(f"\n配置 Git Remote...")
    
    # 检查是否是 git 仓库
    git_dir = project_path / ".git"
    if not git_dir.exists():
        print(f"✗ 不是 Git 仓库: {project_path}")
        return False
    
    try:
        # 进入项目目录
        os.chdir(project_path)
        
        # 获取当前 remote
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  当前 remote:\n{result.stdout}")
        
        # 删除现有的 origin remote
        subprocess.run(
            ["git", "remote", "remove", "origin"],
            capture_output=True,
            text=True
        )
        
        # 添加新的 remote
        new_remote = f"git@github.com:{org}/{repo_name}.git"
        subprocess.run(
            ["git", "remote", "add", "origin", new_remote],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"✓ 已设置 remote 为: {new_remote}")
        
        # 验证新的 remote
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  新 remote:\n{result.stdout}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Git 命令执行失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 设置 remote 失败: {e}")
        return False


def git_push(project_path: Path) -> bool:
    """
    推送代码到 GitHub
    
    Args:
        project_path: 项目路径
        
    Returns:
        bool: 推送是否成功
    """
    print(f"\n推送代码到 GitHub...")
    
    try:
        # 进入项目目录
        os.chdir(project_path)
        
        # 添加所有更改
        subprocess.run(
            ["git", "add", "."],
            capture_output=True,
            text=True,
            check=True
        )
        
        # 提交更改
        subprocess.run(
            ["git", "commit", "-m", "Initial commit: Update project configuration"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ 已提交更改")
        
        # 推送到远程仓库
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"✓ 代码推送成功")
        if result.stderr:
            print(f"  {result.stderr.strip()}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Git 推送失败: {e}")
        if e.stderr:
            print(f"  错误: {e.stderr}")
        return False
    except Exception as e:
        print(f"✗ 推送失败: {e}")
        return False


def load_env_file(env_path: str = ".env") -> None:
    """
    从 .env 文件加载环境变量
    
    Args:
        env_path: .env 文件路径
    """
    script_dir = Path(__file__).parent
    env_file = script_dir / env_path
    
    if not env_file.exists():
        print(f"警告: 未找到 {env_path} 文件")
        return
    
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            # 解析 KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # 移除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                os.environ[key] = value


def main():
    """主函数"""
    # 保存原始工作目录
    original_dir = os.getcwd()
    
    # 从 .env 文件加载环境变量
    load_env_file()
    
    # 从环境变量获取 GitHub Token
    github_token = os.getenv("GH_TOKEN")
    if not github_token:
        print("错误: 请设置 GH_TOKEN 环境变量")
        print("示例: export GH_TOKEN=your_token_here")
        sys.exit(1)
    
    # 获取项目名称
    if len(sys.argv) > 1:
        repo_name = sys.argv[1]
    else:
        repo_name = input("请输入项目名称: ").strip()
    
    if not repo_name:
        print("错误: 项目名称不能为空")
        sys.exit(1)
    
    # 初始化管理器
    manager = GitHubRepoManager(github_token)
    
    # 创建仓库
    print(f"\n开始创建仓库: {repo_name}")
    if not manager.create_repository(repo_name):
        sys.exit(1)
    
        # 配置 secrets - 从环境变量读取
    print("\n配置 Secrets...")
    required_secrets = {
        "DOCKERHUB_TOKEN": os.getenv("DOCKERHUB_TOKEN"),
        "DOCKERHUB_USERNAME": os.getenv("DOCKERHUB_USERNAME"),
        "GH_TOKEN": os.getenv("GH_TOKEN")
    }
    
    # 检查必需的环境变量
    missing_secrets = [name for name, value in required_secrets.items() if not value]
    if missing_secrets:
        print(f"警告: 以下环境变量未设置: {', '.join(missing_secrets)}")
        print("将跳过这些 secrets 的配置")
    
    for secret_name, secret_value in required_secrets.items():
        if secret_value:
            manager.set_secret(repo_name, secret_name, secret_value)
    
    # 配置 variables
    print("\n配置 Variables...")
    # DOCKER_IMAGE_NAME 默认使用 repo_name 格式
    docker_image_name = os.getenv("DOCKER_IMAGE_NAME", f"{repo_name}")
    
    variables = {
        "DOCKER_IMAGE_NAME": docker_image_name
    }
    
    for variable_name, variable_value in variables.items():
        manager.set_variable(repo_name, variable_name, variable_value)
    
    # 从模板复制项目（如果配置了模板路径）
    template_path = os.getenv("TEMPLATE_PROJECT_PATH")
    new_project_path = None
    
    if template_path:
        target_dir = os.getenv("PROJECTS_DIR")
        new_project_path = copy_template_project(template_path, repo_name, target_dir)
        
        # 设置 Git remote
        setup_git_remote(new_project_path, manager.org, repo_name)
        
        # 更新 K8s 项目名称
        update_k8s_project_name(new_project_path, repo_name)
        
        # 推送代码到 GitHub
        git_push(new_project_path)
        
        # 返回原始目录
        os.chdir(original_dir)
    else:
        print("\n跳过项目复制 (未配置 TEMPLATE_PROJECT_PATH)")
    

    print(f"\n✓ 全部完成!")
    print(f"  仓库地址: https://github.com/{manager.org}/{repo_name}")
    if new_project_path:
        print(f"  本地项目: {new_project_path}")
        print(f"\n项目已准备就绪，代码已推送到 GitHub！")


if __name__ == "__main__":
    main()
