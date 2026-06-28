package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/zhonghai/bidpool-go/internal/config"
	"github.com/zhonghai/bidpool-go/internal/execution"
	"github.com/zhonghai/bidpool-go/internal/model"
	"github.com/zhonghai/bidpool-go/internal/scheduler"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type TaskHandler struct {
	db    *gorm.DB
	sched *scheduler.Scheduler
	cfg   *config.Config
	exec  *execution.Manager
}

func NewTaskHandler(db *gorm.DB, sched *scheduler.Scheduler, cfg *config.Config) *TaskHandler {
	return &TaskHandler{
		db:    db,
		sched: sched,
		cfg:   cfg,
		exec:  execution.GetManager(),
	}
}

// CreateTask 创建任务
func (h *TaskHandler) CreateTask(c *gin.Context) {
	var req CreateTaskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "参数错误"})
		return
	}

	// 默认任务类型为crawl
	taskType := req.TaskType
	if taskType == "" {
		taskType = "crawl"
	}

	task := model.TaskConfig{
		ID:            uuid.New().String(),
		Name:          req.Name,
		TaskType:      taskType,
		Platform:      req.Platform,
		RegionCodes:   toJSON(req.RegionCodes),
		StartDate:     req.StartDate,
		EndDate:       req.EndDate,
		DynamicDate:   req.DynamicDate,
		DynamicDays:   req.DynamicDays,
		CronExpr:      req.CronExpr,
		DingTalkGroup: req.DingTalkGroup,
		SendFilter:    toJSON(req.SendFilter),
		SendLimit:     req.SendLimit,
		Enabled:       req.Enabled,
		CreatedAt:     time.Now(),
		UpdatedAt:     time.Now(),
	}

	if err := h.db.Create(&task).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "创建失败"})
		return
	}

	if task.Enabled && task.CronExpr != "" {
		err := h.sched.AddJob(task.ID, task.CronExpr, func() {
			h.executeTaskWithTracking(task.ID)
		})
		if err != nil {
			log.Printf("Failed to add scheduled task %s: %v", task.ID, err)
		} else {
			log.Printf("Added scheduled task: %s (%s)", task.Name, task.CronExpr)
		}
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "data": task, "message": "创建成功"})
}

// ListTasks 获取任务列表
func (h *TaskHandler) ListTasks(c *gin.Context) {
	var tasks []model.TaskConfig
	h.db.Order("created_at desc").Find(&tasks)

	result := make([]map[string]interface{}, 0, len(tasks))
	for _, task := range tasks {
		taskMap := map[string]interface{}{
			"id":             task.ID,
			"name":           task.Name,
			"task_type":      task.TaskType,
			"platform":       task.Platform,
			"region_codes":   task.RegionCodes,
			"dynamic_date":   task.DynamicDate,
			"dynamic_days":   task.DynamicDays,
			"dingtalk_group": task.DingTalkGroup,
			"send_filter":    task.SendFilter,
			"send_limit":     task.SendLimit,
			"cron_expr":      task.CronExpr,
			"enabled":        task.Enabled,
			"created_at":     task.CreatedAt,
			"updated_at":     task.UpdatedAt,
		}

		execState := h.exec.GetExecution(task.ID)
		if execState != nil {
			taskMap["execution_status"] = execState.Status
			taskMap["progress"] = execState.Progress
			taskMap["current_step"] = execState.CurrentStep
		} else {
			taskMap["execution_status"] = ""
			taskMap["progress"] = 0
		}

		// 获取最近一次执行记录
		var execLog model.ExecutionLog
		if err := h.db.Where("task_id = ?", task.ID).Order("started_at desc").First(&execLog).Error; err == nil {
			taskMap["execution_status"] = execLog.Status
			// 计算执行耗时（秒）
			duration := 0
			if !execLog.EndedAt.IsZero() && !execLog.StartedAt.IsZero() {
				duration = int(execLog.EndedAt.Sub(execLog.StartedAt).Seconds())
			}
			taskMap["last_execution"] = map[string]interface{}{
				"started_at":       execLog.StartedAt,
				"ended_at":         execLog.EndedAt,
				"status":           execLog.Status,
				"bids_count":       execLog.BidsCount,
				"message":          execLog.Message,
				"login_status":     execLog.LoginStatus,
				"discovered_count": execLog.DiscoveredCount,
				"stored_count":     execLog.StoredCount,
				"duplicate_count":  execLog.DuplicateCount,
				"duration":         duration,
			}
		}

		result = append(result, taskMap)
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "data": result, "total": len(result)})
}

