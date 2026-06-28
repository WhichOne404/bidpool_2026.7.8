package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server    ServerConfig    `yaml:"server"`
	Database  DatabaseConfig  `yaml:"database"`
	Agent     AgentConfig     `yaml:"agent"`
	DingTalk  DingTalkConfig  `yaml:"dingtalk"`
	Auth      AuthConfig      `yaml:"auth"`
	Platforms PlatformsConfig `yaml:"platforms"`
}

type ServerConfig struct {
	Port string `yaml:"port"`
	Host string `yaml:"host"`
}

type DatabaseConfig struct {
	Path string `yaml:"path"`
}

type AgentConfig struct {
	PythonServiceURL string `yaml:"python_service_url"`
}

type DingTalkConfig struct {
	Groups []DingTalkGroupConfig `yaml:"groups"`
}

type DingTalkGroupConfig struct {
	Name       string   `yaml:"name"`
	WebhookURL string   `yaml:"webhook_url"`
	Industries []string `yaml:"industries"`
}

type AuthConfig struct {
	Enabled  bool   `yaml:"enabled"`
	Username string `yaml:"username"`
	Password string `yaml:"password"`
}

type PlatformsConfig struct {
	Qianlima PlatformCredentials `yaml:"qianlima"`
}

type PlatformCredentials struct {
	Username string `yaml:"username"`
	Password string `yaml:"password"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	// 设置默认值
	if cfg.Server.Port == "" {
		cfg.Server.Port = "8080"
	}
	if cfg.Database.Path == "" {
		cfg.Database.Path = "data/bidpool.db"
	}
	if cfg.Agent.PythonServiceURL == "" {
		cfg.Agent.PythonServiceURL = "http://localhost:8000"
	}

	return &cfg, nil
}