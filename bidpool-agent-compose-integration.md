# BidPool 接入 agent-compose 技术方案

## 1. 背景与目标

BidPool 标讯智能平台原本是一个独立的三层架构（Go 后端 + Python Agent + Vue 前端），通过 REST API 对外服务。目标是将 BidPool 的能力接入 agent-compose 平台，使得 AI Agent 可以通过自然语言直接操作 BidPool 的标讯查询、任务管理、执行调度等全部功能。

### 接入方式对比

| 方案                  | 描述                                        | 选择        |
| ------------------- | ----------------------------------------- | --------- |
| **作为 OctoBus 服务接入** | 创建 Node.js gRPC 代理层，通过 OctoBus 注册为 MCP 工具 | ✅         |
| 作为 Agent 工具代码接入     | 在 agent-compose 中内置 BidPool 的调用逻辑         | ❌ 耦合度高    |
| 直接 API 调用           | Agent 通过 curl 直接调用 BidPool REST API       | ❌ 无统一网关管理 |

选择方案 1 的原因：
- **解耦**：BidPool 的接口变更不影响 agent-compose 主体
- **统一管理**：通过 OctoBus 的 capset 机制控制权限和路由
- **自动 MCP 暴露**：AI Agent 通过 MCP 协议自动发现工具
- **标准化**：gRPC 接口定义清晰，类型安全

## 2. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                    agent-compose (port 7410)                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              AI Agent (Docker 容器)                        │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  1. System Prompt → 指导 Agent 调用哪些接口           │ │ │
│  │  │  2. MCP Tools → 自动发现可用工具                      │ │ │
│  │  │  3. curl → 调用 host.docker.internal:9000 的接口      │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   OctoBus 网关 (port 9000)                     │
│  ┌──────────────────┐  ┌──────────────────────────────────┐  │
│  │  Calculator 实例  │  │    BidPool 实例 (Node.js)        │  │
│  │  (port 65530)     │  │  ┌────────────────────────────┐ │  │
│  │                   │  │  │ defineService({13 handlers})│ │  │
│  │                   │  │  │ 每个 handler:               │ │  │
│  │                   │  │  │   gRPC请求 → HTTP fetch     │ │  │
│  │                   │  │  │   → BidPool Go 后端         │ │  │
│  │                   │  │  └────────────────────────────┘ │  │
│  └──────────────────┘  └──────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  BidPool Go 后端 (port 8080)                   │
│     Gin Router → Handlers → SQLite + Scheduler                │
│                          │                                     │
│                          ▼                                     │
│              BidPool Python Agent (FastAPI)                    │
│     CrawlerAgent / DispatchAgent / OrchestratorAgent           │
└──────────────────────────────────────────────────────────────┘
```

## 3. OctoBus 服务包结构

```
agent_compose_src/bidpool-service/
├── package.json             # Node.js 包定义 (bin.bidpool)
├── service.json             # OctoBus 服务元数据
├── proto/
│   └── bidpool.proto        # gRPC protobuf 定义 (13 RPCs)
├── bin/
│   └── service.js           # 服务实现 (HTTP 代理)
├── config.schema.json       # 实例配置 schema
└── secret.schema.json       # 密钥 schema
```

### 3.1 service.json

```json
{
  "schema": "chaitin.octobus.service.v1",
  "name": "bidpool",
  "displayName": "BidPool Service",
  "description": "标讯智能平台服务",
  "proto": {
    "roots": ["proto"],
    "files": ["proto/bidpool.proto"]
  },
  "configSchema": "config.schema.json",
  "secretSchema": "secret.schema.json"
}
```

### 3.2 Protobuf 定义 (bidpool.proto)

定义 `bidpool.v1.BidPoolService` 服务，包含 13 个 RPC：

| RPC                | 功能          | 对应 REST API                            |
| ------------------ | ----------- | -------------------------------------- |
| `GetStatus`        | 系统状态与统计     | `GET /api/v1/status`                   |
| `ListBids`         | 标讯列表（分页+筛选） | `GET /api/v1/bids`                     |
| `GetBid`           | 标讯详情        | `GET /api/v1/bids/:id`                 |
| `ListTasks`        | 任务列表        | `GET /api/v1/tasks`                    |
| `GetTask`          | 任务详情        | `GET /api/v1/tasks/:id`                |
| `CreateTask`       | 创建任务        | `POST /api/v1/tasks`                   |
| `UpdateTask`       | 更新任务        | `PUT /api/v1/tasks/:id`                |
| `DeleteTask`       | 删除任务        | `DELETE /api/v1/tasks/:id`             |
| `RunTask`          | 执行任务        | `POST /api/v1/tasks/:id/run`           |
| `GetExecution`     | 执行详情        | `GET /api/v1/executions/:task_id`      |
| `GetExecutionLogs` | 执行日志        | `GET /api/v1/executions/:task_id/logs` |
| `DispatchBids`     | 分发标讯到钉钉     | `POST /api/v1/bids/dispatch`           |
| `Chat`             | AI 对话       | `POST /api/v1/chat`                    |

## 4. 核心实现：gRPC → HTTP 代理模式

### 4.1 服务入口

```javascript
import { defineService, runServiceMain } from "@chaitin-ai/octobus-sdk";

