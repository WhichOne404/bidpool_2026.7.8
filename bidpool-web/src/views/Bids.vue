<template>
  <div class="lb-page bids-page">
    <!-- 页面标题 -->
    <h1 class="lb-page-title">
      标讯中心
      <small>管理和分发收集的标讯数据</small>
    </h1>

    <!-- 数据概览 - 紧凑布局 -->
    <div class="lb-widget stats-bar">
      <div class="stat-item">
        <div class="stat-value">{{ total }}</div>
        <div class="stat-label">标讯总量</div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item pending">
        <div class="stat-value">{{ pendingTotal }}</div>
        <div class="stat-label">待发送</div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item sent">
        <div class="stat-value">{{ sentTotal }}</div>
        <div class="stat-label">已发送</div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item regions">
        <div class="stat-label">地区分布</div>
        <div class="region-tags">
          <span v-for="r in regionStats" :key="r.name" class="region-tag">
            {{ r.name }} <b>{{ r.count }}</b>
          </span>
        </div>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="lb-widget filter-widget">
      <div class="search-row">
        <div class="search-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input type="text" v-model="searchKeyword" placeholder="搜索标讯标题..." @input="debounceSearch" class="lb-input" />
        </div>
        <div class="filter-selects">
          <!-- 行业多选 -->
          <div class="multi-select-wrapper">
            <div class="multi-select-trigger" @click="showIndustryDropdown = !showIndustryDropdown">
              <span class="multi-select-text">
                {{ filter.crm_industries.length ? filter.crm_industries.join('、') : '全部行业' }}
              </span>
              <span class="multi-select-count" v-if="filter.crm_industries.length">{{ filter.crm_industries.length }}</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
            <div class="multi-select-dropdown" v-if="showIndustryDropdown">
              <div class="multi-select-option" @click="toggleIndustry('')">
                <span :class="['checkbox', { checked: filter.crm_industries.length === 0 }]"></span>
                <span>全部行业</span>
              </div>
              <div class="multi-select-option" v-for="i in industries" :key="i" @click="toggleIndustry(i)">
                <span :class="['checkbox', { checked: filter.crm_industries.includes(i) }]"></span>
                <span>{{ i }}</span>
              </div>
            </div>
          </div>
          <!-- 地区多选 -->
          <div class="multi-select-wrapper">
            <div class="multi-select-trigger" @click="showRegionDropdown = !showRegionDropdown">
              <span class="multi-select-text">
                {{ filter.regions.length ? filter.regions.join('、') : '全部地区' }}
              </span>
              <span class="multi-select-count" v-if="filter.regions.length">{{ filter.regions.length }}</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
            <div class="multi-select-dropdown" v-if="showRegionDropdown">
              <div class="multi-select-option" @click="toggleRegion('')">
                <span :class="['checkbox', { checked: filter.regions.length === 0 }]"></span>
                <span>全部地区</span>
              </div>
              <div class="multi-select-option" v-for="r in regions" :key="r" @click="toggleRegion(r)">
                <span :class="['checkbox', { checked: filter.regions.includes(r) }]"></span>
                <span>{{ r }}</span>
              </div>
            </div>
          </div>
          <select v-model="filter.status" class="lb-select">
            <option value="">全部状态</option>
            <option value="pending">待发送</option>
            <option value="sent">已发送</option>
          </select>
          <div class="date-filter">
            <span class="date-label">发布日期</span>
            <input type="date" v-model="filter.start_date" class="lb-input lb-input-sm" placeholder="开始日期" @change="fetchBids" />
            <span class="date-separator">至</span>
            <input type="date" v-model="filter.end_date" class="lb-input lb-input-sm" placeholder="结束日期" @change="fetchBids" />
          </div>
        </div>
        <div class="filter-buttons">
          <button class="lb-btn lb-btn-primary" @click="fetchBids">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            搜索
          </button>
          <button class="lb-btn lb-btn-ghost" @click="resetFilter">重置</button>
        </div>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <transition name="slide">
      <div v-if="selectedBids.length" class="lb-widget batch-toolbar">
        <div class="batch-info">
          <div class="selection-badge">{{ selectedBids.length }}</div>
          <span>条标讯已选中</span>
          <button class="lb-btn lb-btn-ghost btn-xs" @click="selectAllPage" v-if="!isAllSelected">
            全选当前页
          </button>
          <button class="lb-btn lb-btn-ghost btn-xs" @click="selectAllAll" v-if="selectedBids.length < total">
            全选全部({{ total }}条)
          </button>
        </div>
        <div class="batch-actions">
          <button class="lb-btn lb-btn-success" @click="showDispatch">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            发送到钉钉
          </button>
          <button class="lb-btn lb-btn-danger" @click="batchDelete">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            批量删除
          </button>
          <button class="lb-btn lb-btn-ghost" @click="clearSelection">取消选择</button>
        </div>
      </div>
    </transition>

    <!-- 标讯列表 -->
    <div class="lb-widget bids-widget">
      <table class="lb-table bids-table">
        <thead>
          <tr>
            <th class="col-checkbox">
              <label class="checkbox-wrapper">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  :indeterminate.prop="isIndeterminate"
                  @change="toggleAllSelection"
                />
                <span class="checkmark"></span>
              </label>
            </th>
            <th class="col-title">标题</th>
            <th class="col-industry">行业</th>
            <th class="col-region">地区</th>
            <th class="col-budget">预算</th>
            <th class="col-date">发布时间</th>
            <th class="col-date">开标时间</th>
            <th class="col-status">状态</th>
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
        <tbody v-else-if="!bids.length">
          <tr>
            <td colspan="9" class="empty-cell">
              <div class="empty-content">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="56" height="56">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
                <h3>暂无标讯数据</h3>
                <p>请先创建收集任务获取标讯</p>
              </div>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr
            v-for="bid in bids"
            :key="bid.id"
            :class="{ selected: isSelected(bid) }"
            class="bid-row"
          >
            <td class="col-checkbox">
              <label class="checkbox-wrapper">
                <input
                  type="checkbox"
                  :checked="isSelected(bid)"
                  @change="toggleSelection(bid)"
                />
                <span class="checkmark"></span>
              </label>
            </td>
            <td class="col-title">
              <span class="bid-title" @click="viewBid(bid)">{{ bid.title }}</span>
            </td>
            <td class="col-industry">
              <span class="lb-badge lb-badge-info">{{ bid.crm_industry || '其他' }}</span>
            </td>
            <td class="col-region">{{ bid.region || '-' }}</td>
            <td class="col-budget">
              <span class="budget-value">{{ formatBudget(bid.budget) }}</span>
            </td>
            <td class="col-date">{{ formatDate(bid.publish_date) }}</td>
            <td class="col-date">{{ formatDate(bid.open_date) }}</td>
            <td class="col-status">
              <span :class="['lb-badge', bid.status === 'pending' ? 'lb-badge-warning' : 'lb-badge-success']">
                {{ bid.status === 'pending' ? '待发送' : '已发送' }}
              </span>
            </td>
            <td class="col-actions">
              <button class="lb-btn lb-btn-ghost btn-sm" @click="viewBid(bid)" title="查看详情">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
              <button class="lb-btn lb-btn-danger btn-sm" @click="deleteBid(bid.id)" title="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="lb-widget pagination-bar">
      <div class="pagination-info">
        显示 {{ (page - 1) * pageSize + 1 }}-{{ Math.min(page * pageSize, total) }} 条，共 {{ total }} 条
      </div>
      <div class="pagination-controls">
        <button class="lb-btn lb-btn-ghost btn-sm" :disabled="page === 1" @click="page--; fetchBids()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <template v-for="p in displayedPages" :key="p">
          <span v-if="p === '...'" class="page-ellipsis">...</span>
          <button v-else :class="['lb-btn', 'btn-sm', page === p ? 'lb-btn-info' : 'lb-btn-ghost']" @click="page = p; fetchBids()">{{ p }}</button>
        </template>
        <button class="lb-btn lb-btn-ghost btn-sm" :disabled="page >= totalPages" @click="page++; fetchBids()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
        <select v-model="pageSize" class="lb-select page-size-select" @change="fetchBids">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
        </select>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="" width="640px" class="lb-dialog bid-detail-dialog">
      <div class="detail-wrapper" v-if="currentBid">
        <div class="detail-header">
          <div class="detail-badges">
            <span :class="['lb-badge', currentBid.status === 'pending' ? 'lb-badge-warning' : 'lb-badge-success']">
              {{ currentBid.status === 'pending' ? '待发送' : '已发送' }}
            </span>
            <span class="lb-badge lb-badge-info">{{ currentBid.crm_industry || '其他' }}</span>
          </div>
          <div class="detail-budget">{{ formatBudget(currentBid.budget) }}</div>
        </div>
        <h3 class="detail-title">{{ currentBid.title }}</h3>

        <div class="detail-info-grid">
          <div class="lb-widget info-item">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
            </div>
            <div class="info-content">
              <label>招标单位</label>
              <span>{{ currentBid.tender_unit || '-' }}</span>
            </div>
          </div>
          <div class="lb-widget info-item">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                <circle cx="12" cy="10" r="3"/>
              </svg>
            </div>
            <div class="info-content">
              <label>所属地区</label>
              <span>{{ currentBid.region || '-' }}</span>
            </div>
          </div>
          <div class="lb-widget info-item">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
            </div>
            <div class="info-content">
              <label>发布时间</label>
              <span>{{ currentBid.publish_date || '-' }}</span>
            </div>
          </div>
          <div class="lb-widget info-item">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="info-content">
              <label>开标时间</label>
              <span>{{ currentBid.open_date || '-' }}</span>
            </div>
          </div>
        </div>

        <div class="detail-actions">
          <a :href="currentBid.link" target="_blank" class="lb-btn lb-btn-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            查看原文
          </a>
        </div>
      </div>
    </el-dialog>

    <!-- 发送弹窗 -->
    <el-dialog v-model="dispatchVisible" title="" width="400px" class="lb-dialog dispatch-dialog">
      <div class="dispatch-wrapper">
        <div class="dispatch-header">
          <div class="dispatch-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </div>
          <h3>发送到钉钉</h3>
          <p>将选中的标讯推送到钉钉群</p>
        </div>

        <div class="lb-widget dispatch-count-box">
          <div class="count-number">{{ selectedBids.length }}</div>
          <div class="count-label">条标讯将发送</div>
        </div>

        <div class="dispatch-form">
          <label class="lb-label">选择钉钉群</label>
          <select v-model="selectedGroup" class="lb-select">
            <option value="">请选择目标群</option>
            <option v-for="g in groups" :key="g.webhook_url" :value="g.webhook_url">{{ g.name }}</option>
          </select>
        </div>
      </div>
      <template #footer>
        <button class="lb-btn lb-btn-ghost" @click="dispatchVisible = false">取消</button>
        <button class="lb-btn lb-btn-primary" @click="doDispatch" :disabled="dispatching || !selectedGroup">
          {{ dispatching ? '发送中...' : '确认发送' }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { bidApi, configApi } from '../api'

const industries = ['政府', '医疗', '金融', '教育', '通信', '企业', '其他']
const regions = ['重庆', '四川', '云南', '贵州', '西藏']

const bids = ref([])
const allBids = ref([]) // 全部数据用于统计
const loading = ref(false)
const total = ref(0)
const pendingTotal = ref(0)
const sentTotal = ref(0)
const page = ref(1)
const pageSize = ref(10)
const selectedBids = ref([])
const searchKeyword = ref('')
const detailVisible = ref(false)
const currentBid = ref(null)
const dispatchVisible = ref(false)
const groups = ref([])
const selectedGroup = ref('')
const dispatching = ref(false)

const filter = reactive({ crm_industries: [], regions: [], status: '', start_date: '', end_date: '' })
const showIndustryDropdown = ref(false)
const showRegionDropdown = ref(false)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)

