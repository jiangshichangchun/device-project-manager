#!/usr/bin/env python3
"""
Project Registration Script
项目注册脚本 - 用于初始化和注册新项目

Usage:
    python init_project.py --path /path/to/project --name my-project
    python init_project.py --git https://github.com/user/repo.git --name my-project
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class ProjectRegistrar:
    """项目注册器"""

    # 项目类型识别规则
    TYPE_DETECTORS = {
        'python': ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile'],
        'node': ['package.json'],
        'go': ['go.mod'],
        'java': ['pom.xml', 'build.gradle'],
        'docker': ['Dockerfile'],
        'rust': ['Cargo.toml'],
        'dotnet': ['*.csproj', '*.fsproj'],
    }

    def __init__(self, registry_path: str = '/opt/project-manager/registry.json'):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        source: str,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        ports: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
        source_type: str = 'local',
        install_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        注册新项目

        Args:
            source: 项目源路径或Git URL
            name: 项目唯一名称
            display_name: 展示名称
            description: 项目描述
            ports: 使用端口列表
            tags: 项目标签
            source_type: 来源类型 (local/git/archive)
            install_path: 安装路径

        Returns:
            项目信息字典
        """
        print(f"🚀 开始注册项目: {name}")

        # 1. 检查项目名是否已存在
        if self._project_exists(name):
            raise ValueError(f"项目 '{name}' 已存在")

        # 2. 获取项目路径
        if source_type == 'git':
            project_path = self._clone_git_repo(source, name)
        else:
            project_path = Path(source).resolve()

        if not project_path.exists():
            raise FileNotFoundError(f"项目路径不存在: {project_path}")

        # 3. 探测项目类型
        project_type = self._detect_project_type(project_path)
        print(f"✓ 检测到项目类型: {project_type}")

        # 4. 准备安装路径
        if not install_path:
            install_path = f"/opt/projects/{name}"
        install_path = Path(install_path)

        # 如果源路径不是安装路径，则复制
        if project_path != install_path:
            if install_path.exists():
                raise FileExistsError(f"安装路径已存在: {install_path}")
            shutil.copytree(project_path, install_path)
            print(f"✓ 项目已复制到: {install_path}")

        # 5. 创建隔离环境并安装依赖
        runtime_env = self._setup_environment(install_path, project_type)

        # 6. 分配端口
        if not ports:
            ports = self._allocate_ports(runtime_env.get('default_ports', [8080]))
        else:
            # 检查端口是否可用
            for port in ports:
                if self._is_port_in_use(port):
                    raise ValueError(f"端口 {port} 已被占用")
        print(f"✓ 分配端口: {ports}")

        # 7. 计算项目大小
        size_mb = self._calculate_size(install_path)
        print(f"✓ 项目大小: {size_mb:.1f} MB")

        # 8. 发现产物路径
        artifacts_spec = self._discover_artifacts(install_path)

        # 9. 构建项目信息
        project = {
            'project_name': name,
            'display_name': display_name or name,
            'description': description or '',
            'source': source,
            'source_type': source_type,
            'tags': tags or [],
            'install_time': datetime.utcnow().isoformat() + 'Z',
            'update_time': datetime.utcnow().isoformat() + 'Z',
            'runtime_env': runtime_env,
            'install_path': str(install_path),
            'ports': ports,
            'size_mb': size_mb,
            'process': {
                'main_pid': None,
                'child_pids': [],
                'status': 'stopped',
                'start_time': None,
                'uptime_seconds': 0,
                'crash_info': None,
                'restart_count': 0,
            },
            'health': {
                'status': 'unknown',
                'last_check_time': None,
                'check_interval_seconds': 30,
                'issues': [],
            },
            'artifacts_spec': artifacts_spec,
            'auto_restart_policy': {
                'enabled': False,
                'max_retries': 3,
                'retry_count': 0,
                'backoff_seconds': 5,
                'reset_after_seconds': 300,
            },
            'resource_limits': {
                'cpu_percent_max': 80,
                'memory_mb_max': 512,
            },
            'backup_config': {
                'enabled': True,
                'paths': [],
                'exclude_patterns': ['*.log', '*.tmp'],
            },
        }

        # 10. 写入注册表
        self._add_to_registry(project)
        print(f"✓ 项目已注册: {name}")

        return project

    def _project_exists(self, name: str) -> bool:
        """检查项目是否已存在"""
        if not self.registry_path.exists():
            return False

        with open(self.registry_path) as f:
            registry = json.load(f)

        return any(p['project_name'] == name for p in registry)

    def _clone_git_repo(self, git_url: str, name: str) -> Path:
        """克隆Git仓库"""
        clone_path = Path(f'/tmp/{name}')
        if clone_path.exists():
            shutil.rmtree(clone_path)

        print(f"📥 克隆仓库: {git_url}")
        subprocess.run(['git', 'clone', git_url, str(clone_path)], check=True)
        print(f"✓ 仓库已克隆到: {clone_path}")

        return clone_path

    def _detect_project_type(self, path: Path) -> str:
        """探测项目类型"""
        for project_type, indicators in self.TYPE_DETECTORS.items():
            for indicator in indicators:
                if indicator.startswith('*'):
                    # 通配符匹配
                    if list(path.glob(indicator)):
                        return project_type
                elif (path / indicator).exists():
                    return project_type

        return 'other'

    def _setup_environment(self, path: Path, project_type: str) -> Dict[str, Any]:
        """设置运行环境"""
        runtime_env = {'type': project_type}

        if project_type == 'python':
            runtime_env.update(self._setup_python_env(path))
        elif project_type == 'node':
            runtime_env.update(self._setup_node_env(path))
        elif project_type == 'go':
            runtime_env.update(self._setup_go_env(path))
        elif project_type == 'java':
            runtime_env.update(self._setup_java_env(path))
        elif project_type == 'docker':
            runtime_env.update(self._setup_docker_env(path))

        return runtime_env

    def _setup_python_env(self, path: Path) -> Dict[str, Any]:
        """设置Python环境"""
        venv_path = path / '.venv'

        # 创建虚拟环境
        if not venv_path.exists():
            print("📦 创建Python虚拟环境...")
            subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], check=True)

        # 获取Python版本
        result = subprocess.run(
            [str(venv_path / 'bin' / 'python'), '--version'],
            capture_output=True, text=True
        )
        version = result.stdout.strip().split()[-1]

        # 安装依赖
        requirements = path / 'requirements.txt'
        if requirements.exists():
            print("📥 安装Python依赖...")
            subprocess.run(
                [str(venv_path / 'bin' / 'pip'), 'install', '-r', str(requirements)],
                check=True
            )

        # 探测启动命令
        startup_cmd = self._detect_startup_cmd(path, 'python')
        default_ports = [8000, 8080]

        return {
            'version': version,
            'env_path': str(venv_path),
            'startup_cmd': startup_cmd,
            'default_ports': default_ports,
        }

    def _setup_node_env(self, path: Path) -> Dict[str, Any]:
        """设置Node.js环境"""
        node_modules = path / 'node_modules'

        # 安装依赖
        if not node_modules.exists():
            print("📥 安装Node.js依赖...")
            subprocess.run(['npm', 'install'], cwd=str(path), check=True)

        # 获取Node版本
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        version = result.stdout.strip().lstrip('v')

        # 读取package.json获取启动命令
        package_json = path / 'package.json'
        startup_cmd = 'node index.js'
        if package_json.exists():
            with open(package_json) as f:
                pkg = json.load(f)
                if 'scripts' in pkg and 'start' in pkg['scripts']:
                    startup_cmd = pkg['scripts']['start']

        return {
            'version': version,
            'env_path': str(path / 'node_modules'),
            'startup_cmd': startup_cmd,
            'default_ports': [3000, 8080],
        }

    def _setup_go_env(self, path: Path) -> Dict[str, Any]:
        """设置Go环境"""
        # 编译Go项目
        go_mod = path / 'go.mod'
        if go_mod.exists():
            print("🔨 编译Go项目...")
            subprocess.run(['go', 'build', '-o', 'app'], cwd=str(path), check=True)

        result = subprocess.run(['go', 'version'], capture_output=True, text=True)
        version = result.stdout.strip().split()[-1]

        return {
            'version': version,
            'startup_cmd': './app',
            'default_ports': [8080],
        }

    def _setup_java_env(self, path: Path) -> Dict[str, Any]:
        """设置Java环境"""
        # Maven或Gradle构建
        if (path / 'pom.xml').exists():
            print("🔨 使用Maven构建...")
            subprocess.run(['mvn', 'package', '-DskipTests'], cwd=str(path), check=True)
        elif (path / 'build.gradle').exists():
            print("🔨 使用Gradle构建...")
            subprocess.run(['./gradlew', 'build', '-x', 'test'], cwd=str(path), check=True)

        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        version = result.stderr.split()[2].strip('"') if result.stderr else 'unknown'

        return {
            'version': version,
            'startup_cmd': 'java -jar target/*.jar',
            'default_ports': [8080],
        }

    def _setup_docker_env(self, path: Path) -> Dict[str, Any]:
        """设置Docker环境"""
        # 构建Docker镜像
        print("🔨 构建Docker镜像...")
        image_name = path.name.lower()
        subprocess.run(['docker', 'build', '-t', image_name, '.'], cwd=str(path), check=True)

        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        version = result.stdout.strip().split()[-1].rstrip(',')

        return {
            'version': version,
            'startup_cmd': f'docker run -d -p {{port}}:8080 {image_name}',
            'default_ports': [8080],
        }

    def _detect_startup_cmd(self, path: Path, project_type: str) -> str:
        """探测启动命令"""
        if project_type == 'python':
            # 查找常见的入口文件
            for entry in ['main.py', 'app.py', 'run.py', 'server.py', 'wsgi.py']:
                if (path / entry).exists():
                    return f'python {entry}'

        return 'python main.py'

    def _allocate_ports(self, preferred_ports: List[int]) -> List[int]:
        """分配可用端口"""
        allocated = []
        for port in preferred_ports:
            if not self._is_port_in_use(port):
                allocated.append(port)
                break

        if not allocated:
            # 找一个可用端口
            port = 8080
            while self._is_port_in_use(port):
                port += 1
            allocated.append(port)

        return allocated

    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def _calculate_size(self, path: Path) -> float:
        """计算目录大小（MB）"""
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total / (1024 * 1024)

    def _discover_artifacts(self, path: Path) -> List[str]:
        """发现运行时产物路径"""
        artifacts = []
        for name in ['logs', 'temp', 'tmp', 'data', 'output', 'cache']:
            artifact_path = path / name
            if artifact_path.exists() or True:  # 记录标准产物路径
                artifacts.append(str(artifact_path))
        return artifacts

    def _add_to_registry(self, project: Dict[str, Any]):
        """添加项目到注册表"""
        if not self.registry_path.exists():
            registry = []
        else:
            with open(self.registry_path) as f:
                registry = json.load(f)

        registry.append(project)

        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='项目注册工具')
    parser.add_argument('--name', required=True, help='项目名称')
    parser.add_argument('--path', help='项目路径')
    parser.add_argument('--git', help='Git仓库URL')
    parser.add_argument('--display-name', help='展示名称')
    parser.add_argument('--description', help='项目描述')
    parser.add_argument('--ports', help='端口列表（逗号分隔）')
    parser.add_argument('--tags', help='标签列表（逗号分隔）')
    parser.add_argument('--install-path', help='安装路径')
    parser.add_argument('--registry', default='/opt/project-manager/registry.json', help='注册表路径')

    args = parser.parse_args()

    if not args.path and not args.git:
        parser.error('需要指定 --path 或 --git')

    registrar = ProjectRegistrar(args.registry)

    try:
        project = registrar.register(
            source=args.path or args.git,
            name=args.name,
            display_name=args.display_name,
            description=args.description,
            ports=[int(p) for p in args.ports.split(',')] if args.ports else None,
            tags=args.tags.split(',') if args.tags else None,
            source_type='git' if args.git else 'local',
            install_path=args.install_path,
        )

        print("\n✅ 项目注册成功!")
        print(f"  名称: {project['project_name']}")
        print(f"  类型: {project['runtime_env']['type']}")
        print(f"  路径: {project['install_path']}")
        print(f"  端口: {project['ports']}")

    except Exception as e:
        print(f"\n❌ 注册失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
