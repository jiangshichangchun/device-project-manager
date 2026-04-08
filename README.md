# Device Project Manager Skill

设备端项目全生命周期管理技能 - 提供项目注册、环境配置、启停监控、安全注销的标准化管理。

## 功能特性

- 📦 **项目注册** - 自动识别项目类型（Python/Node/Go/Java/Docker），创建隔离环境
- 🚀 **启停管理** - 标准化的启动、停止、重启流程
- 📊 **进程监控** - 实时监控进程状态、资源使用、健康检查
- 🧹 **安全卸载** - 四步原子化清理，确保无残留
- 🔔 **自动重启** - 进程崩溃自动恢复
- 📝 **操作审计** - 所有操作留痕，支持追溯

## 目录结构

```
device-project-manager/
├── SKILL.md                          # 技能主文件
├── README.md                         # 说明文档
├── references/
│   ├── registry-schema.json          # 注册表 Schema
│   └── api-reference.md              # API 文档
├── scripts/
│   ├── init_project.py               # 项目注册脚本
│   ├── monitor.py                    # 进程监控脚本
│   └── uninstall.py                  # 安全卸载脚本
└── assets/                           # 资源文件
```

## 快速开始

### 注册项目

```bash
# 注册本地项目
python scripts/init_project.py --path /path/to/project --name my-project

# 从 Git 仓库注册
python scripts/init_project.py --git https://github.com/user/repo.git --name my-project
```

### 启动项目

```bash
python scripts/monitor.py start my-project
```

### 查看状态

```bash
python scripts/monitor.py status my-project
python scripts/monitor.py metrics my-project
```

### 停止项目

```bash
python scripts/monitor.py stop my-project
```

### 卸载项目

```bash
# 卸载并备份
python scripts/uninstall.py my-project --backup

# 强制卸载
python scripts/uninstall.py my-project --force
```

## 支持的项目类型

| 类型 | 标识文件 | 环境隔离 |
|------|----------|----------|
| Python | requirements.txt, pyproject.toml | venv |
| Node.js | package.json | node_modules |
| Go | go.mod | 无需隔离 |
| Java | pom.xml, build.gradle | 无需隔离 |
| Docker | Dockerfile | 容器 |

## 数据模型

项目信息存储在 JSON 注册表中，包含：

- 项目元数据（名称、描述、标签）
- 运行时环境配置
- 进程状态信息
- 健康检查状态
- 自动重启策略
- 资源限制配置
- 备份配置

详细 Schema 定义见 [references/registry-schema.json](references/registry-schema.json)

## API 接口

提供完整的 RESTful API：

- `GET /api/projects` - 获取项目列表
- `POST /api/projects` - 注册新项目
- `GET /api/projects/{name}` - 获取项目详情
- `DELETE /api/projects/{name}` - 卸载项目
- `POST /api/projects/{name}/start` - 启动项目
- `POST /api/projects/{name}/stop` - 停止项目
- `GET /api/projects/{name}/metrics` - 获取资源指标
- `WS /ws/status` - 实时状态推送

详细 API 文档见 [references/api-reference.md](references/api-reference.md)

## 许可证

MIT License