const isAllSelected = computed(() => {
  return bids.value.length > 0 && selectedBids.value.length === bids.value.length
})

const isIndeterminate = computed(() => {
  return selectedBids.value.length > 0 && selectedBids.value.length < bids.value.length
})

const displayedPages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = page.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    if (current > 3) pages.push('...')
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
      pages.push(i)
    }
    if (current < total - 2) pages.push('...')
    pages.push(total)
  }
  return pages
})

const regionStats = computed(() => {
  const counts = {}
  allBids.value.forEach(b => {
    // 从完整地区中提取省份，如"重庆市渝北区" → "重庆"
    let r = b.region || '其他'
    if (r.includes('重庆')) r = '重庆'
    else if (r.includes('四川')) r = '四川'
    else if (r.includes('云南')) r = '云南'
    else if (r.includes('贵州')) r = '贵州'
    else if (r.includes('西藏')) r = '西藏'
    else if (r.includes('北京')) r = '北京'
    else if (r.includes('上海')) r = '上海'
    else if (r.includes('广东')) r = '广东'
    else if (r.includes('浙江')) r = '浙江'
    else if (r.includes('江苏')) r = '江苏'
    else if (r.includes('湖北')) r = '湖北'
    else if (r.includes('湖南')) r = '湖南'
    else if (r.includes('山东')) r = '山东'
    else if (r.includes('河南')) r = '河南'
    else if (r.includes('陕西')) r = '陕西'
    counts[r] = (counts[r] || 0) + 1
  })
  const maxCount = Math.max(...Object.values(counts), 1)
  return Object.entries(counts).map(([name, count]) => ({
    name,
    count,
    percent: (count / maxCount) * 100
  })).sort((a, b) => b.count - a.count).slice(0, 5)
})

