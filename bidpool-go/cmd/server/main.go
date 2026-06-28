package main

import (
	"log"
	"os"

	"github.com/zhonghai/bidpool-go/internal/api"
	"github.com/zhonghai/bidpool-go/internal/config"
	"github.com/zhonghai/bidpool-go/internal/scheduler"
	"github.com/zhonghai/bidpool-go/internal/store"
)

func main() {
	// 从环境变量获取配置路径，默认为 configs/config.yaml
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = "configs/config.yaml"
	}

	// 加载配置
	cfg, err := config.LoadConfig(configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// 初始化数据库
	db, err := store.InitDB(cfg.Database.Path)
	if err != nil {
		log.Fatalf("Failed to init database: %v", err)
	}

	// 初始化调度器
	sched := scheduler.NewScheduler()
	sched.Start()

	// 启动API服务
	router := api.SetupRouter(db, sched, cfg)
	log.Printf("Server starting on port %s", cfg.Server.Port)
	if err := router.Run(":" + cfg.Server.Port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}