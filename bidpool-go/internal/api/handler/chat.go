package handler

import (
	"bytes"
	"encoding/json"
	"net/http"

	"github.com/zhonghai/bidpool-go/internal/config"

	"github.com/gin-gonic/gin"
)

type ChatHandler struct {
	cfg *config.Config
}

func NewChatHandler(cfg *config.Config) *ChatHandler {
	return &ChatHandler{cfg: cfg}
}

// HandleChat 处理对话请求
func (h *ChatHandler) HandleChat(c *gin.Context) {
	var req ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "参数错误"})
		return
	}

	// 调用Python Agent服务处理对话
	payload := map[string]string{"message": req.Message}
	jsonData, _ := json.Marshal(payload)

	resp, err := http.Post(h.cfg.Agent.PythonServiceURL+"/chat", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "Agent服务连接失败"})
		return
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	c.JSON(http.StatusOK, result)
}

type ChatRequest struct {
	Message string `json:"message"`
}