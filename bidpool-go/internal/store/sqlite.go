package store

import (
	"github.com/zhonghai/bidpool-go/internal/model"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

func InitDB(path string) (*gorm.DB, error) {
	db, err := gorm.Open(sqlite.Open(path), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	// 自动迁移
	if err := model.AutoMigrate(db); err != nil {
		return nil, err
	}

	return db, nil
}