const service = defineService({
  handlers: {
    "bidpool.v1.BidPoolService/GetStatus": async (ctx) => {
      const data = await apiFetch(ctx, "/api/v1/status");
      return {
        totalBids: Number(data.bid_count || 0),
        totalTasks: Number(data.task_count || 0),
        // ...
      };
    },
    // ... 其余 12 个 handler
  },
});

runServiceMain(service);
```

### 4.2 HTTP 代理核心

`apiFetch` 封装了 HTTP 请求的公共逻辑：认证、超时、错误处理、响应解包。

```javascript
async function apiFetch(ctx, path, options = {}) {
  const baseUrl = ctx.config.backend_url || "http://127.0.0.1:8080";
  const timeout = ctx.config.request_timeout_ms || 30000;
  const headers = {
    Authorization: basicAuthHeader(ctx.secret.username, ctx.secret.password),
    "Content-Type": "application/json",
  };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: controller.signal,
  });

  return unwrap(await response.json());
}
```

**关键设计**：
- **认证**：从 `ctx.secret` 读取用户名密码 → Basic Auth
- **配置**：从 `ctx.config` 读取后端 URL 和超时
- **响应解包**：BidPool API 返回 `{code, data, message}` 格式，`unwrap()` 自动校验 `code===0` 并提取 `data`，非零 code 自动抛 gRPC 错误
- **字段映射**：BidPool Go 后端使用 snake_case 字段名（如 `tender_unit`），gRPC 响应使用 camelCase（如 `tenderUnit`），`mapBid()` 等函数在代理层完成转换

### 4.3 配置与密钥

config.schema.json：
```json
{
  "properties": {
    "backend_url": { "type": "string", "default": "http://127.0.0.1:8080" },
    "request_timeout_ms": { "type": "integer", "default": 30000 }
  }
}
```

secret.schema.json：
```json
{
  "required": ["password"],
  "properties": {
    "username": { "type": "string", "default": "admin" },
    "password": { "type": "string" }
  }
}
```

## 5. Agent 接入方式

### 5.1 方式一：MCP 协议（自动发现）

OctoBus 将注册的服务自动暴露为 MCP 工具，AI Agent 通过 `tools/list` 自动发现：

```
bidpool__bidpool__list_bids        -> List bids with pagination and filters
bidpool__bidpool__get_status       -> Get system status and statistics
bidpool__bidpool__create_task      -> Create a new task
bidpool__bidpool__run_task         -> Manually run a task
...
```

### 5.2 方式二：System Prompt 定义

在 `octobus-demo.yml` 中为 AI Agent 定义 system_prompt，指导其如何调用这些接口：

```yaml
agents:
  bidpool-agent:
    provider: codex
    image: agent-compose-guest:latest
    system_prompt: |
      你是标讯智能助手，可以通过 HTTP 调用 OctoBus：
      POST http://host.docker.internal:9000/capsets/dev/connect/bidpool/bidpool.v1.BidPoolService/ListBids
      POST http://host.docker.internal:9000/capsets/dev/connect/bidpool/bidpool.v1.BidPoolService/CreateTask
      ...
```

AI Agent 运行在 Docker 容器内，通过 `host.docker.internal` 访问宿主机的 OctoBus 网关（port 9000）。

### 5.3 方式三：直接 curl 调用（调试）

```bash
curl -X POST http://127.0.0.1:9000/capsets/dev/connect/bidpool/bidpool.v1.BidPoolService/GetStatus \
  -H "Content-Type: application/json" -d '{}'