let searchTimer = null

const debounceSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; fetchBids() }, 300)
}

const fetchBids = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value,
      status: filter.status,
      start_date: filter.start_date,
      end_date: filter.end_date,
      // 多选参数用逗号分隔
      crm_industries: filter.crm_industries.join(','),
      regions: filter.regions.join(',')
    }
    // 过滤空值
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    const res = await bidApi.list(params)
    if (res.code === 0) {
      bids.value = res.data
      total.value = res.total
      selectedBids.value = []
    }
    // 获取全部数据用于统计（不带筛选条件）
    const statsRes = await bidApi.list({ page: 1, page_size: 1000 })
    if (statsRes.code === 0) {
      allBids.value = statsRes.data
      pendingTotal.value = statsRes.data.filter(b => b.status === 'pending').length
      sentTotal.value = statsRes.data.filter(b => b.status === 'sent').length
    }
  } finally { loading.value = false }
}

const resetFilter = () => {
  Object.assign(filter, { crm_industries: [], regions: [], status: '', start_date: '', end_date: '' })
  searchKeyword.value = ''
  page.value = 1
  fetchBids()
}

// 行业多选切换
const toggleIndustry = (industry) => {
  if (industry === '') {
    filter.crm_industries = []
  } else {
    const idx = filter.crm_industries.indexOf(industry)
    if (idx > -1) {
      filter.crm_industries.splice(idx, 1)
    } else {
      filter.crm_industries.push(industry)
    }
  }
  showIndustryDropdown.value = false
  fetchBids()
}

