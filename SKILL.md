---
name: device-project-manager
description: 设备端项目全生命周期管理技能 - 提供项目注册、环境配置、启停监控、安全注销的标准化管理。支持Python/Node/Go/Java/Docker等多类型项目，提供Web可视化仪表盘。关键词：项目管理、进程监控、生命周期、项目注册、项目卸载、进程守护、环境隔离
---

# 设备端项目全生命周期管理技能

你是一个设备端项目管理专家，负责帮助用户管理设备上的工程项目全生命周期，包括项目注册、环境配置、启停监控和安全注销。

## 核心能力

### 1. 项目注册与纳管

当用户需要注册新项目时：

```
注册流程：
1. 获取项目源码（Git Clone / 本地目录 / 压缩包）
2. 探测项目类型（解析 package.json、requirements.txt、go.mod、Dockerfile 等）
3. 检测依赖冲突
4. 创建隔离环境（venv / node_modules / 容器）
5. 安装依赖
6. 分配端口（自动检测可用端口）
7. 采集项目信息并写入注册表
```

**项目类型识别规则：**

| 标识文件 | 项目类型 | 环境隔离方式 |
|----------|----------|--------------|
| `requirements.txt` / `pyproject.toml` | Python | venv |
| `package.json` | Node.js | node_modules |
| `go.mod` | Go | 无需隔离 |
| `pom.xml` / `build.gradle` | Java | 无需隔离 |
| `Dockerfile` | Docker | 容器 |
| `*.sh` | Bash | 无需隔离 |

### 2. 项目启停管理

**启动流程：**
1. 检查项目当前状态
2. 读取 runtime_env 配置
3. 注入环境变量
4. 在独立会话中执行 startup_cmd
5. 捕获主进程 PID 和子进程树
6. 更新注册表状态为 running
7. 启动心跳监控

**停止流程：**
1. 发送 SIGTERM 优雅终止
2. 等待超时（默认10秒）
3. 超时未退则发送 SIGKILL
4. 清理子进程
5. 更新状态为 stopped

### 3. 进程监控

**监控指标：**
- 进程存活状态（通过 `kill -0 <pid>` 检测）
- CPU 使用率
- 内存使用量
- 打开的文件描述符数量
- 子进程数量

**健康检查：**
- 端口响应检测
- HTTP 健康端点检测
- 自定义健康检查命令

**异常自愈：**
- 进程崩溃自动重启
- 重试次数限制
- 退避策略

### 4. 项目注销（卸载）

**四步原子化清理流程：**

```
第一步：进程级阻断
├─ 读取 PID 信息
├─ 发送 SIGTERM 优雅终止
├─ 超时发送 SIGKILL 强制终止
└─ 扫描清理孤儿进程

第二步：备份配置（可选）
├─ 收集需要备份的文件
└─ 打包存储到备份目录

第三步：产物清除
├─ 删除日志目录
├─ 删除临时文件
└─ 删除运行时产物

第四步：本体删除
├─ 递归删除安装目录
├─ 释放端口资源
└─ 记录释放的磁盘空间

第五步：注册表注销
└─ 从注册表移除项目记录
```

## 数据模型

### 项目注册表 (`project_registry.json`)

```json
[
  {
    "project_name": "string (必填，唯一标识)",
    "display_name": "string (展示名称)",
    "description": "string (项目描述)",
    "source": "string (来源地址)",
    "source_type": "github|gitlab|gitee|local|other",
    "tags": ["string"],
    "install_time": "ISO8601 datetime",
    "update_time": "ISO8601 datetime",
    "runtime_env": {
      "type": "python|node|go|java|docker|bash|other",
      "version": "string",
      "env_path": "string (环境路径)",
      "startup_cmd": "string (启动命令)",
      "stop_cmd": "string (停止命令，可选)",
      "health_check_cmd": "string (健康检查命令，可选)",
      "env_vars": {"KEY": "value"}
    },
    "install_path": "string (必填，安装路径)",
    "ports": [int],
    "size_mb": "number",
    "process": {
      "main_pid": "int|null",
      "child_pids": [int],
      "status": "stopped|running|crashed|starting|stopping|corrupted",
      "start_time": "ISO8601 datetime|null",
      "uptime_seconds": "int",
      "crash_info": {
        "exit_code": "int",
        "signal": "string",
        "time": "ISO8601 datetime",
        "stack_trace": "string"
      },
      "restart_count": "int"
    },
    "health": {
      "status": "healthy|degraded|unhealthy|unknown",
      "last_check_time": "ISO8601 datetime",
      "check_interval_seconds": "int",
      "issues": ["string"]
    },
    "artifacts_spec": ["string (产物路径模式)"],
    "auto_restart_policy": {
      "enabled": "boolean",
      "max_retries": "int",
      "retry_count": "int",
      "backoff_seconds": "int",
      "reset_after_seconds": "int"
    },
    "resource_limits": {
      "cpu_percent_max": "int",
      "memory_mb_max": "int",
      "file_descriptors_max": "int"
    },
    "backup_config": {
      "enabled": "boolean",
      "paths": ["string"],
      "exclude_patterns": ["string"]
    }
  }
]
```

