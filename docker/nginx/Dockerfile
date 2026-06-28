# Build stage - 构建前端
FROM node:20-alpine AS builder

WORKDIR /app

COPY bidpool-web/package*.json ./
RUN npm ci

COPY bidpool-web/ ./

RUN npm run build

# Runtime stage
FROM nginx:alpine

# 复制 nginx 配置
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# 复制前端构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 添加健康检查
RUN apk add --no-cache curl

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]