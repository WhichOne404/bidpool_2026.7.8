<template>
  <div class="lb-page tasks-page">
    <!-- 页面标题 -->
    <h1 class="lb-page-title">
      任务管理
      <small>创建和管理标讯收集与分发任务</small>
    </h1>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="lb-widget stat-widget">
        <div class="lb-stat-card">
          <div class="lb-stat-icon lb-stat-icon-info">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </div>
          <div class="lb-stat-content">
            <div class="lb-stat-value">{{ tasks.length }}</div>
            <div class="lb-stat-label">全部任务</div>
          </div>
        </div>
      </div>
      <div class="lb-widget stat-widget">
        <div class="lb-stat-card">
          <div class="lb-stat-icon lb-stat-icon-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="lb-stat-content">
            <div class="lb-stat-value">{{ scheduledCount }}</div>
            <div class="lb-stat-label">定时任务</div>
          </div>
        </div>
      </div>
      <div class="lb-widget stat-widget">
        <div class="lb-stat-card">
          <div class="lb-stat-icon lb-stat-icon-success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </div>
          <div class="lb-stat-content">
            <div class="lb-stat-value">{{ manualCount }}</div>
            <div class="lb-stat-label">手动任务</div>
          </div>
        </div>
      </div>
      <div class="lb-widget stat-widget">
        <div class="lb-stat-card">
          <div class="lb-stat-icon lb-stat-icon-warning">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="lb-stat-content">
            <div class="lb-stat-value">{{ activeCount }}</div>
            <div class="lb-stat-label">运行中</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 筛选和操作栏 -->
    <div class="filter-toolbar">
      <div class="filter-tabs">
        <button :class="['lb-btn', 'lb-btn-ghost', { active: filterType === 'all' }]" @click="filterType = 'all'">全部</button>
        <button :class="['lb-btn', 'lb-btn-ghost', { active: filterType === 'scheduled' }]" @click="filterType = 'scheduled'">定时任务</button>
        <button :class="['lb-btn', 'lb-btn-ghost', { active: filterType === 'manual' }]" @click="filterType = 'manual'">手动任务</button>
        <button :class="['lb-btn', 'lb-btn-ghost', { active: filterType === 'crawl' }]" @click="filterType = 'crawl'">收集</button>
        <button :class="['lb-btn', 'lb-btn-ghost', { active: filterType === 'send' }]" @click="filterType = 'send'">发送</button>
      </div>
      <div class="filter-actions">
        <button v-if="selectedTasks.length > 0" class="lb-btn lb-btn-danger" @click="batchDeleteTasks">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          删除 ({{ selectedTasks.length }})
        </button>
        <select v-model="filterStatus" class="lb-select status-select">
          <option value="">全部状态</option>
          <option value="running">运行中</option>
          <option value="success">已完成</option>
          <option value="failed">失败</option>
          <option value="none">未执行</option>
        </select>
        <button class="lb-btn lb-btn-primary" @click="showCreateDialog">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          创建任务
        </button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="lb-widget tasks-widget">
      <table class="lb-table tasks-table">
        <thead>
          <tr>
            <th class="col-check">
              <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" class="checkbox" />
            </th>
            <th class="col-status">状态</th>
            <th class="col-name">任务名称</th>
            <th class="col-type">类型</th>
            <th class="col-config">配置信息</th>
            <th class="col-schedule">定时</th>
            <th class="col-progress">进度</th>
            <th class="col-last">最后执行</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody v-if="loading">
          <tr>
            <td colspan="9" class="loading-cell">
              <div class="loading-spinner">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="32" height="32">
                  <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="20"/>
                </svg>
                <span>加载中...</span>
              </div>
            </td>
          </tr>
        </tbody>
        <tbody v-else-if="!filteredTasks.length">
          <tr>
            <td colspan="9" class="empty-cell">
              <div class="empty-content">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="56" height="56">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                  <line x1="16" y1="2" x2="16" y2="6"/>
                  <line x1="8" y1="2" x2="8" y2="6"/>
                  <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                <h3>暂无任务</h3>
                <p>点击右上角"创建任务"开始</p>
              </div>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr v-for="task in filteredTasks" :key="task.id" class="task-row">
            <td class="col-check" @click.stop>
              <input type="checkbox" :checked="selectedTasks.includes(task.id)" @change="toggleSelect(task.id)" class="checkbox" />
            </td>
            <td class="col-status" @click="showDetail(task)">
              <div class="status-indicator">
                <span :class="['status-dot', task.execution_status || 'none']"></span>
                <span class="status-text">{{ getStatusText(task.execution_status) }}</span>
              </div>
            </td>
            <td class="col-name" @click="showDetail(task)">
              <div class="task-name-cell">
                <span class="task-name">{{ task.name }}</span>
                <span class="task-id">ID: {{ task.id.substring(0, 8) }}</span>
              </div>
            </td>
            <td class="col-type" @click="showDetail(task)">
              <span :class="['lb-badge', task.task_type === 'send' ? 'lb-badge-info' : 'lb-badge-success']">
                {{ task.task_type === 'send' ? '发送' : '收集' }}
              </span>
            </td>
            <td class="col-config">
              <div class="config-info" v-if="task.task_type === 'send'">
                <span class="config-item">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                    <line x1="22" y1="2" x2="11" y2="13"/>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                  </svg>
                  {{ getGroupName(task.dingtalk_group) }}
                </span>
                <span class="config-item" v-if="task.send_limit">限{{ task.send_limit }}条</span>
              </div>
              <div class="config-info" v-else>
                <span class="config-item">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                  {{ task.platform || '千里马' }}
                </span>
                <span class="config-item" v-if="task.region_names">{{ task.region_names }}</span>
              </div>
            </td>
            <td class="col-schedule">
              <div class="schedule-cell" v-if="task.cron_expr">
                <code class="cron-expr">{{ task.cron_expr }}</code>
                <span class="cron-desc">{{ getCronDesc(task.cron_expr) }}</span>
              </div>
              <div class="manual-cell" v-else>
                <span class="manual-badge">手动</span>
                <span class="manual-hint">点击执行</span>
              </div>
            </td>
            <td class="col-progress">
              <div class="progress-cell">
                <div class="lb-progress">
                  <div :class="['lb-progress-bar', getProgressClass(task)]" :style="{ width: getProgressPercent(task) + '%' }"></div>
                </div>
                <span class="progress-text">{{ getProgressText(task) }}</span>
              </div>
            </td>
            <td class="col-last">
              <div class="last-exec-cell" v-if="task.last_execution">
                <span class="last-time">{{ formatTime(task.last_execution.started_at) }}</span>
                <span class="last-result" :class="task.last_execution.status">
                  {{ task.last_execution.bids_count || 0 }}条
                </span>
              </div>
              <span v-else class="no-exec">-</span>
            </td>
            <td class="col-actions" @click.stop>
              <div class="action-cell">
                <el-switch v-model="task.enabled" size="small" @change="toggleTask(task)" />
                <button class="lb-btn lb-btn-success btn-sm" @click="runTask(task.id)" title="执行">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                  </svg>
                </button>
                <button class="lb-btn lb-btn-ghost btn-sm" @click="showDetail(task)" title="详情">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
                <button class="lb-btn lb-btn-danger btn-sm" @click="deleteTask(task.id)" title="删除">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建对话框 -->
    <el-dialog v-model="dialogVisible" title="" width="560px" class="lb-dialog create-dialog">
      <template #header>
        <div class="dialog-header">
          <h2>创建任务</h2>
          <p>配置自动化标讯任务</p>
        </div>
      </template>

      <div class="form-section">
        <!-- 任务模式选择 -->
        <div class="form-group">
          <label class="lb-label">任务模式</label>
          <div class="mode-selector">
            <div :class="['mode-option', { active: form.task_mode === 'scheduled' }]" @click="form.task_mode = 'scheduled'">
              <div class="mode-icon scheduled">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
              </div>
              <div class="mode-info">
                <span>定时任务</span>
                <small>按设定时间自动执行</small>
              </div>
            </div>
            <div :class="['mode-option', { active: form.task_mode === 'manual' }]" @click="form.task_mode = 'manual'">
              <div class="mode-icon manual">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
              </div>
              <div class="mode-info">
                <span>手动任务</span>
                <small>仅手动点击执行</small>
              </div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="lb-label">任务类型</label>
          <div class="type-selector">
            <div :class="['type-option', { active: form.task_type === 'crawl' }]" @click="form.task_type = 'crawl'">
              <div class="type-icon crawl">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </div>
              <span>收集标讯</span>
              <small>从平台抓取标讯数据</small>
            </div>
            <div :class="['type-option', { active: form.task_type === 'send' }]" @click="form.task_type = 'send'">
              <div class="type-icon send">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </div>
              <span>发送标讯</span>
              <small>定时推送到钉钉群</small>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="lb-label">任务名称</label>
          <input type="text" v-model="form.name" placeholder="输入任务名称" class="lb-input" />
        </div>

        <!-- 收集任务配置 -->
        <template v-if="form.task_type === 'crawl'">
          <div class="form-group">
            <label class="lb-label">数据平台</label>
            <select v-model="form.platform" class="lb-select">
              <option value="qianlima">千里马</option>
            </select>
          </div>
          <div class="form-group">
            <label class="lb-label">地区选择</label>
            <div class="region-tags">
              <span v-for="r in regions" :key="r.value"
                    :class="['tag', { active: form.region_codes.includes(r.value) }]"
                    @click="toggleRegion(r.value)">
                {{ r.label }}
              </span>
            </div>
          </div>

          <!-- 日期范围 - 根据任务模式显示不同选项 -->
          <div class="form-group">
            <label class="lb-label">日期范围</label>
            <!-- 定时任务：显示动态日期选项 -->
            <template v-if="form.task_mode === 'scheduled'">
              <div class="date-range-options">
                <span :class="['tag', { active: form.dynamic_days === 7 }]" @click="form.dynamic_days = 7">
                  近7天（推荐）
                </span>
                <span :class="['tag', { active: form.dynamic_days === 1 }]" @click="form.dynamic_days = 1">
                  近1天
                </span>
                <span :class="['tag', { active: form.dynamic_days === 3 }]" @click="form.dynamic_days = 3">
                  近3天
                </span>
                <span :class="['tag', { active: form.dynamic_days === 30 }]" @click="form.dynamic_days = 30">
                  近30天
                </span>
              </div>
              <small class="form-hint">每次执行时自动计算最近 {{ form.dynamic_days }} 天的日期范围</small>
            </template>
            <!-- 手动任务：显示固定日期输入 -->
            <template v-else>
              <div class="form-row">
                <div class="form-group">
                  <label class="lb-label">开始日期</label>
                  <input type="date" v-model="form.start_date" class="lb-input" />
                </div>
                <div class="form-group">
                  <label class="lb-label">结束日期</label>
                  <input type="date" v-model="form.end_date" class="lb-input" />
                </div>
              </div>
              <small class="form-hint">手动任务使用固定日期范围</small>
            </template>
          </div>
        </template>

        <!-- 发送任务配置 -->
        <template v-if="form.task_type === 'send'">
          <div class="form-group">
            <label class="lb-label">目标钉钉群</label>
            <select v-model="form.dingtalk_group" class="lb-select">
              <option value="">请选择</option>
              <option v-for="g in dingtalkGroups" :key="g.webhook_url" :value="g.webhook_url">{{ g.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="lb-label">筛选条件</label>
            <div class="multi-select-section">
              <label class="multi-select-label">地区筛选</label>
              <div class="region-tags">
                <span v-for="r in ['重庆','四川','云南','贵州','西藏']" :key="r"
                      :class="['tag', { active: form.send_filter.regions && form.send_filter.regions.includes(r) }]"
                      @click="toggleSendRegion(r)">
                  {{ r }}
                </span>
                <span :class="['tag', { active: !form.send_filter.regions || form.send_filter.regions.length === 0 }]"
                      @click="form.send_filter.regions = []">
                  全部
                </span>
              </div>
            </div>
            <div class="multi-select-section">
              <label class="multi-select-label">行业筛选</label>
              <div class="region-tags">
                <span v-for="i in ['政府','医疗','金融','教育','通信','企业','其他']" :key="i"
                      :class="['tag', { active: form.send_filter.industries && form.send_filter.industries.includes(i) }]"
                      @click="toggleSendIndustry(i)">
                  {{ i }}
                </span>
                <span :class="['tag', { active: !form.send_filter.industries || form.send_filter.industries.length === 0 }]"
                      @click="form.send_filter.industries = []">
                  全部
                </span>
              </div>
            </div>
          </div>

          <!-- 发送任务日期范围选择 -->
          <div class="form-group">
            <label class="lb-label">发布时间范围</label>
            <!-- 定时任务：动态日期 -->
            <template v-if="form.task_mode === 'scheduled'">
              <div class="date-range-options">
                <span :class="['tag', { active: form.send_filter.days === 7 }]" @click="form.send_filter.days = 7">
                  近7天（推荐）
                </span>
                <span :class="['tag', { active: form.send_filter.days === 1 }]" @click="form.send_filter.days = 1">
                  近1天
                </span>
                <span :class="['tag', { active: form.send_filter.days === 3 }]" @click="form.send_filter.days = 3">
                  近3天
                </span>
                <span :class="['tag', { active: form.send_filter.days === 30 }]" @click="form.send_filter.days = 30">
                  近30天
                </span>
              </div>
              <small class="form-hint">筛选最近 {{ form.send_filter.days }} 天发布的标讯</small>
            </template>
            <!-- 手动任务：固定日期 -->
            <template v-else>
              <div class="form-row">
                <div class="form-group">
                  <label class="lb-label">发布开始日期</label>
                  <input type="date" v-model="form.send_filter.start_date" class="lb-input" />
                </div>
                <div class="form-group">
                  <label class="lb-label">发布结束日期</label>
                  <input type="date" v-model="form.send_filter.end_date" class="lb-input" />
                </div>
              </div>
              <small class="form-hint">手动任务使用固定日期范围筛选标讯</small>
            </template>
          </div>

          <div class="form-group">
            <label class="lb-label">发送数量</label>
            <input type="number" v-model="form.send_limit" min="1" max="20" class="lb-input" />
            <small class="form-hint">每次最多发送的标讯条数</small>
          </div>
        </template>

        <!-- 定时设置 - 仅定时任务显示 -->
        <template v-if="form.task_mode === 'scheduled'">
          <div class="schedule-section">
            <div class="schedule-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <span>定时设置</span>
            </div>
            <div class="form-group">
              <label class="lb-label">执行频率</label>
              <div class="frequency-selector">
                <select v-model="schedule.frequency" class="lb-select">
                  <option v-for="opt in frequencyOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group" v-if="schedule.frequency !== 'hourly'">
              <label class="lb-label">执行时间</label>
              <div class="time-selector">
                <select v-model="schedule.hour" class="lb-select small">
                  <option v-for="h in 24" :key="h-1" :value="h-1">{{ String(h-1).padStart(2, '0') }}</option>
                </select>
                <span class="time-separator">:</span>
                <select v-model="schedule.minute" class="lb-select small">
                  <option v-for="m in 60" :key="m-1" :value="m-1">{{ String(m-1).padStart(2, '0') }}</option>
                </select>
              </div>
            </div>

            <div class="form-group" v-if="schedule.frequency === 'weekly'">
              <label class="lb-label">执行日期</label>
              <div class="weekday-selector">
                <span v-for="day in weekDays" :key="day.value"
                      :class="['weekday-btn', { active: schedule.dayOfWeek === day.value }]"
                      @click="schedule.dayOfWeek = day.value">
                  {{ day.label }}
                </span>
              </div>
            </div>
          </div>
        </template>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.enabled" />
            <span>立即启用</span>
          </label>
        </div>
      </div>

      <template #footer>
        <button class="lb-btn lb-btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="lb-btn lb-btn-primary" @click="submitTask">创建任务</button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="" width="560px" class="lb-dialog edit-dialog">
      <template #header>
        <div class="dialog-header">
          <h2>编辑任务配置</h2>
          <p>修改任务 {{ editForm.name }}</p>
        </div>
      </template>

      <div class="form-section">
        <div class="form-group">
          <label class="lb-label">任务名称</label>
          <input type="text" v-model="editForm.name" placeholder="输入任务名称" class="lb-input" />
        </div>

        <!-- 收集任务编辑 -->
        <template v-if="editForm.task_type === 'crawl' || !editForm.task_type">
          <div class="form-group">
            <label class="lb-label">数据平台</label>
            <select v-model="editForm.platform" class="lb-select">
              <option value="qianlima">千里马</option>
            </select>
          </div>
          <div class="form-group">
            <label class="lb-label">地区选择</label>
            <div class="region-tags">
              <span v-for="r in regions" :key="r.value"
                    :class="['tag', { active: editForm.region_codes.includes(r.value) }]"
                    @click="toggleEditRegion(r.value)">
                {{ r.label }}
              </span>
            </div>
          </div>

          <!-- 日期范围 -->
          <div class="form-group">
            <label class="lb-label">日期范围</label>
            <template v-if="editForm.cron_expr && editForm.cron_expr !== ''">
              <!-- 定时任务：动态日期 -->
              <div class="date-range-options">
                <span :class="['tag', { active: editForm.dynamic_days === 7 }]" @click="editForm.dynamic_days = 7">
                  近7天（推荐）
                </span>
                <span :class="['tag', { active: editForm.dynamic_days === 1 }]" @click="editForm.dynamic_days = 1">
                  近1天
                </span>
                <span :class="['tag', { active: editForm.dynamic_days === 3 }]" @click="editForm.dynamic_days = 3">
                  近3天
                </span>
                <span :class="['tag', { active: editForm.dynamic_days === 30 }]" @click="editForm.dynamic_days = 30">
                  近30天
                </span>
              </div>
              <small class="form-hint">每次执行时自动计算最近 {{ editForm.dynamic_days }} 天的日期范围</small>
            </template>
            <template v-else>
              <!-- 手动任务：固定日期 -->
              <div class="form-row">
                <div class="form-group">
                  <label class="lb-label">开始日期</label>
                  <input type="date" v-model="editForm.start_date" class="lb-input" />
                </div>
                <div class="form-group">
                  <label class="lb-label">结束日期</label>
                  <input type="date" v-model="editForm.end_date" class="lb-input" />
                </div>
              </div>
              <small class="form-hint">手动任务使用固定日期范围</small>
            </template>
          </div>

          <!-- 定时设置 -->
          <template v-if="editForm.cron_expr && editForm.cron_expr !== ''">
            <div class="schedule-section">
              <div class="schedule-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <span>定时设置</span>
              </div>
              <div class="form-group">
                <label class="lb-label">执行频率</label>
                <div class="frequency-selector">
                  <select v-model="editSchedule.frequency" class="lb-select">
                    <option v-for="opt in frequencyOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="form-group" v-if="editSchedule.frequency !== 'hourly'">
                <label class="lb-label">执行时间</label>
                <div class="time-selector">
                  <select v-model="editSchedule.hour" class="lb-select small">
                    <option v-for="h in 24" :key="h-1" :value="h-1">{{ String(h-1).padStart(2, '0') }}</option>
                  </select>
                  <span class="time-separator">:</span>
                  <select v-model="editSchedule.minute" class="lb-select small">
                    <option v-for="m in 60" :key="m-1" :value="m-1">{{ String(m-1).padStart(2, '0') }}</option>
                  </select>
                </div>
              </div>

              <div class="form-group" v-if="editSchedule.frequency === 'weekly'">
                <label class="lb-label">执行日期</label>
                <div class="weekday-selector">
                  <span v-for="day in weekDays" :key="day.value"
                        :class="['weekday-btn', { active: editSchedule.dayOfWeek === day.value }]"
                        @click="editSchedule.dayOfWeek = day.value">
                    {{ day.label }}
                  </span>
                </div>
              </div>
            </div>
          </template>
        </template>

        <!-- 发送任务编辑 -->
        <template v-if="editForm.task_type === 'send'">
          <div class="form-group">
            <label class="lb-label">目标钉钉群</label>
            <select v-model="editForm.dingtalk_group" class="lb-select">
              <option value="">请选择</option>
              <option v-for="g in dingtalkGroups" :key="g.webhook_url" :value="g.webhook_url">{{ g.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="lb-label">筛选条件</label>
            <div class="multi-select-section">
              <label class="multi-select-label">地区筛选</label>
              <div class="region-tags">
                <span v-for="r in ['重庆','四川','云南','贵州','西藏']" :key="r"
                      :class="['tag', { active: editForm.send_filter.regions && editForm.send_filter.regions.includes(r) }]"
                      @click="toggleEditSendRegion(r)">
                  {{ r }}
                </span>
                <span :class="['tag', { active: !editForm.send_filter.regions || editForm.send_filter.regions.length === 0 }]"
                      @click="editForm.send_filter.regions = []">
                  全部
                </span>
              </div>
            </div>
            <div class="multi-select-section">
              <label class="multi-select-label">行业筛选</label>
              <div class="region-tags">
                <span v-for="i in ['政府','医疗','金融','教育','通信','企业','其他']" :key="i"
                      :class="['tag', { active: editForm.send_filter.industries && editForm.send_filter.industries.includes(i) }]"
                      @click="toggleEditSendIndustry(i)">
                  {{ i }}
                </span>
                <span :class="['tag', { active: !editForm.send_filter.industries || editForm.send_filter.industries.length === 0 }]"
                      @click="editForm.send_filter.industries = []">
                  全部
                </span>
              </div>
            </div>
          </div>

          <!-- 发送任务日期范围编辑 -->
          <div class="form-group">
            <label class="lb-label">发布时间范围</label>
            <template v-if="editForm.cron_expr && editForm.cron_expr !== ''">
              <!-- 定时任务：动态日期 -->
              <div class="date-range-options">
                <span :class="['tag', { active: editForm.send_filter.days === 7 }]" @click="editForm.send_filter.days = 7">
                  近7天（推荐）
                </span>
                <span :class="['tag', { active: editForm.send_filter.days === 1 }]" @click="editForm.send_filter.days = 1">
                  近1天
                </span>
                <span :class="['tag', { active: editForm.send_filter.days === 3 }]" @click="editForm.send_filter.days = 3">
                  近3天
                </span>
                <span :class="['tag', { active: editForm.send_filter.days === 30 }]" @click="editForm.send_filter.days = 30">
                  近30天
                </span>
              </div>
              <small class="form-hint">筛选最近 {{ editForm.send_filter.days }} 天发布的标讯</small>
            </template>
            <template v-else>
              <!-- 手动任务：固定日期 -->
              <div class="form-row">
                <div class="form-group">
                  <label class="lb-label">发布开始日期</label>
                  <input type="date" v-model="editForm.send_filter.start_date" class="lb-input" />
                </div>
                <div class="form-group">
                  <label class="lb-label">发布结束日期</label>
                  <input type="date" v-model="editForm.send_filter.end_date" class="lb-input" />
                </div>
              </div>
              <small class="form-hint">手动任务使用固定日期范围筛选标讯</small>
            </template>
          </div>

          <div class="form-group">
            <label class="lb-label">发送数量</label>
            <input type="number" v-model="editForm.send_limit" min="1" max="20" class="lb-input" />
            <small class="form-hint">每次最多发送的标讯条数</small>
          </div>

          <!-- 定时设置 -->
          <template v-if="editForm.cron_expr && editForm.cron_expr !== ''">
            <div class="schedule-section">
              <div class="schedule-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <span>定时设置</span>
              </div>
              <div class="form-group">
                <label class="lb-label">执行频率</label>
                <div class="frequency-selector">
                  <select v-model="editSchedule.frequency" class="lb-select">
                    <option v-for="opt in frequencyOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="form-group" v-if="editSchedule.frequency !== 'hourly'">
                <label class="lb-label">执行时间</label>
                <div class="time-selector">
                  <select v-model="editSchedule.hour" class="lb-select small">
                    <option v-for="h in 24" :key="h-1" :value="h-1">{{ String(h-1).padStart(2, '0') }}</option>
                  </select>
                  <span class="time-separator">:</span>
                  <select v-model="editSchedule.minute" class="lb-select small">
                    <option v-for="m in 60" :key="m-1" :value="m-1">{{ String(m-1).padStart(2, '0') }}</option>
                  </select>
                </div>
              </div>

              <div class="form-group" v-if="editSchedule.frequency === 'weekly'">
                <label class="lb-label">执行日期</label>
                <div class="weekday-selector">
                  <span v-for="day in weekDays" :key="day.value"
                        :class="['weekday-btn', { active: editSchedule.dayOfWeek === day.value }]"
                        @click="editSchedule.dayOfWeek = day.value">
                    {{ day.label }}
                  </span>
                </div>
              </div>
            </div>
          </template>
        </template>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="editForm.enabled" />
            <span>启用任务</span>
          </label>
        </div>
      </div>

      <template #footer>
        <button class="lb-btn lb-btn-ghost" @click="editDialogVisible = false">取消</button>
        <button class="lb-btn lb-btn-primary" @click="updateTask">保存修改</button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="" width="900px" class="lb-dialog detail-dialog">
      <template #header>
        <div class="detail-header">
          <div class="detail-title-row">
            <h2>{{ currentTask?.name }}</h2>
            <span :class="['lb-badge', currentTask?.task_type === 'send' ? 'lb-badge-info' : 'lb-badge-success']">
              {{ currentTask?.task_type === 'send' ? '发送任务' : '收集任务' }}
            </span>
          </div>
          <div class="detail-header-actions">
            <button class="lb-btn lb-btn-ghost btn-sm" @click="showEditDialog">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
              编辑配置
            </button>
          </div>
        </div>
      </template>

      <div class="detail-body" v-if="currentTask">
        <!-- 执行统计卡片 -->
        <div class="exec-stats-grid">
          <div class="lb-widget exec-stat-card">
            <div class="exec-stat-icon" :class="currentTask.execution_status || 'none'">
              <svg v-if="currentTask.execution_status === 'running'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <svg v-else-if="currentTask.execution_status === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <svg v-else-if="currentTask.execution_status === 'failed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
            <div class="exec-stat-content">
              <div class="exec-stat-label">执行状态</div>
              <div class="exec-stat-value">{{ getStatusText(currentTask.execution_status) }}</div>
            </div>
          </div>

          <div class="lb-widget exec-stat-card">
            <div class="exec-stat-icon login" :class="currentTask.last_execution?.login_status || 'unknown'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="exec-stat-content">
              <div class="exec-stat-label">登录状态</div>
              <div class="exec-stat-value">{{ getLoginStatusText(currentTask.last_execution?.login_status) }}</div>
            </div>
          </div>

          <div class="lb-widget exec-stat-card">
            <div class="exec-stat-icon discover">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </div>
            <div class="exec-stat-content">
              <div class="exec-stat-label">发现标讯</div>
              <div class="exec-stat-value highlight">{{ currentTask.last_execution?.discovered_count || 0 }}<span class="unit">条</span></div>
            </div>
          </div>

          <div class="lb-widget exec-stat-card">
            <div class="exec-stat-icon store">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/>
                <polyline points="7 3 7 8 15 8"/>
              </svg>
            </div>
            <div class="exec-stat-content">
              <div class="exec-stat-label">存储标讯</div>
              <div class="exec-stat-value success">{{ currentTask.last_execution?.stored_count || 0 }}<span class="unit">条</span></div>
            </div>
          </div>

          <div class="lb-widget exec-stat-card">
            <div class="exec-stat-icon duplicate">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </div>
            <div class="exec-stat-content">
              <div class="exec-stat-label">去重过滤</div>
              <div class="exec-stat-value">{{ currentTask.last_execution?.duplicate_count || 0 }}<span class="unit">条</span></div>
            </div>
          </div>

          <div class="lb-widget exec-stat-card">
            <div class="exec-stat-icon time">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="exec-stat-content">
              <div class="exec-stat-label">执行耗时</div>
              <div class="exec-stat-value">{{ currentTask.last_execution?.duration || 0 }}<span class="unit">秒</span></div>
            </div>
          </div>
        </div>

        <!-- 执行进度 -->
        <div class="lb-widget exec-progress-section" v-if="currentTask.execution_status === 'running'">
          <div class="section-title">
            <h4>执行进度</h4>
            <span class="progress-percent">{{ currentTask.progress || 0 }}%</span>
          </div>
          <div class="progress-bar-wrapper">
            <div class="lb-progress">
              <div class="lb-progress-bar lb-progress-info" :style="{ width: (currentTask.progress || 0) + '%' }"></div>
            </div>
          </div>
          <div class="progress-steps">
            <div :class="['progress-step', { active: currentTask.progress >= 0, done: currentTask.progress >= 25 }]">
              <div class="step-indicator">
                <span class="step-num">1</span>
              </div>
              <div class="step-info">
                <span class="step-title">检查登录</span>
                <span class="step-desc">验证账号状态</span>
              </div>
            </div>
            <div :class="['progress-step', { active: currentTask.progress >= 25, done: currentTask.progress >= 50 }]">
              <div class="step-indicator">
                <span class="step-num">2</span>
              </div>
              <div class="step-info">
                <span class="step-title">获取数据</span>
                <span class="step-desc">从平台抓取标讯</span>
              </div>
            </div>
            <div :class="['progress-step', { active: currentTask.progress >= 50, done: currentTask.progress >= 75 }]">
              <div class="step-indicator">
                <span class="step-num">3</span>
              </div>
              <div class="step-info">
                <span class="step-title">数据处理</span>
                <span class="step-desc">去重、格式化、存储</span>
              </div>
            </div>
            <div :class="['progress-step', { active: currentTask.progress >= 75, done: currentTask.progress >= 100 }]">
              <div class="step-indicator">
                <span class="step-num">4</span>
              </div>
              <div class="step-info">
                <span class="step-title">完成</span>
                <span class="step-desc">任务执行完毕</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 运行日志 -->
        <div class="lb-widget exec-log-section">
          <div class="section-title">
            <h4>运行日志</h4>
            <span class="log-count-badge" v-if="currentTask.logs">{{ parseLogs(currentTask.logs).length }} 条</span>
          </div>
          <div class="log-viewer">
            <div v-if="currentTask.logs && parseLogs(currentTask.logs).length" class="log-list">
              <div v-for="(log, i) in parseLogs(currentTask.logs)" :key="i" :class="['log-entry', log.level]">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-level">{{ log.level.toUpperCase() }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
            <div v-else class="log-empty">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              <p>暂无运行日志</p>
              <span>执行任务后日志将显示在这里</span>
            </div>
          </div>
        </div>

        <!-- 任务配置 -->
        <div class="lb-widget exec-config-section">
          <h4>任务配置</h4>
          <div class="config-details">
            <div class="config-row">
              <span class="config-key">任务类型</span>
              <span class="config-val">{{ currentTask.task_type === 'send' ? '发送任务' : '收集任务' }}</span>
            </div>
            <div class="config-row" v-if="currentTask.task_type !== 'send'">
              <span class="config-key">数据平台</span>
              <span class="config-val">{{ currentTask.platform || '千里马' }}</span>
            </div>
            <div class="config-row" v-if="currentTask.dingtalk_group">
              <span class="config-key">目标钉钉群</span>
              <span class="config-val">{{ getGroupName(currentTask.dingtalk_group) }}</span>
            </div>
            <div class="config-row" v-if="currentTask.cron_expr">
              <span class="config-key">定时表达式</span>
              <span class="config-val"><code>{{ currentTask.cron_expr }}</code></span>
            </div>
            <div class="config-row">
              <span class="config-key">启用状态</span>
              <span :class="['config-val', currentTask.enabled ? 'enabled' : 'disabled']">
                {{ currentTask.enabled ? '已启用' : '已禁用' }}
              </span>
            </div>
            <div class="config-row" v-if="currentTask.created_at">
              <span class="config-key">创建时间</span>
              <span class="config-val">{{ formatTimeFull(currentTask.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const tasks = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const detailVisible = ref(false)
const currentTask = ref(null)
const refreshTimer = ref(null)
const dingtalkGroups = ref([])
const filterType = ref('all')
const filterStatus = ref('')
const selectedTasks = ref([])

const regions = [
  { label: '重庆', value: '500000' },
  { label: '四川', value: '510000' },
  { label: '云南', value: '530000' },
  { label: '贵州', value: '520000' },
  { label: '西藏', value: '540000' }
]

const cronPresets = [
  { label: '每天9点', value: '0 9 * * *' },
  { label: '每周一8点', value: '0 8 * * 1' },
  { label: '每周五18点', value: '0 18 * * 5' },
  { label: '每天12点', value: '0 12 * * *' }
]

const form = reactive({
  name: '',
  task_mode: 'scheduled',  // scheduled 或 manual
  task_type: 'crawl',
  platform: 'qianlima',
  region_codes: ['500000'],
  start_date: '',
  end_date: '',
  dynamic_days: 7,  // 动态日期天数（定时任务使用）
  cron_expr: '',
  enabled: true,
  dingtalk_group: '',
  send_filter: {
    regions: [],  // 多选地区
    industries: [],  // 多选行业
    days: 7,  // 定时任务使用
    start_date: '',  // 手动任务使用
    end_date: ''  // 手动任务使用
  },
  send_limit: 5
})

const schedule = reactive({
  frequency: 'daily',  // hourly, daily, weekly, monthly
  hour: 9,
  minute: 0,
  dayOfWeek: 1  // 1-7 周一到周日
})

// 编辑表单
const editForm = reactive({
  id: '',
  name: '',
  task_type: 'crawl',
  platform: 'qianlima',
  region_codes: [],
  start_date: '',
  end_date: '',
  dynamic_days: 7,
  cron_expr: '',
  enabled: true,
  dingtalk_group: '',
  send_filter: {
    regions: [],
    industries: [],
    days: 7,
    start_date: '',
    end_date: ''
  },
  send_limit: 5
})

const editSchedule = reactive({
  frequency: 'daily',
  hour: 9,
  minute: 0,
  dayOfWeek: 1
})

const frequencyOptions = [
  { label: '每小时', value: 'hourly' },
  { label: '每天', value: 'daily' },
  { label: '每周', value: 'weekly' },
  { label: '每月', value: 'monthly' }
]

const weekDays = [
  { label: '一', value: 1 },
  { label: '二', value: 2 },
  { label: '三', value: 3 },
  { label: '四', value: 4 },
  { label: '五', value: 5 },
  { label: '六', value: 6 },
  { label: '日', value: 7 }
]

const scheduleToCron = () => {
  const { frequency, hour, minute, dayOfWeek } = schedule
  switch (frequency) {
    case 'hourly':
      return `${minute} * * * *`  // 每小时整分执行
    case 'daily':
      return `${minute} ${hour} * * *`
    case 'weekly':
      return `${minute} ${hour} * * ${dayOfWeek}`
    case 'monthly':
      return `${minute} ${hour} 1 * *`  // 每月1日
    default:
      return ''
  }
}

const filteredTasks = computed(() => {
  let result = tasks.value
  if (filterType.value === 'scheduled') {
    result = result.filter(t => t.cron_expr && t.cron_expr !== '')
  } else if (filterType.value === 'manual') {
    result = result.filter(t => !t.cron_expr || t.cron_expr === '')
  } else if (filterType.value !== 'all') {
    result = result.filter(t => (t.task_type || 'crawl') === filterType.value)
  }
  if (filterStatus.value) {
    result = result.filter(t => (t.execution_status || 'none') === filterStatus.value)
  }
  return result
})

const scheduledCount = computed(() => tasks.value.filter(t => t.cron_expr && t.cron_expr !== '').length)
const manualCount = computed(() => tasks.value.filter(t => !t.cron_expr || t.cron_expr === '').length)
const crawlCount = computed(() => tasks.value.filter(t => (t.task_type || 'crawl') === 'crawl').length)
const sendCount = computed(() => tasks.value.filter(t => t.task_type === 'send').length)
const activeCount = computed(() => tasks.value.filter(t => t.execution_status === 'running').length)
const successCount = computed(() => tasks.value.filter(t => t.execution_status === 'success').length)
const isAllSelected = computed(() => filteredTasks.value.length > 0 && filteredTasks.value.every(t => selectedTasks.value.includes(t.id)))

const toggleSelect = (id) => {
  const idx = selectedTasks.value.indexOf(id)
  if (idx > -1) selectedTasks.value.splice(idx, 1)
  else selectedTasks.value.push(id)
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedTasks.value = []
  } else {
    selectedTasks.value = filteredTasks.value.map(t => t.id)
  }
}

const batchDeleteTasks = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedTasks.value.length} 个任务？`, '批量删除', { type: 'warning' })
    await axios.post('/api/v1/tasks/batch-delete', { ids: selectedTasks.value })
    ElMessage.success('删除成功')
    selectedTasks.value = []
    fetchTasks()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/tasks')
    if (res.data.code === 0) {
      // 记录当前选中的任务ID，以便在刷新后更新 currentTask
      const currentId = currentTask.value?.id
      tasks.value = res.data.data
      // 如果详情对话框打开中，同步更新 currentTask 的数据
      if (detailVisible.value && currentId) {
        const updated = tasks.value.find(t => t.id === currentId)
        if (updated) currentTask.value = updated
      }
    }
  } finally { loading.value = false }
}

const fetchConfig = async () => {
  try {
    const res = await axios.get('/api/v1/config')
    if (res.data.code === 0) {
      dingtalkGroups.value = res.data.data.dingtalk_groups || []
    }
  } catch {}
}

const showCreateDialog = () => {
  Object.assign(form, {
    name: '',
    task_mode: 'scheduled',
    task_type: 'crawl',
    platform: 'qianlima',
    region_codes: ['500000'],
    start_date: '',
    end_date: '',
    dynamic_days: 7,
    cron_expr: '',
    enabled: true,
    dingtalk_group: dingtalkGroups.value[0]?.webhook_url || '',
    send_filter: {
      regions: [],
      industries: [],
      days: 7,
      start_date: '',
      end_date: ''
    },
    send_limit: 5
  })
  Object.assign(schedule, {
    frequency: 'daily',
    hour: 9,
    minute: 0,
    dayOfWeek: 1
  })
  dialogVisible.value = true
}

const toggleRegion = (code) => {
  const idx = form.region_codes.indexOf(code)
  if (idx > -1) form.region_codes.splice(idx, 1)
  else form.region_codes.push(code)
}

const toggleEditRegion = (code) => {
  const idx = editForm.region_codes.indexOf(code)
  if (idx > -1) editForm.region_codes.splice(idx, 1)
  else editForm.region_codes.push(code)
}

// 发送任务筛选条件多选
const toggleSendRegion = (region) => {
  if (!form.send_filter.regions) form.send_filter.regions = []
  const idx = form.send_filter.regions.indexOf(region)
  if (idx > -1) form.send_filter.regions.splice(idx, 1)
  else form.send_filter.regions.push(region)
}

const toggleSendIndustry = (industry) => {
  if (!form.send_filter.industries) form.send_filter.industries = []
  const idx = form.send_filter.industries.indexOf(industry)
  if (idx > -1) form.send_filter.industries.splice(idx, 1)
  else form.send_filter.industries.push(industry)
}

const toggleEditSendRegion = (region) => {
  if (!editForm.send_filter.regions) editForm.send_filter.regions = []
  const idx = editForm.send_filter.regions.indexOf(region)
  if (idx > -1) editForm.send_filter.regions.splice(idx, 1)
  else editForm.send_filter.regions.push(region)
}

const toggleEditSendIndustry = (industry) => {
  if (!editForm.send_filter.industries) editForm.send_filter.industries = []
  const idx = editForm.send_filter.industries.indexOf(industry)
  if (idx > -1) editForm.send_filter.industries.splice(idx, 1)
  else editForm.send_filter.industries.push(industry)
}

// 显示编辑对话框
const showEditDialog = () => {
  if (!currentTask.value) return

  const task = currentTask.value

  // 解析region_codes
  let regionCodes = []
  if (task.region_codes) {
    try {
      regionCodes = typeof task.region_codes === 'string' ? JSON.parse(task.region_codes) : task.region_codes
    } catch {
      regionCodes = []
    }
  }

  // 解析send_filter
  let sendFilter = { regions: [], industries: [], days: 7, start_date: '', end_date: '' }
  if (task.send_filter) {
    try {
      const parsed = typeof task.send_filter === 'string' ? JSON.parse(task.send_filter) : task.send_filter
      // 处理旧数据兼容：如果存在region/industry单选字段，转换为数组
      if (parsed.region && !parsed.regions) {
        parsed.regions = [parsed.region]
      }
      if (parsed.industry && !parsed.industries) {
        parsed.industries = [parsed.industry]
      }
      sendFilter = { ...sendFilter, ...parsed }
    } catch {}
  }

  // 填充编辑表单
  Object.assign(editForm, {
    id: task.id,
    name: task.name,
    task_type: task.task_type || 'crawl',
    platform: task.platform || 'qianlima',
    region_codes: regionCodes,
    start_date: task.start_date || '',
    end_date: task.end_date || '',
    dynamic_days: task.dynamic_days || 7,
    cron_expr: task.cron_expr || '',
    enabled: task.enabled,
    dingtalk_group: task.dingtalk_group || '',
    send_filter: sendFilter,
    send_limit: task.send_limit || 5
  })

  // 解析cron表达式
  parseCronToSchedule(task.cron_expr || '', editSchedule)

  detailVisible.value = false
  editDialogVisible.value = true
}

// 从cron表达式解析schedule
const parseCronToSchedule = (cronExpr, scheduleObj) => {
  if (!cronExpr) {
    scheduleObj.frequency = 'daily'
    scheduleObj.hour = 9
    scheduleObj.minute = 0
    scheduleObj.dayOfWeek = 1
    return
  }

  const parts = cronExpr.split(' ')
  if (parts.length !== 5) return

  const [minute, hour, dayOfMonth, month, dayOfWeek] = parts

  scheduleObj.minute = parseInt(minute) || 0
  scheduleObj.hour = parseInt(hour) || 0

  // 判断频率类型
  if (hour === '*') {
    scheduleObj.frequency = 'hourly'
  } else if (dayOfWeek !== '*') {
    scheduleObj.frequency = 'weekly'
    scheduleObj.dayOfWeek = parseInt(dayOfWeek) || 1
  } else if (dayOfMonth !== '*') {
    scheduleObj.frequency = 'monthly'
  } else {
    scheduleObj.frequency = 'daily'
  }
}

// 更新任务
const updateTask = async () => {
  if (!editForm.name) {
    ElMessage.warning('请输入任务名称')
    return
  }

  try {
    const data = {
      name: editForm.name,
      cron_expr: editForm.cron_expr ? scheduleToCronFromObj(editSchedule) : '',
      enabled: editForm.enabled
    }

    if (editForm.task_type === 'crawl' || !editForm.task_type) {
      data.platform = editForm.platform
      data.region_codes = editForm.region_codes
      data.dynamic_days = editForm.dynamic_days
      data.start_date = editForm.start_date
      data.end_date = editForm.end_date
      data.dynamic_date = editForm.cron_expr ? true : false
    } else {
      data.dingtalk_group = editForm.dingtalk_group
      data.send_limit = editForm.send_limit

      if (editForm.cron_expr) {
        data.send_filter = {
          regions: editForm.send_filter.regions || [],
          industries: editForm.send_filter.industries || [],
          days: editForm.send_filter.days,
          use_dynamic: true
        }
      } else {
        data.send_filter = {
          regions: editForm.send_filter.regions || [],
          industries: editForm.send_filter.industries || [],
          start_date: editForm.send_filter.start_date,
          end_date: editForm.send_filter.end_date,
          use_dynamic: false
        }
      }
    }

    await axios.put(`/api/v1/tasks/${editForm.id}`, data)
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    fetchTasks()
  } catch {
    ElMessage.error('更新失败')
  }
}

// 从schedule对象生成cron表达式
const scheduleToCronFromObj = (scheduleObj) => {
  const { frequency, hour, minute, dayOfWeek } = scheduleObj
  switch (frequency) {
    case 'hourly':
      return `${minute} * * * *`
    case 'daily':
      return `${minute} ${hour} * * *`
    case 'weekly':
      return `${minute} ${hour} * * ${dayOfWeek}`
    case 'monthly':
      return `${minute} ${hour} 1 * *`
    default:
      return ''
  }
}

const submitTask = async () => {
  if (!form.name) {
    ElMessage.warning('请输入任务名称')
    return
  }

  // 手动任务必须选择日期范围
  if (form.task_mode === 'manual') {
    if (form.task_type === 'crawl') {
      if (!form.start_date || !form.end_date) {
        ElMessage.warning('请选择日期范围')
        return
      }
    } else if (form.task_type === 'send') {
      if (!form.send_filter.start_date || !form.send_filter.end_date) {
        ElMessage.warning('请选择发布时间范围')
        return
      }
    }
  }

  try {
    const data = {
      name: form.name,
      task_type: form.task_type,
      cron_expr: form.task_mode === 'scheduled' ? scheduleToCron() : '',
      enabled: form.enabled
    }

    if (form.task_type === 'crawl') {
      data.platform = form.platform
      data.region_codes = form.region_codes

      if (form.task_mode === 'scheduled') {
        // 定时任务：使用动态日期
        data.dynamic_date = true
        data.dynamic_days = form.dynamic_days
      } else {
        // 手动任务：使用固定日期
        data.dynamic_date = false
        data.start_date = form.start_date
        data.end_date = form.end_date
      }
    } else {
      // 发送任务
      data.dingtalk_group = form.dingtalk_group
      data.send_limit = form.send_limit

      if (form.task_mode === 'scheduled') {
        // 定时任务：使用动态天数筛选
        data.send_filter = {
          regions: form.send_filter.regions || [],
          industries: form.send_filter.industries || [],
          days: form.send_filter.days,
          use_dynamic: true
        }
      } else {
        // 手动任务：使用固定日期筛选
        data.send_filter = {
          regions: form.send_filter.regions || [],
          industries: form.send_filter.industries || [],
          start_date: form.send_filter.start_date,
          end_date: form.send_filter.end_date,
          use_dynamic: false
        }
      }
    }

    await axios.post('/api/v1/tasks', data)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchTasks()
  } catch { ElMessage.error('创建失败') }
}

const runTask = async (id) => {
  try {
    await axios.post(`/api/v1/tasks/${id}/run`)
    ElMessage.success('任务已启动')
    fetchTasks()
    startAutoRefresh()
  } catch { ElMessage.error('启动失败') }
}

const toggleTask = async (task) => {
  try {
    await axios.put(`/api/v1/tasks/${task.id}`, { enabled: task.enabled })
    ElMessage.success(task.enabled ? '已启用' : '已禁用')
  } catch { ElMessage.error('更新失败') }
}

const deleteTask = async (id) => {
  try {
    await ElMessageBox.confirm('删除该任务?', '提示', { type: 'warning' })
    await axios.delete(`/api/v1/tasks/${id}`)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const showDetail = async (task) => {
  currentTask.value = task
  detailVisible.value = true
  // 获取执行日志
  if (task.last_execution) {
    try {
      const res = await axios.get(`/api/v1/executions/${task.id}/logs`)
      if (res.data.code === 0) {
        currentTask.value.logs = res.data.data
      }
    } catch {}
  }
}

const startAutoRefresh = () => {
  if (!refreshTimer.value) {
    refreshTimer.value = setInterval(() => {
      fetchTasks()
      if (!tasks.value.some(t => t.execution_status === 'running')) stopAutoRefresh()
    }, 3000)
  }
}

const stopAutoRefresh = () => {
  if (refreshTimer.value) { clearInterval(refreshTimer.value); refreshTimer.value = null }
}

const getStatusText = (status) => {
  const map = { running: '运行中', success: '已完成', failed: '失败' }
  return map[status] || '未执行'
}

const getLoginStatusText = (status) => {
  const map = {
    logged_in: '已登录',
    logged_out: '未登录',
    expired: '登录过期',
    unknown: '未知'
  }
  return map[status] || '未知'
}

const getCronDesc = (expr) => {
  if (!expr) return ''
  const map = {
    '0 9 * * *': '每天9点',
    '0 8 * * 1': '每周一8点',
    '0 18 * * 5': '每周五18点',
    '0 12 * * *': '每天12点'
  }
  return map[expr] || ''
}

const getGroupName = (url) => {
  if (!url) return '-'
  const group = dingtalkGroups.value.find(g => g.webhook_url === url)
  return group?.name || url.substring(0, 30) + '...'
}

const getProgressPercent = (task) => {
  return task.progress || 0
}

const getProgressClass = (task) => {
  if (task.execution_status === 'running') return 'lb-progress-info'
  if (task.execution_status === 'success') return 'lb-progress-success'
  if (task.execution_status === 'failed') return 'lb-progress-danger'
  return 'lb-progress-info'
}

const getProgressText = (task) => {
  if (task.execution_status === 'running') {
    return `${task.progress || 0}%`
  }
  if (task.bids_count) {
    return `${task.bids_count}条`
  }
  return '-'
}

const getDuration = (task) => {
  if (!task?.started_at) return 0
  const start = new Date(task.started_at)
  const end = task.ended_at ? new Date(task.ended_at) : new Date()
  return Math.floor((end - start) / 1000)
}

const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatTimeFull = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const parseLogs = (logs) => {
  if (!logs) return []
  if (Array.isArray(logs)) return logs
  try {
    return JSON.parse(logs)
  } catch {
    return []
  }
}

onMounted(() => {
  fetchTasks()
  fetchConfig()
})
onUnmounted(() => stopAutoRefresh())
</script>

<style scoped lang="scss">
@import '@/styles/light-blue.scss';

.tasks-page {
  padding: $lb-content-padding;
}

/* 统计卡片行 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $lb-grid-gutter;
  margin-bottom: $lb-grid-gutter;
}

.stat-widget {
  margin-bottom: 0;

  .lb-stat-card {
    margin-bottom: 0;
  }
}

/* 筛选工具栏 */
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $lb-grid-gutter;
}

.filter-tabs {
  display: flex;
  gap: 8px;

  .lb-btn.active {
    background: rgba($lb-blue, .2);
    color: $lb-blue;
  }
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-select {
  width: 140px;
}

/* 任务表格 */
.tasks-widget {
  overflow: hidden;
  margin-bottom: 0;
}

.tasks-table {
  th {
    padding: 1rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--lb-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: transparent;
    border: none;
  }

  td {
    padding: 1rem 0.75rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--lb-text-secondary);
    border: none;
    border-bottom: 1px solid $lb-border-light;
  }

  tr:hover td {
    background: $lb-bg-page;
  }

  tr:last-child td {
    border-bottom: none;
  }

  .col-check {
    width: 40px;
    text-align: center;
  }

  .checkbox {
    width: 18px;
    height: 18px;
    accent-color: $lb-blue;
    cursor: pointer;
  }
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;

  &.success { background: $lb-green; box-shadow: 0 0 8px rgba($lb-green, .5); }
  &.failed { background: $lb-red; box-shadow: 0 0 8px rgba($lb-red, .5); }
  &.running { background: $lb-orange; animation: pulse 1s infinite; }
  &.none { background: $lb-border; }
}

.status-text {
  font-size: 0.8125rem;
  color: var(--lb-text-muted);
}

/* 名称列 */
.task-name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-name {
  font-weight: 600;
  color: var(--lb-text-primary);
}

.task-id {
  font-size: 0.6875rem;
  color: var(--lb-text-muted);
  font-family: monospace;
}

/* 配置列 */
.config-info {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.config-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: $lb-bg-page;
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--lb-text-muted);
}

/* 定时列 */
.schedule-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cron-expr {
  background: $lb-bg-page;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-family: monospace;
  color: var(--lb-text-secondary);
}

.cron-desc {
  font-size: 0.6875rem;
  color: var(--lb-text-muted);
}

.no-schedule {
  font-size: 0.8125rem;
  color: var(--lb-text-muted);
}

/* 手动任务显示 */
.manual-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.manual-badge {
  padding: 4px 10px;
  background: rgba($lb-green, .15);
  color: $lb-green;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.manual-hint {
  font-size: 0.6875rem;
  color: var(--lb-text-muted);
}

/* 进度列 */
.progress-cell {
  display: flex;
  align-items: center;
  gap: 10px;

  .lb-progress {
    flex: 1;
    min-width: 60px;
    margin-bottom: 0;
  }
}

.progress-text {
  font-size: 0.75rem;
  color: var(--lb-text-muted);
  min-width: 40px;
}

/* 最后执行列 */
.last-exec-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.last-time {
  font-size: 0.8125rem;
  color: var(--lb-text-secondary);
}

.last-result {
  font-size: 0.6875rem;
  color: var(--lb-text-muted);

  &.success { color: $lb-green; }
  &.failed { color: $lb-red; }
}

.no-exec {
  color: var(--lb-text-muted);
}

/* 操作列 */
.action-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  .btn-sm {
    padding: 6px;

    svg {
      width: 14px;
      height: 14px;
    }
  }
}

/* 加载和空状态 */
.loading-cell, .empty-cell {
  padding: 60px 20px !important;
  text-align: center;
}

.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--lb-text-muted);

  svg {
    animation: spin 1s linear infinite;
    color: $lb-blue;
  }
}

.empty-content {
  color: var(--lb-text-muted);

  h3 {
    font-size: 1rem;
    color: var(--lb-text-primary);
    margin: 16px 0 4px;
  }

  p {
    font-size: 0.875rem;
    margin: 0;
  }
}

/* 对话框样式 */
.dialog-header {
  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--lb-text-primary);
    margin: 0 0 4px;
  }

  p {
    font-size: 0.875rem;
    color: var(--lb-text-muted);
    margin: 0;
  }
}

.form-section {
  padding: 8px 0;
}

.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.filter-row {
  display: flex;
  gap: 8px;

  .lb-select.small, .lb-input.small {
    flex: 1;
    min-width: 0;
  }
}

.form-hint {
  display: block;
  font-size: 0.75rem;
  color: var(--lb-text-muted);
  margin-top: 6px;
}

/* 类型选择器 */
.type-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.type-option {
  padding: 16px;
  border: 2px solid $lb-border;
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: rgba($lb-blue, .5);
  }

  &.active {
    border-color: $lb-blue;
    background: rgba($lb-blue, .1);
  }

  span {
    display: block;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--lb-text-primary);
  }

  small {
    display: block;
    font-size: 0.75rem;
    color: var(--lb-text-muted);
    margin-top: 4px;
  }
}

.type-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto 8px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 20px;
    height: 20px;
  }

  &.crawl {
    background: rgba($lb-green, .15);
    color: $lb-green;
  }

  &.send {
    background: rgba($lb-blue, .15);
    color: $lb-blue;
  }
}

/* 模式选择器 */
.mode-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mode-option {
  padding: 16px;
  border: 2px solid $lb-border;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: rgba($lb-blue, .5);
  }

  &.active {
    border-color: $lb-blue;
    background: rgba($lb-blue, .1);
  }
}

.mode-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 22px;
    height: 22px;
  }

  &.scheduled {
    background: rgba($lb-blue, .15);
    color: $lb-blue;
  }

  &.manual {
    background: rgba($lb-green, .15);
    color: $lb-green;
  }
}

.mode-info {
  span {
    display: block;
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--lb-text-primary);
  }

  small {
    display: block;
    font-size: 0.75rem;
    color: var(--lb-text-muted);
    margin-top: 2px;
  }
}

/* 定时设置区块 */
.schedule-section {
  background: rgba($lb-blue, .05);
  border: 1px solid rgba($lb-blue, .2);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
}

.schedule-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  color: $lb-blue;
  font-weight: 600;
  font-size: 0.875rem;

  svg {
    color: $lb-blue;
  }
}

/* 地区标签 */
.region-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.multi-select-section {
  margin-bottom: 12px;
}

.multi-select-label {
  display: block;
  font-size: 0.8125rem;
  color: var(--lb-text-secondary);
  margin-bottom: 6px;
  font-weight: 500;
}

.tag {
  padding: 8px 16px;
  background: $lb-bg-page;
  border-radius: 6px;
  font-size: 0.8125rem;
  color: var(--lb-text-secondary);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: $lb-border;
  }

  &.active {
    background: $lb-blue;
    color: white;
  }
}

/* 日期范围选项 */
.date-range-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 执行频率选择 */
.frequency-selector {
  display: flex;

  .lb-select {
    flex: 1;
  }
}

/* 时间选择器 */
.time-selector {
  display: flex;
  align-items: center;
  gap: 8px;

  .lb-select.small {
    width: 80px;
  }

  .time-separator {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--lb-text-primary);
  }
}

/* 星期选择器 */
.weekday-selector {
  display: flex;
  gap: 8px;
}

.weekday-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $lb-bg-page;
  border: 1px solid $lb-border;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--lb-text-secondary);
  transition: all 0.15s;

  &:hover {
    background: $lb-border;
  }

  &.active {
    background: $lb-blue;
    border-color: $lb-blue;
    color: white;
  }
}

/* Cron预设 */
.cron-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.preset {
  padding: 6px 12px;
  background: $lb-bg-page;
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--lb-text-muted);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: rgba($lb-blue, .2);
    color: $lb-blue;
  }
}

/* 复选框 */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;

  input {
    width: 18px;
    height: 18px;
    accent-color: $lb-blue;
  }

  span {
    color: var(--lb-text-secondary);
  }
}

/* 详情对话框 */
.detail-header {
  margin-bottom: 20px;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;

  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--lb-text-primary);
    margin: 0;
  }
}

.detail-header-actions {
  margin-left: auto;
}

.detail-header p {
  font-size: 0.8125rem;
  color: var(--lb-text-muted);
  margin: 0;
  font-family: monospace;
}

/* 执行统计卡片 */
.exec-stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: $lb-grid-gutter;
}

.exec-stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 0;
  padding: 1rem;
}

.exec-stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  svg {
    width: 20px;
    height: 20px;
  }

  &.running { background: rgba($lb-orange, .15); color: $lb-orange; }
  &.success { background: rgba($lb-green, .15); color: $lb-green; }
  &.failed { background: rgba($lb-red, .15); color: $lb-red; }
  &.none { background: $lb-bg-page; color: var(--lb-text-muted); }

  &.login.logged_in { background: rgba($lb-green, .15); color: $lb-green; }
  &.login.logged_out { background: rgba($lb-red, .15); color: $lb-red; }
  &.login.expired { background: rgba($lb-orange, .15); color: $lb-orange; }
  &.login.unknown { background: $lb-bg-page; color: var(--lb-text-muted); }

  &.discover { background: rgba($lb-blue, .15); color: $lb-blue; }
  &.store { background: rgba($lb-green, .15); color: $lb-green; }
  &.duplicate { background: rgba($lb-orange, .15); color: $lb-orange; }
  &.time { background: $lb-bg-page; color: var(--lb-text-muted); }
}

.exec-stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.exec-stat-label {
  font-size: 0.6875rem;
  color: var(--lb-text-muted);
}

.exec-stat-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--lb-text-primary);

  .unit {
    font-size: 0.75rem;
    font-weight: 400;
    color: var(--lb-text-muted);
    margin-left: 2px;
  }

  &.highlight { color: $lb-blue; }
  &.success { color: $lb-green; }
}

/* 执行进度 */
.exec-progress-section {
  margin-bottom: $lb-grid-gutter;
  background: $lb-bg-page;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--lb-text-primary);
    margin: 0;
  }
}

.progress-percent {
  font-size: 1.125rem;
  font-weight: 700;
  color: $lb-blue;
}

.progress-bar-wrapper {
  margin-bottom: 16px;
}

.progress-steps {
  display: flex;
  gap: 16px;
}

.progress-step {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  opacity: 0.4;
  transition: opacity 0.3s;

  &.active { opacity: 1; }

  &.done .step-indicator {
    background: $lb-blue;
  }

  &.done .step-num {
    color: white;
  }
}

.step-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: $lb-border;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-num {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--lb-text-muted);
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--lb-text-primary);
}

.step-desc {
  font-size: 0.6875rem;
  color: var(--lb-text-muted);
}

/* 运行日志 */
.exec-log-section {
  margin-bottom: $lb-grid-gutter;
}

.log-count-badge {
  padding: 4px 10px;
  background: $lb-blue;
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.log-viewer {
  background: $lb-bg-page;
  border: 1px solid $lb-border;
  border-radius: 8px;
  overflow: hidden;
}

.log-list {
  padding: 16px;
  max-height: 280px;
  overflow-y: auto;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
}

.log-entry {
  display: flex;
  gap: 16px;
  padding: 8px 0;
  font-size: 0.8125rem;
  color: var(--lb-text-secondary);
  border-bottom: 1px solid $lb-border-light;

  &:last-child {
    border-bottom: none;
  }

  .log-time {
    color: var(--lb-text-muted);
    min-width: 70px;
    font-size: 0.75rem;
  }

  .log-level {
    min-width: 60px;
    font-weight: 600;
    color: $lb-teal;
  }

  .log-message {
    color: var(--lb-text-secondary);
    flex: 1;
  }

  &.info .log-level { color: $lb-teal; }
  &.success .log-level { color: $lb-green; }
  &.warning .log-level { color: $lb-orange; }
  &.error .log-level { color: $lb-red; }
  &.error .log-message { color: lighten($lb-red, 20%); }
}

.log-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--lb-text-muted);

  svg {
    opacity: 0.4;
    margin-bottom: 16px;
  }

  p {
    font-size: 0.875rem;
    color: var(--lb-text-secondary);
    margin: 0 0 4px;
  }

  span {
    font-size: 0.75rem;
    color: var(--lb-text-muted);
  }
}

/* 任务配置 */
.exec-config-section {
  margin-bottom: 0;

  h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--lb-text-primary);
    margin: 0 0 12px;
  }
}

.config-details {
  background: $lb-bg-page;
  border: 1px solid $lb-border;
  border-radius: 8px;
  overflow: hidden;
}

.config-row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid $lb-border-light;

  &:last-child {
    border-bottom: none;
  }
}

.config-key {
  font-size: 0.8125rem;
  color: var(--lb-text-muted);
  min-width: 120px;
}

.config-val {
  font-size: 0.875rem;
  color: var(--lb-text-primary);
  font-weight: 600;

  config {
    background: $lb-bg-page;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-family: monospace;
  }

  &.enabled { color: $lb-green; }
  &.disabled { color: var(--lb-text-muted); }
}

/* 动画 */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 响应式 */
@media (max-width: 1400px) {
  .exec-stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .exec-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .filter-toolbar {
    flex-direction: column;
    gap: 12px;

    .filter-actions {
      width: 100%;
      justify-content: space-between;
    }
  }

  .filter-tabs {
    flex-wrap: wrap;
  }

  .exec-stats-grid {
    grid-template-columns: 1fr;
  }

  .progress-steps {
    flex-direction: column;
    gap: 12px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .type-selector {
    grid-template-columns: 1fr;
  }

  .mode-selector {
    grid-template-columns: 1fr;
  }
}
</style>