curl -X POST http://127.0.0.1:9000/capsets/dev/connect/bidpool/bidpool.v1.BidPoolService/ListBids \
  -H "Content-Type: application/json" -d '{"page":1,"pageSize":5,"industry":"政府"}'
```

## 6. 部署流程

### 6.1 启动 BidPool Go 后端

```bash
cd /Users/zhonghai.liu/Desktop/code/BidPool/bidpool-go
mkdir -p data
./bidpool-go &
# API: http://127.0.0.1:8080
```

### 6.2 导入 OctoBus 服务

```bash
# 安装依赖
cd agent_compose_src/bidpool-service && npm install

# 导入服务（bin 入口名需与 service ID 一致）
../octobus_src/bin/octobus service import bidpool ./bidpool-service

# 创建实例
../octobus_src/bin/octobus instance create bidpool --service bidpool \
  --config-json '{"backend_url": "http://127.0.0.1:8080", "request_timeout_ms": 30000}' \
  --secret-json '{"username": "admin", "password": "bidpool@2026"}'

# 加入 capset
../octobus_src/bin/octobus capset add-instance dev bidpool
```

### 6.3 启动 agent-compose

```bash
# 启动 daemon
cd agent_compose_src
./bin/agent-compose daemon &

# 应用 compose 配置
export OPENAI_API_KEY="sk-xxx"
./bin/agent-compose -f octobus-demo.yml up
```

### 6.4 验证

```bash
# 验证 MCP 工具
curl -X POST http://127.0.0.1:9000/capsets/dev/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 验证 Connect RPC
curl -X POST http://127.0.0.1:9000/capsets/dev/connect/bidpool/bidpool.v1.BidPoolService/GetStatus \
  -H "Content-Type: application/json" -d '{}'
```

## 7. 关键要点

### 7.1 API 响应格式适配

BidPool Go 后端使用统一的响应包装格式：
```json
{"code": 0, "data": {...}, "message": "success"}
```

代理层需要：
1. 校验 `code === 0`，非零视为错误
2. 提取 `data` 字段作为实际响应体
3. 字段名转换：snake_case（Go 后端）→ camelCase（gRPC 响应）

### 7.2 认证传递

- BidPool Go 后端使用 HTTP Basic Auth
- 代理层从 OctoBus 实例的 secret 中读取 `username` / `password`
- 每个 `apiFetch` 调用自动附加 `Authorization: Basic xxx` 头
- 避免在服务代码中硬编码凭证

### 7.3 文件权限

OctoBus 导入服务时会打包源码为 `.tgz` 并解压到 runtime 目录。`bin/service.js` 需要可执行权限，否则启动失败：

```bash
chmod +x agent_compose_src/bidpool-service/bin/service.js
```

### 7.4 网络可达性

- AI Agent 运行在 Docker 容器中，通过 `host.docker.internal:9000` 访问 OctoBus
- OctoBus 的 bidpool 实例通过 `backend_url: http://127.0.0.1:8080` 访问 Go 后端
- `host.docker.internal` 仅在 macOS Docker Desktop 下有效；Linux 下需使用 `--network host` 或 `172.17.0.1`

## 8. 服务一览

| 服务                   | 地址                    | 说明                  |
| -------------------- | --------------------- | ------------------- |
| BidPool 前端 (Vue3)    | http://localhost:3000 | 原始 Web 界面           |
| BidPool Go 后端 API    | http://localhost:8080 | REST API            |
| OctoBus 网关           | http://localhost:9000 | gRPC/Connect/MCP 网关 |
| agent-compose Web UI | http://localhost:7410 | AI Agent 管理界面       |
| bidpool OctoBus 实例   | 127.0.0.1:58965       | Node.js 代理进程        |
| BidPool Python Agent | 内部 :8000              | 爬虫/分发/编排            |

## 9. 扩展：添加新的 BidPool 接口

如果后续 BidPool 增加了新的 API 端点，接入步骤：

1. **更新 proto 文件**：在 `bidpool.proto` 中添加新的 RPC 和消息定义
2. **更新 service.js**：添加对应的 handler，调用 `apiFetch` 代理到新的 REST API
3. **重新导入服务**：`octobus service import bidpool ./bidpool-service`（自动重启实例）
4. **更新 octobus-demo.yml**：在 system_prompt 中添加新接口的调用说明
5. **验证**：通过 curl 和 MCP 确认新接口可用
