package middleware

import (
	"encoding/base64"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// BasicAuth 中间件
func BasicAuth(username, password string) gin.HandlerFunc {
	return func(c *gin.Context) {
		auth := c.GetHeader("Authorization")
		if auth == "" {
			c.Header("WWW-Authenticate", `Basic realm="BidPool"`)
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"code":    -1,
				"message": "需要认证",
			})
			return
		}

		// 解析 Basic Auth
		if !strings.HasPrefix(auth, "Basic ") {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"code":    -1,
				"message": "认证格式错误",
			})
			return
		}

		// 解码
		payload, err := base64.StdEncoding.DecodeString(auth[6:])
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"code":    -1,
				"message": "认证解码失败",
			})
			return
		}

		// 验证用户名密码
		pair := strings.SplitN(string(payload), ":", 2)
		if len(pair) != 2 || pair[0] != username || pair[1] != password {
			c.Header("WWW-Authenticate", `Basic realm="BidPool"`)
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"code":    -1,
				"message": "用户名或密码错误",
			})
			return
		}

		c.Next()
	}
}
