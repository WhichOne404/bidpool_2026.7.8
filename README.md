# BidPool - 标讯智能平台

基于 Go + Python 的标讯采集、智能分发与推送平台，支持多平台爬取、智能体协作、钉钉消息推送。

## 架构

```
┌────────────────────────────────────────────┐
│              Vue3 Frontend                  │
└──────────────────┬─────────────────────────┘
                   │ HTTP API
                   ▼
┌────────────────────────────────────────────┐
│            Go Backend Service              │
│     API层 (Gin) + 调度层 (Cron)            │
│     数据层 (SQLite)                        │
└──┬──────────────┬──────────────┬───────────┘
   │              │              │
   ▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Crawler  │ │ Filter   │ │ Dispatch     │
│ Agent    │ │ Agent    │ │ Agent        │
└──────────┘ └──────────┘ └──────────────┘
```

## 功能特性

- 多平台标讯爬取（先支持千里马）
- 纯API方式，不依赖浏览器
- 智能验证码识别（ddddocr）
- 定时任务调度（Cron表达式）
- 智能体协作系统
- 钉钉消息推送（按行业分群）
- Web界面管理
- 对话交互控制

## 部署架构

| 服务 | 地址 | 技术栈 |
|------|------|--------|
| Web前端 | http://10.2.37.237:8088 | Vue3 |
| Go API | http://10.2.37.237:8088/api/v1 | Gin + Cron + SQLite |
| Python Agents | 内部服务 | FastAPI + Playwright |

## 快速开始

### 1. 安装依赖

```bash
# Go Backend
cd bidpool-go
go mod tidy

# Python Agents
cd bidpool-python
pip install -r requirements.txt

# Web Frontend
cd bidpool-web
npm install
```

### 2. 配置

**LLM配置 (`bidpool-python/config/llm_config.json`):**

```json
{
  "provider": "openai",
  "api_key": "your-api-key",
  "base_url": "https://api.example.com",
  "model": "gpt-4"
}
```

**平台配置 (`bidpool-python/config/settings.json`):**

```json
{
  "platforms": {
    "qianlima": {
      "username": "your-username",
      "password": "your-password"
    }
  },
  "dingtalk_groups": [
    {
      "name": "金融能源群",
      "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
      "industries": ["金融", "能源"]
    }
  ]
}
```

### 3. 启动服务

```bash
# 启动 Go Backend
cd bidpool-go
go run cmd/server/main.go

# 启动 Python Agents
cd bidpool-python
python main.py

# 启动 Web Frontend
cd bidpool-web
npm run dev
```

### 4. 访问

- Web界面: http://localhost:3000
- Go API: http://localhost:8080
- Python Agent: http://localhost:8000

## 智能体说明

| Agent | 功能 |
|-------|------|
| CrawlerAgent | 标讯数据采集，处理登录验证码 |
| FilterAgent | 数据清洗、去重、智能分类 |
| DispatchAgent | 钉钉消息发送，按规则路由 |
| OrchestratorAgent | 协调其他Agent，处理对话 |
| MonitorAgent | 任务监控，异常告警 |

## API接口

```
GET    /api/v1/status        # 系统状态
GET    /api/v1/bids          # 标讯列表
POST   /api/v1/tasks         # 创建任务
GET    /api/v1/tasks         # 任务列表
PUT    /api/v1/tasks/:id     # 更新任务
DELETE /api/v1/tasks/:id     # 删除任务
POST   /api/v1/tasks/:id/run # 执行任务
POST   /api/v1/chat          # 对话接口
```

## 目录结构

```
BidPool/
├── bidpool-go/           # Go后端服务
│   ├── cmd/server/       # 入口
│   ├── internal/         # 内部模块
│   │   ├── api/          # API层
│   │   ├── scheduler/    # 调度层
│   │   ├── model/        # 数据模型
│   │   └── store/        # 数据存储
│   └── configs/          # 配置文件
│
├── bidpool-python/       # Python智能体服务
│   ├── agents/           # 智能体模块
│   ├── crawlers/         # 爬虫模块
│   ├── llm/              # LLM客户端
│   ├── dingtalk/         # 钉钉发送
│   ├── server/           # FastAPI服务
│   └── config/           # 配置管理
│
├── bidpool-web/          # Vue前端
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── api/          # API请求
│   │   └── router/       # 路由配置
│   └── public/
│
├── docker/               # Docker部署
├── configs/              # 公共配置
├── docker-compose.yml
└── deploy-package/
```

## 扩展新平台

继承 `BaseCrawler` 类，实现 `login()`, `search()`, `get_detail()` 方法，注册到 `CrawlerRegistry`：

```python
class NewPlatformCrawler(BaseCrawler):
    name = "new_platform"

    def login(self, credentials):
        pass

    def search(self, params):
        pass

CrawlerRegistry.register("new_platform", NewPlatformCrawler)
```

## License

MIT
