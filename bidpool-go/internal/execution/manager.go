package execution

import (
	"sync"
	"time"

	"github.com/google/uuid"
)

// 任务执行状态管理
type Manager struct {
	mu         sync.RWMutex
	executions map[string]*TaskExecution
}

type TaskExecution struct {
	TaskID      string          `json:"task_id"`
	ExecutionID string          `json:"execution_id"`
	Status      string          `json:"status"` // running/success/failed
	Progress    int             `json:"progress"` // 0-100
	CurrentStep string          `json:"current_step"`
	Steps       []ExecutionStep `json:"steps"`
	StartTime   time.Time       `json:"start_time"`
	EndTime     time.Time       `json:"end_time"`
	BidsCount   int             `json:"bids_count"`
	Error       string          `json:"error"`
	Logs        []ExecutionLog  `json:"logs"`
}

type ExecutionStep struct {
	Name      string    `json:"name"`
	Status    string    `json:"status"` // pending/running/success/failed
	Message   string    `json:"message"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time"`
}

type ExecutionLog struct {
	Time    time.Time `json:"time"`
	Level   string    `json:"level"` // info/warning/error
	Message string    `json:"message"`
}

var defaultManager = &Manager{
	executions: make(map[string]*TaskExecution),
}

// GetManager 获取全局执行管理器
func GetManager() *Manager {
	return defaultManager
}

// StartExecution 创建新的执行记录
func (m *Manager) StartExecution(taskID string) *TaskExecution {
	execution := &TaskExecution{
		TaskID:      taskID,
		ExecutionID: uuid.New().String(),
		Status:      "running",
		Progress:    0,
		StartTime:   time.Now(),
		Steps: []ExecutionStep{
			{Name: "初始化", Status: "running"},
			{Name: "登录平台", Status: "pending"},
			{Name: "搜索标讯", Status: "pending"},
			{Name: "数据处理", Status: "pending"},
		},
		Logs: []ExecutionLog{},
	}

	m.mu.Lock()
	m.executions[taskID] = execution
	m.mu.Unlock()

	return execution
}

// UpdateStep 更新步骤状态
func (m *Manager) UpdateStep(taskID string, stepIndex int, status string, message string) {
	m.mu.Lock()
	if execution, exists := m.executions[taskID]; exists {
		if stepIndex < len(execution.Steps) {
			execution.Steps[stepIndex].Status = status
			execution.Steps[stepIndex].Message = message
			execution.Steps[stepIndex].StartTime = time.Now()
			if status == "success" || status == "failed" {
				execution.Steps[stepIndex].EndTime = time.Now()
			}
		}
		execution.Progress = (stepIndex + 1) * 25
		if status == "success" {
			execution.CurrentStep = execution.Steps[stepIndex].Name + " 完成"
		} else if status == "running" {
			execution.CurrentStep = execution.Steps[stepIndex].Name + " 进行中..."
		}
	}
	m.mu.Unlock()
}

// AddLog 添加执行日志
func (m *Manager) AddLog(taskID string, level string, message string) {
	m.mu.Lock()
	if execution, exists := m.executions[taskID]; exists {
		execution.Logs = append(execution.Logs, ExecutionLog{
			Time:    time.Now(),
			Level:   level,
			Message: message,
		})
	}
	m.mu.Unlock()
}

// FinishExecution 完成执行
func (m *Manager) FinishExecution(taskID string, status string, bidsCount int, errorMsg string) {
	m.mu.Lock()
	if execution, exists := m.executions[taskID]; exists {
		execution.Status = status
		execution.EndTime = time.Now()
		execution.BidsCount = bidsCount
		execution.Progress = 100
		if errorMsg != "" {
			execution.Error = errorMsg
		}
		if status == "success" {
			execution.CurrentStep = "执行完成"
		} else {
			execution.CurrentStep = "执行失败: " + errorMsg
		}
	}
	m.mu.Unlock()
}

// GetExecution 获取执行状态
func (m *Manager) GetExecution(taskID string) *TaskExecution {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.executions[taskID]
}