// 地区多选切换
const toggleRegion = (region) => {
  if (region === '') {
    filter.regions = []
  } else {
    const idx = filter.regions.indexOf(region)
    if (idx > -1) {
      filter.regions.splice(idx, 1)
    } else {
      filter.regions.push(region)
    }
  }
  showRegionDropdown.value = false
  fetchBids()
}

const isSelected = (bid) => selectedBids.value.some(b => b.id === bid.id)

const toggleSelection = (bid) => {
  if (isSelected(bid)) {
    selectedBids.value = selectedBids.value.filter(b => b.id !== bid.id)
  } else {
    selectedBids.value.push(bid)
  }
}

const toggleAllSelection = () => {
  if (isAllSelected.value) {
    selectedBids.value = []
  } else {
    selectedBids.value = [...bids.value]
  }
}

// 全选当前页
const selectAllPage = () => {
  selectedBids.value = [...bids.value]
}

// 全选所有标讯(应用当前筛选条件)
const selectAllAll = async () => {
  try {
    // 传递当前筛选条件,只获取筛选后的标讯
    const params = {
      page: 1,
      page_size: 1000,
      keyword: searchKeyword.value,
      status: filter.status,
      start_date: filter.start_date,
      end_date: filter.end_date,
      crm_industries: filter.crm_industries.join(','),
      regions: filter.regions.join(',')
    }
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    const res = await bidApi.list(params)
    if (res.code === 0) {
      selectedBids.value = res.data
      ElMessage.success(`已选中 ${selectedBids.value.length} 条标讯`)
    }
  } catch {
    ElMessage.error('获取标讯失败')
  }
}