// GetTask 获取任务详情
func (h *TaskHandler) GetTask(c *gin.Context) {
	id := c.Param("id")
	var task model.TaskConfig

	if err := h.db.First(&task, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": -1, "message": "任务不存在"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "data": task})
}

// UpdateTask 更新任务
func (h *TaskHandler) UpdateTask(c *gin.Context) {
	id := c.Param("id")
	var task model.TaskConfig

	if err := h.db.First(&task, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"code": -1, "message": "任务不存在"})
		return
	}

	var req UpdateTaskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "参数错误"})
		return
	}

	// 更新基本字段
	if req.Name != "" {
		task.Name = req.Name
	}
	if req.CronExpr != "" {
		task.CronExpr = req.CronExpr
	}
	task.Enabled = req.Enabled

	// 更新收集任务字段
	if req.Platform != "" {
		task.Platform = req.Platform
	}
	if len(req.RegionCodes) > 0 {
		task.RegionCodes = toJSON(req.RegionCodes)
	}
	if req.StartDate != "" {
		task.StartDate = req.StartDate
	}
	if req.EndDate != "" {
		task.EndDate = req.EndDate
	}
	if req.DynamicDays > 0 {
		task.DynamicDays = req.DynamicDays
	}
	task.DynamicDate = req.DynamicDate

	// 更新发送任务字段
	if req.DingTalkGroup != "" {
		task.DingTalkGroup = req.DingTalkGroup
	}
	if req.SendFilter != nil {
		task.SendFilter = toJSON(req.SendFilter)
	}
	if req.SendLimit > 0 {
		task.SendLimit = req.SendLimit
	}

	task.UpdatedAt = time.Now()

	if err := h.db.Save(&task).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "更新失败"})
		return
	}

	// 更新调度
	if task.CronExpr != "" {
		h.sched.RemoveJob(task.ID)
		if task.Enabled {
			h.sched.AddJob(task.ID, task.CronExpr, func() {
				h.executeTaskWithTracking(task.ID)
			})
		}
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "data": task, "message": "更新成功"})
}

// DeleteTask 删除任务
func (h *TaskHandler) DeleteTask(c *gin.Context) {
	id := c.Param("id")
	h.sched.RemoveJob(id)

	if err := h.db.Delete(&model.TaskConfig{}, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "删除失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "message": "删除成功"})
}

// BatchDeleteTasks 批量删除任务
func (h *TaskHandler) BatchDeleteTasks(c *gin.Context) {
	var req BatchDeleteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "参数错误"})
		return
	}

	if len(req.IDs) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "请选择要删除的任务"})
		return
	}

	// 从调度器中移除所有任务
	for _, id := range req.IDs {
		h.sched.RemoveJob(id)
	}

	// 批量删除
	if err := h.db.Delete(&model.TaskConfig{}, "id IN ?", req.IDs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "删除失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "message": fmt.Sprintf("成功删除 %d 个任务", len(req.IDs))})
}

// RunTask 手动执行任务
func (h *TaskHandler) RunTask(c *gin.Context) {
	id := c.Param("id")
	go h.executeTaskWithTracking(id)
	c.JSON(http.StatusOK, gin.H{"code": 0, "message": "任务已启动"})
}

// RestoreScheduledTasks 恢复已有的定时任务（服务启动时调用）
func (h *TaskHandler) RestoreScheduledTasks() {
	var tasks []model.TaskConfig
	h.db.Where("enabled = ? AND cron_expr != ''", true).Find(&tasks)

	for _, task := range tasks {
		err := h.sched.AddJob(task.ID, task.CronExpr, func() {
			h.executeTaskWithTracking(task.ID)
		})
		if err != nil {
			log.Printf("Failed to restore scheduled task %s: %v", task.ID, err)
		} else {
			log.Printf("Restored scheduled task: %s (%s)", task.Name, task.CronExpr)
		}
	}
}

