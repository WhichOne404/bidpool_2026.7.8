package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/zhonghai/bidpool-go/internal/model"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type BidHandler struct {
	db *gorm.DB
}

func NewBidHandler(db *gorm.DB) *BidHandler {
	return &BidHandler{db: db}
}

// ListBids 获取标讯列表
func (h *BidHandler) ListBids(c *gin.Context) {
	var bids []model.BidInfo

	// 查询参数
	status := c.Query("status")
	source := c.Query("source")
	crmIndustries := c.Query("crm_industries") // 支持多选，逗号分隔
	regions := c.Query("regions")              // 支持多选，逗号分隔
	startDate := c.Query("start_date")
	endDate := c.Query("end_date")
	page := parseInt(c.DefaultQuery("page", "1"))
	pageSize := parseInt(c.DefaultQuery("page_size", "10"))

	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 1000 {
		pageSize = 10
	}

	query := h.db.Model(&model.BidInfo{})
	if status != "" {
		query = query.Where("status = ?", status)
	}
	if source != "" {
		query = query.Where("source = ?", source)
	}
	// 行业多选筛选（OR条件）
	if crmIndustries != "" {
		industries := strings.Split(crmIndustries, ",")
		if len(industries) > 0 {
			conditions := make([]string, len(industries))
			args := make([]interface{}, len(industries))
			for i, ind := range industries {
				conditions[i] = "crm_industry = ?"
				args[i] = strings.TrimSpace(ind)
			}
			query = query.Where(strings.Join(conditions, " OR "), args...)
		}
	}
	// 地区多选筛选（OR条件）
	if regions != "" {
		regionList := strings.Split(regions, ",")
		if len(regionList) > 0 {
			conditions := make([]string, len(regionList))
			args := make([]interface{}, len(regionList))
			for i, r := range regionList {
				conditions[i] = "region LIKE ?"
				args[i] = "%" + strings.TrimSpace(r) + "%"
			}
			query = query.Where(strings.Join(conditions, " OR "), args...)
		}
	}
	if startDate != "" {
		query = query.Where("publish_date >= ?", startDate)
	}
	if endDate != "" {
		query = query.Where("publish_date <= ?", endDate+" 23:59:59")
	}

	// 获取总数
	var total int64
	query.Count(&total)

	// 分页查询
	offset := (page - 1) * pageSize
	query.Order("created_at desc").Offset(offset).Limit(pageSize).Find(&bids)

	c.JSON(http.StatusOK, gin.H{
		"code":      0,
		"data":      bids,
		"total":     total,
		"page":      page,
		"page_size": pageSize,
	})
}

// GetBid 获取标讯详情
func (h *BidHandler) GetBid(c *gin.Context) {
	id := c.Param("id")
	var bid model.BidInfo

	if err := h.db.First(&bid, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"code":    -1,
			"message": "标讯不存在",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": bid,
	})
}

// DeleteBid 删除标讯
func (h *BidHandler) DeleteBid(c *gin.Context) {
	id := c.Param("id")

	if err := h.db.Delete(&model.BidInfo{}, "id = ?", id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"code":    -1,
			"message": "删除失败",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"code":    0,
		"message": "删除成功",
	})
}

// BatchDeleteRequest 批量删除请求
type BatchDeleteRequest struct {
	IDs []string `json:"ids"`
}

// BatchDelete 批量删除标讯
func (h *BidHandler) BatchDelete(c *gin.Context) {
	var req BatchDeleteRequest
	if err := c.ShouldBindJSON(&req); err != nil || len(req.IDs) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "参数错误"})
		return
	}

	if err := h.db.Delete(&model.BidInfo{}, "id IN ?", req.IDs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "删除失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"code": 0, "message": "批量删除成功"})
}

// DispatchRequest 分发请求
type DispatchRequest struct {
	Bids       []BidData `json:"bids"`
	WebhookURL string    `json:"webhook_url"`
	Format     string    `json:"format"`
}

// BidData 标讯数据
type BidData struct {
	ID          string `json:"id"`
	Title       string `json:"title"`
	TenderUnit  string `json:"tender_unit"`
	CRMIndustry string `json:"crm_industry"`
	Budget      string `json:"budget"`
	Region      string `json:"region"`
	PublishDate string `json:"publish_date"`
	OpenDate    string `json:"open_date"`
	Link        string `json:"link"`
}

