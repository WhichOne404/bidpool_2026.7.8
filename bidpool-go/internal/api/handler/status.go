package handler

import (
	"net/http"
	"time"

	"github.com/zhonghai/bidpool-go/internal/model"
	"github.com/zhonghai/bidpool-go/internal/scheduler"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type StatusHandler struct {
	db    *gorm.DB
	sched *scheduler.Scheduler
}

func NewStatusHandler(db *gorm.DB, sched *scheduler.Scheduler) *StatusHandler {
	return &StatusHandler{db: db, sched: sched}
}

// DailyStats 每日统计数据
type DailyStats struct {
	Date  string `json:"date"`
	Count int64  `json:"count"`
}

// GetStatus 获取系统状态
func (h *StatusHandler) GetStatus(c *gin.Context) {
	// 统计标讯数量
	var bidCount int64
	h.db.Model(&model.BidInfo{}).Count(&bidCount)

	// 统计任务数量
	var taskCount int64
	h.db.Model(&model.TaskConfig{}).Count(&taskCount)

	// 获取最近执行日志
	var recentLogs []model.ExecutionLog
	h.db.Order("started_at desc").Limit(10).Find(&recentLogs)

	// 获取调度器状态
	activeJobs := h.sched.GetActiveJobs()

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": gin.H{
			"bid_count":    bidCount,
			"task_count":   taskCount,
			"active_jobs":  activeJobs,
			"recent_logs":  recentLogs,
			"server_time":  time.Now().Format("2006-01-02 15:04:05"),
		},
	})
}

// GetTrend 获取近7日标讯趋势
func (h *StatusHandler) GetTrend(c *gin.Context) {
	now := time.Now()
	results := make([]DailyStats, 7)

	for i := 6; i >= 0; i-- {
		date := now.AddDate(0, 0, -i)
		dateStr := date.Format("2006-01-02")
		startOfDay := time.Date(date.Year(), date.Month(), date.Day(), 0, 0, 0, 0, date.Location())
		endOfDay := startOfDay.Add(24 * time.Hour)

		var count int64
		h.db.Model(&model.BidInfo{}).
			Where("created_at >= ? AND created_at < ?", startOfDay, endOfDay).
			Count(&count)

		results[6-i] = DailyStats{
			Date:  dateStr,
			Count: count,
		}
	}

	// 生成日期标签（周一、周二...）
	weekDays := []string{"周日", "周一", "周二", "周三", "周四", "周五", "周六"}
	dates := make([]string, 7)
	for i := 6; i >= 0; i-- {
		date := now.AddDate(0, 0, -i)
		dates[6-i] = weekDays[int(date.Weekday())]
	}

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": gin.H{
			"dates": dates,
			"stats": results,
		},
	})
}