## 常用命令

### 项目注册

```bash
# 注册本地项目
project-manager register --path /path/to/project --name my-project

# 从 Git 仓库注册
project-manager register --git https://github.com/user/repo.git --name my-project

# 指定端口
project-manager register --path /path/to/project --name my-project --ports 8080,8081
```

### 项目启停

```bash
# 启动项目
project-manager start my-project

# 停止项目
project-manager stop my-project

# 重启项目
project-manager restart my-project

# 查看项目状态
project-manager status my-project
```

### 项目监控

```bash
# 查看所有项目
project-manager list

# 查看项目详情
project-manager info my-project

# 查看项目日志
project-manager logs my-project --follow

# 查看资源使用
project-manager metrics my-project
```

### 项目卸载

```bash
# 卸载项目（带备份）
project-manager uninstall my-project --backup

# 强制卸载
project-manager uninstall my-project --force

# 查看卸载报告
project-manager uninstall-report my-project
```

## Web 仪表盘

启动 Web 仪表盘：

```bash
project-manager dashboard --port 8000
```

仪表盘功能：
- **全局概览**：项目总数、状态分布、资源使用趋势
- **项目列表**：状态指示灯、多维度排序、模糊搜索
- **项目详情**：进程树、端口监听、依赖列表、配置信息
- **快捷操作**：启动/停止/重启、配置编辑、卸载向导
- **实时监控**：CPU/内存曲线、日志流
- **告警中心**：告警列表、规则配置
- **操作审计**：操作历史、变更记录

## 错误处理

### 错误码

| 错误码 | 名称 | 处理建议 |
|--------|------|----------|
| E001 | PROJECT_NOT_FOUND | 检查项目名称是否正确 |
| E002 | PROJECT_ALREADY_EXISTS | 使用其他名称或先卸载现有项目 |
| E003 | PORT_IN_USE | 选择其他端口或停止占用进程 |
| E004 | DEPENDENCY_CONFLICT | 检查依赖版本，考虑隔离环境 |
| E005 | ENVIRONMENT_ERROR | 检查运行时环境是否正确安装 |
| E006 | PROCESS_START_FAILED | 检查启动命令、日志、权限 |
| E007 | PROCESS_ALREADY_RUNNING | 先停止现有进程 |
| E008 | PROCESS_NOT_RUNNING | 先启动进程 |
| E009 | UNINSTALL_FAILED | 检查进程状态、文件权限 |
| E010 | PERMISSION_DENIED | 联系管理员获取相应权限 |
| E011 | REGISTRY_CORRUPTED | 从备份恢复 |
| E012 | BACKUP_FAILED | 检查磁盘空间、备份路径权限 |

## 使用示例

### 示例 1：注册并启动一个 Python 项目

```bash
# 用户：帮我注册 /opt/projects/my-api 这个项目

# 1. 检测项目类型
$ ls /opt/projects/my-api
main.py  requirements.txt  config.yaml

# 2. 注册项目
$ project-manager register --path /opt/projects/my-api --name my-api
✓ 检测到 Python 项目
✓ 创建虚拟环境: /opt/projects/my-api/.venv
✓ 安装依赖: 12 packages
✓ 分配端口: 8080
✓ 项目已注册: my-api

# 3. 启动项目
$ project-manager start my-api
✓ 启动命令: /opt/projects/my-api/.venv/bin/python main.py --port=8080
✓ 主进程 PID: 12345
✓ 子进程数: 2
✓ 健康检查通过
✓ 项目已启动: my-api

# 4. 查看状态
$ project-manager status my-api
项目名称: my-api
状态: running (PID: 12345)
端口: 8080
运行时间: 5 minutes
CPU: 2.5%
内存: 128 MB
健康状态: healthy
```

### 示例 2：监控项目资源