// executeTaskWithTracking 带状态追踪的任务执行
func (h *TaskHandler) executeTaskWithTracking(taskID string) {
	// 初始化执行追踪
	h.exec.StartExecution(taskID)
	h.exec.AddLog(taskID, "info", "开始执行任务")

	// 创建数据库执行日志
	log := model.ExecutionLog{
		ID:        uuid.New().String(),
		TaskID:    taskID,
		Status:    "running",
		StartedAt: time.Now(),
	}
	h.db.Create(&log)

	// 获取任务配置
	var task model.TaskConfig
	if err := h.db.First(&task, "id = ?", taskID).Error; err != nil {
		h.exec.AddLog(taskID, "error", "获取任务配置失败")
		h.exec.FinishExecution(taskID, "failed", 0, "任务配置不存在")
		log.Status = "failed"
		log.Message = "任务配置不存在"
		log.EndedAt = time.Now()
		h.saveExecutionLog(&log)
		return
	}

	// 根据任务类型执行不同逻辑
	taskType := task.TaskType
	if taskType == "" {
		taskType = "crawl" // 默认为爬取任务
	}

	if taskType == "send" {
		// 发送任务
		h.executeSendTask(taskID, task, &log)
	} else {
		// 爬取任务
		h.executeCrawlTask(taskID, task, &log)
	}
}

// executeCrawlTask 执行爬取任务
func (h *TaskHandler) executeCrawlTask(taskID string, task model.TaskConfig, log *model.ExecutionLog) {
	// 解析region_codes
	var regionCodes []string
	if task.RegionCodes != "" {
		json.Unmarshal([]byte(task.RegionCodes), &regionCodes)
	}
	if len(regionCodes) == 0 {
		regionCodes = []string{"500000"} // 默认重庆
	}

	// 计算日期范围
	startDate := task.StartDate
	endDate := task.EndDate
	if task.DynamicDate {
		// 动态计算日期范围
		days := task.DynamicDays
		if days <= 0 {
			days = 7 // 默认7天
		}
		now := time.Now()
		endDate = now.Format("2006-01-02")
		startDate = now.AddDate(0, 0, -days).Format("2006-01-02")
		h.exec.AddLog(taskID, "info", fmt.Sprintf("动态日期范围（近%d天）: %s 至 %s", days, startDate, endDate))
	}

	// 步骤0: 初始化完成
	h.exec.UpdateStep(taskID, 0, "success", "初始化完成")

	// 步骤1: 登录平台
	h.exec.UpdateStep(taskID, 1, "running", "正在登录...")
	h.exec.AddLog(taskID, "info", "开始登录千里马平台")

	// 获取平台凭证
	platformConfig := GetPlatformCredentials("qianlima")

	payload := map[string]interface{}{
		"task_id":      taskID,
		"platform":     task.Platform,
		"credentials":  platformConfig,
		"region_codes": regionCodes,
		"start_date":   startDate,
		"end_date":     endDate,
	}

	jsonData, _ := json.Marshal(payload)

	resp, err := http.Post(h.cfg.Agent.PythonServiceURL+"/agent/crawler/execute", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		h.exec.UpdateStep(taskID, 1, "failed", "连接失败")
		h.exec.AddLog(taskID, "error", "Agent服务连接失败: "+err.Error())
		h.exec.FinishExecution(taskID, "failed", 0, err.Error())
		log.Status = "failed"
		log.Message = err.Error()
		log.EndedAt = time.Now()
		h.saveExecutionLog(log)
		return
	}
	defer resp.Body.Close()

	var crawlResult map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&crawlResult)

	// 正确处理JSON解码后的数字类型（float64）
	code, ok := crawlResult["code"].(float64)
	if !ok || code != 0 {
		errMsg := "未知错误"
		if crawlResult["message"] != nil {
			errMsg, _ = crawlResult["message"].(string)
		}
		h.exec.UpdateStep(taskID, 1, "failed", "爬取失败")
		h.exec.AddLog(taskID, "error", errMsg)
		h.exec.FinishExecution(taskID, "failed", 0, errMsg)
		log.Status = "failed"
		log.Message = errMsg
		log.EndedAt = time.Now()
		h.saveExecutionLog(log)
		return
	}

	// 获取消息和标讯数量
	msg, _ := crawlResult["message"].(string)
	h.exec.UpdateStep(taskID, 1, "success", "登录成功")
	h.exec.UpdateStep(taskID, 2, "success", "搜索完成: "+msg)
	h.exec.AddLog(taskID, "info", msg)

	bidsCount := 0
	if crawlResult["bids_count"] != nil {
		bidsCount = int(crawlResult["bids_count"].(float64))
	}

	// 步骤3: 数据处理 - 保存标讯到数据库
	h.exec.UpdateStep(taskID, 3, "running", "正在保存数据...")
	h.exec.AddLog(taskID, "info", "开始保存标讯数据")

	// 从返回结果中提取bids并保存
	savedCount := 0
	duplicateCount := 0
	if crawlResult["data"] != nil {
		dataMap := crawlResult["data"].(map[string]interface{})
		if dataMap["bids"] != nil {
			bidsList := dataMap["bids"].([]interface{})
			for _, bidItem := range bidsList {
				bidMap := bidItem.(map[string]interface{})

				// 构建BidInfo
				bid := model.BidInfo{
					ID:          getString(bidMap, "id"),
					Title:       getString(bidMap, "title"),
					TenderUnit:  getString(bidMap, "tender_unit"),
					CRMIndustry: getString(bidMap, "crm_industry"),
					Budget:      getString(bidMap, "budget"),
					Region:      getString(bidMap, "region"),
					PublishDate: getString(bidMap, "publish_date"),
					Deadline:    getString(bidMap, "deadline"),
					OpenDate:    getString(bidMap, "open_date"),
					Source:      getString(bidMap, "source"),
					Link:        getString(bidMap, "link"),
					RawData:     toJSON(bidMap["raw_data"]),
					CreatedAt:   time.Now(),
					Status:      "pending",
					TaskID:      taskID,
				}

				// 保存到数据库（如果已存在则跳过）
				var existing model.BidInfo
				if h.db.Where("id = ?", bid.ID).First(&existing).Error != nil {
					if err := h.db.Create(&bid).Error; err == nil {
						savedCount++
					}
				} else {
					duplicateCount++
				}
			}
		}
	}
	h.exec.AddLog(taskID, "info", fmt.Sprintf("保存了 %d 条新标讯，去重过滤 %d 条", savedCount, duplicateCount))
	log.StoredCount = savedCount
	log.DuplicateCount = duplicateCount
	log.DiscoveredCount = savedCount + duplicateCount

	h.exec.UpdateStep(taskID, 3, "success", "数据保存完成")

	// 完成（不自动发送钉钉，需手动分发）
	h.exec.FinishExecution(taskID, "success", bidsCount, "")
	h.exec.AddLog(taskID, "info", "任务执行完成，请在标讯列表手动分发到钉钉")

	// 获取执行状态并保存日志和步骤
	execState := h.exec.GetExecution(taskID)
	log.Status = "success"
	log.BidsCount = bidsCount
	log.EndedAt = time.Now()
	log.LoginStatus = "logged_in" // 登录成功
	if execState != nil {
		log.Logs = toJSON(execState.Logs)
		log.Steps = toJSON(execState.Steps)
	}
	h.saveExecutionLog(log)
}

