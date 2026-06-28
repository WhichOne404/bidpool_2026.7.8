package api

import (
	"log"

	"github.com/zhonghai/bidpool-go/internal/api/handler"
	"github.com/zhonghai/bidpool-go/internal/config"
	"github.com/zhonghai/bidpool-go/internal/middleware"
	"github.com/zhonghai/bidpool-go/internal/scheduler"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func SetupRouter(db *gorm.DB, sched *scheduler.Scheduler, cfg *config.Config) *gin.Engine {
	r := gin.Default()

	// 静态文件服务 - 不需要认证
	r.Static("/assets", "./dist/assets")
	r.StaticFile("/favicon.ico", "./dist/favicon.ico")

	// 创建handlers
	bidHandler := handler.NewBidHandler(db)
	taskHandler := handler.NewTaskHandler(db, sched, cfg)
	chatHandler := handler.NewChatHandler(cfg)
	statusHandler := handler.NewStatusHandler(db, sched)
	configHandler := handler.NewConfigHandler()
	executionHandler := handler.NewExecutionHandler(db)

	// 恢复已有的定时任务
	taskHandler.RestoreScheduledTasks()
	log.Println("Scheduled tasks restored from database")

	// 健康检查 - 不需要认证
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "healthy"})
	})
	r.HEAD("/health", func(c *gin.Context) {
		c.Status(200)
	})

	// API路由组 - 需要认证
	v1 := r.Group("/api/v1")
	if cfg.Auth.Enabled {
		v1.Use(middleware.BasicAuth(cfg.Auth.Username, cfg.Auth.Password))
		log.Printf("Basic Auth enabled for API routes, username: %s", cfg.Auth.Username)
	}
	{
		// 任务管理
		v1.POST("/tasks", taskHandler.CreateTask)
		v1.GET("/tasks", taskHandler.ListTasks)
		v1.POST("/tasks/batch-delete", taskHandler.BatchDeleteTasks)
		v1.GET("/tasks/:id", taskHandler.GetTask)
		v1.PUT("/tasks/:id", taskHandler.UpdateTask)
		v1.DELETE("/tasks/:id", taskHandler.DeleteTask)
		v1.POST("/tasks/:id/run", taskHandler.RunTask)

		// 任务执行详情（使用独立的路径避免冲突）
		v1.GET("/executions/:task_id", executionHandler.GetExecution)
		v1.GET("/executions/:task_id/logs", executionHandler.GetExecutionLogs)

		// 标讯管理
		v1.GET("/bids", bidHandler.ListBids)
		v1.GET("/bids/:id", bidHandler.GetBid)
		v1.DELETE("/bids/:id", bidHandler.DeleteBid)
		v1.POST("/bids/batch-delete", bidHandler.BatchDelete)
		v1.POST("/bids/dispatch", bidHandler.Dispatch)

		// 对话交互
		v1.POST("/chat", chatHandler.HandleChat)

		// 系统状态
		v1.GET("/status", statusHandler.GetStatus)
		v1.GET("/trend", statusHandler.GetTrend)

		// 配置管理
		v1.GET("/config", configHandler.GetConfig)
		v1.POST("/config", configHandler.SaveConfig)
		v1.POST("/config/dingtalk/test", configHandler.TestDingTalk)
	}

	// SPA 前端路由 - 所有非 API 路由返回 index.html
	r.NoRoute(func(c *gin.Context) {
		c.File("./dist/index.html")
	})

	return r
}