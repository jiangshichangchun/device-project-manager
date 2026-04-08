#!/usr/bin/env python3
"""
Project Uninstall Script
项目卸载脚本 - 用于安全卸载项目

Usage:
    python uninstall.py my-project
    python uninstall.py my-project --backup
    python uninstall.py my-project --force
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class ProjectUninstaller:
    """项目卸载器"""

    def __init__(self, registry_path: str = '/opt/project-manager/registry.json'):
        self.registry_path = Path(registry_path)
        self.backup_dir = Path('/opt/project-manager/backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def uninstall(
        self,
        project_name: str,
        backup: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        安全卸载项目

        Args:
            project_name: 项目名称
            backup: 是否备份配置
            force: 是否强制卸载

        Returns:
            卸载报告
        """
        print(f"🗑️  开始卸载项目: {project_name}")

        project = self._get_project(project_name)
        result = {
            'project_name': project_name,
            'uninstall_time': datetime.utcnow().isoformat() + 'Z',
            'success': False,
            'processes_killed': [],
            'orphans_cleaned': [],
            'backup_path': None,
            'artifacts_deleted': [],
            'space_freed_mb': 0.0,
            'errors': [],
        }

        try:
            # 第一步：进程级阻断
            print("\n📋 步骤 1/5: 终止进程...")
            result['processes_killed'] = self._terminate_processes(project)

            # 第二步：备份配置（可选）
            if backup and project.get('backup_config', {}).get('enabled', True):
                print("\n📦 步骤 2/5: 备份配置...")
                result['backup_path'] = self._backup_config(project)

            # 第三步：产物清除
            print("\n🧹 步骤 3/5: 清理产物...")
            result['artifacts_deleted'] = self._delete_artifacts(project)

            # 第四步：本体删除
            print("\n📂 步骤 4/5: 删除安装目录...")
            result['space_freed_mb'] = self._delete_installation(project)

            # 第五步：注册表注销
            print("\n📝 步骤 5/5: 更新注册表...")
            self._remove_from_registry(project_name)

            result['success'] = True

            print(f"\n✅ 项目 '{project_name}' 已成功卸载!")
            print(f"  释放空间: {result['space_freed_mb']:.1f} MB")
            if result['backup_path']:
                print(f"  备份位置: {result['backup_path']}")

        except Exception as e:
            result['errors'].append(str(e))

            # 标记为损坏状态
            project['process']['status'] = 'corrupted'
            project['metadata'] = project.get('metadata', {})
            project['metadata']['uninstall_error'] = str(e)
            self._update_project(project)

            print(f"\n❌ 卸载失败: {e}")
            print("项目已标记为 'corrupted' 状态，请手动处理")

            if not force:
                raise

        # 生成卸载报告
        report_path = self._save_report(result)

        return result

    def _terminate_processes(self, project: Dict[str, Any]) -> List[int]:
        """终止所有相关进程"""
        killed = []

        # Docker 容器
        if project['runtime_env']['type'] == 'docker':
            container_id = project['process'].get('container_id')
            if container_id:
                print(f"  停止容器: {container_id}")
                subprocess.run(['docker', 'stop', container_id], capture_output=True)
                subprocess.run(['docker', 'rm', container_id], capture_output=True)
                return [container_id]

        # 普通进程
        main_pid = project['process'].get('main_pid')
        child_pids = project['process'].get('child_pids', [])

        all_pids = [main_pid] + child_pids

        # 先发送 SIGTERM
        for pid in all_pids:
            if pid and self._is_process_alive(pid):
                print(f"  发送 SIGTERM -> PID {pid}")
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

        # 等待进程退出
        import time
        time.sleep(3)

        # 强制终止仍在运行的进程
        for pid in all_pids:
            if pid and self._is_process_alive(pid):
                print(f"  发送 SIGKILL -> PID {pid}")
                try:
                    os.kill(pid, signal.SIGKILL)
                    killed.append(pid)
                except ProcessLookupError:
                    pass

        # 扫描孤儿进程
        install_path = project['install_path']
        ports = project.get('ports', [])

        # 按路径查找孤儿进程
        orphans = self._find_orphans_by_path(install_path)
        for pid in orphans:
            if self._is_process_alive(pid):
                print(f"  清理孤儿进程: PID {pid}")
                try:
                    os.kill(pid, signal.SIGKILL)
                    killed.append(pid)
                except ProcessLookupError:
                    pass

        return killed

    def _find_orphans_by_path(self, install_path: str) -> List[int]:
        """按路径查找孤儿进程"""
        orphans = []

        try:
            # 使用 lsof 查找打开该路径文件的进程
            result = subprocess.run(
                ['lsof', '-t', install_path],
                capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    orphans.append(int(line.strip()))
        except Exception:
            pass

        return orphans

    def _backup_config(self, project: Dict[str, Any]) -> Optional[str]:
        """备份项目配置"""
        install_path = Path(project['install_path'])
        project_name = project['project_name']

        backup_config = project.get('backup_config', {})
        backup_paths = backup_config.get('paths', [])
        exclude_patterns = backup_config.get('exclude_patterns', [])

        # 如果没有指定备份路径，使用默认配置文件
        if not backup_paths:
            backup_paths = [
                'config.yaml', 'config.json', '.env',
                'settings.py', 'config.py',
            ]

        # 创建备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"{timestamp}_{project_name}.tar.gz"

        # 收集需要备份的文件
        files_to_backup = []
        for pattern in backup_paths:
            if pattern.startswith('/'):
                # 绝对路径
                path = Path(pattern)
            else:
                # 相对路径
                path = install_path / pattern

            if path.exists():
                if path.is_file():
                    files_to_backup.append(path)
                elif path.is_dir():
                    files_to_backup.extend(path.rglob('*'))

        if not files_to_backup:
            print("  没有需要备份的文件")
            return None

        # 创建备份压缩包
        with tarfile.open(backup_file, 'w:gz') as tar:
            for file_path in files_to_backup:
                if file_path.is_file():
                    # 检查排除模式
                    rel_path = file_path.relative_to(install_path)
                    should_exclude = any(
                        self._match_pattern(str(rel_path), pattern)
                        for pattern in exclude_patterns
                    )

                    if not should_exclude:
                        tar.add(file_path, arcname=rel_path)

        print(f"  备份完成: {backup_file}")
        return str(backup_file)

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """匹配 glob 模式"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def _delete_artifacts(self, project: Dict[str, Any]) -> List[str]:
        """删除运行时产物"""
        artifacts_spec = project.get('artifacts_spec', [])
        install_path = Path(project['install_path'])

        deleted = []

        for spec in artifacts_spec:
            if spec.startswith('/'):
                # 绝对路径
                path = Path(spec)
            else:
                # 相对路径或 glob 模式
                if '*' in spec:
                    # glob 模式
                    for matched in install_path.glob(spec):
                        if matched.exists():
                            if matched.is_dir():
                                shutil.rmtree(matched)
                            else:
                                matched.unlink()
                            deleted.append(str(matched))
                    continue
                else:
                    path = install_path / spec

            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                deleted.append(str(path))
                print(f"  已删除: {path}")

        return deleted

    def _delete_installation(self, project: Dict[str, Any]) -> float:
        """删除安装目录"""
        install_path = Path(project['install_path'])

        if not install_path.exists():
            return 0.0

        # 计算目录大小
        total_size = sum(
            f.stat().st_size
            for f in install_path.rglob('*')
            if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)

        # 删除目录
        shutil.rmtree(install_path)
        print(f"  已删除: {install_path}")

        return size_mb

    def _remove_from_registry(self, project_name: str):
        """从注册表移除项目"""
        with open(self.registry_path) as f:
            registry = json.load(f)

        # 过滤掉要删除的项目
        registry = [
            p for p in registry
            if p['project_name'] != project_name
        ]

        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        print(f"  已从注册表移除: {project_name}")

    def _save_report(self, result: Dict[str, Any]) -> Path:
        """保存卸载报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.backup_dir / f"uninstall_{timestamp}_{result['project_name']}.json"

        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return report_file

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


def main():
    parser = argparse.ArgumentParser(description='项目卸载工具')
    parser.add_argument('name', help='项目名称')
    parser.add_argument('--registry', default='/opt/project-manager/registry.json', help='注册表路径')
    parser.add_argument('--backup', action='store_true', help='备份配置文件')
    parser.add_argument('--no-backup', action='store_true', help='不备份配置文件')
    parser.add_argument('--force', action='store_true', help='强制卸载（忽略错误）')

    args = parser.parse_args()

    uninstaller = ProjectUninstaller(args.registry)

    try:
        result = uninstaller.uninstall(
            project_name=args.name,
            backup=args.backup and not args.no_backup,
            force=args.force,
        )

        print("\n" + "=" * 50)
        print("卸载报告:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ 卸载失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