// executeSendTask 执行发送任务
func (h *TaskHandler) executeSendTask(taskID string, task model.TaskConfig, log *model.ExecutionLog) {
	h.exec.UpdateStep(taskID, 0, "success", "初始化完成")
	h.exec.AddLog(taskID, "info", "开始执行发送任务")

	// 解析筛选条件
	var sendFilter map[string]interface{}
	if task.SendFilter != "" {
		json.Unmarshal([]byte(task.SendFilter), &sendFilter)
	}

	// 构建查询
	query := h.db.Model(&model.BidInfo{}).Where("status = ?", "pending")

	// 应用筛选条件
	if sendFilter != nil {
		// 地区筛选：支持多选
		if regions, ok := sendFilter["regions"].([]interface{}); ok && len(regions) > 0 {
			regionFilters := make([]string, 0)
			for _, r := range regions {
				if region, ok := r.(string); ok && region != "" {
					regionFilters = append(regionFilters, region)
				}
			}
			if len(regionFilters) > 0 {
				// 使用OR条件匹配多个地区
				regionConditions := make([]string, len(regionFilters))
				for i, r := range regionFilters {
					regionConditions[i] = fmt.Sprintf("region LIKE '%s'", "%"+r+"%")
				}
				query = query.Where(strings.Join(regionConditions, " OR "))
				h.exec.AddLog(taskID, "info", fmt.Sprintf("地区筛选：%v", regionFilters))
			}
		} else if region, ok := sendFilter["region"].(string); ok && region != "" {
			// 兼容旧数据：单选地区
			query = query.Where("region LIKE ?", "%"+region+"%")
			h.exec.AddLog(taskID, "info", fmt.Sprintf("地区筛选：%s", region))
		}

		// 行业筛选：支持多选
		if industries, ok := sendFilter["industries"].([]interface{}); ok && len(industries) > 0 {
			industryFilters := make([]string, 0)
			for _, i := range industries {
				if industry, ok := i.(string); ok && industry != "" {
					industryFilters = append(industryFilters, industry)
				}
			}
			if len(industryFilters) > 0 {
				query = query.Where("crm_industry IN ?", industryFilters)
				h.exec.AddLog(taskID, "info", fmt.Sprintf("行业筛选：%v", industryFilters))
			}
		} else if industry, ok := sendFilter["industry"].(string); ok && industry != "" {
			// 兼容旧数据：单选行业
			query = query.Where("crm_industry = ?", industry)
			h.exec.AddLog(taskID, "info", fmt.Sprintf("行业筛选：%s", industry))
		}

		// 日期筛选：支持动态日期和固定日期两种模式
		useDynamic, _ := sendFilter["use_dynamic"].(bool)
		if useDynamic {
			// 动态日期：使用days字段
			if days, ok := sendFilter["days"].(float64); ok && days > 0 {
				startDate := time.Now().AddDate(0, 0, -int(days)).Format("2006-01-02")
				query = query.Where("publish_date >= ?", startDate)
				h.exec.AddLog(taskID, "info", fmt.Sprintf("动态日期筛选：最近 %d 天（从 %s 开始）", int(days), startDate))
			}
		} else {
			// 固定日期：使用start_date和end_date字段
			if startDate, ok := sendFilter["start_date"].(string); ok && startDate != "" {
				query = query.Where("publish_date >= ?", startDate)
			}
			if endDate, ok := sendFilter["end_date"].(string); ok && endDate != "" {
				query = query.Where("publish_date <= ?", endDate+" 23:59:59")
			}
			if sendFilter["start_date"] != nil || sendFilter["end_date"] != nil {
				h.exec.AddLog(taskID, "info", fmt.Sprintf("固定日期筛选：%v 至 %v", sendFilter["start_date"], sendFilter["end_date"]))
			}
		}
	}

	// 限制数量
	limit := task.SendLimit
	if limit <= 0 {
		limit = 10
	}
	query = query.Limit(limit)

	// 获取标讯列表
	var bids []model.BidInfo
	if err := query.Find(&bids).Error; err != nil {
		h.exec.AddLog(taskID, "error", "查询标讯失败: "+err.Error())
		h.exec.FinishExecution(taskID, "failed", 0, err.Error())
		log.Status = "failed"
		log.Message = err.Error()
		log.EndedAt = time.Now()
		h.saveExecutionLog(log)
		return
	}

	if len(bids) == 0 {
		h.exec.AddLog(taskID, "info", "没有符合条件的标讯")
		h.exec.FinishExecution(taskID, "success", 0, "没有符合条件的标讯")
		log.Status = "success"
		log.Message = "没有符合条件的标讯"
		log.EndedAt = time.Now()
		h.saveExecutionLog(log)
		return
	}

	h.exec.AddLog(taskID, "info", fmt.Sprintf("找到 %d 条待发送标讯", len(bids)))

	// 调用Python Agent发送钉钉消息
	if task.DingTalkGroup == "" {
		h.exec.AddLog(taskID, "error", "未配置钉钉群")
		h.exec.FinishExecution(taskID, "failed", 0, "未配置钉钉群")
		log.Status = "failed"
		log.Message = "未配置钉钉群"
		log.EndedAt = time.Now()
		h.saveExecutionLog(log)
		return
	}

	// 准备发送数据
	bidsData := make([]map[string]interface{}, len(bids))
	for i, bid := range bids {
		bidsData[i] = map[string]interface{}{
			"id":           bid.ID,
			"title":        bid.Title,
			"tender_unit":  bid.TenderUnit,
			"crm_industry": bid.CRMIndustry,
			"budget":       bid.Budget,
			"region":       bid.Region,
			"publish_date": bid.PublishDate,
			"open_date":    bid.OpenDate,
			"link":         bid.Link,
		}
	}

	payload := map[string]interface{}{
		"webhook_url": task.DingTalkGroup,
		"bids":        bidsData,
	}

	jsonData, _ := json.Marshal(payload)

	resp, err := http.Post(h.cfg.Agent.PythonServiceURL+"/agent/dispatch/send", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		errMsg := fmt.Sprintf("连接Agent服务失败: %s (URL: %s)", err.Error(), h.cfg.Agent.PythonServiceURL)
		h.exec.AddLog(taskID, "error", errMsg)
		h.exec.FinishExecution(taskID, "failed", 0, errMsg)
		log.Status = "failed"
		log.Message = errMsg
		log.EndedAt = time.Now()
		h.saveExecutionLog(log)
		return
	}
	defer resp.Body.Close()

	// 读取响应内容用于调试
	bodyBytes, _ := io.ReadAll(resp.Body)
	bodyString := string(bodyBytes)

	var result map[string]interface{}
	json.Unmarshal(bodyBytes, &result)

	// 记录响应状态和内容
	h.exec.AddLog(taskID, "info", fmt.Sprintf("Agent响应状态: %d", resp.StatusCode))

	code, ok := result["code"].(float64)
	if !ok || code != 0 {
		errMsg := "发送失败"
		if result["message"] != nil {
			errMsg = fmt.Sprintf("Agent错误: %v", result["message"])
		} else {
			errMsg = fmt.Sprintf("Agent返回错误 (code: %v, 响应: %s)", result["code"], bodyString)
		}
		h.exec.AddLog(taskID, "error", errMsg)
		h.exec.FinishExecution(taskID, "failed", 0, errMsg)
		log.Status = "failed"
		log.Message = errMsg
		log.EndedAt = time.Now()
		h.saveExecutionLog(log)
		return
	}

	// 更新标讯状态为已发送
	bidIDs := make([]string, len(bids))
	for i, bid := range bids {
		bidIDs[i] = bid.ID
	}
	h.db.Model(&model.BidInfo{}).Where("id IN ?", bidIDs).Update("status", "sent")

	h.exec.AddLog(taskID, "info", fmt.Sprintf("成功发送 %d 条标讯到钉钉", len(bids)))
	h.exec.FinishExecution(taskID, "success", len(bids), "")

	log.Status = "success"
	log.BidsCount = len(bids)
	log.Message = fmt.Sprintf("成功发送 %d 条标讯", len(bids))
	log.EndedAt = time.Now()
	execState := h.exec.GetExecution(taskID)
	if execState != nil {
		log.Logs = toJSON(execState.Logs)
		log.Steps = toJSON(execState.Steps)
	}
	h.saveExecutionLog(log)
}