// Dispatch 分发标讯到钉钉
func (h *BidHandler) Dispatch(c *gin.Context) {
	var req DispatchRequest
	if err := c.ShouldBindJSON(&req); err != nil || len(req.Bids) == 0 || req.WebhookURL == "" {
		c.JSON(http.StatusBadRequest, gin.H{"code": -1, "message": "参数错误"})
		return
	}

	// 构建消息内容
	var content string
	if req.Format == "detail" {
		content = buildDetailMessage(req.Bids)
	} else {
		content = buildSimpleMessage(req.Bids)
	}

	// 发送到钉钉
	payload := map[string]interface{}{
		"msgtype": "markdown",
		"markdown": map[string]string{
			"title": "标讯推送",
			"text":  content,
		},
	}

	jsonData, _ := json.Marshal(payload)
	resp, err := http.Post(req.WebhookURL, "application/json", bytes.NewReader(jsonData))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"code": -1, "message": "发送失败: " + err.Error()})
		return
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if result["errcode"] != nil && result["errcode"].(float64) == 0 {
		// 更新标讯状态为已发送
		ids := make([]string, len(req.Bids))
		for i, b := range req.Bids {
			ids[i] = b.ID
		}
		h.db.Model(&model.BidInfo{}).Where("id IN ?", ids).Update("status", "sent")

		c.JSON(http.StatusOK, gin.H{"code": 0, "message": "发送成功"})
	} else {
		errMsg := "未知错误"
		if result["errmsg"] != nil {
			errMsg = result["errmsg"].(string)
		}
		c.JSON(http.StatusOK, gin.H{"code": -1, "message": "钉钉返回错误: " + errMsg})
	}
}

func buildSimpleMessage(bids []BidData) string {
	var content string
	content += "## 📋 标讯推送\n\n"
	content += fmt.Sprintf("共推送 **%d** 条标讯\n\n", len(bids))
	content += "---\n\n"

	for i, bid := range bids {
		num := i + 1
		// 标题和序号
		content += fmt.Sprintf("**%d. %s**\n\n", num, bid.Title)

		// 预算（必填）
		budget := bid.Budget
		if budget == "" || budget == "0" || budget == "0.0" {
			budget = "未公开"
		}
		content += fmt.Sprintf("💰 **预算**: %s\n", budget)

		// 开标时间（必填）
		openDate := bid.OpenDate
		if openDate == "" {
			openDate = "暂无"
		} else if len(openDate) > 10 {
			openDate = openDate[:10] // 只显示日期部分
		}
		content += fmt.Sprintf("⏰ **开标时间**: %s\n", openDate)

		// 招标单位（可选）
		if bid.TenderUnit != "" {
			content += fmt.Sprintf("🏢 **招标单位**: %s\n", bid.TenderUnit)
		}

		// 地区（可选）
		if bid.Region != "" {
			content += fmt.Sprintf("📍 **地区**: %s\n", bid.Region)
		}

		// 链接（必填）
		content += fmt.Sprintf("🔗 [查看详情](%s)\n\n", bid.Link)
	}

	return content
}

func buildDetailMessage(bids []BidData) string {
	var content string
	content += "## 📋 标讯推送\n\n"
	content += fmt.Sprintf("共推送 **%d** 条标讯\n\n", len(bids))

	for i, bid := range bids {
		num := i + 1
		content += "---\n\n"
		// 标题和序号
		content += fmt.Sprintf("### %d. %s\n\n", num, bid.Title)

		// 预算（必填）
		budget := bid.Budget
		if budget == "" || budget == "0" || budget == "0.0" {
			budget = "未公开"
		}
		content += fmt.Sprintf("💰 **预算**: %s\n", budget)

		// 开标时间（必填）
		openDate := bid.OpenDate
		if openDate == "" {
			openDate = "暂无"
		} else if len(openDate) > 10 {
			openDate = openDate[:10]
		}
		content += fmt.Sprintf("⏰ **开标时间**: %s\n", openDate)

		// 招标单位
		tenderUnit := bid.TenderUnit
		if tenderUnit == "" {
			tenderUnit = "暂无"
		}
		content += fmt.Sprintf("🏢 **招标单位**: %s\n", tenderUnit)

		// 行业
		industry := bid.CRMIndustry
		if industry == "" {
			industry = "其他"
		}
		content += fmt.Sprintf("🏭 **行业**: %s\n", industry)

		// 地区
		region := bid.Region
		if region == "" {
			region = "暂无"
		}
		content += fmt.Sprintf("📍 **地区**: %s\n", region)

		// 链接（必填）
		content += fmt.Sprintf("🔗 [查看详情](%s)\n\n", bid.Link)
	}
	return content
}

func parseInt(s string) int {
	var i int
	for _, c := range s {
		if c >= '0' && c <= '9' {
			i = i*10 + int(c-'0')
		}
	}
	return i
}