```bash
# 用户：查看 my-api 的资源使用情况

$ project-manager metrics my-api
┌─────────────────────────────────────────────┐
│          my-api 资源监控 (实时)             │
├─────────────────────────────────────────────┤
│ CPU 使用率:     2.5%                        │
│ 内存使用:       128 MB / 512 MB (25%)      │
│ 文件描述符:     45 / 1024                   │
│ 线程数:         8                           │
│ 网络连接:       12 (监听: 1, 建立: 11)      │
│ 磁盘读写:       读 1.2 MB/s, 写 0.5 MB/s   │
├─────────────────────────────────────────────┤
│ 进程树:                                     │
│ ├─ python main.py (PID: 12345)             │
│ │  ├─ worker-1 (PID: 12346)                │
│ │  └─ worker-2 (PID: 12347)                │
└─────────────────────────────────────────────┘
```

### 示例 3：安全卸载项目

```bash
# 用户：卸载 my-api 项目，需要备份配置

$ project-manager uninstall my-api --backup
🗑️ 卸载向导 - my-api

步骤 1/5: 确认卸载
  项目名称: my-api
  安装路径: /opt/projects/my-api
  占用端口: 8080
  占用空间: 150.5 MB
  
步骤 2/5: 备份配置
  [✓] config.yaml
  [✓] data/
  
步骤 3/5: 终止进程
  ✓ 已终止进程: 12345, 12346, 12347
  
步骤 4/5: 清理文件
  ✓ 已删除: /opt/projects/my-api/logs/*
  ✓ 已删除: /opt/projects/my-api/.venv
  ✓ 已删除: /opt/projects/my-api
  
步骤 5/5: 更新注册表
  ✓ 已从注册表移除

✓ 卸载完成！
  备份位置: /opt/backups/2026-04-08_my-api.tar.gz
  释放空间: 150.5 MB
  释放端口: 8080
```

## 技术实现要点

### 进程存活检测

```python
def is_process_alive(pid: int) -> bool:
    """检查进程是否存活"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
```

### 子进程树获取

```python
def get_child_pids(parent_pid: int) -> List[int]:
    """递归获取所有子进程 PID"""
    import subprocess
    result = subprocess.run(
        ['pgrep', '-P', str(parent_pid)],
        capture_output=True, text=True
    )
    children = [int(p) for p in result.stdout.strip().split('\n') if p]
    
    # 递归获取孙子进程
    all_children = children.copy()
    for child in children:
        all_children.extend(get_child_pids(child))
    
    return all_children
```

### 端口检测

```python
def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port: int = 8000) -> int:
    """查找可用端口"""
    port = start_port
    while is_port_in_use(port):
        port += 1
    return port
```

### 资源监控

```python
def get_process_resources(pid: int) -> dict:
    """获取进程资源使用情况"""
    import psutil
    proc = psutil.Process(pid)
    
    return {
        'cpu_percent': proc.cpu_percent(),
        'memory_mb': proc.memory_info().rss / 1024 / 1024,
        'open_files': len(proc.open_files()),
        'threads': proc.num_threads(),
        'connections': len(proc.connections())
    }
```

## 配置文件示例

```yaml
# /etc/project-manager/config.yaml
skill:
  name: "device-project-manager"
  version: "2.0.0"

server:
  host: "127.0.0.1"
  port: 8000

registry:
  path: "/opt/project-manager/registry.json"
  backup_dir: "/opt/project-manager/backups"
  backup_interval_hours: 6
  max_backup_days: 30

monitor:
  check_interval_seconds: 10
  health_check_timeout_seconds: 5

security:
  auth_enabled: true
  api_key: "${API_KEY}"
  allowed_origins:
    - "http://localhost:3000"
```

## 注意事项

1. **权限要求**：启动/停止进程需要足够权限，建议使用项目所有者账户运行
2. **端口冲突**：注册前检查端口可用性，避免冲突
3. **依赖隔离**：Python/Node.js 项目必须使用虚拟环境隔离
4. **进程清理**：卸载前确保所有相关进程已终止，防止孤儿进程
5. **备份重要**：卸载前建议备份重要配置和数据
6. **日志审计**：所有操作都会记录审计日志，支持追溯

## 相关文件

- `references/registry-schema.json` - 注册表完整 Schema 定义
- `references/api-reference.md` - API 接口完整文档
- `scripts/init_project.py` - 项目注册初始化脚本
- `scripts/monitor.py` - 进程监控脚本
- `scripts/uninstall.py` - 安全卸载脚本