const clearSelection = () => selectedBids.value = []

const viewBid = (b) => {
  currentBid.value = b
  detailVisible.value = true
}

const deleteBid = async (id) => {
  try {
    await ElMessageBox.confirm('删除该标讯?', '提示', { type: 'warning' })
    await bidApi.delete(id)
    ElMessage.success('已删除')
    fetchBids()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(`删除 ${selectedBids.value.length} 条标讯?`, '提示', { type: 'warning' })
    await bidApi.batchDelete(selectedBids.value.map(b => b.id))
    ElMessage.success('已删除')
    clearSelection()
    fetchBids()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const showDispatch = () => {
  if (!groups.value.length) {
    ElMessage.warning('请先配置钉钉群')
    return
  }
  dispatchVisible.value = true
}

// BidData 标讯数据结构
const BidData = (bid) => ({
  id: bid.id,
  title: bid.title,
  tender_unit: bid.tender_unit || '',
  crm_industry: bid.crm_industry || '',
  budget: bid.budget || '',
  region: bid.region || '',
  publish_date: bid.publish_date || '',
  open_date: bid.open_date || '',
  link: bid.link || ''
})

const doDispatch = async () => {
  if (!selectedGroup.value) {
    ElMessage.warning('请选择钉钉群')
    return
  }
  dispatching.value = true
  try {
    // 转换标讯数据格式
    const bidsData = selectedBids.value.map(BidData)
    await bidApi.dispatch({ bids: bidsData, webhook_url: selectedGroup.value })
    ElMessage.success('发送成功')
    dispatchVisible.value = false
    clearSelection()
    fetchBids()
  } catch { ElMessage.error('发送失败') }
  finally { dispatching.value = false }
}

const formatBudget = (b) => {
  if (!b) return '-'
  try { return parseFloat(b).toLocaleString() + ' 元' } catch { return b }
}

const formatDate = (d) => {
  if (!d) return '-'
  // 只取日期部分 YYYY-MM-DD
  if (d.length >= 10) return d.substring(0, 10)
  return d
}

// 点击外部关闭下拉框
const handleClickOutside = (e) => {
  const target = e.target
  if (!target.closest('.multi-select-wrapper')) {
    showIndustryDropdown.value = false
    showRegionDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  fetchBids()
  configApi.get().then(res => {
    if (res.code === 0) groups.value = res.data.dingtalk_groups || []
  })
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped lang="scss">
@import '@/styles/light-blue.scss';

.bids-page {
  padding: $lb-content-padding;
}

/* 统计栏 - 紧凑布局 */
.stats-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 1rem 1.5rem;
  margin-bottom: $lb-grid-gutter;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--lb-text-primary);
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--lb-text-muted);
  }

  &.pending .stat-value { color: $lb-orange; }
  &.sent .stat-value { color: $lb-green; }
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: $lb-border;
}

.stat-item.regions {
  flex-direction: row;
  align-items: center;
  gap: 12px;
  margin-left: auto;

  .stat-label {
    font-size: 0.875rem;
    color: var(--lb-text-secondary);
  }
}

.region-tags {
  display: flex;
  gap: 8px;
}

.region-tag {
  padding: 4px 10px;
  background: $lb-bg-page;
  border-radius: 6px;
  font-size: 0.75rem;
  color: var(--lb-text-secondary);

  b {
    color: var(--lb-text-primary);
    margin-left: 4px;
  }
}

.region-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.region-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 筛选 */
.filter-widget {
  margin-bottom: $lb-grid-gutter;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.5rem 1rem;
  background: $lb-bg-page;
  border: 1px solid $lb-border;
  border-radius: 8px;
  width: 280px;
  transition: all 0.15s;

  &:focus-within {
    border-color: $lb-primary;
    box-shadow: 0 0 0 3px rgba($lb-primary, .1);
  }

  svg {
    color: $lb-text-muted;
    flex-shrink: 0;
  }

  .lb-input {
    background: transparent;
    border: none;
    padding: 0.5rem 0;
    width: 100%;
  }
}

