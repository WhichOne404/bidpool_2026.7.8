package handler

import (
	"bytes"
	"encoding/json"
	"net/http"
	"os"
	"sync"

	"github.com/gin-gonic/gin"
)

// 配置文件路径
const configFilePath = "config/app_config.json"

// 应用配置结构
type AppConfig struct {
	Platforms      map[string]PlatformConfig `json:"platforms"`
	DingTalkGroups []DingTalkGroupConfig     `json:"dingtalk_groups"`
	LLM            LLMConfig                 `json:"llm"`
}

type PlatformConfig struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type DingTalkGroupConfig struct {
	Name       string   `json:"name"`
	WebhookURL string   `json:"webhook_url"`
	Industries []string `json:"industries"`
}

type LLMConfig struct {
	APIBase     string  `json:"api_base"`
	APIKey      string  `json:"api_key"`
	Model       string  `json:"model"`
	MaxTokens   int     `json:"max_tokens"`
	Temperature float64 `json:"temperature"`
}

// 配置管理器
type ConfigManager struct {
	mu     sync.RWMutex
	config *AppConfig
}

var configManager = &ConfigManager{
	config: &AppConfig{
		Platforms:      make(map[string]PlatformConfig),
		DingTalkGroups: []DingTalkGroupConfig{},
		LLM: LLMConfig{
			APIBase:     "https://aiapi.chaitin.net/v1",
			Model:       "gpt-4o",
			MaxTokens:   4096,
			Temperature: 0.7,
		},
	},
}

func init() {
	configManager.Load()
}

// Load 从文件加载配置
func (cm *ConfigManager) Load() error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	data, err := os.ReadFile(configFilePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	return json.Unmarshal(data, cm.config)
}

// Save 保存配置到文件
func (cm *ConfigManager) Save() error {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	data, err := json.MarshalIndent(cm.config, "", "  ")
	if err != nil {
		return err
	}

	if err := os.MkdirAll("config", 0755); err != nil {
		return err
	}

	return os.WriteFile(configFilePath, data, 0644)
}

// Get 获取配置
func (cm *ConfigManager) Get() *AppConfig {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	return cm.config
}

// Update 更新配置
func (cm *ConfigManager) Update(newConfig *AppConfig) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	cm.config = newConfig
}

// ConfigHandler 配置处理器
type ConfigHandler struct{}

func NewConfigHandler() *ConfigHandler {
	return &ConfigHandler{}
}

// GetConfig 获取配置
func (h *ConfigHandler) GetConfig(c *gin.Context) {
	config := configManager.Get()

	// 隐藏敏感信息
	safeConfig := &AppConfig{
		Platforms: make(map[string]PlatformConfig),
		DingTalkGroups: config.DingTalkGroups,
		LLM: LLMConfig{
			APIBase:     config.LLM.APIBase,
			APIKey:      maskAPIKey(config.LLM.APIKey),
			Model:       config.LLM.Model,
			MaxTokens:   config.LLM.MaxTokens,
			Temperature: config.LLM.Temperature,
		},
	}

	for k, v := range config.Platforms {
		safeConfig.Platforms[k] = PlatformConfig{
			Username: v.Username,
			Password: maskPassword(v.Password),
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": safeConfig,
	})
}

// SaveConfig 保存配置
func (h *ConfigHandler) SaveConfig(c *gin.Context) {
	var req AppConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "参数错误"})
		return
	}

	currentConfig := configManager.Get()

	// 如果密码是掩码或为空，保留原密码
	for k, v := range req.Platforms {
		if (isMasked(v.Password) || v.Password == "") && currentConfig.Platforms[k].Password != "" {
			req.Platforms[k] = PlatformConfig{
				Username: v.Username,
				Password: currentConfig.Platforms[k].Password,
			}
		}
	}

	// 如果API Key是掩码或为空，保留原Key
	if (isMasked(req.LLM.APIKey) || req.LLM.APIKey == "") && currentConfig.LLM.APIKey != "" {
		req.LLM.APIKey = currentConfig.LLM.APIKey
	}

	configManager.Update(&req)

	if err := configManager.Save(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "保存失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "message": "保存成功"})
}

// TestDingTalk 测试钉钉连接
func (h *ConfigHandler) TestDingTalk(c *gin.Context) {
	var req struct {
		WebhookURL string `json:"webhook_url"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || req.WebhookURL == "" {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "请提供Webhook URL"})
		return
	}

	// 发送测试消息到钉钉
	payload := map[string]interface{}{
		"msgtype": "text",
		"text": map[string]string{
			"content": "BidPool配置测试 - Webhook连接成功",
		},
	}

	jsonData, _ := json.Marshal(payload)
	resp, err := http.Post(req.WebhookURL, "application/json", bytes.NewReader(jsonData))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "请求失败: " + err.Error()})
		return
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if result["errcode"] != nil && result["errcode"].(float64) == 0 {
		c.JSON(http.StatusOK, gin.H{"code": 0, "message": "测试成功"})
	} else {
		errMsg := result["errmsg"].(string)
		c.JSON(http.StatusOK, gin.H{"code": -1, "message": "钉钉返回错误: " + errMsg})
	}
}

// 辅助函数
func maskAPIKey(key string) string {
	if len(key) <= 8 {
		return "****"
	}
	return key[:4] + "****" + key[len(key)-4:]
}

func maskPassword(pwd string) string {
	if len(pwd) <= 4 {
		return "****"
	}
	return pwd[:2] + "****"
}

func isMasked(s string) bool {
	// 支持 *** 和 **** 等多种掩码格式
	if s == "***" || s == "****" {
		return true
	}
	// 检查是否以 **** 结尾（如 ch****）
	return len(s) > 4 && s[len(s)-4:] == "****"
}

// GetPlatformCredentials 获取平台凭证（供其他handler使用）
func GetPlatformCredentials(platform string) map[string]string {
	config := configManager.Get()
	if cred, ok := config.Platforms[platform]; ok {
		return map[string]string{
			"username": cred.Username,
			"password": cred.Password,
		}
	}
	return map[string]string{}
}

// GetDingTalkGroups 获取钉钉群配置（供其他handler使用）
func GetDingTalkGroups() []map[string]interface{} {
	config := configManager.Get()
	groups := make([]map[string]interface{}, 0, len(config.DingTalkGroups))
	for _, g := range config.DingTalkGroups {
		groups = append(groups, map[string]interface{}{
			"name":        g.Name,
			"webhook_url": g.WebhookURL,
			"industries":  g.Industries,
		})
	}
	return groups
}