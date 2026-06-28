package scheduler

import (
	"strings"
	"sync"

	"github.com/robfig/cron/v3"
)

type Scheduler struct {
	cron     *cron.Cron
	jobs     map[string]cron.EntryID
	mu       sync.RWMutex
}

func NewScheduler() *Scheduler {
	return &Scheduler{
		cron: cron.New(cron.WithSeconds()),
		jobs: make(map[string]cron.EntryID),
	}
}

func (s *Scheduler) Start() {
	s.cron.Start()
}

func (s *Scheduler) Stop() {
	s.cron.Stop()
}

func (s *Scheduler) AddJob(id string, spec string, cmd func()) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	// 如果已存在，先移除
	if _, exists := s.jobs[id]; exists {
		s.cron.Remove(s.jobs[id])
	}

	// 处理5字段cron表达式（转换为6字段格式，添加秒字段）
	// 标准5字段: 分 时 日 月 周
	// 6字段格式: 秒 分 时 日 月 周
	fields := strings.Fields(spec)
	if len(fields) == 5 {
		// 在前面添加 "0" 表示第0秒执行
		spec = "0 " + spec
	}

	entryID, err := s.cron.AddFunc(spec, cmd)
	if err != nil {
		return err
	}

	s.jobs[id] = entryID
	return nil
}

func (s *Scheduler) RemoveJob(id string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if entryID, exists := s.jobs[id]; exists {
		s.cron.Remove(entryID)
		delete(s.jobs, id)
	}
}

func (s *Scheduler) GetActiveJobs() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	jobs := make([]string, 0, len(s.jobs))
	for id := range s.jobs {
		jobs = append(jobs, id)
	}
	return jobs
}