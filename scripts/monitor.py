#!/usr/bin/env python3
"""
Process Monitor Script
进程监控脚本 - 用于监控项目进程状态和资源使用

Usage:
    python monitor.py --start my-project
    python monitor.py --stop my-project
    python monitor.py --status my-project
    python monitor.py --list
    python monitor.py --daemon
"""

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class ProcessMonitor:
    """进程监控器"""

    def __init__(self, registry_path: str = '/opt/project-manager/registry.json'):
        self.registry_path = Path(registry_path)
        self.check_interval = 10  # 秒

    def start(self, project_name: str) -> Dict[str, Any]:
        """
        启动项目

        Args:
            project_name: 项目名称

        Returns:
            进程信息
        """
        project = self._get_project(project_name)

        if project['process']['status'] == 'running':
            raise RuntimeError(f"项目 '{project_name}' 已在运行")

        print(f"🚀 启动项目: {project_name}")

        runtime_env = project['runtime_env']
        install_path = Path(project['install_path'])

        # 构建启动命令
        startup_cmd = runtime_env['startup_cmd']
        ports = project['ports']
        if '{port}' in startup_cmd and ports:
            startup_cmd = startup_cmd.replace('{port}', str(ports[0]))

        # 准备环境变量
        env = os.environ.copy()
        if runtime_env.get('env_vars'):
            env.update(runtime_env['env_vars'])

        # 根据项目类型设置工作目录和命令
        cwd = install_path
        executable = None

        if runtime_env['type'] == 'python':
            venv_path = Path(runtime_env.get('env_path', ''))
            if venv_path.exists():
                python_bin = venv_path / 'bin' / 'python'
                if python_bin.exists():
                    executable = str(python_bin)

        elif runtime_env['type'] == 'docker':
            # Docker 容器启动
            container_name = f"pm_{project_name}"
            result = subprocess.run(
                startup_cmd.split() + [f'--name', container_name],
                cwd=cwd,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # 获取容器ID
                result = subprocess.run(
                    ['docker', 'ps', '-q', '-f', f'name={container_name}'],
                    capture_output=True, text=True
                )
                container_id = result.stdout.strip()[:12] if result.stdout else None

                project['process']['container_id'] = container_id
                project['process']['status'] = 'running'
                project['process']['start_time'] = datetime.utcnow().isoformat() + 'Z'
                self._update_project(project)

                print(f"✓ 容器已启动: {container_id}")
                return project['process']
            else:
                raise RuntimeError(f"Docker 启动失败: {result.stderr}")

        # 启动进程
        shell = executable is None
        cmd = startup_cmd if shell else startup_cmd.split()

        process = subprocess.Popen(
            cmd if not shell else startup_cmd,
            cwd=cwd,
            env=env,
            shell=shell,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            executable=executable,
        )

        # 等待进程启动
        time.sleep(1)

        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"进程启动失败 (exit code: {process.returncode})\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        # 获取子进程
        child_pids = self._get_child_pids(process.pid)

        # 更新项目状态
        project['process']['main_pid'] = process.pid
        project['process']['child_pids'] = child_pids
        project['process']['status'] = 'running'
        project['process']['start_time'] = datetime.utcnow().isoformat() + 'Z'
        project['process']['uptime_seconds'] = 0
        self._update_project(project)

        print(f"✓ 进程已启动: PID {process.pid}")
        if child_pids:
            print(f"  子进程: {child_pids}")

        return project['process']

    def stop(self, project_name: str, timeout: int = 10, force: bool = False) -> Dict[str, Any]:
        """
        停止项目

        Args:
            project_name: 项目名称
            timeout: 等待超时秒数
            force: 是否强制终止

        Returns:
            进程信息
        """
        project = self._get_project(project_name)

        if project['process']['status'] != 'running':
            raise RuntimeError(f"项目 '{project_name}' 未在运行")

        print(f"🛑 停止项目: {project_name}")

        main_pid = project['process']['main_pid']
        child_pids = project['process']['child_pids']

        # Docker 容器
        if project['runtime_env']['type'] == 'docker':
            container_id = project['process'].get('container_id')
            if container_id:
                subprocess.run(['docker', 'stop', container_id], capture_output=True)
                subprocess.run(['docker', 'rm', container_id], capture_output=True)

                project['process']['container_id'] = None
                project['process']['status'] = 'stopped'
                project['process']['main_pid'] = None
                project['process']['child_pids'] = []
                self._update_project(project)

                print(f"✓ 容器已停止")
                return project['process']

        all_pids = [main_pid] + child_pids

        # 发送 SIGTERM
        for pid in all_pids:
            if pid and self._is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

        # 等待进程退出
        start_wait = time.time()
        while time.time() - start_wait < timeout:
            all_dead = all(
                not self._is_process_alive(pid)
                for pid in all_pids if pid
            )
            if all_dead:
                break
            time.sleep(0.5)

        # 强制终止仍在运行的进程
        killed = []
        for pid in all_pids:
            if pid and self._is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                    killed.append(pid)
                except ProcessLookupError:
                    pass

        # 更新项目状态
        project['process']['status'] = 'stopped'
        project['process']['main_pid'] = None
        project['process']['child_pids'] = []
        self._update_project(project)

        print(f"✓ 进程已停止")
        if killed:
            print(f"  强制终止: {killed}")

        return project['process']

    def restart(self, project_name: str, timeout: int = 10) -> Dict[str, Any]:
        """重启项目"""
        print(f"🔄 重启项目: {project_name}")

        try:
            self.stop(project_name, timeout=timeout)
        except RuntimeError:
            pass  # 项目未运行，忽略

        time.sleep(1)
        return self.start(project_name)

    def status(self, project_name: str) -> Dict[str, Any]:
        """获取项目状态"""
        project = self._get_project(project_name)

        status_info = {
            'project_name': project_name,
            'status': project['process']['status'],
            'type': project['runtime_env']['type'],
            'ports': project['ports'],
        }

        if project['process']['status'] == 'running':
            main_pid = project['process']['main_pid']

            # 检查进程是否真实存活
            if main_pid and not self._is_process_alive(main_pid):
                # 进程已退出，更新状态
                project['process']['status'] = 'crashed'
                self._update_project(project)
                status_info['status'] = 'crashed'
            else:
                # 计算运行时间
                start_time = datetime.fromisoformat(
                    project['process']['start_time'].rstrip('Z')
                )
                uptime = (datetime.utcnow() - start_time).total_seconds()
                status_info['uptime_seconds'] = int(uptime)
                status_info['main_pid'] = main_pid
                status_info['child_pids'] = project['process']['child_pids']

        return status_info

    def metrics(self, project_name: str) -> Dict[str, Any]:
        """获取资源指标"""
        project = self._get_project(project_name)

        if project['process']['status'] != 'running':
            return {'project_name': project_name, 'status': 'stopped'}

        main_pid = project['process']['main_pid']
        child_pids = project['process']['child_pids']

        # 使用 psutil 获取资源信息
        try:
            import psutil
        except ImportError:
            return {'error': 'psutil not installed'}

        all_pids = [main_pid] + child_pids
        total_cpu = 0.0
        total_memory = 0
        open_files = 0
        threads = 0

        for pid in all_pids:
            if pid:
                try:
                    proc = psutil.Process(pid)
                    total_cpu += proc.cpu_percent()
                    total_memory += proc.memory_info().rss
                    open_files += len(proc.open_files())
                    threads += proc.num_threads()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        # 计算运行时间
        start_time = datetime.fromisoformat(
            project['process']['start_time'].rstrip('Z')
        )
        uptime = (datetime.utcnow() - start_time).total_seconds()

        return {
            'project_name': project_name,
            'status': 'running',
            'main_pid': main_pid,
            'uptime_seconds': int(uptime),
            'cpu_percent': round(total_cpu, 2),
            'memory_mb': round(total_memory / (1024 * 1024), 2),
            'open_files': open_files,
            'threads': threads,
            'process_count': len([p for p in all_pids if p and self._is_process_alive(p)]),
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        """列出所有项目"""
        if not self.registry_path.exists():
            return []

        with open(self.registry_path) as f:
            registry = json.load(f)

        projects = []
        for project in registry:
            status_info = {
                'name': project['project_name'],
                'display_name': project.get('display_name', project['project_name']),
                'type': project['runtime_env']['type'],
                'status': project['process']['status'],
                'ports': project['ports'],
            }

            if project['process']['status'] == 'running':
                # 验证进程是否存活
                main_pid = project['process']['main_pid']
                if main_pid and not self._is_process_alive(main_pid):
                    status_info['status'] = 'crashed'

            projects.append(status_info)

        return projects

    async def daemon(self):
        """后台监控守护进程"""
        print("🔍 启动监控守护进程...")

        while True:
            try:
                await self._monitor_loop()
            except Exception as e:
                print(f"监控异常: {e}")

            await asyncio.sleep(self.check_interval)

    async def _monitor_loop(self):
        """监控循环"""
        if not self.registry_path.exists():
            return

        with open(self.registry_path) as f:
            registry = json.load(f)

        for project in registry:
            if project['process']['status'] == 'running':
                await self._check_project(project)

    async def _check_project(self, project: Dict[str, Any]):
        """检查单个项目"""
        project_name = project['project_name']
        main_pid = project['process']['main_pid']

        # 检查进程存活
        if main_pid and not self._is_process_alive(main_pid):
            print(f"⚠️ 项目 {project_name} 进程已退出")

            # 记录崩溃信息
            project['process']['status'] = 'crashed'
            project['process']['crash_info'] = {
                'time': datetime.utcnow().isoformat() + 'Z',
            }

            # 自动重启
            if project['auto_restart_policy']['enabled']:
                await self._auto_restart(project)

            self._update_project(project)

        else:
            # 更新运行时间
            start_time = datetime.fromisoformat(
                project['process']['start_time'].rstrip('Z')
            )
            uptime = (datetime.utcnow() - start_time).total_seconds()
            project['process']['uptime_seconds'] = int(uptime)
            self._update_project(project)

    async def _auto_restart(self, project: Dict[str, Any]):
        """自动重启"""
        policy = project['auto_restart_policy']
        retry_count = policy['retry_count']
        max_retries = policy['max_retries']

        if retry_count >= max_retries:
            print(f"❌ 项目 {project['project_name']} 达到最大重试次数")
            return

        print(f"🔄 自动重启项目 {project['project_name']} (重试 {retry_count + 1}/{max_retries})")

        policy['retry_count'] = retry_count + 1

        await asyncio.sleep(policy['backoff_seconds'])

        try:
            self.start(project['project_name'])
        except Exception as e:
            print(f"重启失败: {e}")

    def _get_project(self, project_name: str) -> Dict[str, Any]:
        """获取项目信息"""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"注册表不存在: {self.registry_path}")

        with open(self.registry_path) as f:
            registry = json.load(f)

        for project in registry:
            if project['project_name'] == project_name:
                return project

        raise ValueError(f"项目不存在: {project_name}")

    def _update_project(self, project: Dict[str, Any]):
        """更新项目信息"""
        with open(self.registry_path) as f:
            registry = json.load(f)

        for i, p in enumerate(registry):
            if p['project_name'] == project['project_name']:
                registry[i] = project
                break

        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存活"""
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _get_child_pids(self, parent_pid: int) -> List[int]:
        """获取子进程PID列表"""
        try:
            result = subprocess.run(
                ['pgrep', '-P', str(parent_pid)],
                capture_output=True, text=True
            )
            children = [
                int(p) for p in result.stdout.strip().split('\n')
                if p.strip()
            ]

            # 递归获取孙子进程
            all_children = children.copy()
            for child in children:
                all_children.extend(self._get_child_pids(child))

            return all_children
        except Exception:
            return []


def main():
    parser = argparse.ArgumentParser(description='进程监控工具')
    parser.add_argument('--registry', default='/opt/project-manager/registry.json', help='注册表路径')

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # start 命令
    start_parser = subparsers.add_parser('start', help='启动项目')
    start_parser.add_argument('name', help='项目名称')

    # stop 命令
    stop_parser = subparsers.add_parser('stop', help='停止项目')
    stop_parser.add_argument('name', help='项目名称')
    stop_parser.add_argument('--timeout', type=int, default=10, help='等待超时')
    stop_parser.add_argument('--force', action='store_true', help='强制终止')

    # restart 命令
    restart_parser = subparsers.add_parser('restart', help='重启项目')
    restart_parser.add_argument('name', help='项目名称')

    # status 命令
    status_parser = subparsers.add_parser('status', help='查看状态')
    status_parser.add_argument('name', help='项目名称')

    # metrics 命令
    metrics_parser = subparsers.add_parser('metrics', help='查看资源指标')
    metrics_parser.add_argument('name', help='项目名称')

    # list 命令
    subparsers.add_parser('list', help='列出所有项目')

    # daemon 命令
    subparsers.add_parser('daemon', help='启动监控守护进程')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    monitor = ProcessMonitor(args.registry)

    try:
        if args.command == 'start':
            result = monitor.start(args.name)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == 'stop':
            result = monitor.stop(args.name, args.timeout, args.force)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == 'restart':
            result = monitor.restart(args.name)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == 'status':
            result = monitor.status(args.name)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == 'metrics':
            result = monitor.metrics(args.name)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == 'list':
            result = monitor.list_projects()
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == 'daemon':
            asyncio.run(monitor.daemon())

    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
