package handler

import (
	"encoding/json"
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"github.com/zhonghai/bidpool-go/internal/execution"
	"github.com/zhonghai/bidpool-go/internal/model"
)

// ExecutionHandler 执行详情处理器
type ExecutionHandler struct {
	db   *gorm.DB
	exec *execution.Manager
}

func NewExecutionHandler(db *gorm.DB) *ExecutionHandler {
	return &ExecutionHandler{
		db:   db,
		exec: execution.GetManager(),
	}
}

// GetExecution 获取任务执行详情
func (h *ExecutionHandler) GetExecution(c *gin.Context) {
	taskID := c.Param("task_id")

	execState := h.exec.GetExecution(taskID)
	if execState == nil {
		var log model.ExecutionLog
		if err := h.db.Where("task_id = ?", taskID).Order("started_at desc").First(&log).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"code": -1, "message": "未找到执行记录"})
			return
		}

		// 为历史记录构建基本执行状态
		status := log.Status
		progress := 100
		if status == "running" {
			progress = 50
		}

		currentStep := ""
		if status == "success" {
			currentStep = "执行完成"
		} else if status == "failed" {
			currentStep = "执行失败: " + log.Message
		} else {
			currentStep = status
		}

		// 解析保存的日志和步骤
		var logs []execution.ExecutionLog
		var steps []execution.ExecutionStep
		if log.Logs != "" {
			json.Unmarshal([]byte(log.Logs), &logs)
		}
		if log.Steps != "" {
			json.Unmarshal([]byte(log.Steps), &steps)
		}
		if len(steps) == 0 {
			steps = []execution.ExecutionStep{
				{Name: "初始化", Status: "success", Message: "完成"},
				{Name: "登录平台", Status: "success", Message: "完成"},
				{Name: "搜索标讯", Status: "success", Message: "完成"},
				{Name: "数据处理", Status: status, Message: log.Message},
			}
		}

		execState = &execution.TaskExecution{
			TaskID:      taskID,
			ExecutionID: log.ID,
			Status:      status,
			StartTime:   log.StartedAt,
			EndTime:     log.EndedAt,
			BidsCount:   log.BidsCount,
			Progress:    progress,
			CurrentStep: currentStep,
			Error:       log.Message,
			Steps:       steps,
			Logs:        logs,
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": execState,
	})
}

// GetExecutionLogs 获取执行日志
func (h *ExecutionHandler) GetExecutionLogs(c *gin.Context) {
	taskID := c.Param("task_id")

	execState := h.exec.GetExecution(taskID)

	var logs []execution.ExecutionLog
	if execState != nil {
		logs = execState.Logs
	} else {
		logs = []execution.ExecutionLog{}
	}

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": logs,
	})
}

// GetRecentExecutions 获取最近的执行列表
func (h *ExecutionHandler) GetRecentExecutions(c *gin.Context) {
	var logs []model.ExecutionLog
	h.db.Order("started_at desc").Limit(20).Find(&logs)

	executions := make([]map[string]interface{}, 0, len(logs))
	for _, log := range logs {
		executions = append(executions, map[string]interface{}{
			"task_id":      log.TaskID,
			"execution_id": log.ID,
			"status":       log.Status,
			"start_time":   log.StartedAt,
			"end_time":     log.EndedAt,
			"bids_count":   log.BidsCount,
			"error":        log.Message,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": executions,
	})
}