.filter-selects {
  display: flex;
  gap: 12px;
  align-items: center;

  .lb-select {
    width: 120px;
  }
}

/* 多选下拉框 */
.multi-select-wrapper {
  position: relative;
  width: 140px;
}

.multi-select-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0.5rem 0.75rem;
  background: $lb-bg-widget;
  border: 1px solid $lb-border;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--lb-text-secondary);
  min-height: 36px;

  &:hover {
    border-color: $lb-blue;
  }
}

.multi-select-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.multi-select-count {
  padding: 2px 6px;
  background: $lb-blue;
  color: white;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 600;
}

.multi-select-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: $lb-bg-widget;
  border: 1px solid $lb-border;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  max-height: 300px;
  overflow-y: auto;
}

.multi-select-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.625rem 0.75rem;
  font-size: 0.8125rem;
  color: var(--lb-text-primary);
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: $lb-bg-page;
  }

  .checkbox {
    width: 16px;
    height: 16px;
    border: 2px solid $lb-border;
    border-radius: 4px;
    position: relative;
    transition: all 0.15s;

    &.checked {
      background: $lb-blue;
      border-color: $lb-blue;

      &::after {
        content: '';
        position: absolute;
        left: 5px;
        top: 2px;
        width: 4px;
        height: 8px;
        border: solid white;
        border-width: 0 2px 2px 0;
        transform: rotate(45deg);
      }
    }
  }
}

.date-filter {
  display: flex;
  align-items: center;
  gap: 8px;

  .lb-input-sm {
    width: 130px;
    padding: 0.5rem 0.625rem;
    font-size: 0.8125rem;
    border: 1px solid $lb-border;
    border-radius: 6px;
    background: $lb-bg-widget;
  }
}

.date-label {
  font-size: 0.8125rem;
  color: var(--lb-text-secondary);
  font-weight: 500;
}

.date-separator {
  color: var(--lb-text-muted);
  font-size: 0.8125rem;
}

.filter-buttons {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

/* 批量操作栏 */
.batch-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: rgba($lb-green, .1);
  border: 1px solid rgba($lb-green, .2);
  margin-bottom: 1rem;
}

.batch-info {
  display: flex;
  align-items: center;
  gap: 12px;
  color: $lb-green;
  font-size: 0.875rem;
  font-weight: 600;
}

.btn-xs {
  padding: 4px 8px;
  font-size: 0.75rem;
  border: 1px solid rgba($lb-green, .3);
  background: transparent;
  color: $lb-green;
  border-radius: 4px;
  cursor: pointer;

  &:hover {
    background: rgba($lb-green, .1);
  }
}

.selection-badge {
  width: 36px;
  height: 36px;
  background: $lb-green;
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
}

.batch-actions {
  display: flex;
  gap: 10px;
}

/* 表格 */
.bids-widget {
  margin-bottom: $lb-grid-gutter;
  overflow-x: auto;
}

.bids-table {
  width: 100%;
  table-layout: auto;

  th {
    padding: 0.875rem 0.625rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--lb-text-muted);
    background: transparent;
    border: none;
    white-space: nowrap;
  }

  td {
    padding: 0.875rem 0.625rem;
    font-size: 0.8125rem;
    color: var(--lb-text-secondary);
    border: none;
    border-bottom: 1px solid $lb-border-light;
    vertical-align: middle;
  }

  tr:hover td {
    background: $lb-bg-page;
  }

  tr:last-child td {
    border-bottom: none;
  }

  tr.selected td {
    background: rgba($lb-green, .1);
  }
}

.col-checkbox {
  width: 40px;
  text-align: center !important;

  input {
    display: none;
  }
}

