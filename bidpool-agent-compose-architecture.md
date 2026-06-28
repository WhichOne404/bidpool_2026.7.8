# BidPool 标讯平台 × agent-compose AI 平台 集成技术方案

> **编写日期**：2026-06-28
> **系统版本**：Go 1.26 / Node.js 22 / agent-compose 2.1.139 / OctoBus 0.x
> **部署环境**：Ubuntu 24.04, Docker 28.x

---

## 目录

1. [整体架构总览](#1-整体架构总览)
2. [技术栈全景](#2-技术栈全景)
3. [组件详解](#3-组件详解)
   - 3.1 [BidPool Go 后端](#31-bidpool-go-后端)
   - 3.2 [BidPool Python Agent](#32-bidpool-python-agent)
   - 3.3 [OctoBus 集成网关](#33-octobus-集成网关)
   - 3.4 [agent-compose AI 平台](#34-agent-compose-ai-平台)
4. [AI Agent 架构](#4-ai-agent-架构)
   - 4.1 [多层提示词体系](#41-多层提示词体系)
   - 4.2 [MPI Catalog 机制](#42-mpi-catalog-机制)
   - 4.3 [通信协议栈](#43-通信协议栈)
5. [集成实现细节](#5-集成实现细节)
   - 5.1 [gRPC → REST 代理层](#51-grpc--rest-代理层)
   - 5.2 [Connect RPC 调用链路](#52-connect-rpc-调用链路)
   - 5.3 [MCP 工具暴露](#53-mcp-工具暴露)
   - 5.4 [Catalog 动态生成](#54-catalog-动态生成)
6. [数据流完整追踪](#6-数据流完整追踪)
7. [关键问题与解决方案](#7-关键问题与解决方案)
8. [部署与运维](#8-部署与运维)
9. [扩展指南](#9-扩展指南)

---

## 1. 整体架构总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         用户 (User)                                       │
│             浏览器访问 http://10.2.36.217:80 或 API 调用                   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   agent-compose 平台 (10.2.36.217)                        │
│                                                                          │
│  ┌────────────────────┐   ┌──────────────────────────────────────────┐   │
│  │  Nginx 前端 (:80)   │──▶│  agent-compose Daemon (:7410)            │   │
│  │  (静态文件 + 反向代理) │   │  ┌──────────┐  ┌────────────────────┐  │   │
│  └────────────────────┘   │  │ Echo HTTP │  │ Session Manager    │  │   │
│                           │  │ Router    │  │ - 创建/停止/查询     │  │   │
│                           │  ├──────────┤  │ - Docker 容器管理    │  │   │
│                           │  │ Connect  │  │ - Catalog 生成       │  │   │
│                           │  │ gRPC     │  │ - MPI 上下文注入      │  │   │
│                           │  │ Server   │  └────────────────────┘  │   │
│                           │  └──────────┘                           │   │
│                           └──────────────┬──────────────────────────┘   │
│                                          │                              │
│  ┌───────────────────────────────────────▼──────────────────────────┐   │
│  │          AI Agent (Docker 容器)                                  │   │
│  │                                                                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │                  Claude Code CLI                            │  │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌─────────────────────────┐   │  │   │
│  │  │  │ System   │  │ MPI      │  │ Claude SDK              │   │  │   │
│  │  │  │ Prompt   │  │ Catalog  │  │ (Anthropic API 调用)     │   │  │   │
│  │  │  └──────────┘  └──────────┘  └──────────┬──────────────┘   │  │   │
│  │  │                                          │                  │  │   │
│  │  │  ┌───────────────────────────────────────▼────────────────┐  │  │   │
│  │  │  │          LLM (feature/flash)                          │  │  │   │
│  │  │  │  Bash Tool: curl → OctoBus Connect RPC                │  │  │   │
│  │  │  └───────────────────────────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ DNS: octobus:9000 (Docker network)
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    OctoBus 网关 (:9000)                                   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  协议转换层                                                         │  │
│  │  ┌────────────┐  ┌────────────────┐  ┌─────────────────────────┐  │  │
│  │  │ gRPC Server │  │ Connect RPC    │  │ MCP Server              │  │  │
│  │  │ (HTTP/2)    │  │ (HTTP JSON)    │  │ (tools/list, tools/call) │  │  │
│  │  └────────────┘  └────────────────┘  └─────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  BidPool 服务实例                                                    │  │
│  │  Node.js 进程 (grpc proxy)                                          │  │
│  │                                                                     │  │
│  │  13 RPC handlers:                                                   │  │
│  │  bidpool.v1.BidPoolService                                          │  │
│  │  ├── GetStatus     → GET  /api/v1/status           → BidPool Go    │  │
│  │  ├── ListBids      → GET  /api/v1/bids             → BidPool Go    │  │
│  │  ├── GetBid        → GET  /api/v1/bids/:id         → BidPool Go    │  │
│  │  ├── ListTasks     → GET  /api/v1/tasks             → BidPool Go    │  │
│  │  ├── CreateTask    → POST /api/v1/tasks             → BidPool Go    │  │
│  │  ├── ...           → ...                            → BidPool Go    │  │
│  │  └── Chat          → POST /api/v1/chat              → BidPool Go    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ HTTP REST (Basic Auth)
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│          BidPool 后端 (10.2.37.237)                                      │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Nginx (:8088) — 反向代理 + 静态文件                                  │  │
│  └──────────────────────────┬─────────────────────────────────────────┘  │
│                             │                                            │
│  ┌──────────────────────────▼─────────────────────────────────────────┐  │
│  │  Go 后端 (bidpool-go, :8080)                                       │  │
│  │                                                                     │  │
│  │  Gin Router → Handlers                                              │  │
│  │  ├── Basic Auth 中间件                                               │  │
│  │  ├── BidHandler   → CRUD + 分页查询 (GORM + SQLite)                  │  │
│  │  ├── TaskHandler  → CRUD + 手动触发 + 日志查询                         │  │
│  │  ├── ChatHandler  → 转发到 Python Agent                              │  │
│  │  └── SystemHandler → 状态 + 配置                                     │  │
│  │                                                                     │  │
│  │  Scheduler (robfig/cron)                                            │  │
│  │  ├── 定时任务管理 (CRUD + 持久化)                                      │  │
│  │  └── 执行引擎 → HTTP 调用 Python Agent                                │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Python Agent (FastAPI, :8001)                                     │  │
│  │                                                                     │  │
│  │  ├── CrawlerAgent     — Selenium + Chrome 浏览器爬虫                 │  │
│  │  │                     千里马/招标网等平台数据采集                      │  │
│  │  ├── FilterAgent     — 关键词/行业/地区过滤                          │  │
│  │  ├── DispatchAgent   — 钉钉 Webhook 消息分发                        │  │
│  │  └── Orchestrator    — LLM 对话代理 (DeepSeek/SiliconFlow)         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术栈全景

### 2.1 核心平台

| 组件               | 技术                               | 版本      | 部署方式                                      |
| ---------------- | -------------------------------- | ------- | ----------------------------------------- |
| agent-compose 平台 | Go / Echo v4                     | 2.1.139 | Docker 容器 (ghcr.io/chaitin/agent-compose) |
| agent-compose 前端 | Svelte / Vite                    | -       | Docker 容器 (nginx)                         |
| OctoBus 网关       | Go                               | 0.x     | 二进制进程 (10.2.36.217)                       |
| Claude Code CLI  | Anthropic SDK                    | latest  | Docker 容器 (guest)                         |
| LLM              | Anthropic Claude (feature/flash) | -       | 云端 API (ai-api-gateway.app.baizhi.cloud)  |

### 2.2 BidPool 业务层

| 组件           | 技术                         | 版本          | 端口   |
| ------------ | -------------------------- | ----------- | ---- |
| Go 后端        | Gin / GORM / robfig/cron   | Go 1.26     | 8080 |
| Python Agent | FastAPI / Selenium / httpx | Python 3.12 | 8001 |
| Nginx        | nginx:alpine               | 1.31        | 8088 |
| 数据库          | SQLite (通过 GORM)           | -           | 文件存储 |
| LLM 集成       | SiliconFlow API / DeepSeek | -           | 外调   |

### 2.3 集成中间件

| 组件          | 技术                      | 版本      | 作用               |
| ----------- | ----------------------- | ------- | ---------------- |
| OctoBus SDK | @chaitin-ai/octobus-sdk | latest  | Node.js gRPC 服务端 |
| gRPC        | connectrpc.com          | v1.19.2 | 服务间 RPC 协议       |
| Connect RPC | HTTP JSON 传输            | -       | AI Agent 调用协议    |
| MCP         | Model Context Protocol  | -       | 工具自动发现协议         |
| Protobuf    | proto3                  | -       | 接口定义语言           |

---

## 3. 组件详解

### 3.1 BidPool Go 后端

**启动流程** (`cmd/server/main.go`):

```
1. LoadConfig()         → YAML 配置 (端口/数据库/认证/爬虫平台)
2. store.InitDB()       → GORM 初始化 SQLite (自动迁移表结构)
3. scheduler.New()      → robfig/cron 调度器
4. scheduler.Start()    → 从数据库恢复未删除的定时任务
5. api.SetupRouter()    → Gin 路由注册 + Basic Auth 中间件
6. router.Run()         → 监听 :8080
```

**路由结构** (`api.SetupRouter()`):

```
GET    /health                 健康检查（无认证）
GET    /api/v1/status          系统状态统计
GET    /api/v1/bids            标讯列表（分页 + 筛选）
GET    /api/v1/bids/:id        标讯详情
POST   /api/v1/bids/dispatch   分发标讯到钉钉
GET    /api/v1/tasks           任务列表
POST   /api/v1/tasks           创建定时任务
GET    /api/v1/tasks/:id       任务详情
PUT    /api/v1/tasks/:id       更新任务
DELETE /api/v1/tasks/:id       删除任务
POST   /api/v1/tasks/:id/run   手动触发任务
GET    /api/v1/executions/:task_id        执行记录
GET    /api/v1/executions/:task_id/logs   执行日志
POST   /api/v1/chat            AI 对话
```

**认证**：所有 `/api/v1/*` 路径通过 Gin 中间件实现 HTTP Basic Auth，凭据在 `config.yaml` 中配置。

**定时调度**：使用 `robfig/cron` 库，任务定义持久化在 SQLite 中，服务重启后自动恢复。

### 3.2 BidPool Python Agent

Python Agent 提供四类智能体能力：

```
FastAPI 应用 (:8001)
│
├── /api/crawl          → CrawlerAgent (subprocess: selenium + Chrome)
│                          ├── 千里马招标网爬虫
│                          └── 招标网爬虫
│
├── /api/filter         → FilterAgent
│                          ├── 关键词匹配
│                          └── 行业分类
│
├── /api/dispatch       → DispatchAgent
│                          └── 钉钉 Webhook 消息推送
│
└── /api/chat           → OrchestratorAgent (LLM 对话代理)
                           ├── SiliconFlow API (DeepSeek)
                           └── 多轮对话 + 记忆
```

### 3.3 OctoBus 集成网关

OctoBus 是一个服务注册和协议转换网关，核心能力：

1. **服务注册**：通过 `octobus service import` 导入 gRPC 服务定义
2. **实例管理**：每个服务可创建多个实例，配置和密钥分离
3. **CapSet**：能力集 — 将服务实例分组并暴露给 AI Agent
4. **三重协议暴露**：
   - **gRPC**：标准 HTTP/2 gRPC (proto 二进制)
   - **Connect RPC**：HTTP JSON 传输 (curl 友好)
   - **MCP**：Model Context Protocol (AI 工具发现)

**服务导入流程**：

```
octobus service import bidpool ./bidpool-service
  │
  ├── package.json  → 读取入口文件 (bin.service.js)
  ├── service.json  → 服务元数据 (名称、proto 路径)
  ├── proto/        → 编译 .proto 文件
  └── bin/service.js → 打包为 .tgz → 解压到 runtime 目录 → 启动 Node.js 进程
```

**gRPC → REST 代理 (核心逻辑)**：

```javascript
// 每个 RPC handler 复用 apiFetch 进行 HTTP 代理
const service = defineService({
  handlers: {
    "bidpool.v1.BidPoolService/ListBids": async (ctx) => {
      const data = await apiFetch(ctx, "/api/v1/bids", {
        params: { page: ctx.req.page, page_size: ctx.req.pageSize }
      });
      return { bids: data.bids?.map(mapBid), total: Number(data.total) };
    },
    "bidpool.v1.BidPoolService/CreateTask": async (ctx) => {
      const data = await apiFetch(ctx, "/api/v1/tasks", {
        method: "POST", body: ctx.req
      });
      return { task: mapTask(data) };
    },
    // ... 其余 11 个 handler
  }
});
```

**apiFetch 代理函数**：

```
apiFetch(ctx, path, options)
  1. ctx.config.backend_url → BidPool Go 后端地址 (默认 http://127.0.0.1:8080)
  2. ctx.secret.username/password → Basic Auth 头
  3. URL 拼接 + 超时控制 (AbortController, 默认 30s)
  4. HTTP 请求 → JSON 解析 → unwrap(data) 解包
  5. 字段名转换: snake_case → camelCase
  6. 返回 gRPC 响应
```

### 3.4 agent-compose AI 平台

agent-compose 是一个 AI Agent 编排平台，核心架构：

```
agent-compose Daemon (:7410)
│
├── Echo HTTP Router (REST API)
│   ├── /api/auth/*         认证 (session cookie)
│   ├── /api/agent_definition/*  智能体 CRUD
│   ├── /api/agent-compose/sessions/*  会话管理
│   └── /api/webhook-sources/*  事件源管理
│
├── Connect gRPC Server
│   ├── agentcompose.v1.AgentDefinitionService
│   │   ├── ListAgentDefinitions
│   │   ├── CreateAgentSession    ← 创建会话 + 启动 Guest 容器
│   │   └── ...
│   ├── agentcompose.v1.AgentService
│   │   ├── SendAgentMessage      ← 发送消息到 Agent
│   │   └── ...
│   └── agentcompose.v1.SessionService
│       ├── GetSession
│       ├── StopSession
│       └── ...
│
├── Capability Gateway
│   ├── Catalog 生成 → 调用 OctoBus /admin/v1/catalog/:capset_id
│   └── Session Token 管理 (CAP_TOKEN)
│
└── Docker Runtime
    ├── 创建/管理 Guest 容器
    ├── 挂载 Session 数据卷
    └── 网络配置 (tmp_octobus-net)
```

**Guest 容器内部结构**：

```
agent-compose-guest Docker 容器
│
├── Claude Code CLI (Node.js)
│   ├── agent-compose-runtime-js (MPI 上下文注入)
│   │   ├── mpi.ts → formatMpiContext()
│   │   └── loadMpiContext() → catalog.md 读取 + 格式化
│   │
│   ├── System Prompt (来自 agent_definition DB)
│   │   ├── 角色定义 + 语言指令
│   │   └── API 调用示例 (curl 命令)
│   │
│   └── MPI Catalog (来自 OctoBus catalog.md)
│       ├── Gateway 访问说明
│       ├── Connect RPC 端点表
│       ├── gRPC 方法表
│       └── MCP 工具表
│
└── 环境变量
    ├── CAP_GRPC_TARGET=octobus:9000
    ├── CAP_TOKEN=xxxx
    └── ANTHROPIC_API_KEY=xxx
```

---

## 4. AI Agent 架构

### 4.1 多层提示词体系

AI Agent 的提示词由多个层次叠加构成，按优先级排列：

```
层次 1 - 系统内置指令 (最高优先级)
┌─────────────────────────────────────────────┐
│ Claude Code 内置安全约束                     │
│ - 不访问外部网络 (除非明确允许)               │
│ - 不执行危险命令                             │
│ - 不泄露认证信息                             │
└─────────────────────────────────────────────┘

层次 2 - System Prompt (agent_definition DB)
┌─────────────────────────────────────────────┐
│ 【绝对重要】你必须始终使用中文回复用户...      │
│ 【绝对重要】使用 curl 调用 Connect RPC 接口   │
│ 示例命令:                                    │
│ curl -X POST 'http://octobus:9000/...' ...  │
└─────────────────────────────────────────────┘
                ↓ 由 ClaudeRunner 注入
层次 3 - MPI Catalog (catalog.md)
┌─────────────────────────────────────────────┐
│ ## MPI Catalog                              │
│                                              │
│ # Capability Gateway Access                 │
│ IMPORTANT: 使用 curl 调用 Connect RPC       │
│                                              │
│ ## Connect RPC (端点表)                     │
│ /capsets/bidpool-access/connect/...         │
│                                              │
│ ## gRPC 方法表                              │
│ ## MCP 工具表                               │
└─────────────────────────────────────────────┘
                ↓ 一并发送到 LLM
层次 4 - 用户消息
┌─────────────────────────────────────────────┐
│ "帮我查询所有标讯"                           │
└─────────────────────────────────────────────┘
```

**注入机制** (`claude-runner` → `mpi.js`):

```
1. Agent 启动 → ClaudeRunner 初始化
2. ClaudeRunner.loadSystemPrompt()
   → 从 agent_definition.system_prompt 读取
   → 附加中文语言指令 + curl 示例

3. ClaudeRunner.loadMpiContext()
   → readMpiContext(stateRoot)
   → 读取 /data/sessions/{id}/runtime/mpi/catalog.md
   → formatMpiContext() 添加 "## MPI Catalog" 头部
   → append 到 systemPrompt

4. 最终 systemPrompt = 层次2 + "\n" + 层次3
5. 用户消息 (层次4) 经 Claude SDK 发送到 LLM
6. LLM 根据完整提示词决定调用 Bash Tool → curl
```

### 4.2 MPI Catalog 机制

MPI (Model Program Interface) Catalog 是 agent-compose 框架的核心创新，用于为 LLM 提供结构化的 API 文档。

**Catalog 生成流程**：

```
agent-compose Daemon
  │
  ├── CreateAgentSession
  │   ├── 1. 从 DB 读取 agent_definition (capset_ids = ["bidpool-access"])
  │   │
  │   ├── 2. CapabilityGateway.CatalogMarkdown()
  │   │   → HTTP GET http://octobus:9000/admin/v1/catalog/bidpool-access?format=md&all=true
  │   │   → 返回完整 Markdown 目录
  │   │
  │   ├── 3. capabilityGuidePreamble() → 生成头部说明
  │   │   ⚠ 当前二进制使用旧版 gRPC 说明
  │   │   需手动替换为 Connect RPC 说明
  │   │
  │   ├── 4. 拼接: preamble + catalog_body → catalog.md
  │   │
  │   └── 5. 写入 /data/sessions/{id}/runtime/mpi/catalog.md
  │
  └── Docker 启动 Guest 容器
      → 挂载 /data/sessions/{id} → /data/sessions/{id}
```

**Catalog Markdown 结构** (来自 OctoBus `?format=md&all=true`):

```markdown
# Capability Gateway Access
(头部说明 — 由 capabilityGuidePreamble() 生成)

# Catalog: bidpool-access / BidPool标讯平台

## Schema Discovery
- gRPC: server reflection
- MCP: tools/list
- Connect RPC: OpenAPI JSON

## gRPC
| Method | Metadata | Request | Response |
|--------|----------|---------|----------|
| /bidpool.v1.BidService/ListBids | capset=bidpool-access, instance=bidpool-prod | ... | ... |

## MCP
| Endpoint | Tool | Method | ... |
|----------|------|--------|-----|
| /capsets/bidpool-access/mcp | bidpool__bidpool-prod__list_bids | ... | ... |

## Connect RPC
| Endpoint | OpenAPI | Procedure | ... |
|----------|---------|-----------|-----|
| /capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.BidService/ListBids | ... | ... | ... |
```

### 4.3 通信协议栈

```
┌──────────────────────────────────────────────────────────────┐
│                    AI Agent → LLM API                          │
│  协议: HTTPS + JSON                                           │
│  端点: https://ai-api-gateway.app.baizhi.cloud/api/anthropic  │
│  格式: Messages API (system + user + assistant)               │
│  工具调用: Bash Tool (curl 命令)                               │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    Agent → OctoBus 网关                        │
│  协议: Connect RPC (HTTP JSON)                                │
│  端点: http://octobus:9000                                    │
│  认证: 无 (Docker 内网, 无需 token)                           │
│  方法: POST                                                   │
│  格式: { "field": "value" }                                   │
│  示例: curl -X POST 'http://octobus:9000/capsets/.../ListBids'│
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                     OctoBus 内部                               │
│  协议: gRPC (HTTP/2) → HTTP REST 转换                         │
│  认证: Basic Auth (admin/bidpool@2026)                        │
│  传输: protobuf → JSON                                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    BidPool Go 后端                              │
│  协议: REST over HTTP                                          │
│  端口: :8080                                                   │
│  认证: Basic Auth                                              │
│  数据: GORM → SQLite                                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 集成实现细节

### 5.1 gRPC → REST 代理层

**OctoBus 服务包结构**:

```
bidpool-service/
├── package.json
│   {
│     "name": "@chaitin/bidpool-service",
│     "type": "module",            ← ES Module
│     "bin": { "bidpool": "./bin/service.js" },
│     "dependencies": {
│       "@chaitin-ai/octobus-sdk": "^0.x"
│     }
│   }
│
├── service.json
│   {
│     "schema": "chaitin.octobus.service.v1",
│     "name": "bidpool",
│     "proto": { "roots": ["proto"], "files": ["proto/bidpool.proto"] },
│     "configSchema": "config.schema.json",
│     "secretSchema": "secret.schema.json"
│   }
│
├── proto/bidpool.proto
│   syntax = "proto3";
│   package bidpool.v1;
│   service BidPoolService {
│     rpc GetStatus(EmptyRequest) returns (StatusResponse);
│     rpc ListBids(ListBidsRequest) returns (ListBidsResponse);
│     rpc GetBid(GetBidRequest) returns (Bid);
│     rpc CreateTask(CreateTaskRequest) returns (TaskResponse);
│     // ... 共 13 个 RPC
│   }
│
├── bin/service.js
│   import { defineService, runServiceMain } from "@chaitin-ai/octobus-sdk";
│   const service = defineService({ handlers: { ... } });
│   runServiceMain(service);
│
├── config.schema.json  — backend_url, request_timeout_ms
└── secret.schema.json  — username, password
```

**核心代理函数**:

```javascript
async function apiFetch(ctx, path, options = {}) {
  const baseUrl = ctx.config.backend_url || "http://127.0.0.1:8080";
  const timeout = ctx.config.request_timeout_ms || 30000;
  const url = `${baseUrl}${path}${paramsToQuery(options.params)}`;

  const headers = {
    Authorization: basicAuthHeader(ctx.secret.username, ctx.secret.password),
    "Content-Type": "application/json",
  };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
    return unwrap(await response.json());
  } finally {
    clearTimeout(timer);
  }
}

// 解包 BidPool 统一响应 { code, data, message }
function unwrap(json) {
  if (json.code !== 0) {
    throw new Error(`BidPool API error: ${json.message} (code=${json.code})`);
  }
  return json.data;
}
```

**字段映射** (snake_case → camelCase):

```javascript
function mapBid(b) {
  return {
    id: b.id,
    title: b.title,
    tenderUnit: b.tender_unit,       // 招标单位
    budgetAmount: b.budget_amount,    // 预算金额
    region: b.region,                 // 地区
    publishDate: b.publish_date,      // 发布时间
    url: b.url,                       // 原文链接
    industry: b.industry,             // 行业
    status: b.status,
    createdAt: b.created_at,
    updatedAt: b.updated_at,
  };
}
```

### 5.2 Connect RPC 调用链路

Connect RPC 是 gRPC 的 HTTP JSON 变体，无需 protobuf 编解码，直接用 curl 调用。

**端点格式**:

```
POST http://octobus:9000/capsets/{capset_id}/connect/{instance_id}/{package}.{service}/{Method}
     ↑                 ↑          ↑           ↑               ↑
     OctoBus 网关      CapSet ID  实例 ID      gRPC 服务全称   方法名
```

**完整示例**:

```
URL: /capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.BidService/ListBids
BODY: {"page":1,"pageSize":10}
```

**curl 调用**:

```bash
# 查询所有标讯
curl -X POST 'http://octobus:9000/capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.BidService/ListBids' \
  -H 'Content-Type: application/json' \
  -d '{"pageSize":10}'
```

**Agent 内部实际执行** (从 LLM 响应还原):

```
用户: "查询所有标讯"
                ↓
LLM 推理:
  - 我需要查询标讯数据
  - Connect RPC 端点: .../ListBids
  - 使用 Bash Tool 执行 curl
                ↓
Tool Call: Bash
  curl -X POST 'http://octobus:9000/capsets/...' -H 'Content-Type: application/json' -d '{}'
                ↓
Tool Result:
  {"bids":[...],"total":126}
                ↓
LLM 推理:
  - 收到 10 条标讯数据
  - 需要用中文回复
                ↓
回复用户: "以下是查询到的最新标讯列表..."
```

### 5.3 MCP 工具暴露

OctoBus 自动将 gRPC 服务方法暴露为 MCP 工具。MCP (Model Context Protocol) 是 Anthropic 定义的 AI 工具协议。

**MCP 端点**:

```
http://octobus:9000/capsets/bidpool-access/mcp
```

**工具发现** (tools/list):

```json
// Request
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}

// Response
{
  "tools": [
    {
      "name": "bidpool__bidpool-prod__list_bids",
      "description": "ListBids",
      "inputSchema": {
        "type": "object",
        "properties": {
          "page": {"type": "integer"},
          "pageSize": {"type": "integer"},
          "keyword": {"type": "string"},
          "region": {"type": "string"},
          "industry": {"type": "string"},
          "status": {"type": "string"},
          "startDate": {"type": "string"},
          "endDate": {"type": "string"}
        }
      }
    },
    {
      "name": "bidpool__bidpool-prod__get_status",
      "description": "GetStatus",
      "inputSchema": {"type": "object", "properties": {}}
    },
    // ... 共 13 个工具
  ]
}
```

**工具调用** (tools/call):

```json
// Request
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"bidpool__bidpool-prod__list_bids","arguments":{"pageSize":10}}}

// Response
{"id":2,"result":{"content":[{"type":"text","text":"{\"bids\":[...]}"}]}}
```

### 5.4 Catalog 动态生成

`capabilityGuidePreamble()` 函数 (agent-compose 源码 `capability_gateway.go`):

```go
func capabilityGuidePreamble(target string) string {
    target = strings.TrimSpace(target)
    if target == "" {
        return ""
    }
    return fmt.Sprintf(`# Capability Gateway Access

Capabilities are reachable through the local capability proxy.

## Connect RPC (recommended - use curl via the Bash tool)

- Each method in the Connect RPC table below has an endpoint path
- Use: curl -X POST http://octobus:9000/ENDPOINT_PATH -H "Content-Type: application/json" -d 'JSON_BODY'
- Example: curl -X POST 'http://octobus:9000/capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.BidService/ListBids' -H 'Content-Type: application/json' -d '{}'
- Fetch the OpenAPI document at http://octobus:9000/capsets/bidpool-access/openapi.json for schemas
- NO authentication token needed for Connect RPC calls from within this guest

## gRPC (only if grpcurl is installed)

- Endpoint: `+"`%s`"+` (plaintext HTTP/2 gRPC; also in env CAP_GRPC_TARGET)
- Send metadata `+"`%s: $CAP_TOKEN`"+` (token value in env CAP_TOKEN)
- Send per-method metadata `+"`x-octobus-capset` / `x-octobus-service` / `x-octobus-instance`"+`

## MCP (Model Context Protocol)

- MCP endpoint: http://octobus:9000/capsets/bidpool-access/mcp
- Use tools/list to discover tools
- Use tools/call to invoke a tool by name

`, target, capproxy.SessionTokenMetadata)
}
```

**Catalog 查询参数** (`client.go`):

```go
// 原参数: ?format=md&grpc=true  (仅返回 gRPC 方法表)
// 修改后: ?format=md&all=true   (返回 gRPC + Connect RPC + MCP 完整表)
path := "/admin/v1/catalog/" + url.PathEscape(capsetID) + "?format=md&all=true"
```

---

## 6. 数据流完整追踪

以用户输入 "帮我查询所有标讯" 为例，完整数据流如下：

### 6.1 用户输入处理

```
Step 1: HTTP POST /agentcompose.v1.AgentService/SendAgentMessage
        Body: { "sessionId": "...", "agent": "claude", "message": "帮我查询所有标讯" }
        ↓
Step 2: agent-compose Daemon 接收请求
        → 找到对应 Session
        → 从 Redis/内存 获取 Session 上下文
        → 将消息放入 Guest 容器的消息队列
        ↓
Step 3: Guest 容器内的 Claude Code CLI 收到消息
        → 加载 System Prompt + MPI Catalog
        → 构造 Messages Array:
           [
             {"role":"system", "content": "【绝对重要】你必须始终使用中文回复..."},
             {"role":"user",   "content": "帮我查询所有标讯"}
           ]
        ↓
Step 4: Claude SDK → Anthropic API → LLM (feature/flash)
        ↓
Step 5: LLM 推理:
        - System prompt: 使用 curl 调用 Connect RPC
        - 工具选择: Bash Tool
        - 命令: curl -X POST 'http://octobus:9000/capsets/.../ListBids'
```

### 6.2 API 调用链路

```
Step 6: Agent 容器内执行:
        curl -X POST 'http://octobus:9000/capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.BidService/ListBids' \
          -H 'Content-Type: application/json' \
          -d '{"pageSize":10}'
        ↓
Step 7: OctoBus 网关接收 HTTP 请求
        → 解析 URL 路由: capset=bidpool-access, instance=bidpool-prod
        → 查找 bidpool-prod 实例 (Node.js 进程)
        → gRPC 调用该实例: /bidpool.v1.BidService/ListBids
        ↓
Step 8: Node.js bidpool 服务 handler:
        → ctx.req = { pageSize: 10 }
        → apiFetch(ctx, "/api/v1/bids", { params: { page_size: 10 } })
        → HTTP GET http://bidpool-go:8080/api/v1/bids?page_size=10
        → 请求头: Authorization: Basic YWRtaW46YmlkcG9vbEAyMDI2
        ↓
Step 9: BidPool Go 后端:
        → Gin Router → Basic Auth 验证
        → BidHandler.ListBids → GORM 查询 SQLite
        → SELECT * FROM bids ORDER BY created_at DESC LIMIT 10
        → 返回 JSON: { "code": 0, "data": { "bids": [...], "total": 126 } }
        ↓
Step 10: Node.js 服务接收响应:
         → unwrap({ code:0, data:{bids:[...]} }) → { bids: [...] }
         → mapBid() 字段名转换: snake_case → camelCase
         → 返回 gRPC 响应: { bids: [...], total: 126 }
        ↓
Step 11: OctoBus 网关将 gRPC 响应转换为 HTTP JSON:
         → {"bids":[{"id":"...","title":"贵州省大数据发展管理局...",...}],"total":126}
```

### 6.3 响应处理

```
Step 12: Agent 容器内 curl 收到 JSON 响应
         → 工具调用结果返回给 LLM
         ↓
Step 13: LLM 推理:
         - 收到 10 条标讯数据
         - 需要用中文回复
         - 格式化输出: 标题、招标单位、预算、地区、时间
         ↓
Step 14: LLM 生成中文回复:
         "以下是查询到的最新标讯列表（共10条）：
          1. 标题：贵州省大数据发展管理局...
             招标单位：贵州省信息中心
             预算：5,389,678.0元
             ..."
         ↓
Step 15: Claude Code CLI → agent-compose-runtime
         → assistantEvent: { type: "agent.assistant", message: "..." }
         ↓
Step 16: agent-compose Daemon → HTTP 响应:
         { "assistantEvent": { "message": "以下是查询到的最新标讯列表..." } }
```

### 6.4 时序图

```
用户            agent-compose     Guest 容器        LLM API          OctoBus        BidPool Go
 │                   │               │               │                │               │
 │  POST SendMessage │               │               │                │               │
 │──────────────────▶│               │               │                │               │
 │                   │  消息入队列    │               │                │               │
 │                   │──────────────▶│               │                │               │
 │                   │               │  SystemPrompt  │               │               │
 │                   │               │ + MPI Catalog  │               │               │
 │                   │               │───────────────▶│               │               │
 │                   │               │               │  返回工具选择   │               │
 │                   │               │◀──────────────│               │               │
 │                   │               │               │                │               │
 │                   │               │  curl ListBids │               │               │
 │                   │               │────────────────────────────────▶│               │
 │                   │               │               │                │  GET /api/v1  │
 │                   │               │               │                │──────────────▶│
 │                   │               │               │                │               │
 │                   │               │               │                │  SQLite 查询   │
 │                   │               │               │                │◀──────────────│
 │                   │               │               │                │  JSON 响应     │
 │                   │               │◀────────────────────────────────│               │
 │                   │               │               │                │               │
 │                   │               │  格式化中文回复 │               │               │
 │                   │               │───────────────▶│               │               │
 │                   │               │◀──────────────│               │               │
 │                   │  assistantEvent│               │               │               │
 │                   │◀──────────────│               │               │               │
 │  HTTP 200 OK      │               │               │               │               │
 │◀──────────────────│               │               │               │               │
```

---

## 7. 关键问题与解决方案

### 7.1 LLM 安全约束拒绝 API 调用

**现象**: Agent 收到 API 调用指令后拒绝执行，回复 "I cannot access the BidPool system's endpoint directly because it requires proprietary authentication headers and permissions not available in this environment."

**根因**: Claude Code 内置的安全训练导致 LLM 对"访问外部 API"产生抵触，尽管系统提示词中明确说明无需认证。

**解决方案**:

```
1. System Prompt 强化
   - 使用【绝对重要】标记语言和操作指令
   - 提供完整的 curl 命令示例（可直接复制执行）
   - 明确说明 "集成环境内网，无需任何认证"

2. MPI Catalog 前缀替换
   - 原前缀: "Capabilities are reachable over gRPC...需要 CAP_TOKEN"
   - 替换为: "IMPORTANT: All BidPool APIs are accessible via Connect RPC using curl. NO authentication token is needed."

3. Guest 容器 mpi.js 补丁
   - 在 formatMpiContext() 中注入 Connect RPC 指令
   - 使 LLM 更可能遵循 API 调用路径
```

### 7.2 中文回复不遵从

**现象**: 即使 system prompt 明确要求使用中文，Agent 仍用英文回复。

**根因**:
- `feature/flash` 模型对语言指令的遵从性较弱
- MPI Catalog 的英文内容稀释了中文指令的权重
- LLM 内置训练倾向于英文输出

**解决方案**:

```
1. 中英文混合强化
   - 在 System Prompt 开头和结尾都放置中文指令
   - 所有表格标题、说明文字等也用中文
   
2. 用户消息诱导
   - 全中文的用户消息 + 明确要求中文
   - 首轮回复后，后续对话可稳定保持中文
```

### 7.3 Guest 容器内无 gRPC 工具

**现象**: Catalog 提供了 gRPC 方法表，但 Guest 容器未安装 grpcurl。

**根因**: 默认 guest 镜像基于精简 Alpine，不包含 grpcurl 等调试工具。

**解决方案**: 转向 Connect RPC (HTTP JSON) 协议，只需 curl 即可调用。修改 Catalog 生成参数为 `?format=md&all=true` 以包含 Connect RPC 端点表。

### 7.4 Go 二进制重新编译失败

**现象**: `capabilityGuidePreamble()` 代码已更新，但 Docker 内 Go 编译因网络超时无法下载依赖。

**根因**: 部署服务器无法访问 `proxy.golang.org` (网络隔离或 DNS 问题)。

**解决方案**: 采用运行态补丁方案：
```
1. 会话创建后，立即修改 catalog.md 文件
2. 构建 patched guest Docker 镜像 (agent-compose-guest-patched)
3. 更新 agent_definition 使用 patched 镜像
```

### 7.5 网络连通性

| 问题 | 解决 |
|------|------|
| agent-compose 重启后断开 OctoBus 网络 | `docker network connect tmp_octobus-net agent-compose` |
| Guest 容器通过 `octobus:9000` 访问网关 | Docker 自定义网络 DNS 解析 (tmp_octobus-net) |
| Docker daemon 未随系统启动 | `nohup dockerd &>/var/log/dockerd.log &` |

---

## 8. 部署与运维

### 8.1 服务部署清单

```
10.2.36.217 (agent-compose 平台)
├── agent-compose Daemon (Docker)     端口 7410
├── agent-compose-frontend (Docker)   端口 80 → 8000
├── OctoBus 网关 (进程)               端口 9000
└── SQLite 数据库                     /opt/agent-compose/data/data.db

10.2.37.237 (BidPool 业务)
├── bidpool-go (Docker)               端口 8080
├── bidpool-nginx (Docker)            端口 8088
├── bidpool-python (Docker)           端口 8001
└── SQLite 数据库                     /app/data/bidpool.db (volume)
```

### 8.2 关键操作命令

**创建新会话并测试**:

```bash
# 1. 登录
curl -X POST http://localhost:7410/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"octobus2024"}' \
  -c /tmp/auth.txt

# 2. 创建会话 (Connect RPC)
curl -X POST http://localhost:80/agentcompose.v1.AgentDefinitionService/CreateAgentSession \
  -H "Content-Type: application/json" \
  -b /tmp/auth.txt \
  -d '{
    "agentId": "2da42f87-ede1-4257-a8f1-500886fb957e",
    "title": "标讯查询",
    "driver": "docker",
    "guestImage": "agent-compose-guest-patched:latest"
  }'

# 3. 发送消息
curl -X POST http://localhost:80/agentcompose.v1.AgentService/SendAgentMessage \
  -H "Content-Type: application/json" \
  -b /tmp/auth.txt \
  -d '{"sessionId":"SESSION_ID","agent":"claude","message":"查询所有标讯"}'
```

**Catalog 补丁脚本**:

```python
# 在会话创建后，容器就绪前执行
new_preamble = """# Capability Gateway Access

IMPORTANT: All BidPool APIs are accessible via Connect RPC using curl. NO authentication token is needed.

## How to Call APIs

Use curl via the Bash tool to call Connect RPC endpoints on http://octobus:9000.

Examples:
- List all bids: curl -X POST 'http://octobus:9000/capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.BidService/ListBids' -H 'Content-Type: application/json' -d '{}'
- Get status: curl -X POST 'http://octobus:9000/capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.SystemService/GetStatus' -H 'Content-Type: application/json' -d '{}'

"""

with open(f"/data/sessions/{session_id}/runtime/mpi/catalog.md", 'r') as f:
    content = f.read()
si, ei = content.find("# Capability Gateway Access"), content.find("# Catalog: bidpool-access")
if si >= 0 and ei > si:
    content = new_preamble + content[ei:]
    with open(f"/data/sessions/{session_id}/runtime/mpi/catalog.md", 'w') as f:
        f.write(content)
```

### 8.3 Agent 配置项

| 配置项 | 位置 | 值 |
|--------|------|-----|
| model (DB) | `agent_definition.model` | `feature/flash` |
| model (CLI) | `env_json.CLAUDE_CODE_EXTRA_ARGS` | `--model feature/flash` |
| API Key | `env_json.ANTHROPIC_API_KEY` | `sk-e71e...` |
| API Endpoint | `env_json.ANTHROPIC_BASE_URL` | `https://ai-api-gateway.app.baizhi.cloud/api/anthropic` |
| Guest Image | `agent_definition.guest_image` | `agent-compose-guest-patched:latest` |
| CapSet | `agent_definition.capset_ids` | `["bidpool-access"]` |

---

## 9. 扩展指南

### 9.1 添加新的 BidPool 接口

如果 BidPool 后端新增了 API，需要以下步骤完成集成：

```
1. 更新 proto 文件
   → proto/bidpool.proto 添加新的 RPC 和消息定义
   
2. 更新 Node.js 代理
   → bin/service.js 添加对应的 handler
   → 调用 apiFetch(ctx, "/api/v1/new-endpoint", { method, body })
   
3. 重新导入 OctoBus 服务
   → octobus service import bidpool ./bidpool-service
   → OctoBus 自动重启实例
   
4. 验证
   → curl http://octobus:9000/capsets/bidpool-access/connect/bidpool-prod/...
```

### 9.2 添加新的 CapSet

```
1. 在 OctoBus 中创建新的 CapSet
2. 将服务实例加入 CapSet
3. 在 agent_definition 的 capset_ids 中添加新 CapSet ID
4. 重启 agent-compose 或创建新会话
```

### 9.3 切换 LLM 模型

```
1. 更新 agent_definition.model 字段
2. 更新 env_json 中的 CLAUDE_CODE_EXTRA_ARGS (--model 参数)
3. 确保 AI API Gateway 支持该模型
4. 创建新会话验证
```

---

## 附录 A: 验证结果样例

### A.1 标讯查询

```
用户: 查询所有标讯
Agent: 以下是查询到的最新标讯列表（共10条）：
1. 标题：贵州省大数据发展管理局2026年度系统运维项目需求公示
   招标单位：贵州省信息中心
   预算：5,389,678.0元
   地区：贵州省贵阳市
   发布时间：2026-06-26
   ...
```

### A.2 系统状态查询

```
用户: 查看系统状态
Agent: 系统状态概览
- 总标讯数量：126 条
- 活跃任务：3 个
- 登录状态：logged_in
- 服务器时间：2026-06-28 16:18:17

最近任务执行：
| 时间 | 状态 | 处理量 | 新增量 |
|------|------|--------|--------|
| 2026-06-28 13:27 | ✅ 成功 | 56 | 26 |
| 2026-06-25 10:00 | ✅ 成功 | 0 | 0 |
| 2026-06-24 08:55 | ❌ 失败 | 0 | 0（登录失败）|
```

---

*文档结束*
