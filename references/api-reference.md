# Project Manager API Reference

## 概述

Project Manager 提供 RESTful API 和 WebSocket 接口，用于项目全生命周期管理。

- **Base URL**: `http://localhost:8000/api`
- **Content-Type**: `application/json`
- **认证方式**: API Key (Header: `X-API-Key`)

---

## 项目管理

### 获取项目列表

```
GET /api/projects
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 按状态过滤: running, stopped, crashed |
| type | string | 否 | 按类型过滤: python, node, go, java, docker |
| tag | string | 否 | 按标签过滤 |
| search | string | 否 | 搜索项目名称或描述 |
| page | int | 否 | 页码，默认 1 |
| per_page | int | 否 | 每页数量，默认 20 |

**响应示例：**

```json
{
  "projects": [
    {
      "project_name": "my-api",
      "display_name": "My API Service",
      "status": "running",
      "type": "python",
      "ports": [8080],
      "uptime_seconds": 3600,
      "health_status": "healthy"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

---

### 注册新项目

```
POST /api/projects
```

**请求体：**

```json
{
  "project_name": "my-api",
  "source": "/path/to/project",
  "source_type": "local",
  "display_name": "My API Service",
  "description": "API服务项目",
  "tags": ["api", "python"],
  "ports": [8080],
  "runtime_env": {
    "type": "python",
    "version": "3.9",
    "startup_cmd": "python main.py --port={port}",
    "env_vars": {
      "LOG_LEVEL": "INFO"
    }
  },
  "auto_restart_policy": {
    "enabled": true,
    "max_retries": 3
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "project": {
    "project_name": "my-api",
    "install_path": "/opt/projects/my-api",
    "status": "stopped"
  },
  "message": "项目注册成功"
}
```

---

### 获取项目详情

```
GET /api/projects/{project_name}
```

**响应示例：**

```json
{
  "project_name": "my-api",
  "display_name": "My API Service",
  "description": "API服务项目",
  "source": "/path/to/project",
  "source_type": "local",
  "tags": ["api", "python"],
  "install_time": "2026-04-08T10:30:00Z",
  "install_path": "/opt/projects/my-api",
  "ports": [8080],
  "size_mb": 150.5,
  "runtime_env": {
    "type": "python",
    "version": "3.9",
    "env_path": "/opt/projects/my-api/.venv",
    "startup_cmd": "python main.py --port={port}"
  },
  "process": {
    "main_pid": 12345,
    "child_pids": [12346, 12347],
    "status": "running",
    "start_time": "2026-04-08T10:35:00Z",
    "uptime_seconds": 3600
  },
  "health": {
    "status": "healthy",
    "last_check_time": "2026-04-08T11:35:00Z"
  }
}
```

---

### 更新项目配置

```
PUT /api/projects/{project_name}
```

**请求体：**

```json
{
  "display_name": "New Name",
  "tags": ["api", "python", "updated"],
  "runtime_env": {
    "env_vars": {
      "LOG_LEVEL": "DEBUG"
    }
  }
}
```

---

### 删除项目（卸载）

```
DELETE /api/projects/{project_name}
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| backup | bool | 否 | 是否备份，默认 true |
| force | bool | 否 | 是否强制卸载，默认 false |

**响应示例：**

```json
{
  "success": true,
  "report": {
    "project_name": "my-api",
    "uninstall_time": "2026-04-08T12:00:00Z",
    "processes_killed": [12345, 12346, 12347],
    "backup_path": "/opt/backups/2026-04-08_my-api.tar.gz",
    "space_freed_mb": 150.5,
    "ports_released": [8080]
  }
}
```

---

## 进程控制

### 启动项目

```
POST /api/projects/{project_name}/start
```

**响应示例：**

```json
{
  "success": true,
  "process": {
    "main_pid": 12345,
    "child_pids": [12346, 12347],
    "status": "running",
    "start_time": "2026-04-08T10:35:00Z"
  }
}
```

---

### 停止项目

```
POST /api/projects/{project_name}/stop
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| timeout | int | 否 | 等待超时秒数，默认 10 |
| force | bool | 否 | 是否强制终止，默认 false |

**响应示例：**

```json
{
  "success": true,
  "process": {
    "main_pid": null,
    "child_pids": [],
    "status": "stopped",
    "exit_code": 0
  }
}
```

---

### 重启项目

```
POST /api/projects/{project_name}/restart
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| graceful | bool | 否 | 是否优雅重启，默认 true |
| timeout | int | 否 | 停止等待超时秒数，默认 10 |

---

## 监控

### 获取项目状态

```
GET /api/projects/{project_name}/status
```

**响应示例：**

```json
{
  "project_name": "my-api",
  "status": "running",
  "uptime_seconds": 3600,
  "health_status": "healthy",
  "main_pid": 12345,
  "ports": [8080]
}
```

---

### 获取资源指标

```
GET /api/projects/{project_name}/metrics
```

**响应示例：**

```json
{
  "project_name": "my-api",
  "timestamp": "2026-04-08T11:35:00Z",
  "cpu_percent": 2.5,
  "memory_mb": 128.5,
  "memory_percent": 1.2,
  "open_files": 45,
  "threads": 8,
  "connections": 12,
  "disk_read_mb": 10.5,
  "disk_write_mb": 5.2,
  "network_in_mb": 100.0,
  "network_out_mb": 50.0,
  "process_tree": [
    {
      "pid": 12345,
      "name": "python",
      "cmdline": "python main.py --port=8080",
      "cpu_percent": 1.0,
      "memory_mb": 64.0
    },
    {
      "pid": 12346,
      "name": "python",
      "cmdline": "worker-1",
      "cpu_percent": 0.75,
      "memory_mb": 32.0
    }
  ]
}
```

---

### 获取项目日志

```
GET /api/projects/{project_name}/logs
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| lines | int | 否 | 返回行数，默认 100 |
| level | string | 否 | 日志级别过滤: DEBUG, INFO, WARN, ERROR |
| follow | bool | 否 | 是否流式返回（需 WebSocket） |

**响应示例：**

```json
{
  "project_name": "my-api",
  "logs": [
    {
      "timestamp": "2026-04-08T11:35:00Z",
      "level": "INFO",
      "message": "Server started on port 8080"
    },
    {
      "timestamp": "2026-04-08T11:35:01Z",
      "level": "INFO",
      "message": "Worker 1 ready"
    }
  ]
}
```

---

### 执行健康检查

```
POST /api/projects/{project_name}/health-check
```

**响应示例：**

```json
{
  "project_name": "my-api",
  "status": "healthy",
  "response_time_ms": 15,
  "checks": [
    {
      "name": "port_listen",
      "status": "pass",
      "message": "Port 8080 is listening"
    },
    {
      "name": "http_endpoint",
      "status": "pass",
      "message": "HTTP /health returned 200"
    }
  ]
}
```

---

## 批量操作

### 批量启动项目

```
POST /api/projects/batch/start
```

**请求体：**

```json
{
  "projects": ["my-api", "worker-1", "worker-2"]
}
```

**响应示例：**

```json
{
  "success": true,
  "results": {
    "my-api": {"status": "started", "pid": 12345},
    "worker-1": {"status": "started", "pid": 12400},
    "worker-2": {"status": "failed", "error": "Port 8082 already in use"}
  }
}
```

---

### 批量停止项目

```
POST /api/projects/batch/stop
```

---

## 审计日志

### 获取操作日志

```
GET /api/audit-logs
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_name | string | 否 | 按项目过滤 |
| action | string | 否 | 按操作类型过滤 |
| operator | string | 否 | 按操作者过滤 |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |
| page | int | 否 | 页码 |
| per_page | int | 否 | 每页数量 |

**响应示例：**

```json
{
  "logs": [
    {
      "id": "uuid",
      "timestamp": "2026-04-08T10:35:00Z",
      "action": "start",
      "project_name": "my-api",
      "operator": "admin",
      "source_ip": "127.0.0.1",
      "result": "success",
      "duration_ms": 150
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}
```

---

## WebSocket

### 连接状态流

```
WS /ws/status
```

**消息格式：**

```json
{
  "type": "status_change",
  "project_name": "my-api",
  "data": {
    "status": "running",
    "main_pid": 12345,
    "uptime_seconds": 3600
  },
  "timestamp": "2026-04-08T11:35:00Z"
}
```

**事件类型：**

| 类型 | 说明 |
|------|------|
| status_change | 状态变更 |
| health_change | 健康状态变更 |
| resource_alert | 资源告警 |
| crash_alert | 崩溃告警 |
| log | 日志流 |

---

## 错误响应

所有错误响应遵循统一格式：

```json
{
  "error": {
    "code": "E003",
    "name": "PORT_IN_USE",
    "message": "端口 8080 已被占用",
    "details": {
      "port": 8080,
      "process": {
        "pid": 9999,
        "name": "other-service"
      }
    }
  }
}
```

---

## 系统接口

### 获取系统概览

```
GET /api/system/overview
```

**响应示例：**

```json
{
  "total_projects": 12,
  "running": 8,
  "stopped": 3,
  "crashed": 1,
  "total_disk_mb": 2048.5,
  "used_disk_mb": 512.0,
  "ports_in_use": [8080, 3000, 9090],
  "system_metrics": {
    "cpu_percent": 25.5,
    "memory_percent": 60.2,
    "disk_percent": 45.0
  }
}
```

---

### 获取端口使用情况

```
GET /api/system/ports
```

**响应示例：**

```json
{
  "ports": [
    {
      "port": 8080,
      "status": "in_use",
      "project_name": "my-api",
      "process": {
        "pid": 12345,
        "name": "python"
      }
    },
    {
      "port": 8081,
      "status": "available"
    }
  ]
}
```

---

### 备份注册表

```
POST /api/system/backup
```

**响应示例：**

```json
{
  "success": true,
  "backup_path": "/opt/backups/registry_20260408_120000.json",
  "size_kb": 12.5
}
```

---

### 恢复注册表

```
POST /api/system/restore
```

**请求体：**

```json
{
  "backup_path": "/opt/backups/registry_20260408_120000.json"
}
```
