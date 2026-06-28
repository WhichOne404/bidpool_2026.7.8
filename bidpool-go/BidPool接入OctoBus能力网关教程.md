# BidPool 接入 OctoBus 能力网关 — 从零开始教程

> 面向小白，手把手教学。如果你完全不懂 gRPC 和 OctoBus，按这个文档一步步操作就能搞定。

---

## 目录

1. [先搞懂这几个概念](#1-先搞懂这几个概念)
2. [整体架构长什么样](#2-整体架构长什么样)
3. [把 REST API 变成 OctoBus 服务（核心步骤）](#3-把-rest-api-变成-octobus-服务核心步骤)
4. [接入 agent-compose](#4-接入-agent-compose)
5. [以后加新服务怎么做](#5-以后加新服务怎么做)
6. [常见问题](#6-常见问题)

---

## 1. 先搞懂这几个概念

### BidPool 标讯平台
就是你写的那个后端服务，跑在 `http://10.2.37.237:8088`，提供 REST API（比如 `/api/v1/bids`、`/api/v1/tasks`）。用户通过浏览器访问前端页面来使用。

### OctoBus 能力接入网关
跑在 `http://10.2.36.217:9000` 的一个"翻译官"。它的作用是把各种后端服务（比如你的 BidPool）统一成 **gRPC 接口**，让 AI Agent 可以统一调用。

打个比方：
- **BidPool** 是说中文的（REST API）
- **AI Agent** 只听得懂英文（gRPC）
- **OctoBus** 就是同声传译

### agent-compose
跑在 `http://10.2.36.217`（端口 80）的 AI Agent 编排平台。它可以连接 OctoBus，发现里面有哪些能力，然后让 AI Agent 调用这些能力。

### Capset（能力集）
就是把一组功能打包在一起。比如 BidPool 有"标讯管理"、"任务管理"、"智能对话"等功能，打包成一个 capset 叫 `bidpool-access`。

### 三者的关系

```
你的浏览器
    │
    ▼
agent-compose (http://10.2.36.217)  ← 前端页面，编排 AI Agent
    │  通过能力接入网关配置连接 OctoBus
    ▼
OctoBus (http://10.2.36.217:9000)   ← 能力网关，统一接口
    │  通过 Node.js handler 调用 REST API
    ▼
BidPool (http://10.2.37.237:8088)   ← 你的后端服务
```

---

## 2. 整体架构长什么样

部署结构如下（三台机器/服务）：

```
┌─────────────────────────────────────────────────────────────┐
│                     服务器 10.2.36.217                       │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │  agent-compose    │    │  agent-compose-  │              │
│  │  后端 (端口7410)   │◄──►│  frontend        │              │
│  │                   │    │  nginx (端口80)   │              │
│  └──────┬───────────┘    └──────────────────┘              │
│         │                                                   │
│         │ 同一 docker 网络                                   │
│         │                                                   │
│  ┌──────▼───────────┐                                       │
│  │  OctoBus          │                                       │
│  │  (端口 9000)       │                                       │
│  │                   │                                       │
│  │  ┌─────────────┐  │                                       │
│  │  │ Node.js 子进程│  │  ← bidpool 服务的 handler 在这里运行  │
│  │  │ (bidpool)    │  │                                       │
│  │  └──────┬──────┘  │                                       │
│  └─────────┼─────────┘                                       │
└────────────┼─────────────────────────────────────────────────┘
             │ HTTP 请求（带 Basic Auth 认证）
             ▼
  BidPool 后端 (http://10.2.37.237:8088)
```

**关键点：**
- agent-compose 和 OctoBus 在同一个 Docker 网络，通过**容器名**通信
- OctoBus 用 `http://octobus:9000` 就能找到
- BidPool 在另一台机器，OctoBus 通过 `http://10.2.37.237:8088` 访问

---

## 3. 把 REST API 变成 OctoBus 服务（核心步骤）

### 3.1 理解 REST → gRPC 的转换逻辑

**REST API 示例：**
```
GET /api/v1/bids?page=1&page_size=10
→ 返回: { "code": 0, "data": [...], "total": 90 }
```

**对应的 gRPC 定义：**
```protobuf
service BidService {
  rpc ListBids(ListBidsRequest) returns (ListBidsResponse);
}

message ListBidsRequest {
  int32 page = 1;      // ← 对应 URL 参数 page
  int32 page_size = 2; // ← 对应 URL 参数 page_size
}

message ListBidsResponse {
  int32 code = 1;
  string message = 2;
  string data_json = 3;  // ← REST 的 data 数组，原样塞进 JSON 字符串
  int32 total = 4;       // ← 对应 REST 的 total 字段
}
```

**转换流程：**
```
客户端请求 → gRPC 请求 → Node.js handler → HTTP 请求 → BidPool REST API
                                                              │
客户端响应 ← gRPC 响应 ← Node.js handler ← HTTP 响应 ←────────┘
```

### 3.2 一个完整的 OctoBus 服务包长什么样

每个服务需要以下文件：

```
bidpool-service/                  # 服务包根目录
├── service.json                  # 告诉 OctoBus 这个服务的信息
├── package.json                  # Node.js 包信息
├── secret.schema.json            # 密钥配置（存登录密码等敏感信息）
├── proto/
│   └── bidpool.proto             # gRPC 接口定义（最重要）
└── bin/
    └── bidpool.js                # 实现代码（写转换逻辑）
```

### 3.3 第一步：写 Proto 文件（定义接口契约）

**文件: `proto/bidpool.proto`**

```protobuf
syntax = "proto3";           // 使用 proto3 语法
package bidpool.v1;          // 包名，类似 Java 的 package

// ========== 任务管理 ==========
service TaskService {        // 定义一个服务
  rpc CreateTask(CreateTaskRequest) returns (ApiResponse);
  rpc ListTasks(ListTasksRequest) returns (ListTasksResponse);
  rpc GetTask(GetTaskRequest) returns (ApiResponse);
  rpc UpdateTask(UpdateTaskRequest) returns (ApiResponse);
  rpc DeleteTask(DeleteTaskRequest) returns (ApiResponse);
  rpc RunTask(RunTaskRequest) returns (ApiResponse);
  rpc BatchDeleteTasks(BatchDeleteTasksRequest) returns (ApiResponse);
}

// ========== 标讯管理 ==========
service BidService {
  rpc ListBids(ListBidsRequest) returns (ListBidsResponse);
  rpc GetBid(GetBidRequest) returns (ApiResponse);
  rpc DeleteBid(DeleteBidRequest) returns (ApiResponse);
  rpc BatchDeleteBids(BatchDeleteBidsRequest) returns (ApiResponse);
  rpc DispatchBids(DispatchBidsRequest) returns (ApiResponse);  // 发送到钉钉
}

// ========== 智能对话 ==========
service ChatService {
  rpc Chat(ChatRequest) returns (ChatResponse);
}

// ========== 系统管理 ==========
service SystemService {
  rpc GetStatus(EmptyRequest) returns (ApiResponse);
  rpc GetConfig(EmptyRequest) returns (ApiResponse);
  rpc SaveConfig(SaveConfigRequest) returns (ApiResponse);
}

// ===== 下面是各种数据结构的定义 =====

message CreateTaskRequest {
  string name = 1;          // 每个字段有类型、名称、编号
  string task_type = 2;     // 任务类型：crawl(收集)/send(发送)
  string cron_expr = 3;     // 定时表达式（可选）
  bool enabled = 4;         // 是否启用
}

message ListTasksRequest {
  int32 page = 1;
  int32 page_size = 2;
}

message GetTaskRequest      { string id = 1; }
message DeleteTaskRequest   { string id = 1; }
message RunTaskRequest      { string id = 1; }

message BatchDeleteTasksRequest { repeated string ids = 1; }  // repeated = 数组

// ... 其他请求消息类似 ...

// ========== 统一的响应格式 ==========
message ApiResponse {
  int32 code = 1;
  string message = 2;
  string data_json = 3;     // REST 返回的 data 字段，转为 JSON 字符串存这里
}

message ListTasksResponse {
  int32 code = 1;
  string message = 2;
  string data_json = 3;
  int32 total = 4;
}
```

**编写规则（小白版）：**
1. 每个 REST 接口对应 proto 里的一行 `rpc`
2. REST 的请求参数（URL 参数或 body）写成 `message`，字段对应
3. REST 的响应体字段也写成 `message`
4. 字段编号从 1 开始连续编号
5. `repeated` 表示数组，`string` 表示字符串，`int32` 表示整数，`bool` 表示布尔值

### 3.4 第二步：写 Service 描述文件

**文件: `service.json`**

```json
{
  "schema": "chaitin.octobus.service.v1",
  "name": "bidpool",
  "displayName": "BidPool 标讯智能平台",
  "description": "BidPool bidding intelligence platform",
  "proto": {
    "roots": ["proto"],
    "files": ["proto/bidpool.proto"]
  },
  "secretSchema": "secret.schema.json"
}
```

字段说明：
- `name`：服务 ID，唯一标识，以后导入/调用都用这个
- `displayName`：显示名称，在 agent-compose 界面上看到的名字
- `proto.roots`：proto 文件根目录
- `proto.files`：proto 文件路径
- `secretSchema`：密钥配置文件的路径（存密码等敏感信息）

### 3.5 第三步：写 Node.js Handler（核心转换逻辑）

**文件: `bin/bidpool.js`**

这是整个接入最关键的部分——把 gRPC 请求转成 REST 调用。

```javascript
#!/usr/bin/env node

// 导入 OctoBus SDK
import { defineService, runServiceMain } from "@chaitin-ai/octobus-sdk";

// BidPool 后端 REST API 的地址
// 如果 BidPool 和 OctoBus 在同一台机器，可以写内网地址
const BIDPOOL_BASE = process.env.BIDPOOL_BASE_URL || "http://10.2.37.237:8088";

// ===== 工具函数 =====

// 生成 Basic Auth 认证头
function basicAuthHeader(username, password) {
  return "Basic " + Buffer.from(`${username}:${password}`).toString("base64");
}

// 通用 HTTP 请求函数
// 作用：用 HTTP 调用 BidPool 的 REST API，拿到 JSON 结果
async function apiCall(method, path, body, authHeader) {
  const url = `${BIDPOOL_BASE}${path}`;           // 拼出完整 URL
  const headers = { "Content-Type": "application/json" };
  if (authHeader) headers["Authorization"] = authHeader;  // 加认证头
  
  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);   // 如果有 body，转 JSON
  
  const res = await fetch(url, options);
  return res.json();                                // 返回解析后的 JSON
}

// 从实例配置中读取用户名密码
// ctx.secret 存的是创建实例时传入的 --secret-json
function authFrom(ctx) {
  const u = ctx.secret?.username || "admin";
  const p = ctx.secret?.password || "bidpool@2026";
  return basicAuthHeader(u, p);
}

// ===== 以下是各种 handler 生成函数 =====

// 简单 GET 请求（不需要参数）
function req(method, path) {
  return async (ctx) => {
    const data = await apiCall(method, path, null, authFrom(ctx));
    return {
      code: data.code ?? 0,
      message: data.message ?? "",
      data_json: JSON.stringify(data.data ?? {}),
    };
  };
}

// 带 body 的 POST/PUT 请求
function reqWithBody(method, path, bodyFn) {
  return async (ctx) => {
    const body = bodyFn(ctx);           // bodyFn 从 ctx.request 提取参数
    const data = await apiCall(method, path, body, authFrom(ctx));
    return {
      code: data.code ?? 0,
      message: data.message ?? "",
      data_json: JSON.stringify(data.data ?? {}),
    };
  };
}

// 带 ID 的请求（如 GET /api/v1/tasks/123）
function reqWithId(method, pathPrefix) {
  return async (ctx) => {
    const path = `${pathPrefix}/${ctx.request.id}`;   // 把 ID 拼进 URL
    const data = await apiCall(method, path, null, authFrom(ctx));
    return { /* 同上 */ };
  };
}

// ===== 核心：注册所有 handler =====

const service = defineService({
  handlers: {
    // ===== 任务管理 =====
    // 方法名格式: "包名.服务名/方法名"
    // ctx.request 就是 proto 定义的那个请求消息
    "bidpool.v1.TaskService/CreateTask": reqWithBody("POST", "/api/v1/tasks", (ctx) => ({
      name: ctx.request.name,
      task_type: ctx.request.task_type,
      cron_expr: ctx.request.cron_expr || "",
      enabled: ctx.request.enabled || false,
    })),

    "bidpool.v1.TaskService/ListTasks": async (ctx) => {
      // 处理带查询参数的 GET 请求
      const params = new URLSearchParams();
      if (ctx.request.page) params.set("page", ctx.request.page);
      if (ctx.request.page_size) params.set("page_size", ctx.request.page_size);
      const qs = params.toString();
      const data = await apiCall("GET", `/api/v1/tasks?${qs}`, null, authFrom(ctx));
      return {
        code: data.code ?? 0,
        message: data.message ?? "",
        data_json: JSON.stringify(data.data ?? []),
        total: data.total ?? 0,
      };
    },

    "bidpool.v1.TaskService/GetTask": reqWithId("GET", "/api/v1/tasks"),
    "bidpool.v1.TaskService/UpdateTask": reqWithIdBody("PUT", "/api/v1/tasks", (ctx) => ({
      enabled: ctx.request.enabled,
      cron_expr: ctx.request.cron_expr || "",
    })),
    "bidpool.v1.TaskService/DeleteTask": reqWithId("DELETE", "/api/v1/tasks"),
    "bidpool.v1.TaskService/RunTask": reqWithId("POST", "/api/v1/tasks"), // 实际路径是 /api/v1/tasks/:id/run
    "bidpool.v1.TaskService/BatchDeleteTasks": reqWithBody("POST", "/api/v1/tasks/batch-delete", (ctx) => ({
      ids: ctx.request.ids || [],
    })),

    // ===== 标讯管理 =====
    "bidpool.v1.BidService/ListBids": async (ctx) => {
      const params = new URLSearchParams();
      if (ctx.request.page) params.set("page", ctx.request.page);
      if (ctx.request.page_size) params.set("page_size", ctx.request.page_size);
      if (ctx.request.keyword) params.set("keyword", ctx.request.keyword);
      // ... 类似 ListTasks
    },
    "bidpool.v1.BidService/GetBid": reqWithId("GET", "/api/v1/bids"),
    "bidpool.v1.BidService/DispatchBids": reqWithBody("POST", "/api/v1/bids/dispatch", (ctx) => ({
      ids: ctx.request.ids || [],
      webhook_url: ctx.request.webhook_url,
    })),
    // ... 其他方法类似

    // ===== 智能对话（特殊的响应格式）=====
    "bidpool.v1.ChatService/Chat": async (ctx) => {
      const data = await apiCall("POST", "/api/v1/chat", {
        message: ctx.request.message,
        session_id: ctx.request.session_id || "",
      }, authFrom(ctx));
      return {
        code: data.code ?? 0,
        message: data.message ?? "",
        data: {
          response: data.data?.response || "",
          session_id: data.data?.session_id || "",
        },
      };
    },

    // ===== 系统管理（无需参数的 GET 请求）=====
    "bidpool.v1.SystemService/GetStatus": req("GET", "/api/v1/status"),
    "bidpool.v1.SystemService/GetConfig": req("GET", "/api/v1/config"),
    "bidpool.v1.SystemService/SaveConfig": reqWithBody("POST", "/api/v1/config", (ctx) => {
      try { return JSON.parse(ctx.request.config_json); } catch { return {}; }
    }),
  },
});

// ===== 启动！=====
// 这行代码让 OctoBus 知道这个服务已经准备好了
// 它会启动一个 gRPC 服务端，等待 OctoBus 网关转发请求过来
runServiceMain(service);
```

### 3.6 第四步：配置文件

**文件: `package.json`**
```json
{
  "name": "octobus-bidpool",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "bin": {
    "bidpool": "bin/bidpool.js"
  },
  "dependencies": {
    "@chaitin-ai/octobus-sdk": "^0.5.0"
  }
}
```

**文件: `secret.schema.json`**（定义哪些信息可以存为"密钥"）
```json
{
  "type": "object",
  "properties": {
    "username": { "type": "string", "description": "BidPool 登录用户名" },
    "password": { "type": "string", "description": "BidPool 登录密码" }
  }
}
```

> 密钥（secret）和配置（config）的区别：
> - **secret**：存敏感信息，如密码、API Key。创建实例时通过 `--secret-json` 传入
> - **config**：存非敏感信息，如服务器地址。创建实例时通过 `--config-json` 传入

### 3.7 第五步：导入到 OctoBus

准备工作：确保服务包文件完整
```
bidpool-service/
├── service.json
├── package.json
├── secret.schema.json
├── proto/bidpool.proto
└── bin/bidpool.js
```

然后执行以下命令（在服务器 `10.2.36.217` 上执行）：

```bash
# 1. 把服务包复制到 OctoBus 容器内
docker cp /opt/octobus/services/bidpool-service octobus:/var/lib/octobus/bidpool-service

# 2. 导入服务
#    OctoBus 会自动：
#    - 用 protoc 编译 proto 文件
#    - 注册所有 rpc 方法
#    - 安装 npm 依赖
docker exec octobus octobus service import bidpool /var/lib/octobus/bidpool-service

# ※ 如果之前导入过，需要先删除旧的
docker exec octobus octobus instance delete bidpool-prod   # 先删实例
docker exec octobus octobus service delete bidpool          # 再删服务
```

### 3.8 第六步：创建实例

```bash
# 创建实例（启动 Node.js 子进程）
# --service 指定用哪个服务
# --secret-json 传入登录凭据（对应 secret.schema.json）
# --config-json 传入配置
docker exec octobus octobus instance create bidpool-prod \
  --service bidpool \
  --secret-json '{"username":"admin","password":"bidpool@2026"}' \
  --config-json '{}'
```

**如果遇到 `permission denied` 错误：**
```bash
# 给运行时文件加执行权限
docker exec octobus find /var/lib/octobus/artifacts/services/bidpool/runtime/bin \
  -type f -exec chmod +x {} \;
# 重新创建实例
docker exec octobus octobus instance create bidpool-prod \
  --service bidpool \
  --secret-json '{"username":"admin","password":"bidpool@2026"}' \
  --config-json '{}'
```

验证实例是否运行：
```bash
docker exec octobus octobus instance list
# 应该能看到 Status: running, PID: 数字
```

### 3.9 第七步：创建能力集并绑定

```bash
# 1. 创建能力集
#    capset 就像"功能包"，把实例的方法打包给 AI Agent 用
docker exec octobus octobus capset create bidpool-access --name "BidPool标讯平台"

# 2. 把实例加入能力集
#    --include-all-methods 表示暴露这个实例的所有方法
docker exec octobus octobus capset add-instance bidpool-access bidpool-prod

# 3. 查看能力目录（确认所有方法都已暴露）
docker exec octobus octobus catalog bidpool-access --all
```

预期输出：能看到 16 个方法，每个方法都有 Connect RPC 端点。

### 3.10 第八步：测试调用

```bash
# 测试系统状态接口
curl -X POST "http://10.2.36.217:9000/capsets/bidpool-access/connect/bidpool-prod/bidpool.v1.SystemService/GetStatus" \
  -H "Content-Type: application/json" \
  -d '{}'

# 成功的话会返回 BidPool 的实时数据
# {"code":0,"dataJson":"{\"bid_count\":90,\"task_count\":4,...}","message":"成功"}
```

---

## 4. 接入 agent-compose

### 4.1 配置能力接入网关

**方式一：通过前端页面配置（推荐）**

1. 浏览器打开 `http://10.2.36.217`
2. 用 `admin / octobus2024` 登录
3. 左侧菜单点击 **系统配置**
4. 默认就在 **能力接入网关** 面板
5. 在"网关地址"输入框填写 `http://octobus:9000`
6. 点击 **保存**

> 为什么用 `http://octobus:9000` 而不是 `http://10.2.36.217:9000`？
> 因为 agent-compose 和 OctoBus 在同一个 Docker 网络里，通过容器名 `octobus` 就能访问。
> 如果用 `10.2.36.217:9000` 就走外网了，速度慢且可能不通。

**方式二：通过 API 配置**

```bash
# 1. 先登录 agent-compose，获取 cookie
curl -c /tmp/cookies.txt -X POST http://10.2.36.217/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"octobus2024"}'

# 2. 配置 OctoBus 地址
curl -b /tmp/cookies.txt -X POST \
  http://10.2.36.217/agentcompose.v1.ConfigService/UpdateCapabilityGatewayConfig \
  -H "Content-Type: application/json" \
  -d '{"addr":"http://octobus:9000"}'
```

### 4.2 验证是否配置成功

配置好后，agent-compose 会自动连接 OctoBus：

```bash
# 查看连接状态
curl -b /tmp/cookies.txt -X POST \
  http://10.2.36.217/agentcompose.v1.CapabilityService/GetCapabilityStatus \
  -H "Content-Type: application/json" -d '{}'

# 正确返回：
# {"configured": true, "ok": true, "serviceCount": 1}

# 查看所有能力集
curl -b /tmp/cookies.txt -X POST \
  http://10.2.36.217/agentcompose.v1.CapabilityService/ListCapabilitySets \
  -H "Content-Type: application/json" -d '{}'

# 查看具体能力的接口列表
curl -b /tmp/cookies.txt -X POST \
  http://10.2.36.217/agentcompose.v1.CapabilityService/GetCapabilityCatalog \
  -H "Content-Type: application/json" -d '{"capset_id":"bidpool-access"}'
```

### 4.3 在前端页面上查看

配置成功后，打开 agent-compose 前端：
1. `http://10.2.36.217` → 登录
2. **系统配置 → 能力接入网关**
3. 你会看到：
   - 连接状态：**正常**
   - 能力集列表：**BidPool标讯平台**
   - 展开就能看到 16 个接口的详细信息

---

## 5. 以后加新服务怎么做

### 5.1 通用流程

```mermaid
graph LR
    A[后端REST API] --> B[写proto文件]
    B --> C[写Node.js handler]
    C --> D[service.json配置]
    D --> E[导入OctoBus]
    E --> F[创建实例]
    F --> G[创建capset并绑定]
    G --> H[agent-compose自动发现]
```

### 5.2 三步添加新服务

**第一步：准备服务包**

仿照 bidpool-service 的目录结构创建新服务：

```bash
# 例如加一个"天气预报"服务
mkdir -p /opt/octobus/services/weather-service/{proto,bin}
```

**第二步：写 proto 文件**（定义接口）

按照 3.3 节的格式写，重点是：
1. 分析 REST API 有哪些接口
2. 每个接口对应一个 `rpc`
3. 请求参数和响应字段写成 `message`

**第三步：写 handler 做转换**

仿照 3.5 节写 `bin/weather.js`：

```javascript
async function callWeatherAPI(path) {
  const res = await fetch(`http://天气服务地址${path}`);
  return res.json();
}

const service = defineService({
  handlers: {
    "weather.v1.WeatherService/GetForecast": async (ctx) => {
      const data = await callWeatherAPI(`/api/forecast?city=${ctx.request.city}`);
      return { code: 0, data_json: JSON.stringify(data) };
    },
  },
});
runServiceMain(service);
```

**第四步：导入 + 创建实例 + 创建 capset**

```bash
# 导入
docker cp /opt/octobus/services/weather-service octobus:/var/lib/octobus/weather-service
docker exec octobus octobus service import weather /var/lib/octobus/weather-service

# 创建实例
docker exec octobus octobus instance create weather-prod --service weather --config-json '{}' --secret-json '{}'

# 创建能力集并绑定
docker exec octobus octobus capset create weather-access --name "天气预报"
docker exec octobus octobus capset add-instance weather-access weather-prod
```

**完成！** 新服务的接口会自动出现在 agent-compose 的 **能力接入网关** 页面中。

### 5.3 已有 OctoBus 服务怎么用

OctoBus 仓库自带 30+ 个安全产品服务包（在 `services/` 目录下），直接导入即可使用：

```bash
# 例如导入 SafeLine WAF 服务
docker exec octobus octobus service import safeline-waf /path/to/services/chaitin__safeline-waf
```

---

## 6. 常见问题

### Q1: 导入服务时提示 `permission denied`

**原因：** 服务包文件没有执行权限。

**解决：**
```bash
docker exec octobus find /var/lib/octobus/artifacts/services/你的服务名/runtime/bin \
  -type f -exec chmod +x {} \;
```

### Q2: 创建实例后状态不是 running

**排查步骤：**
```bash
# 查看实例详情
docker exec octobus octobus instance get 你的实例名

# 查看 OctoBus 日志
docker logs octobus --tail 20
```

### Q3: 调用接口返回"需要认证"

**原因：** BidPool 需要 HTTP Basic Auth，但没传对用户名密码。

**解决：** 重新创建实例，传入正确的 secret：
```bash
docker exec octobus octobus instance create 实例名 \
  --service bidpool \
  --secret-json '{"username":"你的用户名","password":"你的密码"}'
```

### Q4: agent-compose 显示"能力接入网关未配置"

**原因：** 没有在 agent-compose 中配置 OctoBus 地址。

**解决：** 按第 4 节步骤，在系统配置页面填写网关地址。

### Q5: 如何删除一个服务？

```bash
# 先停止并删除实例
docker exec octobus octobus instance stop 实例名
docker exec octobus octobus instance delete 实例名

# 再删除服务
docker exec octobus octobus service delete 服务名

# 清理文件
docker exec octobus rm -rf /var/lib/octobus/artifacts/services/服务名
```

### Q6: 如何更新服务代码？

```bash
# 1. 更新服务包文件
# 2. 删除旧实例和服务
docker exec octobus octobus instance delete 实例名
docker exec octobus octobus service delete 服务名

# 3. 重新复制和导入
docker cp 新服务包目录 octobus:/var/lib/octobus/服务名
docker exec octobus octobus service import 服务名 /var/lib/octobus/服务名

# 4. 重新创建实例和 capset
# （按 3.8 和 3.9 节的步骤）
```

---

## 附录：常用命令速查

### OctoBus 操作

```bash
# 服务管理
docker exec octobus octobus service list                    # 查看所有服务
docker exec octobus octobus service import <id> <path>       # 导入服务
docker exec octobus octobus service delete <id>              # 删除服务

# 实例管理
docker exec octobus octobus instance list                    # 查看所有实例
docker exec octobus octobus instance get <id>                # 查看实例详情
docker exec octobus octobus instance create <id> ...         # 创建实例
docker exec octobus octobus instance delete <id>             # 删除实例

# 能力集管理
docker exec octobus octobus capset list                      # 查看所有能力集
docker exec octobus octobus capset create <id> --name <n>    # 创建能力集
docker exec octobus octobus capset add-instance <c> <i>      # 绑定实例到能力集
docker exec octobus octobus catalog <capset-id> --all        # 查看能力目录

# 状态检查
docker exec octobus octobus status                           # OctoBus 运行状态
```

### Docker 操作

```bash
# 容器管理
docker ps                                                     # 查看运行中的容器
docker logs <容器名> --tail 20                                # 查看容器日志
docker restart <容器名>                                       # 重启容器
docker exec <容器名> <命令>                                   # 在容器内执行命令

# 文件操作
docker cp <本地路径> <容器名>:<容器路径>                      # 复制文件到容器
docker cp <容器名>:<容器路径> <本地路径>                      # 从容器复制文件
```