type CreateTaskRequest struct {
	Name          string                 `json:"name"`
	TaskType      string                 `json:"task_type"` // crawl/send
	Platform      string                 `json:"platform"`
	RegionCodes   []string               `json:"region_codes"`
	StartDate     string                 `json:"start_date"`
	EndDate       string                 `json:"end_date"`
	DynamicDate   bool                   `json:"dynamic_date"`   // 动态日期，每次执行时计算
	DynamicDays   int                    `json:"dynamic_days"`   // 动态日期天数（默认7天）
	CronExpr      string                 `json:"cron_expr"`
	DingTalkGroup string                 `json:"dingtalk_group"` // send任务目标群
	SendFilter    map[string]interface{} `json:"send_filter"`    // send任务筛选条件
	SendLimit     int                    `json:"send_limit"`     // send任务发送数量
	Enabled       bool                   `json:"enabled"`
}

type UpdateTaskRequest struct {
	Name          string                 `json:"name"`
	CronExpr      string                 `json:"cron_expr"`
	Enabled       bool                   `json:"enabled"`
	// 收集任务字段
	Platform      string                 `json:"platform"`
	RegionCodes   []string               `json:"region_codes"`
	StartDate     string                 `json:"start_date"`
	EndDate       string                 `json:"end_date"`
	DynamicDate   bool                   `json:"dynamic_date"`
	DynamicDays   int                    `json:"dynamic_days"`
	// 发送任务字段
	DingTalkGroup string                 `json:"dingtalk_group"`
	SendFilter    map[string]interface{} `json:"send_filter"`
	SendLimit     int                    `json:"send_limit"`
}

func toJSON(v interface{}) string {
	data, _ := json.Marshal(v)
	return string(data)
}

func getString(m map[string]interface{}, key string) string {
	if m[key] == nil {
		return ""
	}
	val, ok := m[key].(string)
	if ok {
		return val
	}
	return ""
}

// saveExecutionLog 保存执行日志到数据库
func (h *TaskHandler) saveExecutionLog(log *model.ExecutionLog) {
	execState := h.exec.GetExecution(log.TaskID)
	if execState != nil {
		log.Logs = toJSON(execState.Logs)
		log.Steps = toJSON(execState.Steps)
	}
	h.db.Save(log)
}
