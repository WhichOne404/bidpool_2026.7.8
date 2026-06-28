package model

import (
	"time"

	"gorm.io/gorm"
)

// BidInfo 标讯信息
type BidInfo struct {
	ID          string         `gorm:"primaryKey" json:"id"`
	Title       string         `json:"title"`
	TenderUnit  string         `json:"tender_unit"`
	CRMIndustry string         `json:"crm_industry"`
	Budget      string         `json:"budget"`
	Region      string         `json:"region"`
	PublishDate string         `json:"publish_date"`
	Deadline    string         `json:"deadline"`
	OpenDate    string         `json:"open_date"`
	Source      string         `json:"source"`
	Link        string         `json:"link"`
	RawData     string         `json:"raw_data"` // JSON原始数据
	CreatedAt   time.Time      `json:"created_at"`
	Status      string         `json:"status"`  // pending/sent/failed
	TaskID      string         `json:"task_id"` // 关联任务ID
}

// TaskConfig 任务配置
type TaskConfig struct {
	ID            string    `gorm:"primaryKey" json:"id"`
	Name          string    `json:"name"`
	TaskType      string    `gorm:"column:task_type" json:"task_type"`                         // crawl/send
	Platform      string    `json:"platform"`                                                  // qianlima/... (crawl任务)
	RegionCodes   string    `json:"region_codes"`                                              // JSON数组存储 (crawl任务)
	StartDate     string    `json:"start_date"`                                                // crawl任务日期范围
	EndDate       string    `json:"end_date"`
	DynamicDate   bool      `json:"dynamic_date"`                                              // 动态日期，每次执行时计算
	DynamicDays   int       `json:"dynamic_days"`                                              // 动态日期天数（默认7天）
	DingTalkGroup string    `gorm:"column:ding_talk_group" json:"dingtalk_group"`              // 发送目标群webhook (send任务)
	SendFilter    string    `gorm:"column:send_filter" json:"send_filter"`                     // JSON: region/industry/days (send任务)
	SendLimit     int       `gorm:"column:send_limit" json:"send_limit"`                       // 发送数量限制 (send任务)
	CronExpr      string    `json:"cron_expr"`                                                 // 定时表达式
	Enabled       bool      `json:"enabled"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// ExecutionLog 执行日志
type ExecutionLog struct {
	ID             string    `gorm:"primaryKey" json:"id"`
	TaskID         string    `json:"task_id"`
	Status         string    `json:"status"` // running/success/failed
	Message        string    `json:"message"`
	BidsCount      int       `json:"bids_count"`
	StartedAt      time.Time `json:"started_at"`
	EndedAt        time.Time `json:"ended_at"`
	Logs           string    `json:"logs"` // JSON格式的日志条目
	Steps          string    `json:"steps"` // JSON格式的步骤信息
	LoginStatus    string    `json:"login_status"` // logged_in/logged_out/expired/unknown
	DiscoveredCount int      `json:"discovered_count"` // 发现标讯数量
	StoredCount    int       `json:"stored_count"` // 存储标讯数量
	DuplicateCount int       `json:"duplicate_count"` // 去重过滤数量
}

// DingTalkGroup 钉钉群配置
type DingTalkGroup struct {
	Name       string   `json:"name"`
	WebhookURL string   `json:"webhook_url"`
	Industries []string `json:"industries"` // 匹配行业
}

// 自动迁移
func AutoMigrate(db *gorm.DB) error {
	return db.AutoMigrate(&BidInfo{}, &TaskConfig{}, &ExecutionLog{})
}