.checkbox-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.checkmark {
  width: 20px;
  height: 20px;
  border: 2px solid $lb-border;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.checkbox-wrapper input:checked + .checkmark {
  background: $lb-green;
  border-color: $lb-green;
}

.checkbox-wrapper input:checked + .checkmark::after {
  content: '';
  width: 6px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
  margin-bottom: 2px;
}

.checkbox-wrapper input:indeterminate + .checkmark {
  background: $lb-green;
  border-color: $lb-green;
}

.checkbox-wrapper input:indeterminate + .checkmark::after {
  content: '';
  width: 10px;
  height: 2px;
  background: white;
  border-radius: 1px;
}

.col-title {
  width: 35%;
  min-width: 180px;
}

.bid-title {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--lb-text-primary);
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s;
  line-height: 1.4;
  font-size: 0.8125rem;

  &:hover {
    color: $lb-blue;
  }
}

.col-industry { width: 60px; }
.col-budget { width: 85px; }
.col-region { width: 90px; }
.col-date { width: 90px; }
.col-status { width: 65px; }
.col-actions { width: 65px; }

.budget-value {
  font-weight: 500;
  color: $lb-orange;
  font-size: 0.8125rem;
}

.btn-sm {
  padding: 6px;

  svg {
    width: 14px;
    height: 14px;
  }
}

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

/* 分页 */
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
}

.pagination-info {
  font-size: 0.875rem;
  color: var(--lb-text-muted);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 6px;

  .btn-sm {
    min-width: 36px;
    height: 36px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.page-ellipsis {
  padding: 0 8px;
  color: var(--lb-text-muted);
}

.page-size-select {
  width: auto;
  margin-left: 8px;
}

/* 详情弹窗 */
.detail-wrapper {
  padding: 8px 0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.detail-badges {
  display: flex;
  gap: 8px;
}

.detail-budget {
  font-size: 1.25rem;
  font-weight: 700;
  color: $lb-orange;
}

.detail-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--lb-text-primary);
  margin: 0 0 24px;
  line-height: 1.5;
}

.detail-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.info-item {
  display: flex;
  gap: 14px;
  padding: 1rem;
  margin-bottom: 0;
}

.info-icon {
  width: 40px;
  height: 40px;
  background: $lb-bg-page;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $lb-blue;
  flex-shrink: 0;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 4px;

  label {
    font-size: 0.75rem;
    color: var(--lb-text-muted);
  }

  span {
    font-size: 0.875rem;
    color: var(--lb-text-primary);
    font-weight: 600;
  }
}

.detail-actions {
  padding-top: 16px;
  border-top: 1px solid $lb-border;
}

/* 发送弹窗 */
.dispatch-wrapper {
  padding: 16px 0;
}

.dispatch-header {
  text-align: center;
  margin-bottom: 20px;
}

.dispatch-icon {
  width: 56px;
  height: 56px;
  background: rgba($lb-green, .15);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $lb-green;
  margin: 0 auto 12px;

  svg {
    width: 28px;
    height: 28px;
  }
}

.dispatch-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--lb-text-primary);
  margin: 0 0 4px;
}

.dispatch-header p {
  font-size: 0.875rem;
  color: var(--lb-text-muted);
  margin: 0;
}

.dispatch-count-box {
  text-align: center;
  padding: 24px;
  background: rgba($lb-green, .1);
  margin-bottom: 20px;
}

.count-number {
  font-size: 2.5rem;
  font-weight: 700;
  color: $lb-green;
  line-height: 1;
}

.count-label {
  font-size: 0.875rem;
  color: var(--lb-text-muted);
  margin-top: 4px;
}

.dispatch-form {
  label {
    display: block;
    margin-bottom: 8px;
  }
}

/* 动画 */
.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
}
.slide-enter-from, .slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 1200px) {
  .stats-bar {
    flex-wrap: wrap;
  }

  .stat-item.regions {
    margin-left: 0;
    width: 100%;
    justify-content: flex-start;
    margin-top: 12px;
  }
}

@media (max-width: 768px) {
  .stats-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .stat-divider {
    display: none;
  }

  .search-row {
    flex-direction: column;
    align-items: stretch;
  }

  .search-box {
    width: 100%;
  }

  .filter-selects {
    flex-wrap: wrap;
  }

  .filter-buttons {
    margin-left: 0;
    margin-top: 12px;
  }

  .detail-info-grid {
    grid-template-columns: 1fr;
  }
}
</style>